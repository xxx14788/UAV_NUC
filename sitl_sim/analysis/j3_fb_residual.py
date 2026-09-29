#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-J3 双目 FB 残差（C09 E3②/H6; E4 离线复刻版）.

输入: j3_extract_frames.py --pairs 产出的双目帧目录（L*/R* 前缀）。
方法（非仓内管线声明: 离线 LK 复刻, 同 VINS 参数 21x21/3 层/EPS 0.01）:
  时序 FB: 左图 t 角点 -> LK 到左图 t+1 -> FB 回 t, 残差=往返欧氏距离
  立体 FB: 左图 t 角点 -> LK 到右图 t -> FB 回左, 同上
  角点: gFT(0.01, 30, 150)（VINS 复刻）
判读（H6 FPN 立体-时序不对称）: 立体残差尾部（P90/P95/P99）应重于时序。
输出: 两组分布分位数 + D11 CI + 尾部对比 JSON。

用法: python3 j3_fb_residual.py --frames-dir DIR --out fb.json
"""
import argparse
import glob
import json
import math
import os
import re

import cv2
import numpy as np

LK_WIN = (21, 21)
LK_MAXLVL = 3
LK_EPS = 0.01
FT_QUALITY, FT_MINDIST, FT_MAXCNT = 0.01, 30, 150


def binom_ci(n, q, cov=0.90):
    def pmf(k):
        if k < 0 or k > n:
            return 0.0
        logp = (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                + k * math.log(q) + (n - k) * math.log(1 - q))
        return math.exp(logp)
    probs = [pmf(k) for k in range(n + 1)]
    acc, lo = 0.0, 0
    for k in range(n + 1):
        acc += probs[k]
        if acc > (1 - cov) / 2:
            lo = k
            break
    acc, hi = 0.0, n
    for k in range(n, -1, -1):
        acc += probs[k]
        if acc > (1 - cov) / 2:
            hi = k
            break
    return lo, hi


def fb_residual(img_from, img_to, pts):
    if pts is None or len(pts) < 8:
        return None
    p1, st1, _ = cv2.calcOpticalFlowPyrLK(img_from, img_to, pts, None,
                                          winSize=LK_WIN, maxLevel=LK_MAXLVL,
                                          criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, LK_EPS))
    good1 = st1.ravel() == 1
    if good1.sum() < 8:
        return None
    p0, st0, _ = cv2.calcOpticalFlowPyrLK(img_to, img_from, p1, None,
                                          winSize=LK_WIN, maxLevel=LK_MAXLVL,
                                          criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, LK_EPS))
    good0 = st0.ravel() == 1
    if good0.sum() < 8:
        return None
    d = np.linalg.norm(pts[good0].reshape(-1, 2) - p0[good0].reshape(-1, 2), axis=1)
    return d


def stats(vals, label):
    v = np.sort(np.asarray(vals, dtype=float))
    n = v.size
    out = {'label': label, 'n': n,
           'p50': float(np.percentile(v, 50)),
           'p90': float(np.percentile(v, 90)),
           'p95': float(np.percentile(v, 95)),
           'p99': float(np.percentile(v, 99)),
           'median': float(np.median(v))}
    if n >= 8:
        lo, hi = binom_ci(n, 0.9)
        out['p90_ci'] = [float(v[min(lo, n - 1)]), float(v[min(hi, n - 1)])]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames-dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    with open(os.path.join(args.frames_dir, 'manifest.json')) as f:
        man = json.load(f)
    lf = sorted([fr for fr in man['frames']
                 if ('cam_left' in fr['topic'] or 'infra1' in fr['topic']
                     or 'left' in fr['topic']) and fr['tag'] == ''],
                key=lambda x: x['t_rec'])
    rf = sorted([fr for fr in man['frames']
                 if ('cam_right' in fr['topic'] or 'infra2' in fr['topic']
                     or 'right' in fr['topic']) and fr['tag'] == ''],
                key=lambda x: x['t_rec'])
    # 备选: 文件名匹配
    if not lf:
        lf = [dict(file=os.path.basename(p), t_rec=0.0, tag='')
              for p in sorted(glob.glob(os.path.join(args.frames_dir, '*_L*_s*.png')))
              if '_next' not in p]
    if not rf:
        rf = [dict(file=os.path.basename(p), t_rec=0.0, tag='')
              for p in sorted(glob.glob(os.path.join(args.frames_dir, '*_R*_s*.png')))
              if '_next' not in p]
    nf = min(len(lf), len(rf))
    assert nf >= 2, 'need >=2 stereo pairs, got L=%d R=%d' % (len(lf), len(rf))

    seq_t, seq_s = [], []   # (时序残差), (立体残差)
    for i in range(nf):
        li = cv2.imread(os.path.join(args.frames_dir, lf[i]['file']), cv2.IMREAD_GRAYSCALE)
        ri = cv2.imread(os.path.join(args.frames_dir, rf[i]['file']), cv2.IMREAD_GRAYSCALE)
        pts = cv2.goodFeaturesToTrack(li, FT_MAXCNT, FT_QUALITY, FT_MINDIST)
        # 立体 FB
        d = fb_residual(li, ri, pts)
        if d is not None:
            seq_s.append(d)
        # 时序 FB（相邻选中帧）
        if i + 1 < nf:
            ln = cv2.imread(os.path.join(args.frames_dir, lf[i + 1]['file']), cv2.IMREAD_GRAYSCALE)
            d = fb_residual(li, ln, pts)
            if d is not None:
                seq_t.append(d)

    out = {
        'frames_dir': os.path.abspath(args.frames_dir),
        'lk_params': {'win': list(LK_WIN), 'maxLevel': LK_MAXLVL, 'eps': LK_EPS,
                      'gFT': [FT_QUALITY, FT_MINDIST, FT_MAXCNT]},
        'method_note': 'offline LK replica, NOT in-repo pipeline (E4 stopgap declaration)',
        'temporal': [stats(d, 'temporal_fb_t%d' % i) for i, d in enumerate(seq_t)],
        'stereo': [stats(d, 'stereo_fb_t%d' % i) for i, d in enumerate(seq_s)],
    }
    # 合并池（帧池级分布）
    tp = np.concatenate(seq_t) if seq_t else np.array([])
    sp = np.concatenate(seq_s) if seq_s else np.array([])
    if tp.size:
        out['temporal_pool'] = stats(tp, 'temporal_pool')
    if sp.size:
        out['stereo_pool'] = stats(sp, 'stereo_pool')
    if tp.size and sp.size:
        out['h6_tail_compare'] = {
            'p90_ratio_stereo_over_temporal': out['stereo_pool']['p90'] / max(out['temporal_pool']['p90'], 1e-9),
            'h6_prediction': 'stereo tail heavier (ratio > 1) supports FPN asymmetry',
        }
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ('temporal_pool', 'stereo_pool', 'h6_tail_compare')
                      if k in out}, indent=1))


if __name__ == '__main__':
    main()
