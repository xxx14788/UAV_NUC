#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# P1-1b E4 悬停预算重算 — 三分解判读器 (C02 DOSSIER 口径; v9.0 P1-1b)
# 用法: t1_p11b_hover.py <flight.bag> [tag]
# 输入: hover 轮袋 (GT=/gazebo/model_states, VINS=/vins_estimator/imu_propagate,
#       EKF2=/mavros/local_position/odom)
# 三分解: ①重锚阶跃逐事件(|dp|>0.15m 单帧, 时刻+幅值+前后窗均值差+bootstrap CI)
#         ②慢漂(去阶跃段线性拟合, cm/min, 静态长窗)
#         ③跟踪残差(去阶跃+去漂后 |GT-odom| p50/p95)
# 双口径: birth-aligned(第一共同样本对齐) 与 raw(红线9 双口径强制)
# 判据: 逐事件≤0.02m 且 XY改善≥30% ⇒ 改写 V1.3 口径(登记,不自动改)
import io, json, math, os, sys

import rosbag

def pct(a, p):
    if not a: return None
    a = sorted(a); k = (len(a)-1)*p/100.0
    f, c = int(math.floor(k)), int(math.ceil(k))
    return a[f] if f == c else a[f]+(a[c]-a[f])*(k-f)

def boot_ci(diff, n=400, seed=7):
    import random
    random.seed(seed)
    if len(diff) < 8: return None
    ms = []
    for _ in range(n):
        s = [random.choice(diff) for _ in diff]
        ms.append(sum(s)/len(s))
    ms.sort()
    return [round(ms[int(0.025*len(ms))], 4), round(ms[int(0.975*len(ms))], 4)]

def main():
    bagp = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(bagp).replace(".bag", "")
    b = rosbag.Bag(bagp)
    gt, vins, ekf = [], [], []
    for tp, m, _ in b.read_messages():
        if tp == "/gazebo/model_states":
            if "iris_stereo_vins" in m.name:
                i = m.name.index("iris_stereo_vins")
                p = m.pose[i].position
                gt.append((_.to_sec(), p.x, p.y, p.z))
        elif tp == "/vins_estimator/imu_propagate":
            p = m.pose.pose.position
            vins.append((_.to_sec(), p.x, p.y, p.z))
        elif tp == "/mavros/local_position/odom":
            p = m.pose.pose.position
            ekf.append((_.to_sec(), p.x, p.y, p.z))
    R = {"bag": bagp, "tag": tag, "n": {"gt": len(gt), "vins": len(vins), "ekf": len(ekf)}}

    def decompose(name, od):
        if len(od) < 100: return {"skip": "insufficient"}
        # airborne mask via GT z if available (gt z>0.3), else t>15%..95%
        z3 = [g[3] for g in gt]
        air0 = next((i for i, z in enumerate(z3) if z > 0.3), 0)
        air1 = len(z3) - next((i for i, z in enumerate(reversed(z3)) if z > 0.3), 0)
        t0g = gt[air0][0] if air1 > air0 else gt[0][0]
        t1g = gt[air1-1][0] if air1 > air0 else gt[-1][0]
        seg = [(t, x, y, z) for (t, x, y, z) in od if t0g <= t <= t1g]
        if len(seg) < 100: return {"skip": "no overlap with airborne"}
        # dual calibration
        out = {}
        for cal in ("birth", "raw"):
            s = seg
            if cal == "birth":
                dx = s[0][1]; dy = s[0][2]
                s = [(t, x-dx, y-dy, z) for (t, x, y, z) in s]
            # 1) reanchor step events
            ev = []
            for i in range(1, len(s)):
                dp = math.dist(s[i][1:4], s[i-1][1:4])
                if dp > 0.15:
                    ev.append({"t_rel": round(s[i][0]-s[0][0], 2), "dp": round(dp, 4),
                               "xyz": [round(v, 3) for v in s[i][1:4]]})
            # 2) slow drift: mask +/-1.5s around events, linear fit on xy norm
            bad = set()
            for e in ev:
                for j, (t, *_r) in enumerate(s):
                    if abs(t - (s[0][0]+e["t_rel"])) <= 1.5: bad.add(j)
            clean = [r for j, r in enumerate(s) if j not in bad]
            drift = None
            if len(clean) > 50:
                n = len(clean)
                ts = [c[0]-clean[0][0] for c in clean]
                rn = [math.hypot(c[1], c[2]) for c in clean]
                mt, mr = sum(ts)/n, sum(rn)/n
                slope = sum((t-mt)*(r-mr) for t, r in zip(ts, rn)) / max(1e-9, sum((t-mt)**2 for t in ts))
                drift = {"slope_cm_per_min": round(slope*6000, 3),
                         "range_m": round(max(rn)-min(rn), 4), "n_clean": n}
            # 3) tracking residual vs GT (nearest-in-time)
            gi = 0; res = []
            for (t, x, y, z) in seg:
                while gi < len(gt)-1 and gt[gi][0] < t: gi += 1
                g = gt[gi]
                res.append(math.dist((x, y, z), (g[1], g[2], g[3])))
            res_sorted = sorted(res)
            out[cal] = {"n_events": len(ev), "events": ev[:12],
                        "drift": drift,
                        "resid_p50": round(pct(res, 50), 4), "resid_p95": round(pct(res, 95), 4),
                        "resid_max": round(max(res), 4)}
            # per-event CI: mean |pos| 1.0s pre vs post window
            for e in out[cal]["events"]:
                te = s[0][0] + e["t_rel"]
                pre = [r for r in seg if 0 < te - r[0] <= 1.0]
                post = [r for r in seg if 0 <= r[0] - te <= 1.0]
                if pre and post:
                    mp = sum(math.hypot(r[1], r[2]) for r in pre)/len(pre)
                    mq = sum(math.hypot(r[1], r[2]) for r in post)/len(post)
                    diff = [math.hypot(r[1], r[2]) - mp for r in post]
                    e["jump_xy_pre_post"] = round(mq - mp, 4)
                    ci = boot_ci(diff)
                    if ci: e["ci95_post"] = ci
        return out

    R["vins"] = decompose("vins", vins)
    R["ekf2"] = decompose("ekf", ekf)
    outp = os.path.expanduser("~/sitl_sim/t1_results/p11b_%s.json" % tag)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    io.open(outp, "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False)[:1600])
    print("WROTE", outp)

if __name__ == "__main__":
    main()
