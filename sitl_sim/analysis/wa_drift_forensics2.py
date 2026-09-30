#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA 攻击面B v2:慢性漂移根源取证——起飞窗速度冲击检验(H-B1)
修复:v1 的两个 bug——①VINS odometry twist 是 body 系,用 pose.orientation
转世界系再对比;②用 header.stamp(bag 域)而非 bag 接收时戳(墙钟域)。
对象:WA6C_c_a5a4a3(最佳组合)+ 对照 WA1_CTRL2_LO(健康流)
产出:起飞窗(t=33-38)逐秒 VINS 世界系速度 vs GT 速度;悬停窗基线;
     全程分段位移误差;H-B1 判决(起飞瞬态速度冲击是否固化)
"""
import rosbag, numpy as np, json

def read_odom(p):
    ts, P, Vw = [], [], []
    with rosbag.Bag(p, "r") as b:
        for tp, m, t in b.read_messages(topics=["/vins_estimator/odometry"]):
            ts.append(m.header.stamp.to_sec())  # bag time domain
            q = m.pose.pose.orientation
            P.append([m.pose.pose.position.x, m.pose.pose.position.y, m.pose.pose.position.z])
            # VINS publishes BODY-frame twist; rotate to world via body attitude
            vb = np.array([m.twist.twist.linear.x, m.twist.twist.linear.y, m.twist.twist.linear.z])
            R = quat2R(q.w, q.x, q.y, q.z)
            Vw.append(R @ vb)
    return np.array(ts), np.array(P), np.array(Vw)

def quat2R(w, x, y, z):
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

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

import sys
REPLAY = sys.argv[1] if len(sys.argv) > 1 else "/home/uav/sitl_sim/t3_results/WA6C_c_a5a4a3_flight/vins_out.bag"
GTBAG = "/home/uav/sitl_sim/vins_smoke_runs/run_X1final_173345/flight.bag"

ts, P, Vw = read_odom(REPLAY)
gts, G = read_gt(GTBAG)
print("odom n=%d (t %.1f-%.1f)  gt n=%d (t %.1f-%.1f)" % (len(ts), ts[0]-gts[0], ts[-1]-gts[0], len(gts), gts[0]-gts[0], gts[-1]-gts[0]))
# relative time
ts_r = ts - gts[0]; gts_r = gts - gts[0]
# GT velocity (central diff, smoothed over ~0.5s window)
gv_raw = np.gradient(G, axis=0) / np.gradient(gts_r).reshape(-1, 1)
w = 25  # ~25 samples at 50Hz = 0.5s smoothing
k = np.ones(w)/w
gv = np.column_stack([np.convolve(gv_raw[:, i], k, mode="same") for i in range(3)])

def seg(t0, t1):
    oi = (ts_r >= t0) & (ts_r < t1)
    if oi.sum() < 3: return None
    idx = np.clip(np.searchsorted(gts_r, ts_r[oi]), 1, len(gts_r)-1)
    dv = Vw[oi] - gv[idx]
    dP = P[oi][-1] - P[oi][0]
    gi = (gts_r >= t0) & (gts_r < t1)
    dG = G[gi][-1] - G[gi][0] if gi.sum() > 1 else np.zeros(3)
    return oi.sum(), Vw[oi].mean(axis=0), gv[idx].mean(axis=0), dv.mean(axis=0), np.linalg.norm(dP-dG), dP, dG

print("\n=== 逐段:VINS 世界系速度均值 vs GT 速度均值 ===")
print("  seg |  n | VINS_v(x,y,z)          | GT_v(x,y,z)            | dv_norm | |disp_err|")
for t0 in range(26, 76, 4):
    r = seg(t0, t0+4)
    if r is None: continue
    n, vv, gvv, dv, dperr, dP, dG = r
    print(" %3d-%3d | %3d | [%6.2f %6.2f %6.2f] | [%6.2f %6.2f %6.2f] | %7.3f | %8.2f" %
          (t0, t0+4, n, vv[0], vv[1], vv[2], gvv[0], gvv[1], gvv[2], np.linalg.norm(dv), dperr))

# H-B1 verdict: takeoff window speed overshoot
pre = seg(29, 33); tk = seg(33.5, 36); mid = seg(36, 42)
if pre and tk:
    print("\n=== H-B1 起飞瞬态检验 ===")
    print("悬停窗(29-33): |VINS v|=%.3f |GT v|=%.3f" % (np.linalg.norm(pre[1]), np.linalg.norm(pre[2])))
    print("起飞窗(33.5-36): |VINS v|=%.3f |GT v|=%.3f  过估比=%.2f" %
          (np.linalg.norm(tk[1]), np.linalg.norm(tk[2]),
           np.linalg.norm(tk[1])/max(np.linalg.norm(tk[2]), 0.01)))
    if mid:
        print("起飞后(36-42): |VINS v|=%.3f |GT v|=%.3f  过估比=%.2f" %
              (np.linalg.norm(mid[1]), np.linalg.norm(mid[2]),
               np.linalg.norm(mid[1])/max(np.linalg.norm(mid[2]), 0.01)))
print("\nsaved context -> console (no file this run)")
