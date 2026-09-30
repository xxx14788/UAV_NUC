#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3-Z1.2 自留件 E6(C07-E6):慢漂检测件定标——σ_w 重标 + T 扫描 SNR + 泄漏上界表

对象与分层(C07 红线 4:当前代码+当前栈):
  L_cur = WA1C_HOVER203248 回放 vins_out.bag 的 imu_propagate
          (W-A 全防线二进制 × 健康悬停袋 = 当前栈健康悬停样本)
  L_ref = t2v3_hover_203248.bag 原在线 imu_propagate(旧观测层,量级参考)
方法(C07-03 D4 扩散模型):
  悬停段(尾 60s)位移 std(p(t+T)−p(t)) 随 √T 标度 → σ_w(随机游走强度)
  SNR(T) = δ·√T/σ_w(δ=0.1 m/s 注入档;C07-P13:自然漂移裕度 ~200×)
  泄漏上界表:检测门限前的位移泄漏 ≈ δ·T_detect(T_detect=SNR 达 10 的窗)
输出: analysis/t3_e6_drift_budget.json + stdout 表
"""
import json
import math
import os
import statistics
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DELTA = 0.1          # m/s 注入档
WINDOWS = [1, 2, 5, 10, 30, 60]
TAIL_S = 60.0


def prop_from_bag(path, topic="/vins_estimator/imu_propagate"):
    import rosbag
    P = []
    with rosbag.Bag(path, "r") as b:
        for tp, msg, ts in b.read_messages(topics=[topic]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            p = msg.pose.pose.position
            if all(math.isfinite(v) for v in (p.x, p.y, p.z)):
                P.append((t, p.x, p.y, p.z))
    return P


def hover_segment(P, tail_s=TAIL_S):
    if not P:
        return []
    t_end = P[-1][0]
    seg = [r for r in P if r[0] > t_end - tail_s]
    # 悬停核验:位移包络 <0.5m(否则不是稳定悬停,如实报)
    if seg:
        env = max(math.dist((seg[i][1], seg[i][2], seg[i][3]),
                            (seg[0][1], seg[0][2], seg[0][3]))
                  for i in range(len(seg)))
        return seg, env
    return seg, None


def displacement_std(seg, T):
    """窗口 T 的位移 std(3D 合成;按 bag 时间配对最近的 ≥T 间隔帧)。"""
    ts = [r[0] for r in seg]
    from bisect import bisect_left
    ds = []
    for i, r in enumerate(seg):
        j = bisect_left(ts, r[0] + T)
        if j < len(seg) and ts[j] - r[0] < T * 1.2:
            ds.append(math.dist(r[1:4], seg[j][1:4]))
    return (statistics.pstdev(ds) if len(ds) > 20 else None), len(ds)


def sigma_w_fit(seg):
    pts = []
    for T in WINDOWS:
        s, n = displacement_std(seg, T)
        if s is not None:
            pts.append((math.sqrt(T), s, T))
    if len(pts) < 3:
        return None, pts
    # 过原点最小二乘: s = σ_w·√T
    num = sum(x * y for x, y, _ in pts)
    den = sum(x * x for x, _, _ in pts)
    return (num / den if den > 0 else None), pts


def main():
    cur_path = os.path.expanduser(
        "~/sitl_sim/t3_results/WA1C_HOVER203248_t2v3_hover_203248/vins_out.bag")
    ref_path = os.path.expanduser("~/sitl_sim/bags/t2v3_hover_203248.bag")
    out = {"delta_ms": DELTA, "windows": WINDOWS}
    for tag, path in (("L_cur_WA_binary_hover_replay", cur_path),
                      ("L_ref_oldstack_hover_online", ref_path)):
        if not os.path.exists(path):
            out[tag] = {"error": "bag 不存在"}
            continue
        P = prop_from_bag(path)
        seg_env = hover_segment(P)
        seg, env = seg_env if isinstance(seg_env, tuple) else (seg_env, None)
        ent = {"n_frames_total": len(P), "tail_frames": len(seg),
               "tail_envelope_m": round(env, 3) if env is not None else None}
        if len(seg) < 100:
            ent["error"] = "悬停段样本不足"
            out[tag] = ent
            continue
        sw, pts = sigma_w_fit(seg)
        ent["scale_fit"] = [(round(x, 3), round(y, 5), T) for x, y, T in pts]
        if sw:
            ent["sigma_w_m_per_sqrtS"] = round(sw, 5)
            # SNR 表与 T_detect(SNR≥10)
            ent["snr_table"] = {T: round(DELTA * math.sqrt(T) / sw, 1)
                                for T in WINDOWS}
            td = next((T for T in WINDOWS
                       if DELTA * math.sqrt(T) / sw >= 10), None)
            ent["T_detect_snr10_s"] = td
            ent["leak_at_detect_m"] = round(DELTA * td, 2) if td else None
        out[tag] = ent
        print(f"[e6] {tag}: σ_w={ent.get('sigma_w_m_per_sqrtS')} "
              f"包络={ent.get('tail_envelope_m')}m SNR表={ent.get('snr_table')} "
              f"T_detect={ent.get('T_detect_snr10_s')}s 泄漏={ent.get('leak_at_detect_m')}m")
    with open(os.path.join(SCRIPT_DIR, "t3_e6_drift_budget.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("[e6] 输出: analysis/t3_e6_drift_budget.json")


if __name__ == "__main__":
    main()
