#!/usr/bin/env python3
"""t1_odom_monitor.py — odom 监控告警器 v1.0 (T1 v11.25 阶段 4a 案5;实机监控规程载体)

双阈值(预注册=drill_prereg_v1):
  V 阈: |v|>0.5 m/s 持续 ≥3s            —— 速度异常
  D 阈: 位置位移率>0.3 m/s(滑窗 10s)     —— 慢漂(静默发散族不可自动检测型的人眼前置防线)
任一触发→<out>/odom_alarm.json+stdout ALARM 行(一次性;--repeat 可重复)。
用法: t1_odom_monitor.py <out_dir> [--vmax 0.5] [--vsec 3] [--drate 0.3] [--win 10] [--repeat]"""
import sys, os, json, argparse, math, collections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--vmax", type=float, default=0.5)
    ap.add_argument("--vsec", type=float, default=3.0)
    ap.add_argument("--drate", type=float, default=0.3)
    ap.add_argument("--win", type=float, default=10.0)
    ap.add_argument("--repeat", action="store_true")
    a = ap.parse_args()
    import rospy
    from nav_msgs.msg import Odometry
    rospy.init_node("t1_odom_monitor", anonymous=True, disable_signals=True)
    hist = collections.deque()  # (t, x, y, z)
    v_run_start = None
    alarmed = False
    state = {"t0": None, "frames": 0, "alarms": []}

    def cb(msg):
        nonlocal v_run_start, alarmed
        if alarmed and not a.repeat:
            return
        t = msg.header.stamp.to_sec() or rospy.get_time()
        p = msg.pose.pose.position
        tw = msg.twist.twist.linear
        v = math.sqrt(tw.x ** 2 + tw.y ** 2 + tw.z ** 2)
        hist.append((t, p.x, p.y, p.z))
        while hist and t - hist[0][0] > a.win:
            hist.popleft()
        state["frames"] += 1
        if state["t0"] is None:
            state["t0"] = t
        fires = []
        # V 阈: 持续超速
        if v > a.vmax:
            v_run_start = v_run_start or t
            if t - v_run_start >= a.vsec:
                fires.append("V|v|=%.2f>%.2f 持续 %.1fs" % (v, a.vmax, t - v_run_start))
        else:
            v_run_start = None
        # D 阈: 滑窗位移率
        if len(hist) >= 2 and t - hist[0][0] >= a.win * 0.5:
            d = math.dist(hist[0][1:], (p.x, p.y, p.z))
            if d / (t - hist[0][0]) > a.drate:
                fires.append("D 漂移率=%.2f>%.2f m/s(窗 %.0fs 位移 %.2fm)"
                             % (d / (t - hist[0][0]), a.drate, t - hist[0][0], d))
        if fires:
            alarmed = True
            rec = {"t": round(t - (state["t0"] or t), 2), "wall": rospy.get_time(),
                   "fires": fires, "pos": [round(p.x, 3), round(p.y, 3), round(p.z, 3)]}
            state["alarms"].append(rec)
            outp = os.path.join(a.out_dir, "odom_alarm.json")
            json.dump(state, open(outp, "w"), ensure_ascii=False, indent=1)
            print("ODOM-ALARM " + json.dumps(rec, ensure_ascii=False), flush=True)
            open(os.path.join(a.out_dir, "odom_alarm.flag"), "w").write("alarm\n")

    rospy.Subscriber("/vins_estimator/odometry", Odometry, cb, queue_size=2)
    rospy.spin()
    json.dump(state, open(os.path.join(a.out_dir, "odom_monitor_state.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
