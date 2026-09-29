#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z1.2/C07-E2:r(运动学残差)分布全库扫描——jump 门统计量升级的定值件

r_k = ‖P_k − P_{k−1} − ½(V_{k−1}+V_k)·Δt‖(梯形积分恒等式;健康流 r≡0 基线,C07-03 D3)
分层(C07 红线 4 双分层):
  L_cur = 当前代码+当前栈健康层(canonical 噪声基线代 09-29 10:00+ 的健康/边际轮 + CTRL2 回放)
  L_pre = pre-fix 层(旧观测层/污染轮)——仅换代证据,不触发定值
双流前置:话题连接数>1(dual publisher)标记;时戳回退>1000 标记污染(剔除)。
输出: analysis/t3_r_scan.json + 阈值建议(当前层 p999×裕度)
"""
import json
import math
import os
import statistics
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TARGETS = [
    # (路径, 袋内话题, 分层, 注记)
    ("~/sitl_sim/bags/t2v3_route_112652.bag", "/vins_estimator/imu_propagate", "L_cur",
     "T2 W1.3 PASS 轮(canonical 在线,当前栈唯一健康在线样本)"),
    ("~/sitl_sim/bags/t2v3_route_112652.bag", "/vins_estimator/odometry", "L_cur",
     "同轮优化器流"),
    ("~/sitl_sim/bags/t2v3_hover_203248.bag", "/vins_estimator/imu_propagate", "L_pre",
     "旧观测层悬停(D3 预算分解用袋)"),
    ("~/sitl_sim/bags/t2v3_ground_202520.bag", "/vins_estimator/imu_propagate", "L_pre",
     "旧观测层地面"),
    ("~/sitl_sim/t3_results/CTRL2_t2v3_route_112652/vins_out.bag", "/vins_estimator/odometry",
     "L_cur", "canonical×route 回放(883c75c PASS-substance)"),
    ("~/sitl_sim/vins_smoke_runs/run_X1final_105449/flight.bag", "/vins_estimator/imu_propagate",
     "L_pre", "canonical 在线但 VINS 瞬态发散(速度爬坡轮,换代证据)"),
]


def conns(bag, topic):
    return list(bag._get_connections(topic))


def r_series(path, topic):
    import rosbag
    P, V, T = [], [], []
    dual = False
    reg_n = 0
    with rosbag.Bag(os.path.expanduser(path), "r") as b:
        cl = conns(b, topic)
        dual = len(cl) > 1
        for tp, msg, ts in b.read_messages(topics=[topic]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            p = msg.pose.pose.position
            v = msg.twist.twist.linear
            P.append((p.x, p.y, p.z))
            V.append((v.x, v.y, v.z))
            T.append(t)
    r = []
    for i in range(1, len(T)):
        dt = T[i] - T[i - 1]
        if dt <= 0 or dt > 0.5:
            reg_n += 1
            continue
        pred = tuple(P[i - 1][k] + 0.5 * (V[i - 1][k] + V[i][k]) * dt for k in range(3))
        if not all(math.isfinite(x) for x in pred + P[i]):
            continue
        r.append(math.dist(pred, P[i]))
    return r, dual, reg_n, len(T)


def pct(sorted_v, q):
    return sorted_v[min(len(sorted_v) - 1, int(q * len(sorted_v)))] if sorted_v else None


def main():
    out = {"layers": {}}
    for path, topic, layer, note in TARGETS:
        key = os.path.basename(os.path.expanduser(path)) + ":" + topic.split("/")[-1]
        try:
            r, dual, reg_n, n = r_series(path, topic)
        except Exception as e:
            out["layers"].setdefault(layer, []).append(
                {"src": key, "error": repr(e), "note": note})
            print(f"[r] {key}: ERROR {e!r}")
            continue
        rs = sorted(r)
        ent = {"src": key, "note": note, "n_frames": n, "dual_publisher": dual,
               "stamp_regected": reg_n,
               "r_p50": round(pct(rs, 0.50), 5) if rs else None,
               "r_p99": round(pct(rs, 0.99), 5) if rs else None,
               "r_p999": round(pct(rs, 0.999), 5) if rs else None,
               "r_max": round(rs[-1], 5) if rs else None}
        out["layers"].setdefault(layer, []).append(ent)
        print(f"[r] {layer} {key}: n={n} dual={dual} p50={ent['r_p50']} "
              f"p99={ent['r_p99']} p999={ent['r_p999']} max={ent['r_max']} ({note})")
    # 阈值建议:当前层健康 p999 × 裕度(3×,下限 0.02 上限 0.1,C07 方向 2 带)
    cur = [e for e in out["layers"].get("L_cur", [])
           if e.get("r_p999") is not None and not e.get("dual_publisher")
           and e.get("r_max", 0) < 0.3]
    if cur:
        p999 = max(e["r_p999"] for e in cur)
        rec = min(0.1, max(0.02, round(p999 * 3, 4)))
        out["threshold_recommendation"] = {
            "basis": "L_cur 健康 p999=%s ×3 裕度,夹在 C07 带 [0.02,0.10]" % p999,
            "r_gate_m": rec,
            "samples": [e["src"] for e in cur]}
        print(f"[r] 建议阈值 r_gate={rec} m(基于 {len(cur)} 当前层健康样本)")
    else:
        out["threshold_recommendation"] = {
            "basis": "当前层健康样本不足或 p999>0.3(C07-E2 止损线)",
            "r_gate_m": None,
            "fallback": "退回 |Δp| 门(C07-E2 止损),阈值另行标定"}
        print("[r] 当前层健康样本不足——止损口径:退回 |Δp| 门")
    with open(os.path.join(SCRIPT_DIR, "t3_r_scan.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
