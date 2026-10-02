#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR1 腿结构预演(T3 v8.7 池件④):X3 两段式(--leg2)锚差口径在真双 goal 袋上的预演。
口径=X7 §3 表:到位双口径 min_truth/min_vins + 腿末 3s 锚差漂移(prop-vs-truth 距离均值)
+ 腿切分=goal 时戳。素材=compact_U3PR1_212450(goal1≈68s 到达+goal2≈344s 无反应史实)。"""
import bisect
import math
import sys
import rosbag

bag = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/uav/sitl_sim/bags/compact_U3PR1_212450.bag"
prop, truth, goals = [], [], []
with rosbag.Bag(bag, "r") as b:
    for topic, msg, ts in b.read_messages(
            topics=["/vins_estimator/imu_propagate", "/gazebo/model_states",
                    "/move_base_simple/goal"]):
        t = ts.to_sec()
        if topic == "/vins_estimator/imu_propagate":
            p = msg.pose.pose.position
            prop.append((t, p.x, p.y, p.z))
        elif topic == "/move_base_simple/goal":
            p = msg.pose.position
            goals.append((t, p.x, p.y, p.z))
        else:
            try:
                i = msg.name.index("iris_stereo_vins")
            except ValueError:
                continue
            p = msg.pose[i].position
            truth.append((t, p.x, p.y, p.z))
t0 = truth[0][0]
print("bag=%s prop_n=%d truth_n=%d goals=%d" % (
    bag.split("/")[-1], len(prop), len(truth), len(goals)))
ts_t = [r[0] for r in truth]


def near_truth(t):
    j = bisect.bisect_left(ts_t, t)
    best = None
    for k in (j - 1, j):
        if 0 <= k < len(truth) and abs(truth[k][0] - t) < abs(truth[best][0] - t) if best is not None else True:
            if 0 <= k < len(truth):
                if best is None or abs(truth[k][0] - t) < abs(truth[best][0] - t):
                    best = k
    return truth[best]


seen = set()
legs = []
for gt, gx, gy, gz in goals:
    key = (round(gx, 2), round(gy, 2), round(gz, 2))
    if key in seen:
        continue
    seen.add(key)
    legs.append((gt, gx, gy, gz))
for i, (gt, gx, gy, gz) in enumerate(legs, 1):
    t_end = legs[i][0] if i < len(legs) else truth[-1][0]
    seg = [p for p in prop if gt <= p[0] <= t_end]
    if not seg:
        print("leg%d goal=(%.1f,%.1f,%.1f)@+%.0fs: prop 空" % (i, gx, gy, gz, gt - t0))
        continue
    # 出生点对齐(段首)
    g0 = near_truth(seg[0][0])
    off = (g0[1] - seg[0][1], g0[2] - seg[0][2], g0[3] - seg[0][3])
    # 到位双口径(对齐后 prop 距 goal;truth 距 goal)
    dv = min(math.dist(p[1:4], (gx, gy, gz)) for p in seg)
    ts_seg = [p[0] for p in seg]
    tg = [q for q in truth if gt <= q[0] <= t_end]
    dt = min(math.dist(q[1:4], (gx, gy, gz)) for q in tg) if tg else -1
    # 腿末 3s 锚差漂移(段首对齐系)
    tail = [p for p in seg if p[0] >= t_end - 3]
    drift = sum(math.dist((p[1] + off[0], p[2] + off[1], p[3] + off[2]),
                          near_truth(p[0])[1:4]) for p in tail) / max(len(tail), 1)
    print("leg%d goal=(%.1f,%.1f,%.1f)@+%.0fs 窗=+%.0f..+%.0f: 到位 truth=%.3f vins=%.3f "
          "腿末3s锚差漂移=%.3f m (n_tail=%d)" % (
              i, gx, gy, gz, gt - t0, gt - t0, t_end - t0, dt, dv, drift, len(tail)))
