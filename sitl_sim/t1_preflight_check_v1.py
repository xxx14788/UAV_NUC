#!/usr/bin/env python3
"""t1_preflight_check_v1.py — 起飞前自检脚本 v1 (T1 v11.34 单元1: 实机参数适配版)

v0→v1 变更 (v0=t1_preflight_check.py v11.25):
  1 [bugfix] mavparam 子命令 fetch→get (v0 实弹在实机全 None 的根因)
  2 [实机参数] CAL gyro 带=0.005 (实机实测 2026-10-09: X=-0.0024/Y=+0.0011/Z=-0.0007 全在带内);
    ACC 现值注记行 (X=0.009/Y=-0.258/Z=-0.093 — Y/Z 偏大, P1 物理窗标定核对项, 不设门只登记)
  3 [实机参数] min-v 默认 14.0 = 4S×3.5V (实机 BAT1_N_CELLS=4/V_EMPTY=3.6 实证)
  4 [新增第6项] VINS 静态病理带 (v11.34 2d 三症状链入自检): --vins-log 指定 VINS log,
    解析最近 120s T2diag |Bas| 与 T2slv final_cost 中位数; |Bas|med>0.8 或 cost_med>1e4 → FAIL
    (v11.31 实机静止三症状: |Bas|1.03 漂大→cost 3.3e8 爆→Eigen 断言崩; 0.8=病理前兆带)
"""
import sys, json, argparse, subprocess, math, time, re, statistics, os


def fetch_param(name, timeout=8):
    try:
        r = subprocess.run(["rosrun", "mavros", "mavparam", "get", name],
                           capture_output=True, text=True, timeout=timeout)
        val = r.stdout.strip().split()
        return float(val[-1]) if val else None
    except Exception:
        return None


def vins_pathology(vlog, window=120.0):
    """返回 (|Bas|_med, cost_med, n) 最近 window 秒; log 缺失/无数据返回 (None,None,0)"""
    if not vlog or not os.path.isfile(vlog):
        return None, None, 0
    pat_diag = re.compile(r"\[T2diag\] t=([0-9.]+).*\|Bas\|=([0-9.e+-]+)")
    pat_slv = re.compile(r"\[T2slv\] t=([0-9.]+).*final_cost=([0-9.e+-]+)")
    bas, costs, tmax = [], [], 0.0
    try:
        with open(vlog, errors="replace") as f:
            for line in f:
                m = pat_diag.search(line)
                if m:
                    t, v = float(m.group(1)), float(m.group(2)); tmax = max(tmax, t); bas.append((t, v))
                    continue
                m = pat_slv.search(line)
                if m:
                    t, v = float(m.group(1)), float(m.group(2)); tmax = max(tmax, t); costs.append((t, v))
    except OSError:
        return None, None, 0
    w0 = tmax - window
    b = [v for t, v in bas if t >= w0]
    c = [v for t, v in costs if t >= w0]
    return (statistics.median(b) if b else None,
            statistics.median(c) if c else None,
            len(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", type=float, default=0.005)
    ap.add_argument("--min-v", type=float, default=14.0)
    ap.add_argument("--watch", type=float, default=5.0)
    ap.add_argument("--vins-log", default=None, help="VINS log 路径(第6项病理带; 不给则该项 SKIP)")
    ap.add_argument("--bas-band", type=float, default=0.8)
    ap.add_argument("--cost-band", type=float, default=1e4)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    import rospy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import BatteryState
    from mavros_msgs.msg import State
    rospy.init_node("t1_preflight_check_v1", anonymous=True, disable_signals=True)
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
    # 1 CAL 门 (gyro; 实机带 0.005)
    for ax in ("X", "Y", "Z"):
        v = fetch_param("CAL_GYRO0_%sOFF" % ax)
        ok = (v is not None) and abs(v) <= a.band
        items.append({"item": "CAL_GYRO0_%sOFF" % ax, "value": v,
                      "band": "|v|<=%.4f" % a.band, "pass": bool(ok)})
    # 1b ACC 现值注记行 (不设门; 基准=2026-10-09 实测, 偏离>0.05 提示重标定)
    acc_ref = {"X": 0.0089, "Y": -0.2583, "Z": -0.0925}
    for ax in ("X", "Y", "Z"):
        v = fetch_param("CAL_ACC0_%sOFF" % ax)
        drift = abs(v - acc_ref[ax]) if v is not None else None
        items.append({"item": "CAL_ACC0_%sOFF(note)" % ax, "value": v,
                      "band": "注记项: vs基准%s偏离<0.05" % acc_ref[ax],
                      "pass": True, "note": "drift=%.4f%s" % (drift, " (提示物理窗重标定)" if drift and drift > 0.05 else "") if drift is not None else "fetch失败"})
    # 2/3 odom 流
    items.append({"item": "odom_stream_alive", "value": round(st["odom"]["hz"], 1),
                  "band": ">=5Hz", "pass": st["odom"]["hz"] >= 5.0})
    items.append({"item": "odom_finite", "value": st["odom"]["finite"],
                  "band": "全有限", "pass": st["odom"]["finite"]})
    # 4 电池 (4S: 14.0=3.5V/cell)
    items.append({"item": "battery_voltage", "value": st["bat"],
                  "band": ">=%.1fV(4S)" % a.min_v,
                  "pass": st["bat"] is not None and st["bat"] >= a.min_v})
    # 5 链路
    items.append({"item": "mavros_link", "value": st["link"], "band": "connected",
                  "pass": st["link"] is True})
    # 6 VINS 静态病理带 (v11.34 2d: |Bas|/cost)
    if a.vins_log:
        bmed, cmed, n = vins_pathology(a.vins_log)
        if n == 0:
            items.append({"item": "vins_static_pathology", "value": "no-data",
                          "band": "|Bas|med<=%.1f & cost_med<=%.0e (120s窗)" % (a.bas_band, a.cost_band),
                          "pass": False})
        else:
            ok = (bmed is not None and bmed <= a.bas_band) and (cmed is not None and cmed <= a.cost_band)
            items.append({"item": "vins_static_pathology", "value": {"bas_med": bmed, "cost_med": cmed, "n": n},
                          "band": "|Bas|med<=%.1f & cost_med<=%.0e (120s窗)" % (a.bas_band, a.cost_band),
                          "pass": bool(ok)})
    else:
        items.append({"item": "vins_static_pathology", "value": "SKIP", "band": "--vins-log 未给", "pass": True})
    verdict = "GO" if all(i["pass"] for i in items) else "NO-GO"
    for i in items:
        print("  [%s] %-24s value=%s band=%s %s" % ("PASS" if i["pass"] else "FAIL",
                                                    i["item"], i["value"], i["band"], i.get("note", "")))
    print("PREFLIGHT %s" % verdict)
    if a.json:
        json.dump({"verdict": verdict, "items": items, "ts": time.time(), "version": "v1"},
                  open(a.json, "w"), ensure_ascii=False, indent=1)
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
