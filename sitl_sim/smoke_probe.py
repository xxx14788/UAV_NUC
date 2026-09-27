#!/usr/bin/env python3
"""sitl_smoke 六指标探针(U5)。
--yaw      起飞前 est-vs-truth 偏航差:订阅 /mavros/local_position/odom 与
           /gazebo/model_states,1.5s 窗,输出 YAWDIFF=<deg>(truth 与估计的 yaw 差)。
--depthhz  飞行中深度流:订阅 /iris_depth_camera/camera/depth/image_raw,
           5s 窗,输出 DEPTHHZ=<hz>。
"""
import sys, math, time

import rospy
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
from sensor_msgs.msg import Image


def yaw_of(q):
    return math.degrees(2 * math.atan2(q.z, q.w))


def yaw_probe():
    got = {}

    def odom_cb(m):
        got.setdefault("odom", []).append(yaw_of(m.pose.pose.orientation))

    def ms_cb(m):
        try:
            i = m.name.index("iris_depth_camera")
        except ValueError:
            return
        got.setdefault("truth", []).append(yaw_of(m.pose[i].orientation))

    rospy.init_node("smoke_probe_yaw", anonymous=True, disable_signals=True)
    rospy.Subscriber("/mavros/local_position/odom", Odometry, odom_cb)
    rospy.Subscriber("/gazebo/model_states", ModelStates, ms_cb)
    t0 = time.time()
    while not rospy.is_shutdown() and time.time() - t0 < 8 and (
            len(got.get("odom", [])) < 3 or len(got.get("truth", [])) < 3):
        time.sleep(0.1)
    if "odom" not in got or "truth" not in got:
        print("YAWDIFF=nan")
        return
    o = got["odom"][-1]; t = got["truth"][-1]
    d = (o - t + 180) % 360 - 180
    print(f"YAWDIFF={d:.2f}")


def depth_probe():
    n = [0]
    rospy.init_node("smoke_probe_depth", anonymous=True, disable_signals=True)
    rospy.Subscriber("/iris_depth_camera/camera/depth/image_raw", Image,
                     lambda m: n.__setitem__(0, n[0] + 1))
    t0 = time.time()
    while not rospy.is_shutdown() and time.time() - t0 < 6.5:
        time.sleep(0.2)
    hz = n[0] / 5.0
    print(f"DEPTHHZ={hz:.1f}")


if __name__ == "__main__":
    if "--yaw" in sys.argv:
        yaw_probe()
    elif "--depthhz" in sys.argv:
        depth_probe()
