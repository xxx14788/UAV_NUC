#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U6 域卫士: 时钟域分裂的结构性检测器(W5-1 220 次拒绝本可 3s 内诊断)。

机制: 订阅双目与 IMU, 维护 stamp 滑窗; |img_stamp - imu_stamp| 滑窗中位
> 阈值(默认 1.0s, 远大于正常配对抖动 ~50ms, 远小于域差 1.79e9) 即判定
"domain split detected" 并 ROS_ERROR 熔断告警(附数值), 告警重复周期 3s。
可选 ~halt_vins=true 时通过 rosnode kill 停掉 vins_estimator(防毒状态)。

用法: rosrun ... domain_guard.py  (或 python3 domain_guard.py)
参数: ~win_sec(默认 3) ~thresh_sec(默认 1.0) ~halt_vins(默认 false)
自测: rosparam set /use_sim_time false 制造分裂 → 3s 内告警(见 U6 自测记录)
"""
import subprocess
import threading

import rospy
from sensor_msgs.msg import Imu
from sensor_msgs.msg import Image

IMG_TOPIC = "/iris_stereo_vins/vins_cam_left/image_raw"
IMU_TOPIC = "/mavros/imu/data_raw"


class DomainGuard:
    def __init__(self):
        self.img_stamps = []
        self.imu_stamps = []
        self.lock = threading.Lock()
        self.warned = False
        self.win = rospy.get_param("~win_sec", 3.0)
        self.thresh = rospy.get_param("~thresh_sec", 1.0)
        self.halt = rospy.get_param("~halt_vins", False)
        self.last_warn = 0.0
        rospy.Subscriber(IMG_TOPIC, Image, self.cb_img, queue_size=2)
        rospy.Subscriber(IMU_TOPIC, Imu, self.cb_imu, queue_size=10)
        rospy.Timer(rospy.Duration(1.0), self.check)

    def cb_img(self, msg):
        with self.lock:
            self.img_stamps.append(msg.header.stamp.to_sec())
            self.img_stamps = self.img_stamps[-200:]

    def cb_imu(self, msg):
        with self.lock:
            self.imu_stamps.append(msg.header.stamp.to_sec())
            self.imu_stamps = self.imu_stamps[-2000:]

    def check(self, _):
        with self.lock:
            if not self.img_stamps or not self.imu_stamps:
                return
            now = self.img_stamps[-1]
            recent_imu = [t for t in self.imu_stamps if abs(t - now) < self.win]
            if not recent_imu:
                # 时间轴上两边根本没有重叠: 也是分裂(或 IMU 断流)
                recent_imu = [self.imu_stamps[-1]]
            diff = now - sorted(recent_imu)[len(recent_imu) // 2]
        if abs(diff) > self.thresh:
            if rospy.get_time() - self.last_warn >= 3.0:
                rospy.logerr(
                    "DOMAIN SPLIT DETECTED: img_stamp - imu_stamp = %+.3e s "
                    "(thresh %.1f). VINS init will never align. "
                    "Fix: use_sim_time=true BEFORE mavros, single master.",
                    diff, self.thresh)
                self.last_warn = rospy.get_time()
                if self.halt and not self.warned:
                    subprocess.call(["rosnode", "kill", "/vins_estimator"])
            self.warned = True
        else:
            if self.warned:
                rospy.loginfo("domain guard: stamps re-aligned (diff %+.3f s)", diff)
            self.warned = False


if __name__ == "__main__":
    rospy.init_node("domain_guard")
    DomainGuard()
    rospy.spin()
