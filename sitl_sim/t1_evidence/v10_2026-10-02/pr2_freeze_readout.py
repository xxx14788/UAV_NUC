#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U3PR2 smooth-lie probe-side readback (T1 v10.4 unit 7-3, 0-lock).

Reads t2v3_route_213717.bag (21G full): odom fixation face after burst
(48.7-61s) vs GT (model_states iris) drift timeline. Console log lost ->
bag-level substitute, honestly labeled.
"""
import math

import rosbag

BAG = "/home/uav/sitl_sim/bags/t2v3_route_213717.bag"

p_last = None
t_last = 0.0
frozen_dP = []
gt_last_t = -100.0

with rosbag.Bag(BAG) as bag:
    for topic, m, _t in bag.read_messages(
        topics=["/vins_estimator/odometry", "/gazebo/model_states"]
    ):
        if topic.endswith("odometry"):
            ts = m.header.stamp.to_sec()
            p = m.pose.pose.position
            if p_last is not None and ts - t_last > 0:
                dP = math.sqrt(
                    (p.x - p_last[0]) ** 2 + (p.y - p_last[1]) ** 2 + (p.z - p_last[2]) ** 2
                )
                if ts > 65:
                    frozen_dP.append(dP)
            if ts - t_last >= 20.0:
                print(
                    "ODOM",
                    round(ts, 0),
                    (round(p.x, 2), round(p.y, 2), round(p.z, 2)),
                    flush=True,
                )
                t_last = ts
            p_last = (p.x, p.y, p.z)
        else:
            try:
                i = m.name.index("iris")
            except ValueError:
                continue
            p = m.pose[i].position
            ts2 = _t.to_sec()
            if ts2 > 60 and ts2 - gt_last_t >= 60.0:
                print(
                    "GT  ",
                    round(ts2, 0),
                    (round(p.x, 2), round(p.y, 2), round(p.z, 2)),
                    flush=True,
                )
                gt_last_t = ts2

frozen_dP.sort()
n = len(frozen_dP)
if n:
    print(
        "POST65 dP: n=%d p50=%.5f p99=%.4f max=%.4f"
        % (n, frozen_dP[n // 2], frozen_dP[int(n * 0.99)], frozen_dP[-1])
    )
