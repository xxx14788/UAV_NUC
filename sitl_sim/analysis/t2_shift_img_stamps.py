#!/usr/bin/env python3
"""bag 图像/相机戳域平移重写（T2-W5 卡点工具）。

背景: 共享 roscore 的 /use_sim_time 被并行会话中途翻面时，gazebo 相机戳
(sim 域) 与 mavros IMU 戳(unix 域) 分家，VINS 永远无法对齐（t2w5_p1 bag
实测偏移 -1.79e9 s）。本工具把图像类话题 header.stamp 平移到 IMU 域。

用法: python3 t2_shift_img_stamps.py <in.bag> <out.bag>
依赖: ROS Noetic python3 (rosbag)
"""
import sys

import rosbag


def main():
    src, dst = sys.argv[1], sys.argv[2]
    IMG_TOPICS = ("/iris_stereo_vins/vins_cam_left/image_raw",
                  "/iris_stereo_vins/vins_cam_right/image_raw",
                  "/iris_stereo_vins/vins_cam_left/camera_info",
                  "/iris_stereo_vins/vins_cam_right/camera_info")
    imu_t, img_t = [], []
    imu_bag, img_bag = [], []
    with rosbag.Bag(src, "r") as b:
        for _, m, _t in b.read_messages(topics=["/mavros/imu/data_raw"]):
            imu_t.append(m.header.stamp.to_sec())
            imu_bag.append(_t.to_sec())
            if len(imu_t) > 400:
                break
        for _, m, _t in b.read_messages(topics=[IMG_TOPICS[0]]):
            img_t.append(m.header.stamp.to_sec())
            img_bag.append(_t.to_sec())
            if len(img_t) > 100:
                break
    if not imu_t or not img_t:
        sys.exit("数据不足")
    import numpy as np
    # 用 bag 到达时间(域无关)配对同刻样本求偏移: 对每帧图像找 bag 时间最近
    # 的 IMU，offset = imu_stamp - img_stamp 的中位（真同一时刻，无窗口偏差）
    imu_bag = np.array(imu_bag)
    imu_t = np.array(imu_t)
    offs = []
    for ib, it in zip(img_bag, img_t):
        j = np.argmin(np.abs(imu_bag - ib))
        if abs(imu_bag[j] - ib) < 0.05:  # 配对容差
            offs.append(imu_t[j] - it)
    offs = np.array(offs)
    off = float(np.median(offs))
    print(f"配对样本 {len(offs)}/100，偏移 med={off:+.4f}s "
          f"(p5={np.percentile(offs,5):+.4f} p95={np.percentile(offs,95):+.4f})")
    n = 0
    with rosbag.Bag(src, "r") as bi, rosbag.Bag(dst, "w") as bo:
        for topic, msg, t in bi.read_messages():
            if topic in IMG_TOPICS and hasattr(msg, "header"):
                msg.header.stamp = rospy_Time(off, msg)
                bo.write(topic, msg, t)
                n += 1
            else:
                bo.write(topic, msg, t)
    print(f"平移 {n} 条图像消息 → {dst}")


def rospy_Time(off, msg):
    import rospy
    sec = off + msg.header.stamp.to_sec()
    return rospy.Time.from_sec(sec)


if __name__ == "__main__":
    main()
