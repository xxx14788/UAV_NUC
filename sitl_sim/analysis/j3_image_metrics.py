#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-J3 六维图像侧指标（C09 E3①预备/E6/E7）.

输入: j3_extract_frames.py 产出的帧目录（含 manifest.json）。
指标（每帧）:
  曝光  p_sat=P(I<=2)+P(I>=253)、直方图动态范围 p99-p1、中位亮度、帧间 γ(配对帧)
  纹理  gFT(0.01,30,150) 角点数(VINS 参数复刻)、梯度幅值 P50、梯度方向直方图
        集中度 maxbin 占比(重复纹理鉴别, R16 反噬预警)
  噪声  D12 平坦区帧间差分 sigma_hat = sqrt(Var(dI)/2)（平坦 patch=16x16 块
        梯度幅值最低 25% 分位集合）
  模糊  梯度方向能量各向同性度 = 方向能量最大 bin / 平均 bin（sinc² 塌缩检测,
        sim 零假设=各向同性）
聚合: 全体 + 分段(seg) 分位数 P10/P50/P90 + n=30 D11 顺序统计量 CI
（q90: [X24,X29]@93.2%; median: [X10,X21]@95.7%; 其他 n 按二项精确分布求 90% CI）。

用法: python3 j3_image_metrics.py --frames-dir DIR --out metrics.json
"""
import argparse
import json
import math
import os

import cv2
import numpy as np

PATCH = 16
FT_QUALITY, FT_MINDIST, FT_MAXCNT = 0.01, 30, 150   # VINS feature_tracker 参数复刻


def binom_ci(n, q, cov=0.90):
    """顺序统计量 CI: 求最小 [r,s] 使 P(r<=K<=s)>=cov, K~Bin(n,q)."""
    def pmf(k):
        if k < 0 or k > n:
            return 0.0
        # log-space 二项概率
        logp = (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                + k * math.log(q) + (n - k) * math.log(1 - q))
        return math.exp(logp)
    cdf = 0.0
    probs = [pmf(k) for k in range(n + 1)]
    target = (1 - cov) / 2
    lo = 0
    acc = 0.0
    for k in range(n + 1):
        acc += probs[k]
        if acc > target:
            lo = k
            break
    acc = 0.0
    hi = n
    for k in range(n, -1, -1):
        acc += probs[k]
        if acc > target:
            hi = k
            break
    return lo, hi  # 0-based 顺序统计量下标 [lo, hi]


def quant(x, qs):
    x = np.asarray(x, dtype=float)
    return {('p%d' % round(q * 100)): float(np.percentile(x, q * 100)) for q in qs}


def aggregate(vals, segs):
    """全体+分层分位数; n>=8 时附 D11 CI（P90 与 median）."""
    vals = np.asarray(vals, dtype=float)
    segs = np.asarray(segs)
    out = {'n': int(vals.size), **quant(vals, [0.10, 0.50, 0.90])}
    if vals.size >= 8:
        lo, hi = binom_ci(vals.size, 0.9)
        sv = np.sort(vals)
        out['p90_ci'] = [float(sv[min(lo, vals.size - 1)]), float(sv[min(hi, vals.size - 1)])]
        lo, hi = binom_ci(vals.size, 0.5)
        out['med_ci'] = [float(sv[min(lo, vals.size - 1)]), float(sv[min(hi, vals.size - 1)])]
    by_seg = {}
    for s in sorted(set(segs.tolist())):
        v = vals[segs == s]
        by_seg[str(int(s))] = {'n': int(v.size), **quant(v, [0.50])}
    out['by_seg_median'] = by_seg
    return out


def frame_metrics(gray, gray_prev=None):
    g = gray.astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    # 曝光
    p_sat = float(np.mean(gray <= 2) + np.mean(gray >= 253))
    p1, p99 = np.percentile(gray, [1, 99])
    m = {
        'p_sat': p_sat,
        'hist_range_p1_p99': float(p99 - p1),
        'med_gray': float(np.median(gray)),
    }

    # 纹理: VINS 参数复刻角点 + 梯度统计 + 方向集中度
    corners = cv2.goodFeaturesToTrack(gray, FT_MAXCNT, FT_QUALITY, FT_MINDIST)
    m['corners_gFT'] = 0 if corners is None else int(len(corners))
    m['grad_med'] = float(np.median(mag))
    ang = np.arctan2(gy, gx)  # [-pi,pi]
    e = mag[mag > 1e-3]
    a = ang[mag > 1e-3]
    if e.size > 100:
        hb, _ = np.histogram(a, bins=18, range=(-math.pi, math.pi),
                             weights=e, density=False)
        m['grad_dir_maxbin_frac'] = float(hb.max() / hb.sum())
        m['grad_dir_entropy_norm'] = float(
            -(hb / hb.sum() * np.log(hb / hb.sum() + 1e-12)).sum() / math.log(18))
    else:
        m['grad_dir_maxbin_frac'] = float('nan')
        m['grad_dir_entropy_norm'] = float('nan')

    # 噪声: D12 平坦区帧间差分（双口径）
    #   pool: Var(dI)/2 全平坦 patch 池（移动序列下为上界）
    #   p25 : 每 patch σ̂ 分布 P25（运动伪差分 patch 级稀疏, 低分位抗污染）
    if gray_prev is not None:
        h, w = g.shape
        nh, nw = h // PATCH, w // PATCH
        pmag = np.zeros((nh, nw), dtype=np.float32)
        for i in range(nh):
            for j in range(nw):
                pmag[i, j] = mag[i * PATCH:(i + 1) * PATCH, j * PATCH:(j + 1) * PATCH].mean()
        thr = np.percentile(pmag, 25)  # 平坦=梯度幅值最低 25% 分位 patch
        stds = []
        for i in range(nh):
            for j in range(nw):
                if pmag[i, j] <= thr:
                    d = (gray[i * PATCH:(i + 1) * PATCH, j * PATCH:(j + 1) * PATCH]
                         .astype(np.float32)
                         - gray_prev[i * PATCH:(i + 1) * PATCH, j * PATCH:(j + 1) * PATCH]
                         .astype(np.float32))
                    stds.append(d.std() / math.sqrt(2.0))
        if stds:
            s = np.sort(np.asarray(stds))
            m['d12_sigma_flat'] = float(np.sqrt(np.mean(np.square(stds))))  # pool 口径
            m['d12_sigma_p25'] = float(s[int(0.25 * (len(s) - 1))])          # 抗运动口径
            m['d12_flat_frac'] = float(len(stds) / (nh * nw))
        else:
            m['d12_sigma_flat'] = float('nan')
            m['d12_sigma_p25'] = float('nan')
            m['d12_flat_frac'] = 0.0
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames-dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    with open(os.path.join(args.frames_dir, 'manifest.json')) as f:
        man = json.load(f)
    frames = [fr for fr in man['frames'] if fr['tag'] in ('', 'next')]
    cache = {}
    per_frame = []
    for fr in frames:
        img = cv2.imread(os.path.join(args.frames_dir, fr['file']), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        cache[fr['file']] = img
    for fr in frames:
        if fr['file'] not in cache:
            continue
        prev = None
        if fr['tag'] == 'next':  # next 帧与其配对的选中帧相邻序号
            base = fr['file'].replace('_next', '')
            prev = cache.get(base)
        m = frame_metrics(cache[fr['file']], prev)
        m.update({'file': fr['file'], 'topic': fr['topic'], 'seg': fr['seg'], 'tag': fr['tag']})
        per_frame.append(m)
        # D12 差分归属采样点（选中帧）: next 帧算出的 σ̂ 回填到其 pair base
        if fr['tag'] == 'next' and 'd12_sigma_flat' in m:
            base = fr['file'].replace('_next', '')
            for pm in per_frame:
                if pm['file'] == base:
                    pm['d12_sigma_flat'] = m['d12_sigma_flat']
                    pm['d12_sigma_p25'] = m.get('d12_sigma_p25', float('nan'))
                    pm['d12_flat_frac'] = m.get('d12_flat_frac', 0.0)
                    break

    # 聚合: 仅用选中帧（非 next）避免 pair 重复计入
    prim = [m for m in per_frame if m['tag'] == '']
    segs = [m['seg'] for m in prim]

    def agg(key, filt=None):
        v = [(m[key], m['seg']) for m in prim
             if key in m and not math.isnan(m.get(key, float('nan')))
             and (filt is None or filt(m))]
        if not v:
            return {'n': 0}
        return aggregate([x[0] for x in v], [x[1] for x in v])

    out = {
        'frames_dir': os.path.abspath(args.frames_dir),
        'bag': man['bag'],
        'camera_info': man.get('camera_info'),
        'sensor_property': man.get('sensor_property'),
        'n_primary': len(prim),
        'metrics': {
            'p_sat': agg('p_sat'),
            'hist_range_p1_p99': agg('hist_range_p1_p99'),
            'med_gray': agg('med_gray'),
            'corners_gFT': agg('corners_gFT'),
            'grad_med': agg('grad_med'),
            'grad_dir_maxbin_frac': agg('grad_dir_maxbin_frac'),
            'grad_dir_entropy_norm': agg('grad_dir_entropy_norm'),
            'd12_sigma_flat': agg('d12_sigma_flat'),
            'd12_sigma_p25': agg('d12_sigma_p25'),
            'gamma_pair': agg('gamma_pair'),
        },
        'per_frame': per_frame,
    }
    # 帧间增益 gamma（配对帧中位亮度比）: next 帧 med_gray / 选中帧 med_gray
    pairs = {}
    for m in per_frame:
        if m['tag'] == 'next':
            base = m['file'].replace('_next', '')
            pairs[base] = m
    gam = []
    for m in prim:
        if m['file'] in pairs and m['med_gray'] > 5:
            gam.append(pairs[m['file']]['med_gray'] / m['med_gray'])
    if gam:
        out['metrics']['gamma_pair'] = aggregate(gam, [m['seg'] for m in prim if m['file'] in pairs])

    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    b = {k: {kk: vv for kk, vv in v.items() if kk != 'by_seg_median'}
         for k, v in out['metrics'].items() if isinstance(v, dict)}
    print(json.dumps(b, indent=1))


if __name__ == '__main__':
    main()
