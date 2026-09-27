#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W13-1: 停顿机制分解（T3 续篇任务书 W13 离线件）。

用 /gazebo/model_states 真值（与 analyze_flight.py 到位口径一致，
odom 系 = gazebo − (1.01,0.98)）划分巡航段（goal 发布 → 首次到位
<0.5m），统计停顿（|v|<0.1m/s 持续>0.5s）与 replan 事件
（/position_cmd.trajectory_id 变化代理）的对齐：
  - 停顿占比（P3 基线 12.6-24.5%）
  - adjacent（停顿邻接 replan <0.3s 或区间内含 replan）= 重规划等待型
  - mid_traj = 速度规划保守型

用法: python3 stoppage_analysis.py BAG [BAG...] [--t0 S] [--t1 S] [--vth 0.1]
"""

import argparse
import math
import sys

import numpy as np

try:
    import rosbag
except ImportError:
    sys.stderr.write("需要 ROS1 环境\n")
    sys.exit(1)

BIRTH = (1.01, 0.98)  # iris 出生 gazebo 偏移


def analyze(path, t0, t1, vth, hold=0.5, adj=0.3):
    cmds, ts, vv, pos = [], [], [], []
    goals = []
    with rosbag.Bag(path) as bag:
        lo = bag.get_start_time() + t0
        hi = bag.get_start_time() + t1
        for topic, msg, t in bag.read_messages(
                topics=['/position_cmd', '/gazebo/model_states',
                        '/move_base_simple/goal']):
            tsx = t.to_sec()
            if not (lo <= tsx <= hi):
                continue
            if topic == '/position_cmd':
                cmds.append((tsx, msg.trajectory_id))
            elif topic == '/move_base_simple/goal':
                goals.append((tsx, msg.pose.position.x, msg.pose.position.y,
                              msg.pose.position.z))
            else:
                idx = [k for k, n in enumerate(msg.name) if 'iris' in n]
                if not idx:
                    continue
                i = idx[0]
                p = msg.pose[i].position
                w = msg.twist[i].linear
                ts.append(tsx)
                vv.append(math.sqrt(w.x**2 + w.y**2 + w.z**2))
                pos.append((p.x - BIRTH[0], p.y - BIRTH[1], p.z))
    if len(ts) < 100 or not goals:
        return None
    ts = np.array(ts)
    vv = np.array(vv)
    pos = np.array(pos)
    # goal 批次：相邻 <10s 为同批（harness 重发），取末批首条为巡航起点
    goals.sort()
    batches = [[goals[0]]]
    for g in goals[1:]:
        if g[0] - batches[-1][-1][0] < 10.0:
            batches[-1].append(g)
        else:
            batches.append([g])
    goal = batches[-1][0]
    d = np.linalg.norm(pos - np.array(goal[1:]), axis=1)
    m = ts > goal[0]
    near = np.where(m & (d < 0.5))[0]
    if len(near) == 0:
        return None
    b0 = ts[near[0]]
    a0 = ts[np.searchsorted(ts, goal[0])]
    w = (ts >= a0) & (ts <= b0)
    ts_w, vv_w = ts[w], vv[w]
    dur = ts_w[-1] - ts_w[0]
    if dur < 5:
        return None

    stop = vv_w < vth
    spans = []
    i = 0
    while i < len(stop):
        if stop[i]:
            j = i
            while j + 1 < len(stop) and stop[j + 1]:
                j += 1
            if ts_w[j] - ts_w[i] >= hold:
                spans.append((ts_w[i], ts_w[j]))
            i = j + 1
        else:
            i += 1
    stop_total = sum(b - a for a, b in spans)

    tc = np.array([c[0] for c in cmds])
    tid = np.array([c[1] for c in cmds])
    replans = np.asarray(
        tc[np.where(np.diff(tid) != 0)[0] + 1] if len(tc) > 1 else [])
    replans = replans[(replans >= a0) & (replans <= b0)]

    n_adjacent = n_mid = 0
    for (a, b) in spans:
        near_r = replans[(replans >= a - adj) & (replans <= b + adj)] \
            if len(replans) else []
        if len(near_r) > 0:
            n_adjacent += 1
        else:
            n_mid += 1

    return {
        'bag': path.split('/')[-1].replace('flight_', '').replace('.bag', ''),
        'fly_dur_s': round(dur, 1),
        'stop_pct': round(100 * stop_total / dur, 1),
        'n_stops': len(spans),
        'adjacent': n_adjacent,
        'mid_traj': n_mid,
        'adj_pct': round(100 * n_adjacent / max(1, len(spans)), 1),
    }


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
        print('无有效巡航段（需 bag 含 goal + model_states + 到位<0.5m）')
        return
    cols = ['bag', 'fly_dur_s', 'stop_pct', 'n_stops', 'adjacent',
            'mid_traj', 'adj_pct']
    print('\n=== W13-1 停顿-replan 对齐（真值口径; adjacent=邻接replan'
          '=重规划等待型; adj_pct高→改 thresh_replan 系参数有效）===')
    print('%-18s %10s %8s %7s %8s %8s %7s' % tuple(cols))
    for r in rows:
        print('%-18s %10s %8s %7s %8s %8s %7s' % (
            r['bag'][:18], r['fly_dur_s'], r['stop_pct'], r['n_stops'],
            r['adjacent'], r['mid_traj'], r['adj_pct']))


if __name__ == '__main__':
    main()
