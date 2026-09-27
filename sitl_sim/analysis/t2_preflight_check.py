#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U6 启动自检: 起栈后 N 秒内五项全绿才放行起飞/启动 vins。

检查项:
  1 stamp 同域: |img_med - imu_med| < 1.0s(以最近窗口中位)
  2 双目 ~20Hz(>15)
  3 IMU >100Hz(提频后 ~125)
  4 /gazebo/model_states 存在(真值链路)
  5 /mavros/state connected==true
退出码 0=全绿, 1=有红项(逐项打印)。供 t2_w5_run.sh / t2_init_probe.sh 调用。

注意: 计时用 time.time()(踩坑 3: use_sim_time 下 /clock 未达时 rospy.get_time 恒 0)。
"""
import sys
import time

import rospy
from mavros_msgs.msg import State
from sensor_msgs.msg import Image, Imu

IMG_L = "/iris_stereo_vins/vins_cam_left/image_raw"
IMG_R = "/iris_stereo_vins/vins_cam_right/image_raw"
IMU = "/mavros/imu/data_raw"


class Collector:
    def __init__(self):
        self.img_l = []
        self.img_r = []
        self.imu = []
        self.gt = 0
        self.state = None

    def cb_img_l(self, m):
        self.img_l.append(m.header.stamp.to_sec())

    def cb_img_r(self, m):
        self.img_r.append(m.header.stamp.to_sec())

    def cb_imu(self, m):
        self.imu.append(m.header.stamp.to_sec())


def main():
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    rospy.init_node("t2_preflight_check", anonymous=True, disable_signals=True)
    c = Collector()
    rospy.Subscriber(IMG_L, Image, c.cb_img_l, queue_size=2)
    rospy.Subscriber(IMG_R, Image, c.cb_img_r, queue_size=2)
    rospy.Subscriber(IMU, Imu, c.cb_imu, queue_size=20)
    rospy.Subscriber("/gazebo/model_states", rospy.AnyMsg,
                     lambda m: setattr(c, "gt", c.gt + 1), queue_size=2)
    rospy.Subscriber("/mavros/state", State, lambda m: setattr(c, "state", m))
    t0 = time.time()
    while time.time() - t0 < dur and not rospy.is_shutdown():
        time.sleep(0.2)
        # mavros state 1Hz, 等首帧(踩坑 4)
        if c.state is not None and len(c.img_l) > 5 and len(c.imu) > 100:
            break
    time.sleep(1.0)

    ok = True

    def report(name, good, detail):
        nonlocal ok
        print("[%s] %s: %s" % ("绿" if good else "红", name, detail))
        ok = ok and good

    if not c.img_l or not c.imu:
        print("[红] 无图像或 IMU 数据, 全项失败")
        sys.exit(1)
    img_med = sorted(c.img_l)[len(c.img_l) // 2]
    imu_med = sorted(c.imu)[len(c.imu) // 2]
    d = img_med - imu_med
    report("stamp 同域", abs(d) < 1.0,
           "img-imu 中位差 %+.3e s%s" % (d, " (1.79e9 级=分裂!)" if abs(d) > 1e6 else ""))
    span = max(c.img_l) - min(c.img_l)
    hz_l = (len(c.img_l) - 1) / span if span > 0.1 else 0
    hz_r = (len(c.img_r) - 1) / (max(c.img_r) - min(c.img_r)) if c.img_r and max(c.img_r) > min(c.img_r) + 0.1 else 0
    report("双目频率", hz_l > 15 and hz_r > 15, "L %.1fHz R %.1fHz" % (hz_l, hz_r))
    ispan = max(c.imu) - min(c.imu)
    hz_i = (len(c.imu) - 1) / ispan if ispan > 0.1 else 0
    report("IMU 频率", hz_i > 100, "%.1fHz (需 >100, mavcmd long 511 105 5000 0 提频)" % hz_i)
    report("真值 model_states", c.gt > 0, "%d 帧" % c.gt)
    report("mavros connected", c.state is not None and bool(c.state.connected),
           "connected=%s" % (c.state.connected if c.state else "无消息"))
    print("RESULT: %s" % ("ALL_GREEN 放行" if ok else "RED_ITEM 禁止起飞/启动 vins"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
