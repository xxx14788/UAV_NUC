#!/usr/bin/env python3
# Unit-1 post-flight disk recovery (caliber-22): compact R3 (streams only),
# extract glitch timestamps for R1/R2/R4, then the caller deletes full bags.
import rosbag, math, sys

def glitch_times(bag):
    ts = []
    with rosbag.Bag(bag) as b:
        for tp, msg, tt in b.read_messages(topics=['/mavros/imu/data_raw']):
            a = msg.linear_acceleration
            if math.sqrt(a.x*a.x+a.y*a.y+a.z*a.z) > 15:
                ts.append(round(tt.to_sec(), 3))
    return ts

for tag, bag in [('R1', '/home/uav/sitl_sim/bags/t2v3_route_021054.bag'),
                 ('R2', '/home/uav/sitl_sim/bags/t2v3_route_021519.bag'),
                 ('R4', '/home/uav/sitl_sim/bags/t2v3_route_025251.bag')]:
    print(tag, 'glitch times:', glitch_times(bag))

# R3 compact
SRC = '/home/uav/sitl_sim/bags/t2v3_route_023852.bag'
DST = '/home/uav/sitl_sim/bags/compact_T2pairR3_023852.bag'
KEEP = ['/vins_estimator/odometry', '/vins_estimator/imu_propagate',
        '/mavros/imu/data_raw', '/gazebo/model_states', '/mavros/vision_pose/pose',
        '/px4ctrl/takeoff_land', '/move_base_simple/goal', '/mavros/local_position/odom']
with rosbag.Bag(SRC) as src, rosbag.Bag(DST, 'w') as dst:
    n = 0
    for tp, msg, tt in src.read_messages(topics=KEEP):
        dst.write(tp, msg, tt)
        n += 1
print('R3 compact written:', DST, 'msgs:', n)
