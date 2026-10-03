#!/usr/bin/env python3
# t1_r3x_probe.py — T1-R3x three-face online probe (v11.0 unit 6; design:
# t1_evidence/v10_2026-10-02/u25_r3x_probe_design.md)
# Faces:
#   imu_jit   (1) /mavros/imu/data_raw arrival-interval jitter, wall-clock
#                monotonic diff + (5) glitch_align spike counters |acc|>50
#   stampage (2a) /vins_estimator/{imu_propagate,odometry} stamp age at receive
#   rtf       (3) /clock vs wall clock lag + windowed RTF
#   cpu       (4) /proc/<vins_pid> stat/statm differential 1 Hz
# Output: jsonl, one line per face per 5s window, dual clock stamps.
# Overhead budget (prereg §4): ring buffers, no per-msg allocation steady-state;
# CPU<0.5% core, RAM<1MB, disk<5MB/h. If budget is exceeded the probe is void.
# Usage: t1_r3x_probe.py OUT.jsonl [--mode online|replay] [--vins-pid N]

import argparse
import json
import os
import sys
import time

try:
    import rospy
    import std_msgs.msg
    from sensor_msgs.msg import Imu
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
except ImportError:
    print("ROS python env missing; source /opt/ros/noetic/setup.bash", file=sys.stderr)
    sys.exit(1)

WIN = 5.0          # emit interval (s, wall)
RING = 4096        # ring capacity per stream (RAM budget anchor)
IMU_HZ_EXPECT = 200.0
SPIKE_MS2 = 50.0   # face-5 glitch threshold (m/s^2), prereg §7
HIST_EDGES = [0, 2, 4, 8, 16, 32, 64, 10 ** 9]  # ms buckets


class Ring:
    """fixed-capacity float ring (no allocation on push steady-state)"""

    def __init__(self, cap):
        self.buf = [0.0] * cap
        self.cap = cap
        self.n = 0
        self.i = 0

    def push(self, v):
        self.buf[self.i] = v
        self.i = (self.i + 1) % self.cap
        if self.n < self.cap:
            self.n += 1

    def sorted_vals(self):
        return sorted(self.buf[: self.n])

    def clear(self):
        self.n = 0
        self.i = 0


def pct(sorted_vals, q):
    if not sorted_vals:
        return None
    k = min(int(q * len(sorted_vals)), len(sorted_vals) - 1)
    return sorted_vals[k]


class ProcSampler:
    def __init__(self, pid):
        self.pid = pid
        self.last = None  # (t, utime+stime, rss_pages)
        self.hz = os.sysconf("SC_CLK_TCK")

    def sample(self):
        if not self.pid:
            return None
        try:
            with open("/proc/%d/stat" % self.pid, "rb") as f:
                parts = f.read().split()
            utime, stime = int(parts[13]), int(parts[14])
            rss = int(parts[23])
            t = time.monotonic()
            cur = (t, utime + stime, rss)
            out = None
            if self.last:
                dt = cur[0] - self.last[0]
                if dt > 0.01:
                    cpu_pct = 100.0 * (cur[1] - self.last[1]) / self.hz / dt
                    out = {"pid": self.pid, "cpu_pct": round(cpu_pct, 2),
                           "rss_mb": round(cur[2] * os.sysconf("SC_PAGE_SIZE") / 1e6, 1)}
            self.last = cur
            return out
        except (OSError, ValueError, IndexError):
            return None


def find_vins_pid():
    try:
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open("/proc/%s/cmdline" % d, "rb") as f:
                    cmd = f.read().decode("utf-8", "replace")
            except OSError:
                continue
            if "vins_node" in cmd:
                return int(d)
    except OSError:
        pass
    return None


