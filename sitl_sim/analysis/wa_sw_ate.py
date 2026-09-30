#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA 判据修正:滑窗解 ATE——用 vins.log 的 [T2diag] P 序列(滑窗解,视觉每帧拉回)
对齐 GT 重算 ATE,替代被 fastPredict 链污染的 odom-ATE。
方法:t*(首跳>0.1m)后 Umeyama 刚体对齐(无尺度),post60 窗 RMSE。
用法: wa_sw_ate.py <replay_dir> <src_bag_with_truth>   # 打印一行
      wa_sw_ate.py --batch  # 全部 WA1X/WA2P/WA3C/WA4C/WA5C/WA6C/WA1C 格
"""
import sys, os, re, json, glob
import numpy as np

def read_diag(path):
    ts, P = [], []
    for line in open(path, errors="replace"):
        m = re.search(r"\[T2diag\] t=([\d.]+) P=\[([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)\]", line)
        if m:
            ts.append(float(m.group(1)))
            P.append([float(m.group(2)), float(m.group(3)), float(m.group(4))])
    return np.array(ts), np.array(P)

def read_gt(p):
    import rosbag
    ts, P = [], []
    with rosbag.Bag(p, "r") as b:
        for tp, m, t in b.read_messages(topics=["/gazebo/model_states"]):
            for i, n in enumerate(m.name):
                if "iris" in n:
                    ts.append(t.to_sec()); P.append([m.pose[i].position.x, m.pose[i].position.y, m.pose[i].position.z]); break
    ts = np.array(ts); P = np.array(P)
    keep = np.concatenate([[True], np.diff(ts) > 1e-6])
    return ts[keep], P[keep]

def umeyama_align(A, B):
    # find R,t s.t. A ≈ R@B + t (A=gt, B=est)
    ca, cb = A.mean(0), B.mean(0)
    H = (B - ca).T @ (A - cb) / len(A)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    t = ca - R @ cb
    return R, t

def sw_ate(diag_log, gt_bag, jump=0.1):
    ts, P = read_diag(diag_log)
    gts, G = read_gt(gt_bag)
    if len(ts) < 20: return None
    ts_r = ts - gts[0]; gts_r = gts - gts[0]
    # t*: first sliding-window jump >0.1m (same spirit as eval t*)
    tstar = None
    for i in range(1, len(ts_r)):
        if abs(np.linalg.norm(P[i] - P[i-1])) > jump and ts_r[i] > ts_r[0] + 5:
            tstar = ts_r[i]; break
    if tstar is None: tstar = ts_r[0] + 10
    W0 = max(tstar, ts_r[0])
    oi = (ts_r >= W0)
    idx = np.clip(np.searchsorted(gts_r, ts_r[oi]), 1, len(gts_r) - 2)
    A = G[idx]; B = P[oi]
    if len(A) < 10: return None
    R, t = umuyama = umeyama_align(A, B)
    Bal = (R @ B.T).T + t
    err = np.linalg.norm(A - Bal, axis=1)
    return dict(n=len(A), t_star=round(tstar, 1), sw_ate=round(float(np.sqrt((err**2).mean())), 3))

if __name__ == "__main__":
    GT = "/home/uav/sitl_sim/vins_smoke_runs/run_X1final_173345/flight.bag"
    if sys.argv[1] == "--batch":
        rows = []
        for pat in ("WA1X_*", "WA2P_*", "WA3C_*", "WA4C_*", "WA5C_*", "WA6C_*"):
            for d in sorted(glob.glob(os.path.expanduser("~/sitl_sim/t3_results/" + pat))):
                log = os.path.join(d, "vins.log")
                if not os.path.exists(log): continue
                r = sw_ate(log, GT)
                name = os.path.basename(d)
                jp = os.path.join(d, "judge.json")
                reboot = bas = ate_odom = None
                if os.path.exists(jp):
                    j = json.load(open(jp))
                    reboot, bas, ate_odom = j.get("reboot_n"), j.get("bas_max"), j.get("ate")
                rows.append((name, r["sw_ate"] if r else None, r["n"] if r else 0,
                             r["t_star"] if r else None, bas, reboot, ate_odom))
        print("%-32s %8s %5s %6s %8s %7s %8s" % ("cell", "sw_ATE", "n", "t*", "bas_max", "reboot", "odomATE"))
        for r in rows:
            print("%-32s %8s %5s %6s %8s %7s %8s" %
                  (r[0][:32], r[1], r[2], r[3], r[4], r[5], r[6]))
    else:
        print(sw_ate(os.path.join(sys.argv[1], "vins.log"), sys.argv[2]))
