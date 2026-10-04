#!/usr/bin/env python3
# h4c_climb.py — takeoff-climb timeline: truth z vs vins z vs thrust, 1s bins
import sys

import rosbag

IRIS = 'iris_stereo_vins'

bag = rosbag.Bag(sys.argv[1])
truth = []
vins = []
sp = []
for row in bag.read_messages():
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, topic, msg = row[0], row[1], row[2]
    else:
        topic, msg, t = row[0], row[1], row[2]
    ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
    if topic == '/gazebo/model_states':
        try:
            i = msg.name.index(IRIS)
        except ValueError:
            continue
        truth.append((ts, msg.pose[i].position.z))
    elif topic == '/vins_estimator/imu_propagate':
        vins.append((ts, msg.pose.pose.position.z))
    elif topic == '/mavros/setpoint_raw/attitude':
        sp.append((ts, msg.thrust))
bag.close()
t0 = min(truth[0][0], vins[0][0], sp[0][0]) if truth and vins and sp else 0
print('bin  truth_z  vins_z  thr_p50  thr_max  (n_t/n_v/n_sp)')
bins = {}
for arr, k in ((truth, 't'), (vins, 'v'), (sp, 's')):
    for ts, val in arr:
        b = int(ts - t0)
        bins.setdefault(b, {'t': [], 'v': [], 's': []})[k].append(val)
for b in sorted(bins)[:40]:
    d = bins[b]
    tz = d['t']
    vz = d['v']
    ss = sorted(d['s'])
    print('%3d %8.3f %7.3f %7.3f %7.3f  (%d/%d/%d)' % (
        b, max(tz) if tz else -9, max(vz) if vz else -9,
        ss[len(ss) // 2] if ss else -9, ss[-1] if ss else -9,
        len(tz), len(vz), len(ss)))
