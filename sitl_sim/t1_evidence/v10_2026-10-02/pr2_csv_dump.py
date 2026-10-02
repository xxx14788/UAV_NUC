#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U3PR2 odom+GT CSV dump for M1 spectral prototype (unit 7-3 companion).

Both streams use header stamps (sim time) as the common timeline.
Output: /tmp/pr2_odom.csv, /tmp/pr2_gt.csv (sampled 1Hz for GT, full for odom
downsampled to 5Hz to keep CSV small).
"""
import csv

import rosbag

BAG = "/home/uav/sitl_sim/bags/t2v3_route_213717.bag"


def main():
    n_odom = 0
    n_gt = 0
    gt_last = -10.0
    with rosbag.Bag(BAG) as bag, open("/tmp/pr2_odom.csv", "w", newline="") as fo, open(
        "/tmp/pr2_gt.csv", "w", newline=""
    ) as fg:
        wo = csv.writer(fo)
        wg = csv.writer(fg)
        wo.writerow(["t", "x", "y", "z"])
        wg.writerow(["t", "x", "y", "z"])
        for topic, m, _t in bag.read_messages(
            topics=["/vins_estimator/odometry", "/gazebo/model_states"]
        ):
            if topic.endswith("odometry"):
                n_odom += 1
                if n_odom % 2 == 0:  # ~5Hz from 10Hz
                    p = m.pose.pose.position
                    wo.writerow(
                        [
                            round(m.header.stamp.to_sec(), 4),
                            round(p.x, 5),
                            round(p.y, 5),
                            round(p.z, 5),
                        ]
                    )
            else:
                try:
                    i = m.name.index("iris")
                except ValueError:
                    continue
                ts = m.header.stamp.to_sec()
                if ts - gt_last >= 1.0:
                    p = m.pose[i].position
                    wg.writerow(
                        [round(ts, 3), round(p.x, 4), round(p.y, 4), round(p.z, 4)]
                    )
                    gt_last = ts
                    n_gt += 1
    print(f"odom rows={n_odom // 2} gt rows={n_gt}")


if __name__ == "__main__":
    main()
