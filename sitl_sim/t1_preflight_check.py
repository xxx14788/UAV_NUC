#!/usr/bin/env python3
"""t1_preflight_check.py — 起飞前自检脚本 v0 (T1 v11.25 阶段 4d;一键 go/no-go)

检查项(安全盘点件 1a475cf4 §6b/6d 消费):
  1 CAL 门: CAL_GYRO0_{X,Y,Z}OFF 对标定带(|值|≤带)——E5P 型出界拒飞(评估 bfed27bf)
  2 VINS init 健康: /vins_estimator/odometry 流活+帧率≥5Hz+有限值
  3 odom 流活: 同上(与 2 合并判读但分列输出)
  4 电池: voltage ≥ min_v(默认 14.0=4S 健带下沿注记;实机按机架定) 且非 None
  5 链路: /mavros/state connected=True
输出: 逐项 PASS/FAIL + 终行 GO/NO-GO(任一 FAIL=NO-GO);--json 落盘。
用法: t1_preflight_check.py [--band 0.005] [--min-v 14.0] [--json out] [--watch 秒]
  CAL 带默认 0.005 rad/s(sim 绿格带量级~0.001 的 5×;实机标定带=地面静置标定后定带,
  本 v0 给保守占位+参数化——实机域注记)"""
import sys, json, argparse, subprocess, math, time


def fetch_param(name, timeout=8):
    try:
        r = subprocess.run(["rosrun", "mavros", "mavparam", "fetch", name],
                           capture_output=True, text=True, timeout=timeout)
        val = r.stdout.strip().split()
        return float(val[-1]) if val else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", type=float, default=0.005)
    ap.add_argument("--min-v", type=float, default=14.0)
    ap.add_argument("--watch", type=float, default=5.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    import rospy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import BatteryState
    from mavros_msgs.msg import State
    rospy.init_node("t1_preflight_check", anonymous=True, disable_signals=True)
    st = {"odom": {"n": 0, "finite": True, "hz": 0.0}, "bat": None, "link": None}

    def cb_odom(m):
        st["odom"]["n"] += 1
        p = m.pose.pose.position
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            st["odom"]["finite"] = False

    def cb_bat(m):
        st["bat"] = m.voltage

    def cb_state(m):
        st["link"] = m.connected

    rospy.Subscriber("/vins_estimator/odometry", Odometry, cb_odom, queue_size=5)
    rospy.Subscriber("/mavros/battery", BatteryState, cb_bat, queue_size=2)
    rospy.Subscriber("/mavros/state", State, cb_state, queue_size=2)
    t0 = time.time()
    while time.time() - t0 < a.watch and not rospy.is_shutdown():
        time.sleep(0.2)
    dt = time.time() - t0
    st["odom"]["hz"] = st["odom"]["n"] / dt if dt > 0 else 0.0

    items = []
    # 1 CAL 门
    for ax in ("X", "Y", "Z"):
        v = fetch_param("CAL_GYRO0_%sOFF" % ax)
        ok = (v is not None) and abs(v) <= a.band
        items.append({"item": "CAL_GYRO0_%sOFF" % ax, "value": v,
                      "band": "±%.4f" % a.band, "pass": bool(ok)})
    # 2/3 odom 流
    items.append({"item": "odom_stream_alive", "value": round(st["odom"]["hz"], 1),
                  "band": "≥5Hz", "pass": st["odom"]["hz"] >= 5.0})
    items.append({"item": "odom_finite", "value": st["odom"]["finite"],
                  "band": "全有限", "pass": st["odom"]["finite"]})
    # 4 电池
    items.append({"item": "battery_voltage", "value": st["bat"],
                  "band": "≥%.1fV" % a.min_v,
                  "pass": st["bat"] is not None and st["bat"] >= a.min_v})
    # 5 链路
    items.append({"item": "mavros_link", "value": st["link"], "band": "connected",
                  "pass": st["link"] is True})
    verdict = "GO" if all(i["pass"] for i in items) else "NO-GO"
    for i in items:
        print("  [%s] %-20s value=%s band=%s" % ("PASS" if i["pass"] else "FAIL",
                                                 i["item"], i["value"], i["band"]))
    print("PREFLIGHT %s" % verdict)
    if a.json:
        json.dump({"verdict": verdict, "items": items, "ts": time.time()},
                  open(a.json, "w"), ensure_ascii=False, indent=1)
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
