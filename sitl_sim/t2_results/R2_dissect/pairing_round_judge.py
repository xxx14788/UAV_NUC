#!/usr/bin/env python3
# Unit-1 pairing round quick judge: reads the round's compact bag + archived
# vins log; emits the pre-registered verdict fields.
#   V-pairing main: freeze-burst window cost-gate fire AND post-reboot recovery
#   V-fix main: any gate fire -> odom gap <=10s -> resume at meter scale
#   V-fix aux : post-trigger poison <=2s and |P| peak <5m
import rosbag, math, sys, glob, os, re

bag_path = sys.argv[1]
log_path = sys.argv[2] if len(sys.argv) > 2 else None

def streams(bag):
    odom, prop = [], []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=['/vins_estimator/odometry', '/vins_estimator/imu_propagate']):
            p = msg.pose.pose.position
            mag = math.sqrt(p.x*p.x + p.y*p.y + p.z*p.z)
            (odom if tp.endswith('odometry') else prop).append((tt.to_sec(), mag))
    return odom, prop

odom, prop = streams(bag_path)
print('odom n=%d span %.2f-%.2f' % (len(odom), odom[0][0], odom[-1][0]) if odom else 'odom EMPTY')
print('prop n=%d span %.2f-%.2f peak|P|=%.1f' % (len(prop), prop[0][0], prop[-1][0], max(m for _, m in prop)) if prop else 'prop EMPTY')

# largest odom gap (reboot window)
if len(odom) > 2:
    gaps = sorted(((odom[i+1][0]-odom[i][0], odom[i][0]) for i in range(len(odom)-1)), reverse=True)[:3]
    print('odom top gaps (s, at_t):', [(round(g,2), round(t,2)) for g, t in gaps])
    # post-gap resume magnitude
    g0, tg = gaps[0]
    after = [m for t, m in odom if t > tg + g0 and t < tg + g0 + 2]
    if g0 > 1.0 and after:
        print('resume-after-gap |P| p50=%.2f (meter-scale check)' % sorted(after)[len(after)//2])

# poison: prop peak after last odom frame
if odom and prop:
    t_last_odom = odom[-1][0]
    post = [(t, m) for t, m in prop if t > t_last_odom]
    if post:
        pk = max(m for _, m in post)
        dur = post[-1][0] - post[0][0]
        print('post-last-odom prop: n=%d span=%.2fs peak|P|=%.1f' % (len(post), dur, pk))

# glitch count
glitch = 0
with rosbag.Bag(bag_path) as b:
    for tp, msg, tt in b.read_messages(topics=['/mavros/imu/data_raw']):
        a = msg.linear_acceleration
        if math.sqrt(a.x*a.x+a.y*a.y+a.z*a.z) > 15: glitch += 1
print('IMU glitch samples (>15 m/s2):', glitch)

if log_path:
    txt = open(log_path, errors='ignore').read()
    fires = re.findall(r'cost gate: streak=(\d+)', txt)
    fdt = re.findall(r'\[T2fail\] t=([0-9.]+)', txt)
    banners = txt.count('[T2GATECFG]')
    reboot_req = txt.count('system reboot requested')
    print('log: T2GATECFG banners=%d reboot-requests=%d T2fail=%s cost-fires=%d' % (
        banners, reboot_req, fdt[:3] if fdt else 'none', len(fires)))
    # solver health resume: count T2slv after last T2fail
    if fdt:
        tf = float(fdt[-1])
        slv_after = [m for m in re.findall(r'\[T2slv\] t=([0-9.]+)', txt) if float(m) > tf + 1.0]
        print('T2slv lines >1s after last T2fail: %d (recovery activity)' % len(slv_after))
