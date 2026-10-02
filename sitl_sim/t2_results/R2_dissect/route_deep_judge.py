#!/usr/bin/env python3
# U3pp-rerun route deep judge: post-last-reboot recovery scale per round.
import rosbag, math, sys

for tag in ['route_032809', 'route_033941', 'route_035800', 'route_040932']:
    bag = '/home/uav/sitl_sim/bags/t2v3_%s.bag' % tag
    odom = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=['/vins_estimator/odometry']):
            p = msg.pose.pose.position
            odom.append((tt.to_sec(), math.sqrt(p.x*p.x+p.y*p.y+p.z*p.z), p.x, p.y, p.z))
    mags = [m for _, m, _, _, _ in odom]
    jumps = sum(1 for i in range(1, len(odom)) if abs(odom[i][1]-odom[i-1][1]) > 0.5)
    # last 60s stability (post-everything state)
    tail = odom[-600:]
    tm = [m for _, m, _, _, _ in tail]
    tm.sort()
    last = odom[-1]
    print('%s: odom n=%d |P|max=%.1f jumps>0.5m=%d | tail60s |P| p50=%.2f p95=%.2f | final=[%.1f %.1f %.1f] |P|=%.1f' % (
        tag, len(odom), max(mags), jumps, tm[len(tm)//2], tm[int(len(tm)*0.95)],
        last[2], last[3], last[4], last[1]))
