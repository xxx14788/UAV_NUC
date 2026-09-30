#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA 攻击面B:慢性漂移根源取证——VINS 速度 vs GT 逐段对齐
对象:chi2 格(WA2P_wa4_m5c95,慢性漂移形态代表)
产出:分段(t 每 10s)位置误差范数/速度误差/速度误差方向;漂移起始时刻;
     起飞前后(33s)对比;判定漂移=速度恒偏 vs 加速度漂
"""
import rosbag, numpy as np, json, math

RB = "/home/uav/sitl_sim/t3_results/WA2P_wa4_m5c95_flight/vins_out.bag"
SB = "/home/uav/sitl_sim/vins_smoke_runs/run_X1final_173345/flight.bag"

def read_odom(p):
    ts, P, V = [], [], []
    with rosbag.Bag(p, "r") as b:
        for tp, m, t in b.read_messages(topics=["/vins_estimator/odometry"]):
            ts.append(t.to_sec())
            P.append([m.pose.pose.position.x, m.pose.pose.position.y, m.pose.pose.position.z])
            V.append([m.twist.twist.linear.x, m.twist.twist.linear.y, m.twist.twist.linear.z])
    return np.array(ts), np.array(P), np.array(V)

def read_gt(p):
    ts, P = [], []
    with rosbag.Bag(p, "r") as b:
        for tp, m, t in b.read_messages(topics=["/gazebo/model_states"]):
            for i, n in enumerate(m.name):
                if "iris" in n:
                    ts.append(t.to_sec())
                    P.append([m.pose[i].position.x, m.pose[i].position.y, m.pose[i].position.z])
                    break
    return np.array(ts), np.array(P)

ts, P, V = read_odom(RB)
gts, G = read_gt(SB)
# time base: align by relative time from bag start (both start ~bag t0)
t0 = gts[0]
ts_r = ts - t0; gts_r = gts - t0
# GT velocity by finite diff
gv = np.gradient(G, axis=0) / np.gradient(gts_r).reshape(-1, 1)
print("odom n=%d  gt n=%d" % (len(ts), len(gts)))

# per-10s segment: position drift (relative displacement error, avoids alignment) and velocity error
print("\n seg |  |dp_err| (disp err)  |dv| mean   v_err dir(x,y,z)")
res = []
for s10 in range(25, 120, 10):
    oi = (ts_r >= s10) & (ts_r < s10 + 10)
    gi = (gts_r >= s10) & (gts_r < s10 + 10)
    if oi.sum() < 5 or gi.sum() < 5: continue
    # relative displacement over segment (drift accumulates regardless of frame)
    dP = P[oi][-1] - P[oi][0]
    dG = G[gi][-1] - G[gi][0]
    dp_err = np.linalg.norm(dP - dG)
    # velocity error: nearest GT idx for each odom ts
    idx = np.searchsorted(gts_r, ts_r[oi])
    idx = np.clip(idx, 1, len(gts_r) - 1)
    dv = V[oi] - gv[idx]
    dvm = dv.mean(axis=0)
    res.append((s10, dp_err, np.linalg.norm(dvm), dvm.tolist()))
    print(" %3d | %10.3f m     %8.3f m/s   [%6.2f %6.2f %6.2f]" %
          (s10, dp_err, np.linalg.norm(dvm), dvm[0], dvm[1], dvm[2]))

json.dump(res, open("/home/uav/sitl_sim/t2_results/wa_drift_forensics_chi2cell.json", "w"), indent=1)
print("\nsaved -> wa_drift_forensics_chi2cell.json")
