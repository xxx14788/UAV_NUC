#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U8.5 T4 移交项: 立体对左缘带 dx 异常排查(T4 判读轮 17/19 帧有左缘带,
dx 区间 -81.3~+13.4 含正值)。

两个独立检验:
  1. LK 列分桶 dx: 按 matched 点列位置分桶(10 列带), 正常 stereo dx=x_R-x_L
     应恒负(右相机向左看); 左缘带 dx 异常(正值/零/突变)=匹配或渲染问题
  2. 列亮度剖面: 左右图逐列均值亮度差, 缝带/黑边会呈现列带状差分

用法: python3 t2_dx_col_profile.py <bag> [--pairs 80] [--static-sec 20]
"""
import argparse
import collections

import cv2
import numpy as np
import rosbag

cv2.setNumThreads(2)

LT = "/iris_stereo_vins/vins_cam_left/image_raw"
RT = "/iris_stereo_vins/vins_cam_right/image_raw"


def to_gray(msg):
    arr = np.frombuffer(msg.data, dtype=np.uint8)
    if msg.encoding in ("bgr8", "rgb8"):
        return cv2.cvtColor(arr.reshape(msg.height, msg.width, 3), cv2.COLOR_BGR2GRAY)
    return arr.reshape(msg.height, msg.width)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("--pairs", type=int, default=80)
    ap.add_argument("--static-sec", type=float, default=20.0)
    a = ap.parse_args()

    buf = {}
    with rosbag.Bag(a.bag, "r") as b:
        t0 = b.get_start_time()
        for tp, m, t in b.read_messages(topics=[LT, RT]):
            if t.to_sec() > t0 + a.static_sec:
                break
            buf.setdefault(tp, []).append(m)
            if len(buf.get(LT, [])) > a.pairs and len(buf.get(RT, [])) > a.pairs:
                break
    L = buf.get(LT, [])[:a.pairs]
    R = buf.get(RT, [])[:a.pairs]
    n = min(len(L), len(R))
    W = L[0].width
    ncol = 10
    edges = [int(W * i / ncol) for i in range(ncol + 1)]

    col_dx = collections.defaultdict(list)
    col_pos = collections.defaultdict(list)
    lum_diff = []
    for i in range(n):
        li, ri = to_gray(L[i]), to_gray(R[i])
        # 检验2: 列亮度差(前 10 帧平均)
        if i < 10:
            lum_diff.append(li.mean(axis=0).astype(float) - ri.mean(axis=0).astype(float))
        p0 = cv2.goodFeaturesToTrack(li, 300, 0.01, 10)
        if p0 is None or len(p0) < 30:
            continue
        p1, st, _ = cv2.calcOpticalFlowPyrLK(li, ri, p0, None,
                                             winSize=(21, 21), maxLevel=3,
                                             criteria=(cv2.TERM_CRITERIA_EPS |
                                                       cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        ok = st.ravel() == 1
        pts0, pts1 = p0[ok].reshape(-1, 2), p1[ok].reshape(-1, 2)
        d = pts1 - pts0
        inl = (d[:, 0] < -0.5) & (d[:, 0] > -90) & (np.abs(d[:, 1]) < 12)
        pts0, dx = pts0[inl], d[inl, 0]
        for k in range(ncol):
            sel = (pts0[:, 0] >= edges[k]) & (pts0[:, 0] < edges[k + 1])
            if sel.sum() >= 6:
                col_dx[k].append((float(np.median(dx[sel])),
                                  float(np.percentile(dx[sel], 5)),
                                  float(np.percentile(dx[sel], 95))))
            # 全量(不筛 stereo 内点)列带 dx —— 左缘带异常若是匹配产物, 在全量里才看得见
            sel2 = ((p0[ok].reshape(-1, 2)[:, 0] >= edges[k]) &
                    (p0[ok].reshape(-1, 2)[:, 0] < edges[k + 1]))
            if sel2.sum() >= 6:
                col_pos[k].append(float(np.median(d[sel2 & ~inl if False else sel2, 0])) if sel2.sum() else np.nan)

    print("样本对 %d, 图宽 %d, 列带宽 %d px" % (n, W, W // ncol))
    print("\n列带(stereo 内点) dx 中位 [p5, p95] px:")
    for k in range(ncol):
        if col_dx[k]:
            m = np.array([x[0] for x in col_dx[k]])
            p5 = np.median([x[1] for x in col_dx[k]])
            p95 = np.median([x[2] for x in col_dx[k]])
            print("  列%2d [%4d-%4d]: dx_med=%+7.2f  p5=%+7.2f p95=%+7.2f  n帧=%d" %
                  (k, edges[k], edges[k + 1], np.median(m), p5, p95, len(m)))

    ld = np.mean(lum_diff, axis=0) if lum_diff else None
    if ld is not None:
        print("\n列亮度差 L-R (左 64 列逐 8 列均值):")
        for c0 in range(0, min(64, W), 8):
            print("  列 %3d-%3d: %+.2f" % (c0, c0 + 8, ld[c0:c0 + 8].mean()))
        print("全图中位列差 %+.2f; 左缘 0-32 列均值 %+.2f vs 中央 %+.2f" %
              (np.median(ld), ld[:32].mean(), ld[W // 2 - 16:W // 2 + 16].mean()))


if __name__ == "__main__":
    main()
