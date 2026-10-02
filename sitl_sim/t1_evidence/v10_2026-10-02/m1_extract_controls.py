#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract odom CSVs for M1 spectral controls (healthy static/moving).

Usage: python3 m1_extract_controls.py <out.csv> <bag>
Full-rate /vins_estimator/odometry positions (t from header stamp).
"""
import csv
import sys

import rosbag


def main():
    out, bag_path = sys.argv[1], sys.argv[2]
    n = 0
    with rosbag.Bag(bag_path) as bag, open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "z"])
        for _, m, _t in bag.read_messages(topics=["/vins_estimator/odometry"]):
            p = m.pose.pose.position
            w.writerow(
                [
                    round(m.header.stamp.to_sec(), 4),
                    round(p.x, 6),
                    round(p.y, 6),
                    round(p.z, 6),
                ]
            )
            n += 1
    print(f"{bag_path}: {n} rows -> {out}")


if __name__ == "__main__":
    main()
