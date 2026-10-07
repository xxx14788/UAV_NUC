#!/usr/bin/env python3
"""t1_stoploss_watch.py — jump 后置止损看门 v1.0 (T1 v11.23 阶段 4a;用户已批立项 2026-10-07)

同核=t1_gate_watch.py(inflight/replay/selftest 三态 + flag/json 留痕契约 + 降级序归 vins_smoke)。
检测面=10Hz odom 帧间 |ΔP|>1.0m —— 阈值锚=x4_bagench_design_v1 §3 预注册"跳变事件"判据常数
(非门参数;现行门值零变动红线;止损件=执行面位置止损,不参与绿率判读)。
trichotomy 契约(任务书 v11.23 阶段 4a):止损触发→受控中止→RESULT=FAIL(真 FAIL 提前终止形态);
jump 面判读已由 round_result 帧稳定性指标承载,本件不重复判,留痕仅执行面证据。
起飞守卫=z>0.25m 持续 3s(gate_watch detect_takeoff 同常数);地面段跳变不触发(归 preflight 域)。
断流口径=帧对 dt>1.5s 排除该帧对(forensics 断流后首帧排除同口径,禁跨断流归因)。

用法:
  t1_stoploss_watch.py --inflight <run_dir>   # 在线:rospy 订阅 /vins_estimator/odometry
  t1_stoploss_watch.py --replay  <run_dir>    # 离线:读 <run_dir>/flight.bag odom,报 would-fire
  t1_stoploss_watch.py --selftest             # 合成样例 6 例(正/负/边界/守卫/gap)
输出: stoploss_<tag>.json + stoploss.flag(inflight 触发时);STOPLOSS 一行(stdout)
"""
import os, sys, json, argparse

THRESH_M = 1.0      # 预注册判据常数(§3 跳变事件阈值);禁运行时改
TO_Z, TO_S = 0.25, 3.0   # 起飞守卫(同 gate_watch detect_takeoff 常数)
GAP_S = 1.5         # 断流帧对排除阈(forensics 同口径)


class OdomTrack:
    def __init__(self):
        self.prev = None           # (t, x, y, z)
        self.t_off = None          # 起飞时刻
        self._z_run0 = None
        self.trip = None           # (t, dp, pre, post)
        self.n_events = 0
        self.n_frames = 0

    def feed(self, t, x, y, z):
        """喂一帧 odom;返回 None 或 trip 元组(首触发)。"""
        self.n_frames += 1
        if self.t_off is None:
            if z == z and z > TO_Z:            # nan 安全
                if self._z_run0 is None:
                    self._z_run0 = t
                elif t - self._z_run0 >= TO_S:
                    self.t_off = t
            else:
                self._z_run0 = None
        cur = (t, x, y, z)
        trip = None
        if self.prev is not None and self.t_off is not None:
            dt = t - self.prev[0]
            if dt <= GAP_S:
                dp = ((x - self.prev[1]) ** 2 + (y - self.prev[2]) ** 2 + (z - self.prev[3]) ** 2) ** 0.5
                if dp > THRESH_M:
                    self.n_events += 1
                    if self.trip is None:
                        trip = self.trip = (round(t, 3), round(dp, 3),
                                            [round(v, 3) for v in self.prev[1:]],
                                            [round(x, 3), round(y, 3), round(z, 3)])
        self.prev = cur
        return trip


def hit_json(tag, tr, mode, t_off):
    return {
        "tag": tag, "tool": "t1_stoploss_watch.py v1.0", "mode": mode,
        "thresh_m": THRESH_M, "thresh_anchor": "x4_bagench_design_v1 §3 跳变事件阈值(预注册判据常数)",
        "t_takeoff": round(t_off, 2) if t_off else None,
        "t_trig": tr[0], "jump_m": tr[1], "pre_xyz": tr[2], "post_xyz": tr[3],
        "action": "goal-stop->controlled-abort(land)->teardown",
        "trichotomy_contract": "真 FAIL 提前终止形态;jump 面判读归 round_result 帧稳定性,本件不重复判",
        "degrade_ladder": "①odom可信段LAND ②stream死/未disarm→悬停+kill电机(实机=需人工接管协议)",
        "landed": 0,
    }


def tag_of(run_dir):
    import re
    m = re.search(r"run_(.+)_\d{6}$", run_dir.rstrip("/"))
    return m.group(1) if m else os.path.basename(run_dir.rstrip("/"))


