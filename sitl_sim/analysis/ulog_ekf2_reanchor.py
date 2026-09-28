#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U4: 传送重锚 ulog 定罪（T3 ulog 线产物）。

对传送轮 ulog 提取 EKF2 重锚证据链：
  1. estimator_aid_src_gnss_pos/vel: innovation、fusion 状态（fused 标志）
  2. estimator_innovation_test_ratios: 越界（>1 = gate 拒绝）
  3. estimator_event_flags: 位置/速度 reset 事件累计
  4. estimator_local_position/vehicle 位置: 识别传送跳变与失控发散时刻
输出时间轴表：传送时刻（位置跳 9m）前后 60s 的 fusion/innovation 演化。

用法: python3 ulog_ekf2_reanchor.py ULG [--win 60] [--csv OUT]
"""

import argparse
import sys

import numpy as np
from pyulog import ULog


def get(u, name):
    for d in u.data_list:
        if d.name == name:
            return d
    return None


def t0_of(u):
    """boot 起始时间戳（第一条消息的时间）。"""
    ts = [d.data['timestamp'][0] for d in u.data_list
          if 'timestamp' in d.data and len(d.data['timestamp'])]
    return min(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ulg')
    ap.add_argument('--win', type=float, default=60.0)
    ap.add_argument('--csv', default=None)
    args = ap.parse_args()

    u = ULog(args.ulg, None)
    base = t0_of(u)

    lp = get(u, 'estimator_local_position')
    if lp is None:
        print('无 estimator_local_position')
        return 2
    t = np.array(lp.data['timestamp']) / 1e6 - base / 1e6
    x = np.array(lp.data['x'])
    y = np.array(lp.data['y'])
    # 传送时刻：位置单步跳 >5m
    step = np.hypot(np.diff(x), np.diff(y))
    dt = np.diff(t)
    jumps = np.where((step > 5.0) & (dt < 0.5))[0]
    if len(jumps) == 0:
        print('%s: 无 >5m 跳变（非传送轮或跳变小于阈值）' % args.ulg)
        tp = None
    else:
        j = jumps[np.argmax(step[jumps])]
        tp = t[j + 1]
        print('传送跳变 t+%.2fs: (%.2f,%.2f)->(%.2f,%.2f) step=%.1fm' %
              (tp, x[j], y[j], x[j + 1], y[j + 1], step[j]))

    # GPS aid src（字段带 [0]/[1] 索引；EKF2 多 instance 分开统计主实例 0）
    for src in ('estimator_aid_src_gnss_pos', 'estimator_aid_src_gnss_vel',
                'estimator_aid_src_mag', 'estimator_aid_src_baro_hgt',
                'estimator_aid_src_gnss_hgt'):
        d = get(u, src)
        if d is None:
            print('%s: 缺' % src)
            continue
        inst = np.array(d.data.get('estimator_instance',
                                   np.zeros(len(d.data['timestamp']))))
        for ei in sorted(set(inst.tolist())):
            mi = inst == ei
            tt = np.array(d.data['timestamp'])[mi] / 1e6 - base / 1e6
            if 'innovation[0]' in d.data:
                a0 = np.array(d.data['innovation[0]'])[mi]
                a1 = np.array(d.data['innovation[1]'])[mi]
                innov = np.hypot(a0, a1)
            else:
                innov = np.array(d.data['innovation'])[mi]
            fused = np.array(d.data['fused'])[mi].astype(bool) \
                if 'fused' in d.data else None
            healthy = np.array(d.data['healthy'])[mi].astype(bool) \
                if 'healthy' in d.data else None
            if tp is None:
                print('%s[inst%d]: |innov| p50=%.2f p95=%.2f max=%.2f '
                      'fused_frac=%.2f' % (
                          src, ei, np.percentile(np.abs(innov), 50),
                          np.percentile(np.abs(innov), 95),
                          np.abs(innov).max(),
                          fused.mean() if fused is not None else -1))
                continue
            print('== %s [instance %d]（传送±%.0fs）==' % (src, ei, args.win))
            for label, mask in (
                    ('传送前', (tt >= tp - args.win) & (tt < tp)),
                    ('传送后0-10s', (tt >= tp) & (tt < tp + 10)),
                    ('传送后10-30s', (tt >= tp + 10) & (tt < tp + 30)),
                    ('传送后30-60s', (tt >= tp + 30) & (tt < tp + 60))):
                if mask.sum() == 0:
                    print('  %-12s 无样本' % label)
                    continue
                f = fused[mask] if fused is not None else np.array([np.nan])
                h = healthy[mask] if healthy is not None else np.array([np.nan])
                print('  %-12s n=%5d |innov| p50=%7.3f p95=%7.3f max=%8.3f '
                      'fused=%.2f healthy=%.2f' % (
                          label, mask.sum(),
                          np.percentile(np.abs(innov[mask]), 50),
                          np.percentile(np.abs(innov[mask]), 95),
                          np.abs(innov[mask]).max(),
                          np.nanmean(f), np.nanmean(h)))

    # 姿态：yaw 序列（传送后 yaw 是否被拉扯/疯转）+ 姿态 innovation
    att = get(u, 'estimator_attitude')
    if att is not None and tp is not None:
        tt = np.array(att.data['timestamp']) / 1e6 - base / 1e6
        print('== estimator_attitude（传送±60s,每5s 采样）==')
        keys = [k for k in ('yaw', 'roll', 'pitch', 'delta_angle_bias[2]')
                if k in att.data]
        idx = np.where((tt > tp - 30) & (tt < tp + 60))[0][::50]
        for k in keys:
            print('  t(s)  ' + '  '.join('%.1f' % (tt[i] - tp) for i in idx[:12]))
            v = att.data[k]
            print('  %-20s ' % k + '  '.join(
                '%.2f' % v[i] for i in idx[:12]))
        # yaw 速率（差分）
        if 'yaw' in att.data:
            y = np.array(att.data['yaw'])
            m = (tt > tp) & (tt < tp + 60)
            if m.sum() > 10:
                dy = np.abs(np.diff(y[m]))
                dtm = np.diff(tt[m])
                rate = np.degrees(dy / np.maximum(dtm, 1e-3))
                print('  yaw 速率(deg/s,传送后60s): p95=%.0f max=%.0f' % (
                    np.percentile(rate, 95), rate.max()))

    # event flags: reset 计数在传送窗内的增量
    ef = get(u, 'estimator_event_flags')
    if ef is not None and tp is not None:
        tt = np.array(ef.data['timestamp']) / 1e6 - base / 1e6
        keys = [k for k in ef.data.keys()
                if 'reset' in k or 'fault' in k or 'gps' in k]
        print('== estimator_event_flags（reset/fault 计数，传送前→后60s）==')
        for k in keys[:12]:
            v = np.array(ef.data[k])
            pre = v[tt < tp][-1] if (tt < tp).any() else 0
            post = v[tt < tp + 60][-1] if (tt < tp + 60).any() else pre
            if int(post) != int(pre):
                print('  %-32s %d -> %d (Δ=%d)' % (k, pre, post, post - pre))
        print('  （未列出的 reset/fault 键传送窗内无增量）')

    # innovation test ratios 越界时刻
    itr = get(u, 'estimator_innovation_test_ratios')
    if itr is not None and tp is not None:
        tt = np.array(itr.data['timestamp']) / 1e6 - base / 1e6
        print('== gate 拒绝（test ratio>1）时长占比（传送后 60s 窗）==')
        for k in ('hpos_test_ratio', 'vel_test_ratio', 'mag_test_ratio',
                  'hgt_test_ratio'):
            if k not in itr.data:
                continue
            v = np.array(itr.data[k])
            m = (tt >= tp) & (tt < tp + 60)
            if m.sum():
                print('  %-16s 超1 占比 %.2f 峰值 %.1f' % (
                    k, (v[m] > 1.0).mean(), v[m].max()))

    if args.csv and tp is not None:
        import csv as _csv
        d = get(u, 'estimator_aid_src_gnss_pos')
        tt = np.array(d.data['timestamp']) / 1e6 - base / 1e6
        with open(args.csv, 'w', newline='') as f:
            w = _csv.writer(f)
            w.writerow(['t_rel_tp', 'innovation', 'fused', 'healthy'])
            m = np.abs(tt - tp) < args.win
            for i in np.where(m)[0][::5]:
                w.writerow([round(tt[i] - tp, 2), d.data['innovation'][i],
                            d.data['fused'][i] if 'fused' in d.data else '',
                            d.data['healthy'][i] if 'healthy' in d.data else ''])
        print('CSV: %s' % args.csv)


if __name__ == '__main__':
    sys.exit(main() or 0)
