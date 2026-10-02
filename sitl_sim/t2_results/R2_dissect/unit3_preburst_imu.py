#!/usr/bin/env python3
# T2 v8.2 unit-3: pre-burst-window IMU-domain profiling across arms.
# Sick arms: 20s window ending at each burst onset; healthy controls:
# mid-round 20s windows. Stats: rate, dt distribution, |acc|/|gyr| percentiles.
import rosbag, math, sys

BAGS = [
    # (label, bag, w0, w1, kind)  times = bag record clock
    ('A1-sick-Bas',   '/home/uav/sitl_sim/bags/t2v3_route_035325.bag', 29.2, 49.2),
    ('A3-sick-cost',  '/home/uav/sitl_sim/bags/t2v3_hover_033842.bag', 26.5, 46.5),
    ('PR2-sick-frz',  '/home/uav/sitl_sim/bags/t2v3_route_213717.bag', 32.0, 52.0),
    ('U3PH-sick-tr',  '/home/uav/sitl_sim/bags/compact_U3PH_210708.bag', None, None),
    ('A2-sick-frz',   '/home/uav/sitl_sim/bags/t2v3_route_034144.bag', None, None),
    ('A5-ctl-ground', '/home/uav/sitl_sim/bags/t2v3_ground_030355.bag', None, None),
    ('A4-ctl-hover',  '/home/uav/sitl_sim/bags/t2v3_hover_033544.bag', None, None),
    ('U3PO-ctl-nav',  '/home/uav/sitl_sim/vins_smoke_runs/run_U3PO_211438/flight.bag', None, None),
    ('U3PG-ctl-grnd', '/home/uav/sitl_sim/bags/t2v3_ground_210307.bag', None, None),
]

def find_burst(bag):
    # burst onset = first |P|>1 in imu_propagate that keeps growing (>5m within 5s)
    rows = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=['/vins_estimator/imu_propagate']):
            p = msg.pose.pose.position
            rows.append((tt.to_sec(), math.sqrt(p.x*p.x+p.y*p.y+p.z*p.z)))
    if not rows: return None, rows
    t0 = rows[0][0]
    for i, (t, m) in enumerate(rows):
        if m > 1.0:
            for (t2, m2) in rows[i:i+2500]:
                if m2 > 5.0:
                    return t, rows
            # not sustained; keep scanning
    return None, rows

def stats(rows, w0, w1, label):
    dts, accs, gyrs, ax, ay, az, gx, gy, gz = [], [], [], [], [], [], [], [], []
    for r in rows:
        if w0 <= r[0] <= w1:
            dts.append(r[0])
            accs.append(math.sqrt(r[2]**2+r[3]**2+r[4]**2))
            gyrs.append(math.sqrt(r[5]**2+r[6]**2+r[7]**2))
            ax.append(abs(r[2])); ay.append(abs(r[3])); az.append(abs(r[4]))
            gx.append(abs(r[5])); gy.append(abs(r[6])); gz.append(abs(r[7]))
    if len(dts) < 50:
        print('%-14s window %.1f-%.1f n=%d TOO-FEW' % (label, w0, w1, len(dts))); return
    d = sorted(dts[i+1]-dts[i] for i in range(len(dts)-1))
    def pct(v, q): s=sorted(v); return s[min(len(s)-1, int(q*len(s)))]
    print('%-14s w=%.1f-%.1f n=%4d rate=%.1fHz dt p50=%.4f p95=%.4f max=%.4f neg=%d | |acc| p50=%.3f p95=%.3f max=%.3f | |gyr| p50=%.4f p95=%.4f max=%.4f | acc-ax p95 [%.2f %.2f %.2f] gyr-ax p95 [%.4f %.4f %.4f]' % (
        label, w0, w1, len(dts), (len(dts)-1)/(dts[-1]-dts[0]),
        pct(d,0.5), pct(d,0.95), d[-1], sum(1 for x in d if x<=0),
        pct(accs,0.5), pct(accs,0.95), max(accs),
        pct(gyrs,0.5), pct(gyrs,0.95), max(gyrs),
        pct(ax,0.95), pct(ay,0.95), pct(az,0.95),
        pct(gx,0.95), pct(gy,0.95), pct(gz,0.95)))

for label, bag, w0, w1 in BAGS:
    try:
        rows = []
        with rosbag.Bag(bag) as b:
            for tp, msg, tt in b.read_messages(topics=['/mavros/imu/data_raw']):
                a = msg.linear_acceleration; g = msg.angular_velocity
                rows.append((tt.to_sec(), msg.header.stamp.to_sec(), a.x, a.y, a.z, g.x, g.y, g.z))
        if not rows:
            print('%-14s NO-IMU-TOPIC' % label); continue
        if w0 is None:
            bt, prow = find_burst(bag)
            if bt is not None:
                w0, w1 = bt - 20, bt
                print('%-14s auto-burst@%.2f' % (label, bt))
            else:
                mid = (rows[0][0] + rows[-1][0]) / 2
                w0, w1 = mid, mid + 20
        # window is in record-clock; rows carry record time at idx0
        stats([(r[0], 0, r[2], r[3], r[4], r[5], r[6], r[7]) for r in rows], w0, w1, label)
    except Exception as e:
        print('%-14s ERR %s' % (label, e))
