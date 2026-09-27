#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U6 域卫士自测: 人为制造 stamp 分裂 → 断言 3s 内 DOMAIN SPLIT 告警; 对齐后恢复。

用法(独立端口, 不干扰批跑): python3 t2_domain_guard_selftest.py
判定: 退出码 0=自测通过
"""
import os
import subprocess
import sys
import time

import rospy
from sensor_msgs.msg import Image, Imu

PORT = "11399"


def main():
    master = "http://localhost:%s" % PORT
    os.environ["ROS_MASTER_URI"] = master
    env = dict(os.environ, ROS_MASTER_URI=master)
    core = subprocess.Popen(["rosmaster", "-p", PORT], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    guard = subprocess.Popen(
        ["python3", os.path.expanduser(
            "~/catkin_ws/sitl_sim/analysis/t2_domain_guard.py")],
        env=dict(env, PYTHONUNBUFFERED="1"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    time.sleep(1.5)

    rospy.init_node("selftest_pub", anonymous=True, disable_signals=True)
    img_pub = rospy.Publisher("/iris_stereo_vins/vins_cam_left/image_raw", Image,
                              queue_size=2)
    imu_pub = rospy.Publisher("/mavros/imu/data_raw", Imu, queue_size=10)

    def pub(img_sec, imu_sec):
        im, iu = Image(), Imu()
        im.header.stamp = rospy.Time(img_sec)
        im.width, im.height, im.encoding = 4, 4, "mono8"
        im.data = b"\x00" * 16
        iu.header.stamp = rospy.Time(imu_sec)
        for _ in range(6):
            img_pub.publish(im)
            imu_pub.publish(iu)
            time.sleep(0.1)

    logs = []
    def pump():
        while True:
            line = guard.stdout.readline()
            if not line:
                break
            logs.append(line)

    import threading
    threading.Thread(target=pump, daemon=True).start()

    # 阶段1: 同域(100.x) → 无告警
    pub(100.0, 100.02)
    time.sleep(3.5)
    split_early = any("DOMAIN SPLIT" in l for l in logs)
    print("阶段1 同域: 告警出现=%s(期望 False)" % split_early)

    # 阶段2: 分裂(img=unix 1.79e9, imu=100.x) → 3s 内告警
    pub(1790500000.0, 100.02)
    time.sleep(4.0)
    split_seen = any("DOMAIN SPLIT" in l for l in logs)
    print("阶段2 分裂: DOMAIN SPLIT 告警=%s(期望 True)" % split_seen)

    # 阶段3: 恢复同域 → re-aligned 日志
    pub(100.0, 100.02)
    time.sleep(4.0)
    realign_seen = any("re-aligned" in l for l in logs)
    print("阶段3 恢复: re-aligned=%s(期望 True)" % realign_seen)

    guard.terminate()
    core.terminate()
    ok = (not split_early) and split_seen and realign_seen
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
