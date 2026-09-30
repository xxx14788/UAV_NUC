#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WB3 场景条件性对照(毒源定位):obstacles 带图袋 vs 无障碍带图袋
抽帧(每 N 秒 1 帧,IO 纪律)统计:
  - 梯度分布(强梯度像素占比:|grad|>50 的像素比例)
  - 弱纹理占比(8x8 块 std<5 的块比例=pyrLK 假设违反度)
  - 近距视差代理(左右帧 SAD 匹配粗视差直方图)
  - 图像统计(均值/std=光照/噪声代理)
对照窗:悬停期(26-33s,毒暴发窗)vs 起飞后(34-40s)
用法: wa_scene_contrast.py <bag> <t0> <t1> <label>   # 单袋单窗
"""
import sys, os
import numpy as np
import cv2
import rosbag

BAG = sys.argv[1]
T0, T1 = float(sys.argv[2]), float(sys.argv[3])
LABEL = sys.argv[4]
EVERY = 1.0  # 1 frame per second

def stats(img):
    g = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR565) if img.ndim == 3 else img
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    strong = (mag > 50).mean()
    # weak-texture blocks (8x8)
    h, w = g.shape[:2]
    gs = g[:h // 8 * 8, :w // 8 * 8].reshape(h // 8, 8, w // 8, 8)
    bstd = gs.astype(np.float32).reshape(h // 8, 8, w // 8, 8).std(axis=(1, 3))
    weak = (bstd < 5).mean()
    return g.mean(), g.std(), strong, weak

def stereo_parallax(l, r):
    # coarse SAD parallax on a sparse grid (proxy only)
    if l.ndim == 3: l = cv2.cvtColor(l, cv2.COLOR_BGR2GRAY)
    if r.ndim == 3: r = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
    h, w = l.shape
    best = []
    for y in range(40, h - 40, 60):
        for x in range(60, w - 60, 60):
            tpl = l[y:y+16, x:x+16].astype(np.float32)
            xs = np.arange(max(0, x - 90), min(w - 16, x + 10))
            if len(xs) < 20: continue
            errs = [np.abs(tpl - r[y:y+16, xx:xx+16].astype(np.float32)).mean() for xx in xs]
            i = int(np.argmin(errs))
            best.append(x - xs[i])
    b = np.array(best)
    b = b[np.abs(b) < 90]
    if len(b) < 10: return None
    return np.percentile(b, [10, 50, 90]).tolist(), (b > 40).mean()

rows = []
with rosbag.Bag(BAG, "r") as b:
    t0_bag = b.get_start_time()
    last_t = -10
    for tp, m, ts in b.read_messages(topics=["/iris_stereo_vins/vins_cam_left/image_raw",
                                             "/iris_stereo_vins/vins_cam_right/image_raw"]):
        t = ts.to_sec() - t0_bag
        if t < T0 or t > T1: continue
        if tp.endswith("left") and t - last_t >= EVERY:
            last_t = t
            li = np.frombuffer(m.data, dtype=np.uint8).reshape(m.height, m.width) if m.encoding in ("mono8",) else cv2.cvtColor(np.frombuffer(m.data, dtype=np.uint8).reshape(m.height, m.width, 3), cv2.COLOR_BGR2GRAY)
            rows.append((t,) + stats(li))
print("[%s] window %.0f-%.0fs frames=%d" % (LABEL, T0, T1, len(rows)))
if rows:
    a = np.array(rows)
    print("  mean  img_mean=%.1f img_std=%.1f strong_grad%%=%.3f weak_tex%%=%.3f" %
          (a[:, 1].mean(), a[:, 2].mean(), 100 * a[:, 3].mean(), 100 * a[:, 4].mean()))
    print("  per-sec strong_grad: " + " ".join("%.3f" % v for v in a[:, 3]))
    print("  per-sec weak_tex:    " + " ".join("%.3f" % v for v in a[:, 4]))
