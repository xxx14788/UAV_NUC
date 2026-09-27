#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U8.3 dy 基线机制追查: bagA 静止段按图像行分桶测 dy。

W1 实测静态 dy-RMS 2.16px(合成 0.065px)≈0.24° 垂直失配, SDF rig RPY=0
理论应为 0。分桶裁决:
  - 上/中/下带 dy 中位近似相等(常数) → 整体垂直失配(rig 高差/俯仰安装差)
  - dy 随行线性变化 → roll 失配
  - dy 随列(disparity)变化 → vergence(深度相关)
  - 各带 std 大而中位≈0 → LK 噪声主导
对照 SDF pose(y=±0.05 基线, z=0.03, RPY=0)反推: 0.24° 在 rig 上对应
tan(0.24°)*0.10m(基线) ≈ 0.42mm 量级安装差/或 vergence 角。

用法: python3 dy_row_profile.py <bag> [--pairs 60] [--static-sec 20]
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
    ap.add_argument("--pairs", type=int, default=60)
    ap.add_argument("--static-sec", type=float, default=20.0)
    args = ap.parse_args()

    rows = collections.defaultdict(list)   # bucket -> [(dy_med, n)]
    cols_by_disp = collections.defaultdict(list)
    npairs = 0
    with rosbag.Bag(args.bag, "r") as b:
        buf = {}
        for topic, msg, t in b.read_messages(topics=[LT, RT]):
            if t.to_sec() > b.get_start_time() + args.static_sec:
                break
            buf.setdefault(topic, []).append(msg)
            if len(buf.get(LT, [])) > args.pairs and len(buf.get(RT, [])) > args.pairs:
                break
    L, Rr = buf.get(LT, [])[:args.pairs], buf.get(RT, [])[:args.pairs]
    n = min(len(L), len(Rr))
    H = L[0].height
    bands = [(0, H // 3, "上"), (H // 3, 2 * H // 3, "中"), (2 * H // 3, H, "下")]

    for i in range(n):
        li, ri = to_gray(L[i]), to_gray(Rr[i])
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
        # 立体内点: dx 为负(右相机向左看)且 |dx| 在合理视差范围
        inl = (d[:, 0] < -0.5) & (d[:, 0] > -90) & (np.abs(d[:, 1]) < 12)
        pts0, dy, dx = pts0[inl], d[inl, 1], d[inl, 0]
        if len(dy) < 20:
            continue
        npairs += 1
        for (a, b_, name) in bands:
            sel = (pts0[:, 1] >= a) & (pts0[:, 1] < b_)
            if sel.sum() >= 8:
                rows[name].append((float(np.median(dy[sel])), int(sel.sum())))
        # 按 disparity 三分桶(近/中/远), 检验 vergence(depth 依赖)
        disp = -dx
        for q, name in ((0.33, "近(大视差)"), (0.66, "中"), (1.01, "远(小视差)")):
            pass
        d1, d2 = np.percentile(disp, 33), np.percentile(disp, 66)
        for name, sel in (("近(大视差)", disp >= d2), ("中视差", (disp >= d1) & (disp < d2)),
                          ("远(小视差)", disp < d1)):
            if sel.sum() >= 8:
                cols_by_disp[name].append(float(np.median(dy[sel])))

    print("样本对 %d" % npairs)
    print("\n按行分带 dy(中位 px):")
    for name in ("上", "中", "下"):
        if rows[name]:
            m = np.array([r[0] for r in rows[name]])
            print("  %-2s带: dy_med=%+.3f px  帧间std=%.3f  n帧=%d" %
                  (name, np.median(m), m.std(), len(m)))
    print("\n按视差分桶 dy(中位 px, vergence 检验):")
    for name in ("近(大视差)", "中视差", "远(小视差)"):
        if cols_by_disp[name]:
            m = np.array(cols_by_disp[name])
            print("  %s: dy_med=%+.3f px (帧间std=%.3f)" % (name, np.median(m), m.std()))

    # 常数 vs 随机 裁决
    meds = {name: np.median([r[0] for r in rows[name]]) for name in ("上", "中", "下")}
    if all(abs(v) > 0.5 for v in meds.values()):
        spread = max(meds.values()) - min(meds.values())
        if spread < 0.4:
            print("\n判决: 三带 dy 近似相等(常数 %+.2f px) → 整体垂直失配"
                  "(SDF rig 高差/俯仰安装差), 非随机噪声" % np.mean(list(meds.values())))
        else:
            print("\n判决: dy 随行变化(上%+.2f 中%+.2f 下%+.2f) → roll/俯仰失配梯度" %
                  (meds["上"], meds["中"], meds["下"]))
    else:
        print("\n判决: 各带 dy 中位≈0 → LK 噪声主导, 无系统性失配")
    print("对照: fx≈468, 2.16px ≈ %.3f° ; SDF 基线 0.10m 上 0.24° ≈ tan(0.24°)*100mm ≈ %.2fmm 高差等效" %
          (np.degrees(np.arctan(2.16 / 468)), np.tan(np.radians(0.24)) * 100))


if __name__ == "__main__":
    main()
