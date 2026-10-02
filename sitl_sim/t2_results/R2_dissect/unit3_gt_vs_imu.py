#!/usr/bin/env python3
# Unit-3 deep: GT-vs-IMU discrimination at PR2's 48.7s spike + PR1/WC2 scans.
# If GT twist-derivative stays physical (<15 m/s^2) while raw IMU hits 84 =>
# sensor-domain artifact (the trigger lives between gazebo IMU plugin and
# mavros). If GT matches => physical event (gazebo physics).
import rosbag, math, sys

def gt_accel(bag, model_name, t0, t1):
    with rosbag.Bag(bag) as b:
        rows = []
        for tp, msg, tt in b.read_messages(topics=['/gazebo/model_states']):
            if model_name in msg.name:
                i = msg.name.index(model_name)
                v = msg.twist[i]
                rows.append((tt.to_sec(), v.x, v.y, v.z))
    out = []
    for k in range(1, len(rows)):
        dt = rows[k][0] - rows[k-1][0]
        if dt <= 0 or dt > 0.1: continue
        ax = (rows[k][1]-rows[k-1][1])/dt
        ay = (rows[k][2]-rows[k-1][2])/dt
        az = (rows[k][3]-rows[k-1][3])/dt
        out.append((rows[k][0], math.sqrt(ax*ax+ay*ay+az*az)))
    return [(t, m) for t, m in out if t0 <= t <= t1]

def imu_spikes(bag, t0, t1, thr=15.0):
    rows = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=['/mavros/imu/data_raw']):
            a = msg.linear_acceleration
            m = math.sqrt(a.x*a.x+a.y*a.y+a.z*a.z)
            t = tt.to_sec()
            if t0 <= t <= t1 and m > thr:
                rows.append((t, m))
    return rows

BAG = '/home/uav/sitl_sim/bags/t2v3_route_213717.bag'
with rosbag.Bag(BAG) as b:
    names = None
    for tp, msg, tt in b.read_messages(topics=['/gazebo/model_states']):
        names = msg.name; break
print('gazebo models:', names[:6])
model = 'iris' if names and any('iris' in n for n in names) else names[1]
print('using model:', model)

gt = gt_accel(BAG, model, 46.0, 52.0)
gt.sort(key=lambda r: -r[1])
print('GT accel top-6 in 46-52s: ' + ' | '.join('t=%.3f a=%.2f' % r for r in gt[:6]))
imu = imu_spikes(BAG, 46.0, 52.0)
print('IMU |acc|>15 in 46-52s: n=%d' % len(imu), 'max=%s' % (max(imu, key=lambda r: r[1]) if imu else None))

# PR1 burst window scan
PR1 = '/home/uav/sitl_sim/bags/compact_U3PR1_212450.bag'
imu1 = imu_spikes(PR1, 50.0, 85.0)
print('PR1 50-85s IMU spikes>15: n=%d' % len(imu1), (max(imu1, key=lambda r: r[1]) if imu1 else 'none'))

# WC2 bags burst windows
for w, bag, t0, t1 in [('WC2-030927', '/home/uav/sitl_sim/vins_smoke_runs/run_WC2OBS1_030927/flight.bag', 50.0, 73.0),
                       ('WC2-032005', '/home/uav/sitl_sim/vins_smoke_runs/run_WC2OBS1_032005/flight.bag', 105.0, 130.0)]:
    try:
        sp = imu_spikes(bag, t0, t1)
        print('%s %.0f-%.0fs spikes>15: n=%d %s' % (w, t0, t1, len(sp), (max(sp, key=lambda r: r[1]) if sp else 'none')))
    except Exception as e:
        print(w, 'ERR', e)
