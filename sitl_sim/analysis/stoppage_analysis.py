#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W13-1: 停顿机制分解（T3 续篇任务书 W13 离线件）。

把飞行段的停顿（|v|<0.1m/s 持续>0.5s）与 replan 事件
（/position_cmd.trajectory_id 变化；/drone_0_planning/bspline 未录制时的
代理，新录制清单的 bag 可直接换用 bspline 时间轴）对齐统计：
  - 停顿占比（基线 12.6-24.5%）
  - 每停顿区间内/近旁的 replan 个数
  - 停顿起点落在 replan 后多少 ms（正=紧跟 replan，重规划等待型；
    负且区间内无 replan=轨迹段中停顿，速度规划保守型）
  - 分类占比：replan-adjacent（区间起点距 replan <0.3s 或区间内含
    replan）vs mid-trajectory

用法: python3 stoppage_analysis.py BAG [BAG...] [--t0 S] [--t1 S] [--vth 0.1]
"""

import argparse
import sys

import numpy as np

try:
    import rosbag
except ImportError:
    sys.stderr.write("需要 ROS1 环境\n")
    sys.exit(1)


def analyze(path, t0, t1, vth, hold=0.5, adj=0.3):
    cmds, vels = [], []
    with rosbag.Bag(path) as bag:
        lo = bag.get_start_time() + t0
        hi = bag.get_start_time() + t1
        for topic, msg, t in bag.read_messages(
                topics=['/position_cmd', '/mavros/local_position/odom']):
            ts = t.to_sec()
            if not (lo <= ts <= hi):
                continue
            if topic == '/position_cmd':
                cmds.append((ts, msg.trajectory_id))
            else:
                v = msg.twist.twist.linear
                vels.append((ts, math_hypot3(v.x, v.y, v.z)))
    if len(vels) < 50:
        return None
    tv = np.array([x[0] for x in vels])
    vv = np.array([x[1] for x in vels])
    # 飞行段：空中（|z| 无法从这里取——用 odom 全量重读 z）
    # 飞行窗口 = 连续 z>0.3 的区间（排除地面静置大段污染停顿占比）
    with rosbag.Bag(path) as bag:
        zs = [(t.to_sec(), msg.pose.pose.position.z) for _, msg, t in
              bag.read_messages(topics=['/mavros/local_position/odom'])]
    tz = np.array([z[0] for z in zs])
    zz = np.array([z[1] for z in zs])
    win = []
    i = 0
    while i < len(zz):
        if zz[i] > 0.3:
            j = i
            while j + 1 < len(zz) and zz[j + 1] > 0.3:
                j += 1
            if tz[j] - tz[i] >= 3.0:
                win.append((tz[i], tz[j]))
            i = j + 1
        else:
            i += 1
    if not win:
        return None
    # 取最长空中窗
    a0, b0 = max(win, key=lambda w: w[1] - w[0])
    m = (tv >= a0) & (tv <= b0)
    tv, vv = tv[m], vv[m]
    dur = tv[-1] - tv[0]
    if dur < 5:
        return None

    stop = vv < vth
    # 停顿区间
    spans = []
    i = 0
    while i < len(stop):
        if stop[i]:
            j = i
            while j + 1 < len(stop) and stop[j + 1]:
                j += 1
            if tv[j] - tv[i] >= hold:
                spans.append((tv[i], tv[j]))
            i = j + 1
        else:
            i += 1
    stop_total = sum(b - a for a, b in spans)

    tc = np.array([c[0] for c in cmds])
    tid = np.array([c[1] for c in cmds])
    replans = np.asarray(
        tc[np.where(np.diff(tid) != 0)[0] + 1] if len(tc) > 1 else [])

    n_adjacent = n_mid = 0
    gaps = []
    for (a, b) in spans:
        near = replans[(replans >= a - adj) & (replans <= b + adj)]
        if len(near) > 0:
            n_adjacent += 1
            gaps.append(float(near[0] - a) * 1000)
        else:
            n_mid += 1
            d = np.min(np.abs(replans - a)) if len(replans) else float('nan')
            gaps.append(float(d))

    return {
        'bag': path.split('/')[-2],
        'fly_dur_s': round(dur, 1),
        'stop_pct': round(100 * stop_total / dur, 1),
        'n_stops': len(spans),
        'adjacent': n_adjacent,
        'mid_traj': n_mid,
        'adj_pct': round(100 * n_adjacent / max(1, len(spans)), 1),
    }


def math_hypot3(a, b, c):
    import math
    return math.sqrt(a * a + b * b + c * c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bags', nargs='+')
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=1e9)
    ap.add_argument('--vth', type=float, default=0.1)
    args = ap.parse_args()
    rows = []
    for p in args.bags:
        r = analyze(p, args.t0, args.t1, args.vth)
        if r:
            rows.append(r)
    if not rows:
        print('无有效飞行段')
        return
    cols = ['bag', 'fly_dur_s', 'stop_pct', 'n_stops', 'adjacent',
            'mid_traj', 'adj_pct']
    print('\n=== W13-1 停顿-replan 对齐（adjacent=停顿与replan邻接; '
          'adj_pct高=重规划等待主导）===')
    print('%-18s %10s %8s %7s %8s %8s %7s' % tuple(cols))
    for r in rows:
        print('%-18s %10s %8s %7s %8s %8s %7s' % (
            r['bag'][:18], r['fly_dur_s'], r['stop_pct'], r['n_stops'],
            r['adjacent'], r['mid_traj'], r['adj_pct']))


if __name__ == '__main__':
    main()
