#!/usr/bin/env python3
# m1_static_harvest.py — M1 second-cut: pre-takeoff static-segment harvest
# from E-4 round bags (imu_propagate stream). One CSV per bag (independent
# time base per round, avoids cross-bag window splicing).
import os
import sys

import rosbag

OUTDIR = sys.argv[1]
os.makedirs(OUTDIR, exist_ok=True)
bags = sys.argv[2:]


def static_window(bag):
    pts = []
    for row in bag.read_messages(topics=['/vins_estimator/imu_propagate']):
        if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
            t, msg = row[0], row[2]
        else:
            msg, t = row[1], row[2]
        ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
        p = msg.pose.pose.position
        pts.append((ts, p.x, p.y, p.z))
    if not pts:
        return []
    up = None
    for i in range(1, len(pts)):
        if pts[i][3] > 0.3 and pts[i - 1][3] <= 0.3:
            j = min(i + 100, len(pts) - 1)
            if pts[j][3] > 0.3:
                up = pts[i][0]
                break
    if up is None:
        return pts
    return [p for p in pts if p[0] < up]


for b in bags:
    d = os.path.basename(os.path.dirname(b))
    f = os.path.basename(b).replace('bag', '').replace('.', '')
    tag = d.replace('run_', '') if d.startswith('run_') else f
    bag = rosbag.Bag(b)
    pts = static_window(bag)
    bag.close()
    out = os.path.join(OUTDIR, 'm1_e4_%s.csv' % tag)
    with open(out, 'w') as f:
        f.write('t,x,y,z\n')
        if pts:
            t0 = pts[0][0]
            for ts, x, y, z in pts:
                f.write('%.4f,%.5f,%.5f,%.5f\n' % (ts - t0, x, y, z))
    print('%s: %d static pts -> %s' % (tag, len(pts), out))