class Probe:
    def __init__(self, out_path, mode):
        self.out = open(out_path, "a", buffering=1)
        self.mode = mode
        self.imu_iv = Ring(RING)        # face 1 intervals ms
        self.imu_last_mono = None
        self.imu_n = 0
        self.drop_n = 0
        self.p50_ref = None
        # face 5
        self.spike_n = 0
        self.spike_max = 0.0
        # face 2a
        self.age = {"imu_propagate": Ring(RING), "odometry": Ring(RING)}
        self.age_n = {"imu_propagate": 0, "odometry": 0}
        # face 3
        self.clock_wall0 = None
        self.clock_sim0 = None
        self.sim_lag = None
        self.rtf_win = []  # (wall_mono, sim_t)
        # face 4
        self.proc = None
        self.last_emit = time.monotonic()

    def emit(self, face, obj):
        rec = {"face": face, "t_wall": time.time(),
               "t_ros": (rospy.get_time() if rospy.get_rostime_initialized() else 0.0),
               "mode": self.mode}
        rec.update(obj)
        self.out.write(json.dumps(rec, separators=(",", ":")) + "\n")

    def on_imu(self, msg):
        mono = time.monotonic()
        self.imu_n += 1
        if self.imu_last_mono is not None:
            iv_ms = (mono - self.imu_last_mono) * 1000.0
            self.imu_iv.push(iv_ms)
            if self.p50_ref and iv_ms > 3.0 * self.p50_ref:
                self.drop_n += 1
        self.imu_last_mono = mono
        # face 5: |acc| norm (linear accel only; gravity-compensated stream)
        a = msg.linear_acceleration
        m2 = a.x * a.x + a.y * a.y + a.z * a.z
        if m2 > SPIKE_MS2 * SPIKE_MS2:
            self.spike_n += 1
            if m2 > self.spike_max:
                self.spike_max = m2

    def on_odom_stream(self, name, msg):
        wall = rospy.get_time() if not rospy.get_param("/use_sim_time", False) else None
        # stamp age = receive-time minus header stamp; in sim-time domain both
        # stamps are sim-domain; in wall domain both wall (replay: mixed, tagged)
        now_t = time.time()
        st = msg.header.stamp.to_sec()
        now_ros = rospy.get_time()
        age_ms = (now_ros - st) * 1000.0 if now_ros > 0 else None
        if age_ms is not None and age_ms >= 0:
            self.age[name].push(age_ms)
            self.age_n[name] += 1
        _ = wall, now_t  # wall kept for future mixed-domain analysis

    def on_clock(self, msg):
        mono = time.monotonic()
        sim = msg.clock.to_sec()
        if self.clock_sim0 is None:
            self.clock_sim0 = sim
            self.clock_wall0 = mono
        self.sim_lag = mono - self.clock_wall0 - (sim - self.clock_sim0)
        self.rtf_win.append((mono, sim))
        if len(self.rtf_win) > 4000:
            del self.rtf_win[:2000]

    def maybe_emit(self):
        now = time.monotonic()
        if now - self.last_emit < WIN:
            return
        self.last_emit = now
        # face 1 + 5
        vals = self.imu_iv.sorted_vals()
        if vals:
            hist = [0] * (len(HIST_EDGES) - 1)
            for v in vals:
                for k in range(len(HIST_EDGES) - 1):
                    if HIST_EDGES[k] <= v < HIST_EDGES[k + 1]:
                        hist[k] += 1
                        break
            p50 = pct(vals, 0.50)
            self.emit("imu_jit", {
                "n": self.imu_n, "p50_ms": round(p50, 3),
                "p95_ms": round(pct(vals, 0.95), 3), "p99_ms": round(pct(vals, 0.99), 3),
                "max_ms": round(vals[-1], 3), "drop_n": self.drop_n,
                "hist": hist,
                "spike_n": self.spike_n,
                "spike_max_ms2": round(self.spike_max ** 0.5, 2)})
            self.p50_ref = p50
        self.imu_n = 0
        self.drop_n = 0
        self.spike_n = 0
        self.spike_max = 0.0
        # face 2a
        for name in ("imu_propagate", "odometry"):
            vals = self.age[name].sorted_vals()
            if vals:
                self.emit("stampage", {"stream": name, "n": self.age_n[name],
                                       "p50_ms": round(pct(vals, 0.50), 3),
                                       "p95_ms": round(pct(vals, 0.95), 3),
                                       "p99_ms": round(pct(vals, 0.99), 3),
                                       "max_ms": round(vals[-1], 3)})
            self.age[name].clear()
            self.age_n[name] = 0
        # face 3
        if self.rtf_win and len(self.rtf_win) >= 2:
            w0, w1 = self.rtf_win[0], self.rtf_win[-1]
            dtw = w1[0] - w0[0]
            dts = w1[1] - w0[1]
            rtf_all = dts / dtw if dtw > 0 else None
            rtf1 = None
            if len(self.rtf_win) >= 2:
                t1 = self.rtf_win[-1]
                for j in range(len(self.rtf_win) - 1, -1, -1):
                    if t1[0] - self.rtf_win[j][0] >= 1.0:
                        dw = t1[0] - self.rtf_win[j][0]
                        ds = t1[1] - self.rtf_win[j][1]
                        rtf1 = ds / dw if dw > 0 else None
                        break
            self.emit("rtf", {"sim_lag_s": round(self.sim_lag or 0.0, 3),
                              "rtf_1s": round(rtf1, 4) if rtf1 else None,
                              "rtf_win": round(rtf_all, 4) if rtf_all else None,
                              "clock_n": len(self.rtf_win)})
        # face 4
        if self.proc:
            c = self.proc.sample()
            if c:
                self.emit("cpu", c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="/tmp/r3x_probe.jsonl")
    ap.add_argument("--mode", default="online", choices=["online", "replay"])
    ap.add_argument("--vins-pid", type=int, default=0)
    args = ap.parse_args()

    rospy.init_node("t1_r3x_probe_%d" % os.getpid(), anonymous=True, disable_signals=True)
    probe = Probe(args.out, args.mode)
    pid = args.vins_pid or find_vins_pid()
    probe.proc = ProcSampler(pid) if pid else None
    if pid:
        probe.emit("meta", {"vins_pid": pid, "imu_expected_hz": IMU_HZ_EXPECT})

    rospy.Subscriber("/mavros/imu/data_raw", Imu, probe.on_imu, queue_size=2)
    rospy.Subscriber("/vins_estimator/imu_propagate", Odometry,
                     lambda m: probe.on_odom_stream("imu_propagate", m), queue_size=2)
    rospy.Subscriber("/vins_estimator/odometry", Odometry,
                     lambda m: probe.on_odom_stream("odometry", m), queue_size=2)
    rospy.Subscriber("/clock", Clock, probe.on_clock, queue_size=2)

    rate = rospy.Rate(5)
    while not rospy.is_shutdown():
        probe.maybe_emit()
        rate.tick()
    probe.out.close()


if __name__ == "__main__":
    main()
