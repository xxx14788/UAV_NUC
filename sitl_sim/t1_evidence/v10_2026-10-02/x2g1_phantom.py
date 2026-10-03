#!/usr/bin/env python3
# x2g1_phantom.py — specimen 1 forensics: phantom climb on a never-flew drone
# (truth z==0 all along). Reads odometry+imu_prop vs truth from the round bag.
import sys

import rosbag

BAG = sys.argv[1]
IRIS = "iris_stereo_vins"

bag = rosbag.Bag(BAG)
odom = []   # (t, x, y, z)  /vins_estimator/odometry
prop = []   # imu_propagate
truth = []  # model_states
for row in bag.read_messages():
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, topic, msg = row[0], row[1], row[2]
    else:
        topic, msg, t = row[0], row[1], row[2]
    ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
    if topic == '/vins_estimator/odometry':
        p = msg.pose.pose.position
        odom.append((ts, p.x, p.y, p.z))
    elif topic == '/vins_estimator/imu_propagate':
        p = msg.pose.pose.position
        prop.append((ts, p.x, p.y, p.z))
    elif topic == '/gazebo/model_states':
        try:
            i = msg.name.index(IRIS)
        except ValueError:
            continue
        p = msg.pose[i].position
        truth.append((ts, p.x, p.y, p.z))
bag.close()
print('n_odom=%d n_prop=%d n_truth=%d' % (len(odom), len(prop), len(truth)))
for name, arr in (('odom', odom), ('prop', prop)):
    if not arr:
        continue
    t0 = arr[0][0]
    print('%s: t0=%.2f span=%.1f' % (name, 0.0, arr[-1][0] - t0))
    # first 12 samples + jump profile
    print('  first:', [(round(r[0] - t0, 2), round(r[1], 2), round(r[2], 2), round(r[3], 2)) for r in arr[:6]])
    jumps = []
    for i in range(1, len(arr)):
        d = ((arr[i][1] - arr[i - 1][1]) ** 2 + (arr[i][2] - arr[i - 1][2]) ** 2 +
             (arr[i][3] - arr[i - 1][3]) ** 2) ** 0.5
        if d > 0.3:
            jumps.append((round(arr[i][0] - t0, 2), round(d, 3)))
    print('  jumps>0.3m:', jumps[:12])
    # z profile at 5s marks
    marks = []
    for k in range(0, int(arr[-1][0] - t0), 5):
        w = [r for r in arr if k <= r[0] - t0 < k + 5]
        if w:
            marks.append((k + 5, round(max(r[3] for r in w), 2), round(max(abs(r[1]) + abs(r[2]), 2), 2)))
    print('  z/xy_max per 5s:', marks[:14])
if truth:
    t0 = truth[0][0]
    zs = [r[3] for r in truth]
    print('truth: z[min=%.3f,max=%.3f] span=%.1fs' % (min(zs), max(zs), truth[-1][0] - t0))
