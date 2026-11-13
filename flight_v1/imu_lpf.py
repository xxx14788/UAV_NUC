#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMU 低通中继（2026-11-15，VINS 振动根因修复 V1）。

背景（11-14 三袋实测）：VINS 用的 /mavros/imu/data_raw 在悬停时加计 std 0.40/0.52/0.26 m/s²、
陀螺 0.149 rad/s，PSD 在 63-81 Hz 有桨/电机峰；Allan 零偏不稳定性从静态 0.0015 涨到 0.0067
（加计）/ 4.2e-5 涨到 0.022（陀螺）= 振动整流。acc_w 取 1e-6 焊死零偏、取 1e-4 又追振动包络，
两个都不是药。先在 IMU 入口把 63-81 Hz 压掉，再按滤波后的 Allan 重设噪声。

实现：4 阶 Butterworth（两级 biquad，fc=35 Hz，Q=0.5412/1.3066），fs 默认 200 Hz。
- 加计/陀螺 6 轴各一套；因果滤波，实测相位延迟 5 Hz ≈10.7 ms、15 Hz ≈11.1 ms
  （群延迟 10.8–12.1 ms），VINS `td=0` 未补偿——重新启用前必须做 td/estimate_td A/B。
- 首样本做 DC 初始化（z1/z2 设到稳态），避免启动阶跃；输入非有限值时直通并复位滤波器。
- 时间戳/协方差/orientation 原样保留；只改 linear_acceleration 与 angular_velocity。
- 默认 in=/mavros/imu/data_raw，out=/vins_imu/data_raw（VINS yaml 的 imu_topic 指到 out）。
- 2026-11-15 第三方审查 B1：空中 VINS failure-detection reboot 后必须**重新直通** raw，
  否则会用滤波 IMU 重新 init（重放实测会卡死）。订阅 /vins_estimator/reboot_notify
  （std_msgs/UInt32, latched）复位 bypass 计数与滤波器状态。
"""
import math

import rospy
from sensor_msgs.msg import Imu
from std_msgs.msg import UInt32


class Biquad:
    def __init__(self, fc, fs, q):
        w0 = 2.0 * math.pi * fc / fs
        cw, sw = math.cos(w0), math.sin(w0)
        alpha = sw / (2.0 * q)
        b0 = (1.0 - cw) / 2.0
        b1 = 1.0 - cw
        b2 = (1.0 - cw) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cw
        a2 = 1.0 - alpha
        self.b0, self.b1, self.b2 = b0 / a0, b1 / a0, b2 / a0
        self.a1, self.a2 = a1 / a0, a2 / a0
        self.z1 = 0.0
        self.z2 = 0.0
        self.started = False

    def step(self, x):
        if not self.started:
            # 常数 x 的稳态：y=x, z2=(b2-a2)x, z1=(b1-a1)x+z2
            self.z2 = (self.b2 - self.a2) * x
            self.z1 = (self.b1 - self.a1) * x + self.z2
            self.started = True
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return y


class Cascade:
    """4 阶 Butterworth = Q=0.5412 + 1.3066 两级 biquad。"""

    def __init__(self, fc, fs):
        self.s1 = Biquad(fc, fs, 0.54119610)
        self.s2 = Biquad(fc, fs, 1.30656296)

    def step(self, x):
        return self.s2.step(self.s1.step(x))


class ImuLpf:
    def __init__(self):
        rospy.init_node("imu_lpf")
        self.fc = float(rospy.get_param("~fc", 35.0))
        self.fs = float(rospy.get_param("~fs", 200.0))
        # 2026-11-15（自检抓到）：VINS 重放实测——从第一帧就用滤波 IMU 会让 init 卡死
        # （P 全程 0）；原始 IMU 能 init。所以前 bypass_s 秒**直通原始**，让 VINS 用和
        # 实飞同样的原始 IMU 完成初始化；之后切换滤波（切换时对滤波器做 DC 初始化）。
        self.bypass_n = int(float(rospy.get_param("~bypass_s", 5.0)) * self.fs)
        in_topic = rospy.get_param("~in_topic", "/mavros/imu/data_raw")
        out_topic = rospy.get_param("~out_topic", "/vins_imu/data_raw")
        self.acc = [Cascade(self.fc, self.fs) for _ in range(3)]
        self.gyr = [Cascade(self.fc, self.fs) for _ in range(3)]
        self.n = 0
        self.pub = rospy.Publisher(out_topic, Imu, queue_size=20)
        rospy.Subscriber(in_topic, Imu, self.cb, queue_size=20)
        # B1：VINS 空中 failure-detection reboot 会重新 init；收到通知就重新直通 raw。
        rospy.Subscriber("/vins_estimator/reboot_notify", UInt32, self.reboot_cb, queue_size=1)
        self.reboot_cnt = 0
        rospy.loginfo("imu_lpf: %s -> %s | 4th-order Butterworth fc=%.1f Hz fs=%.1f Hz",
                      in_topic, out_topic, self.fc, self.fs)

    def reboot_cb(self, msg):
        self.n = 0
        for c in self.acc + self.gyr:
            c.s1.started = False
            c.s2.started = False
        self.reboot_cnt += 1
        rospy.logwarn("imu_lpf: VINS reboot_notify=%s -> re-arm raw bypass (%d)",
                      msg.data, self.reboot_cnt)

    def cb(self, m):
        out = Imu()
        out.header = m.header
        out.orientation = m.orientation
        out.orientation_covariance = m.orientation_covariance
        out.linear_acceleration_covariance = m.linear_acceleration_covariance
        out.angular_velocity_covariance = m.angular_velocity_covariance
        a = m.linear_acceleration
        g = m.angular_velocity
        if not all(math.isfinite(v) for v in (a.x, a.y, a.z, g.x, g.y, g.z)):
            # L3：非有限值直通并复位滤波器，避免 NaN 永久污染 z1/z2。
            for c in self.acc + self.gyr:
                c.s1.started = False
                c.s2.started = False
            out.linear_acceleration = a
            out.angular_velocity = g
            self.pub.publish(out)
            self.n += 1
            return
        if self.n < self.bypass_n:
            # init 窗口：原样直通（VINS 的初始化和实飞一致）
            out.linear_acceleration = a
            out.angular_velocity = g
        else:
            out.linear_acceleration.x = self.acc[0].step(a.x)
            out.linear_acceleration.y = self.acc[1].step(a.y)
            out.linear_acceleration.z = self.acc[2].step(a.z)
            out.angular_velocity.x = self.gyr[0].step(g.x)
            out.angular_velocity.y = self.gyr[1].step(g.y)
            out.angular_velocity.z = self.gyr[2].step(g.z)
        self.pub.publish(out)
        self.n += 1
        if self.n == self.bypass_n:
            rospy.loginfo("imu_lpf: %d samples bypassed (VINS init), filter ON (fc=%.1f)",
                          self.bypass_n, self.fc)


if __name__ == "__main__":
    ImuLpf()
    rospy.spin()
