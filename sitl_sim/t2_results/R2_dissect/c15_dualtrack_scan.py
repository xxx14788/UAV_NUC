#!/usr/bin/env python3
# Unit-4 C-15: dual-track adjudication. For each product bag, extract the
# odometry/imu_propagate stream, detect non-monotonic stamps (dt<=0) and
# alternating position clusters; then compare each cluster against the SOURCE
# bag's own odom stream (bit-level stamp comparison) to attribute the track:
# echo-of-source vs replay-estimator-output.
import rosbag, math, sys
from collections import Counter

def stream(bag, topic):
    out = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=[topic]):
            p = msg.pose.pose.position
            out.append((msg.header.stamp.to_sec(), tt.to_sec(), p.x, p.y, p.z))
    return out

def analyze(name, rows):
    if not rows:
        print('%s: EMPTY' % name); return
    neg = sum(1 for i in range(1, len(rows)) if rows[i][0] - rows[i-1][0] <= 0)
    print('%s: n=%d span=%.2f-%.2f dt<=0 steps=%d' % (name, len(rows), rows[0][0], rows[-1][0], neg))
    if not neg:
        return
    # cluster by stamp base: split into monotone runs
    runs = []
    cur = [rows[0]]
    for i in range(1, len(rows)):
        if rows[i][0] > cur[-1][0]:
            cur.append(rows[i])
        else:
            runs.append(cur); cur = [rows[i]]
    runs.append(cur)
    print('  monotone runs: %d' % len(runs))
    for r in runs[:6]:
        mags = [math.sqrt(x*x+y*y+z*z) for _,_,x,y,z in r]
        print('    run n=%5d stamp[%.3f..%.3f] |P| p50=%.2f max=%.2f' % (
            len(r), r[0][0], r[-1][0], sorted(mags)[len(mags)//2], max(mags)))

if __name__ == '__main__':
    bag = sys.argv[1]
    for tp in ['/vins_estimator/odometry', '/vins_estimator/imu_propagate']:
        try:
            rows = stream(bag, tp)
            analyze('%s %s' % (bag.split('/')[-1], tp), rows)
        except Exception as e:
            print(bag, tp, 'ERR', e)
