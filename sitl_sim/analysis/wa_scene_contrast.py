#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WB3 场景对照 v2(修 topic 匹配+灰度化)"""
import sys
import numpy as np
import cv2
import rosbag

BAG = sys.argv[1]
T0, T1 = float(sys.argv[2]), float(sys.argv[3])
LABEL = sys.argv[4]
EVERY = 1.0

def to_gray(m):
    a = np.frombuffer(m.data, dtype=np.uint8)
    if m.encoding in ("mono8",):
        return a.reshape(m.height, m.width)
    a = a.reshape(m.height, m.width, -1)
    return cv2.cvtColor(a[:, :, :3], cv2.COLOR_BGR2GRAY)

def stats(g):
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    strong = (mag > 50).mean()
    h, w = g.shape
    gs = g[:h // 8 * 8, :w // 8 * 8].astype(np.float32).reshape(h // 8, 8, w // 8, 8)
    bstd = gs.std(axis=(1, 3))
    weak = (bstd < 5).mean()
    return float(g.mean()), float(g.std()), float(strong), float(weak)

rows = []
with rosbag.Bag(BAG, "r") as b:
    t0 = b.get_start_time()
    last_t = -10.0
    for tp, m, ts in b.read_messages(topics=["/iris_stereo_vins/vins_cam_left/image_raw"]):
        t = ts.to_sec() - t0
        if t < T0 or t > T1:
            continue
        if t - last_t >= EVERY:
            last_t = t
            rows.append((t,) + stats(to_gray(m)))
print("[%s] window %.0f-%.0fs frames=%d" % (LABEL, T0, T1, len(rows)))
if rows:
    a = np.array(rows)
    print("  img_mean=%.1f img_std=%.1f strong_grad%%=%.3f weak_tex%%=%.3f" %
          (a[:, 1].mean(), a[:, 2].mean(), 100 * a[:, 3].mean(), 100 * a[:, 4].mean()))
    print("  per-sec t:      " + " ".join("%5.0f" % v for v in a[:, 0]))
    print("  per-sec strong: " + " ".join("%.3f" % v for v in a[:, 3]))
    print("  per-sec weak:   " + " ".join("%.3f" % v for v in a[:, 4]))
