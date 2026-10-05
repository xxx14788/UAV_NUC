#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anchor 窗内配对差离散度定标探针(v1.4 prereg 支撑;只读)。
窗口定义与 t3_anchor_batch_probe.py 逐字一致:
  dyn = [g1_ts, g1_ts+5], sta = [g1_ts-15, g1_ts-5]
每窗: 前 50 prop 样本配最近 truth(同 anchor() 口径),输出配对差逐轴 std/IQR/极差 + 窗内对数/时长。
用法: anchor_disp.py <run_dir_or_bag>   (run 目录含 flight.bag,或直接给 .bag 路径)
"""
import math, os, sys
import numpy as np
import rosbag

arg = sys.argv[1]
bag_path = arg if arg.endswith('.bag') else os.path.join(arg, 'flight.bag')
MODEL = 'iris_stereo_vins'

prop, truth, goals = [], [], []
with rosbag.Bag(bag_path, 'r') as b:
    for topic, msg, ts in b.read_messages(topics=[
            '/vins_estimator/imu_propagate', '/gazebo/model_states',
            '/move_base_simple/goal']):
        t = ts.to_sec() if hasattr(ts, 'to_sec') else ts / 1e9
        if topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position
            prop.append((t, p.x, p.y, p.z))
        elif topic == '/gazebo/model_states':
            try:
                i = msg.name.index(MODEL)
            except ValueError:
                continue
            p = msg.pose[i].position
            truth.append((t, p.x, p.y, p.z))
        else:
            goals.append((t, msg.pose.position.x, msg.pose.position.y, msg.pose.position.z))

if not prop or not truth:
    print('%s: EMPTY prop=%d truth=%d (goal 匹配前)' % (os.path.basename(bag_path), len(prop), len(truth)))
    sys.exit(0)

g1_ts = prop[0][0]
if goals:
    g0 = goals[0]
    g1_ts = next((g[0] for g in goals if abs(g[1]-g0[1]) < .05 and abs(g[2]-g0[2]) < .05), prop[0][0])

T = np.array([[q[1], q[2], q[3]] for q in truth])
tT = np.array([q[0] for q in truth])

def near_many(ts_q):
    idx = np.abs(tT[:, None] - ts_q[None, :]).argmin(axis=0)
    return T[idx]

def stats(name, f, to):
    pw = [(p[0], (p[1], p[2], p[3])) for p in prop if f <= p[0] <= to][:50]
    if len(pw) < 5:
        print('  %-4s: 窗内无足够样本 n=%d' % (name, len(pw)))
        return None
    ts_q = np.array([q[0] for q in pw])
    P = np.array([q[1] for q in pw])
    d = near_many(ts_q) - P
    std = d.std(axis=0); iqr = np.percentile(d, 75, axis=0) - np.percentile(d, 25, axis=0); rng = d.max(axis=0) - d.min(axis=0)
    dur = pw[-1][0] - pw[0][0] if len(pw) > 1 else 0.0
    anchor = d.mean(axis=0)
    print('  %-4s: n=%2d dur=%4.1fs anchor=(%7.3f,%7.3f,%7.3f) | std=(%.3f,%.3f,%.3f) iqr=(%.3f,%.3f,%.3f) rng=(%.3f,%.3f,%.3f)'
          % (name, len(pw), dur, *anchor, *std, *iqr, *rng))
    return std, iqr

print('%s: prop=%d truth=%d goals=%d g1_ts=%.1f' % (os.path.basename(os.path.dirname(bag_path)) or bag_path, len(prop), len(truth), len(goals), g1_ts))
stats('dyn', g1_ts, g1_ts + 5)
stats('sta', g1_ts - 15, g1_ts - 5)
