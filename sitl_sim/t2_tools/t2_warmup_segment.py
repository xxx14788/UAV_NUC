#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t2_warmup_segment.py -- T2 unit-1b item-3: pre-takeoff bias warmup segment (v1.0)

Taskbook: 2026-10-07_T2_vins_quality_v10.4.md unit 1b (bias-route item #3,
priority item). Design prereg: staging/INPUTFACE/1b_bias_route/
1b_bias_three_prereg_v1.md section 2 -- parameters FROZEN there:

  duration 8s
  yaw   +-30 deg  sine 0.25 Hz
  pitch/roll +-10 deg sine 0.25 Hz
  x/y   +-0.3 m   sine 0.20 Hz, z hold
  executes at 0.5 m fixed height (SITL), then hands over to mission

Harness-level: publishes parameterized goal stream only. ZERO stack changes
(no VINS/mavros/px4ctrl code touched). Attitude goals vs position goals:
this generator emits POSITION goals (x/y sine + z hold); attitude excitation
emerges from tracking. (The frozen prereg lists attitude amplitudes as the
OBSERVED excitation targets, not separate attitude commands.)

Convergence metric (frozen): warmup-segment-end d(Ba)/dt and d(Bg)/dt =
mean |rate| over last 2s < 20% of first 2s -> "converged". Bias source =
VINS-internal Ba/Bg (from vins log T2diag P/V lines or estimator output;
adapter point below).

Adaptation points for 3090 (marked ADAPT):
  --goal-topic   (default /move_base_simple/goal; px4ctrl chains vary)
  --goal-type    geometry_msgs/PoseStamped | other
  --hz           goal rate (default 10)
  --bias-log     vins log path or live subscriber for convergence metric
ASCII logs only. py_compile is the only local check.
"""

import argparse
import math
import sys
import time

FROZEN = {
    "duration_s": 8.0,
    "yaw_amp_deg": 30.0,
    "att_hz": 0.25,
    "xy_amp_m": 0.3,
    "xy_hz": 0.20,
    "z_hold_m": 0.5,
}


def warmup_goal(t):
    """Position goal at warmup time t (seconds since segment start).
    Frozen parameterization; returns (x, y, z, yaw_rad)."""
    x = FROZEN["xy_amp_m"] * math.sin(2 * math.pi * FROZEN["xy_hz"] * t)
    y = FROZEN["xy_amp_m"] * math.sin(2 * math.pi * FROZEN["xy_hz"] * t + math.pi / 2)
    z = FROZEN["z_hold_m"]
    yaw = math.radians(FROZEN["yaw_amp_deg"]) * math.sin(
        2 * math.pi * FROZEN["att_hz"] * t)
    return x, y, z, yaw


def selftest():
    """Verify frozen parameter envelope: amplitudes and rates within prereg."""
    import numpy as np  # only for selftest; core math is stdlib

    ts = [i / 100.0 for i in range(int(FROZEN["duration_s"] * 100) + 1)]
    xs, ys, yaws = [], [], []
    for t in ts:
        x, y, z, yaw = warmup_goal(t)
        xs.append(x)
        ys.append(y)
        yaws.append(yaw)
    checks = [
        ("xy amp <= 0.3m", max(abs(min(xs)), abs(max(xs))) <= FROZEN["xy_amp_m"] + 1e-9),
        ("z hold = 0.5", all(
            abs(warmup_goal(t)[2] - FROZEN["z_hold_m"]) < 1e-9 for t in ts)),
        ("yaw amp <= 30deg", math.degrees(max(abs(min(yaws)), abs(max(yaws))))
         <= FROZEN["yaw_amp_deg"] + 1e-6),
        ("peak speed < 1 m/s", max(
            math.hypot(
                2 * math.pi * FROZEN["xy_amp_m"] * FROZEN["xy_hz"],
                2 * math.pi * FROZEN["xy_amp_m"] * FROZEN["xy_hz"]) for _ in [0]) < 1.0),
    ]
    ok = True
    for name, res in checks:
        print("  %-22s %s" % (name, "PASS" if res else "FAIL"))
        ok = ok and res
    return ok


def run_publish(args):
    import rospy  # ADAPT: goal type per harness chain
    from geometry_msgs.msg import PoseStamped

    pub = rospy.Publisher(args.goal_topic, PoseStamped, queue_size=10)
    rospy.init_node("t2_warmup_segment", anonymous=True)
    rate = rospy.Rate(args.hz)
    t0 = time.time()
    n = 0
    while not rospy.is_shutdown():
        t = time.time() - t0
        if t > FROZEN["duration_s"]:
            break
        x, y, z, yaw = warmup_goal(t)
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = args.frame_id
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        msg.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.orientation.w = math.cos(yaw / 2.0)
        pub.publish(msg)
        n += 1
        rate.sleep()
    print("[done] warmup segment published %d goals over %.1fs" % (n, FROZEN["duration_s"]))
    return 0


def convergence_metric(bias_series):
    """bias_series: list of (t, ba_vec, bg_vec). Frozen metric:
    mean |rate| last 2s < 20% of first 2s -> converged."""
    if len(bias_series) < 4:
        return None, "insufficient samples"
    import math as m

    def seg_rate(seg):
        if len(seg) < 2:
            return None
        rates = []
        for (t0, ba0, bg0), (t1, ba1, bg1) in zip(seg, seg[1:]):
            dt = t1 - t0
            if dt <= 0:
                continue
            d = sum(abs(b - a) for a, b in zip(ba0, ba1)) + \
                sum(abs(b - a) for a, b in zip(bg0, bg1))
            rates.append(d / dt)
        return sum(rates) / len(rates) if rates else None

    t_end = bias_series[-1][0]
    first = [s for s in bias_series if s[0] - bias_series[0][0] <= 2.0]
    last = [s for s in bias_series if t_end - s[0] <= 2.0]
    r_first, r_last = seg_rate(first), seg_rate(last)
    if r_first is None or r_last is None:
        return None, "segment degenerate"
    converged = r_last < 0.2 * r_first
    return converged, {"rate_first2s": r_first, "rate_last2s": r_last,
                       "ratio": r_last / r_first if r_first else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--publish", action="store_true",
                    help="actually publish goals (needs live ROS)")
    ap.add_argument("--goal-topic", default="/move_base_simple/goal")  # ADAPT
    ap.add_argument("--frame-id", default="world")
    ap.add_argument("--hz", type=float, default=10.0)
    ap.add_argument("--bias-log", default=None)  # ADAPT: convergence source
    args = ap.parse_args()

    if args.selftest:
        print("[selftest] frozen parameter envelope:")
        return 0 if selftest() else 1
    if args.publish:
        return run_publish(args)
    print("[info] nothing to do: --selftest or --publish (ADAPT points first)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
