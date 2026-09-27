#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U3 E18-lite: bag 图像降帧/降分辨率离线变换(零锁近似 E18)。

真 60Hz 需改 SDF 重录(持锁);帧率向下(30→20→10Hz)与分辨率向下
(640×480→320×240, 等效 2x2 binning: fx/2 fy/2 cx/2 cy/2)可离线变换,
裁决 H-C 的方向性(帧率 vs 带宽谁主导 VINS 短板)。

用法: python3 t2_bag_transform.py <in.bag> <out.bag> [--img-dec 2] [--half] [--imu-keep]
只变换双目 image_raw + camera_info(K 同步缩放);其余话题原样。
"""
import argparse

import cv2
import numpy as np
import rosbag
from sensor_msgs import image_encodings

IMGS = ("/iris_stereo_vins/vins_cam_left/image_raw",
        "/iris_stereo_vins/vins_cam_right/image_raw")
CINFOS = ("/iris_stereo_vins/vins_cam_left/camera_info",
          "/iris_stereo_vins/vins_cam_right/camera_info")


def to_gray(msg):
    arr = np.frombuffer(msg.data, dtype=np.uint8)
    if msg.encoding in ("bgr8", "rgb8"):
        return cv2.cvtColor(arr.reshape(msg.height, msg.width, 3), cv2.COLOR_BGR2GRAY)
    return arr.reshape(msg.height, msg.width)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--img-dec", type=int, default=1, help="图像抽帧系数(2=减半)")
    ap.add_argument("--half", action="store_true", help="分辨率减半(320x240)")
    a = ap.parse_args()

    counters = {t: 0 for t in IMGS}
    n_keep = n_drop = n_ci = 0
    with rosbag.Bag(a.src, "r") as bi, rosbag.Bag(a.dst, "w") as bo:
        for tp, m, t in bi.read_messages():
            if tp in IMGS:
                counters[tp] += 1
                if counters[tp] % a.img_dec != 1:
                    n_drop += 1
                    continue
                if a.half:
                    g = to_gray(m)
                    small = cv2.resize(g, (m.width // 2, m.height // 2),
                                       interpolation=cv2.INTER_AREA)
                    m.height, m.width = small.shape[0], small.shape[1]
                    m.encoding = "mono8"
                    m.step = m.width
                    m.data = small.tobytes()
                    m.is_bigendian = 0
                bo.write(tp, m, t)
                n_keep += 1
            elif tp in CINFOS and a.half:
                m.K[0] /= 2; m.K[1] *= 1; m.K[2] /= 2
                m.K[3] *= 1; m.K[4] /= 2; m.K[5] /= 2
                m.P[0] /= 2; m.P[2] /= 2; m.P[5] /= 2
                m.height //= 2
                m.width //= 2
                bo.write(tp, m, t)
                n_ci += 1
            else:
                bo.write(tp, m, t)
    print("keep=%d drop=%d cinfos=%d -> %s" % (n_keep, n_drop, n_ci, a.dst))


if __name__ == "__main__":
    main()