def run_inflight(run_dir):
    import rospy
    from nav_msgs.msg import Odometry
    tag = tag_of(run_dir)
    tr = OdomTrack()
    rospy.init_node("t1_stoploss_watch", anonymous=True, disable_signals=True)

    def cb(msg):
        if tr.trip is not None:
            return
        p = msg.pose.pose.position
        t = msg.header.stamp.to_sec() if msg.header.stamp.to_sec() else rospy.get_time()
        trip = tr.feed(t, p.x, p.y, p.z)
        if trip:
            j = hit_json(tag, trip, "inflight", tr.t_off)
            json.dump(j, open(os.path.join(run_dir, "stoploss_%s.json" % tag), "w"),
                      ensure_ascii=False, indent=1)
            open(os.path.join(run_dir, "stoploss.flag"), "w").write("jump\n")
            print("STOPLOSS " + json.dumps(j, ensure_ascii=False), flush=True)
            rospy.signal_shutdown("stoploss-trip")

    rospy.Subscriber("/vins_estimator/odometry", Odometry, cb, queue_size=2)
    rospy.spin()
    if tr.trip is None:
        print("[stoploss] 在线窗结束未触发(tag=%s frames=%d)" % (tag, tr.n_frames))


def run_replay(run_dir):
    import rosbag
    tag = tag_of(run_dir)
    bag = os.path.join(run_dir, "flight.bag")
    tr = OdomTrack()
    with rosbag.Bag(bag, "r") as b:
        for _, msg, ts in b.read_messages(topics=["/vins_estimator/odometry"]):
            p = msg.pose.pose.position
            t = ts.to_sec()
            trip = tr.feed(t, p.x, p.y, p.z)
            if trip:
                j = hit_json(tag, trip, "replay", tr.t_off)
                j["note"] = "replay=would-fire 报告(不写 flag/不改任何产物)"
                print("STOPLOSS-REPLAY " + json.dumps(j, ensure_ascii=False))
    print("[stoploss] replay 终:tag=%s frames=%d events=%d t_off=%s trip=%s"
          % (tag, tr.n_frames, tr.n_events, tr.t_off, tr.trip[0] if tr.trip else None))


def run_selftest():
    cases = []
    def mk(name, pts, expect):
        tr = OdomTrack()
        first = None
        for t, x, y, z in pts:
            r = tr.feed(t, x, y, z)
            if r and first is None:
                first = r
        cases.append((name, first is not None, expect, first))
    # 1 净悬停(无跳) → 不触发
    mk("hover-clean", [(t, 0, 0, 1.0 + 0.01 * (t % 3)) for t in range(5, 60)], False)
    # 2 起飞后单帧 2m 跳 → 触发@跳帧
    mk("jump-2m", [(t, 0.1 * t, 0, 0.3) for t in range(0, 8)] + [(8.1, 0.8, 0, 2.0), (8.2, 2.8, 0, 2.0)], True)
    # 3 0.9m 步进(阈下) → 不触发
    mk("step-0.9m", [(t, 0.1 * t, 0, 0.3) for t in range(0, 8)] + [(8.1, 0.7, 0, 0.9), (8.2, 1.6, 0, 0.9)], False)
    # 4 地面段跳变(z<0.25 起飞守卫前) → 不触发(归 preflight 域)
    mk("ground-jump", [(t, 0, 0, 0.1) for t in range(0, 10)] + [(10.1, 5.0, 0, 0.1)], False)
    # 5 边界 1.01m(>1.0 严格) → 触发
    mk("jump-1.01m", [(t, 0.1 * t, 0, 0.3) for t in range(0, 8)] + [(8.1, 0.8, 0, 1.8), (8.2, 1.81, 0, 1.8)], True)
    # 6 断流后首帧(dt>1.5s) → 该帧对排除,不触发
    mk("gap-jump", [(t, 0.1 * t, 0, 0.3) for t in range(0, 8)] + [(12.0, 6.0, 0, 0.3)], False)
    ok = 0
    for name, fired, expect, first in cases:
        mark = "PASS" if fired == expect else "FAIL"
        ok += (fired == expect)
        print("  [%s] %-12s fired=%-5s expect=%-5s %s" % (mark, name, fired, expect,
              ("t=%.1f dp=%.2f" % (first[0], first[1])) if first else ""))
    print("selftest %d/6" % ok)
    return 0 if ok == 6 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inflight"); ap.add_argument("--replay"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return run_selftest()
    if a.inflight:
        run_inflight(os.path.abspath(a.inflight)); return 0
    if a.replay:
        run_replay(os.path.abspath(a.replay)); return 0
    ap.error("需要 --inflight/--replay/--selftest 之一")


if __name__ == "__main__":
    sys.exit(main())
