#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anchor 污染批量验证(P18;只读)。用法: anchor_batch.py <run_dir> <gx> <gy> <gz>
输出:动态窗锚(goal+5s,round_result 口径)/静止窗锚(goal-15~-5s)/两锚差/到位三口径。"""
import math, sys
import rosbag

D, GX, GY, GZ = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
GOAL = (GX, GY, GZ)
prop, truth, goals = [], [], []
with rosbag.Bag(D + "/flight.bag", "r") as b:
    for topic, msg, ts in b.read_messages(topics=[
            "/vins_estimator/imu_propagate", "/gazebo/model_states",
            "/move_base_simple/goal"]):
        t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
        if topic == "/vins_estimator/imu_propagate":
            p = msg.pose.pose.position
            prop.append((t, p.x, p.y, p.z))
        elif topic == "/gazebo/model_states":
            try:
                i = msg.name.index("iris_stereo_vins")
            except ValueError:
                continue
            p = msg.pose[i].position
            truth.append((t, p.x, p.y, p.z))
        else:
            goals.append((t, msg.pose.position.x, msg.pose.position.y, msg.pose.position.z))

g1_ts = next((g[0] for g in goals if abs(g[1]-GOAL[0]) < .05 and abs(g[2]-GOAL[1]) < .05), prop[0][0])

def near(arr, tt):
    return min(arr, key=lambda q: abs(q[0]-tt))

def anchor(f, to):
    pw = [p for p in prop if f <= p[0] <= to]
    tw = [near(truth, p[0]) for p in pw[:50]]
    return tuple(sum(t[k] for t in tw)/len(tw) - sum(p[k] for p in pw[:50])/len(pw) for k in (1,2,3))

a_dyn = anchor(g1_ts, g1_ts + 5)
a_st = anchor(g1_ts - 15, g1_ts - 5)
t_end = truth[-1][0]

def leg_min(ref):
    sel = [p for p in truth if g1_ts <= p[0] <= t_end]
    return min(math.dist((p[1],p[2],p[3]), ref) for p in sel)

d_dyn = leg_min(tuple(GOAL[k]+a_dyn[k] for k in range(3)))
d_st = leg_min(tuple(GOAL[k]+a_st[k] for k in range(3)))
d_bare = leg_min(GOAL)
print("%s: dyn=(%.3f,%.3f,%.3f) static=(%.3f,%.3f,%.3f) dz=%.3f | arrive dyn/static/bare = %.3f / %.3f / %.3f"
      % (D.split("/")[-1], *a_dyn, *a_st, a_dyn[2]-a_st[2], d_dyn, d_st, d_bare))
