#!/usr/bin/env python3
# Unit6-5: A1 poison-window frame-level dissection (feeds unit-2a selection)
# Streams: /vins_estimator/imu_propagate (the poison flow), /vins_estimator/odometry
import rosbag, math, sys

BAG = '/home/uav/sitl_sim/bags/t2v3_route_035325.bag'
prop, odom = [], []
with rosbag.Bag(BAG) as b:
    t0 = b.get_start_time()
    for tp, msg, tt in b.read_messages(topics=['/vins_estimator/imu_propagate', '/vins_estimator/odometry']):
        p = msg.pose.pose.position
        v = msg.twist.twist.linear
        rec = (tt.to_sec() - t0, p.x, p.y, p.z, math.sqrt(p.x*p.x+p.y*p.y+p.z*p.z),
               math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z))
        (prop if tp.endswith('imu_propagate') else odom).append(rec)

print('imu_propagate n=%d span %.2f-%.2f  rate=%.1fHz' % (
    len(prop), prop[0][0], prop[-1][0], (len(prop)-1)/(prop[-1][0]-prop[0][0])))
print('odometry     n=%d span %.2f-%.2f  rate=%.2fHz' % (
    len(odom), odom[0][0], odom[-1][0], (len(odom)-1)/max(1e-9, odom[-1][0]-odom[0][0])))

def mag(r): return r[4]

# key epochs relative to known timeline: Bas gate fire t=49.16 (log clock ~ bag clock? check)
# print |P| profile every 0.5s from t=44 to flow end
print()
print('--- imu_propagate |P|/|V| profile (0.5s steps, t = bag-relative) ---')
next_t = 44.0
prev = None
jumps = []
for r in prop:
    if prev is not None:
        dp = math.dist(r[1:4], prev[1:4])
        dtr = r[0] - prev[0]
        if dp > 0.5 and r[0] > 40:
            jumps.append((r[0], dp, dtr, r[4]))
    prev = r
for r in prop:
    if r[0] >= next_t:
        print('  t=%6.2f  |P|=%8.2f  |V|=%7.2f  P=[%7.2f %7.2f %6.2f]' % (r[0], r[4], r[5], r[1], r[2], r[3]))
        next_t += 0.5
    if r[0] > 70: break

print()
print('--- frame-to-frame |dP|>0.5m events (t>40s): n=%d ---' % len(jumps))
for j in jumps[:25]:
    print('  t=%6.3f  dP=%7.3f  dt=%.4f  |P|=%8.2f' % j)

# last frames of the flow + odometry tail
print()
print('--- flow tail (last 8 imu_propagate frames) ---')
for r in prop[-8:]:
    print('  t=%6.3f  |P|=%8.2f  |V|=%7.2f' % (r[0], r[4], r[5]))
print('--- odometry tail (last 5) + first 2 ---')
for r in odom[:2] + odom[-5:]:
    print('  t=%6.3f  |P|=%8.2f  |V|=%7.2f' % (r[0], r[4], r[5]))

# growth segmentation: when did |P| cross 1,5,20,50,100,142
print()
print('--- |P| thresholds crossing ---')
for thr in (1, 5, 20, 50, 100, 142):
    for r in prop:
        if r[4] > thr:
            print('  |P|>%4d first@t=%.3f' % (thr, r[0])); break
    else:
        print('  |P|>%4d never' % thr)
# healthy baseline band pre-49s
hb = [r[4] for r in prop if 35 < r[0] < 49]
hb.sort()
print('healthy band 35-49s: |P| p50=%.3f max=%.3f' % (hb[len(hb)//2], hb[-1]))
