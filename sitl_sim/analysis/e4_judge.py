#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# T1-E4 J1-J5 快判(P0C3_E4_design §4 预埋判据; ulog 域; 只读) v2
# 用法: e4_judge.py <ulg> [tag] → stdout 摘要 + ~/sitl_sim/e4_runs/<tag>_judge.json
import io, json, math, os, sys
from pyulog import ULog

def pct(a, p):
    if not a: return None
    a = sorted(a); k = (len(a)-1)*p/100.0
    f, c = int(math.floor(k)), int(math.ceil(k))
    return a[f] if f == c else a[f]+(a[c]-a[f])*(k-f)

def get(u, name):
    return [d for d in u.data_list if d.name == name]

def stats(a):
    a = [float(x) for x in a]
    if not a: return None
    return {"n": len(a), "p50": round(pct(a,50),4), "p95": round(pct(a,95),4),
            "max": round(max(a),4), "min": round(min(a),4)}

def main():
    ulg, tag = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else os.path.basename(ulg).replace(".ulg",""))
    u = ULog(ulg, None)
    R = {"ulg": ulg, "tag": tag, "dur_s": round((u.last_timestamp - u.start_timestamp)/1e6, 1)}
    lp = get(u, "vehicle_local_position")
    if lp:
        d = lp[0].data; t = d["timestamp"]
        s0, s1 = int(len(t)*0.15), len(t)
        xs = [float(d["x"][i]) for i in range(s0, s1)]
        ys = [float(d["y"][i]) for i in range(s0, s1)]
        zs = [float(d["z"][i]) for i in range(s0, s1)]
        mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
        dx = [math.hypot(x-mx, y-my) for x, y in zip(xs, ys)]
        R["J1_xy_drift"] = stats(dx)
        mz = sum(zs)/len(zs)
        R["J5_z_rel"] = stats([abs(z-mz) for z in zs])
        R["J5_z_mean_ned"] = round(mz, 3)
    inv = get(u, "estimator_innovations"); var = get(u, "estimator_innovation_variances")
    ev = {}
    if inv and var:
        di, dv = inv[0].data, var[0].data
        for ch in ("ev_hpos", "ev_vpos", "ev_vel", "ev_yaw"):
            if ch in di:
                iv = [abs(float(x)) for x in di[ch]]
                vv = [float(x) for x in dv[ch]]
                ratios = [iv[i]/(3.0*math.sqrt(vv[i])) for i in range(len(iv)) if vv[i] > 1e-9]
                ev[ch] = {"n_active": sum(1 for x in iv if x != 0.0), "innov": stats(iv),
                          "ratio": stats(ratios), "ratio_gt1": sum(1 for r in ratios if r > 1.0)}
        R["J2_J3_ev"] = ev
    aid = {}
    for d in get(u, "estimator_aid_src"):
        if "fused" in d.data:
            aid["inst%d" % d.multi_id] = {"fused_n": int(sum(1 for x in d.data["fused"] if x)),
                                          "n": len(d.data["fused"])}
    if aid: R["J2_aid_src"] = aid
    R["ev_too_fast_msgs"] = [str(m.message)[:100] for m in getattr(u, "logged_messages", [])
                             if "too fast" in str(m.message).lower() and "ev" in str(m.message).lower()]
    ip = u.initial_parameters
    R["params"] = {k: ip.get(k) for k in ("EKF2_EV_CTRL", "EKF2_GPS_CTRL", "EKF2_PREDICT_US",
                                          "EKF2_DELAY_MAX", "EKF2_EV_DELAY", "EKF2_TAU_POS", "EKF2_TAU_VEL")}
    out = os.path.expanduser("~/sitl_sim/e4_runs/%s_judge.json" % tag)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False)[:1400])
    print("WROTE", out)

if __name__ == "__main__":
    main()
