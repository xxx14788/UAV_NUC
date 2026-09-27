#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W14-2: 跨会话飞行腿数据库（T3 续篇任务书 W14-2 产物）。

扫描 ~/sitl_sim/bags + smoke_runs + t3_runs 全部 bag，逐腿提取指标：
  日期/来源/场景（goal 与 world 推断）/到位误差(真值口径)/避障最小距离
  (v1|v2 箱表)/速度峰值/停发-悬停段有无(粗签名)/bag 规模
代码版本列由目录-时间手工映射表给出（main 分支提交时间轴）。
输出: legs.csv + legs_summary.txt（人读汇总表）。

用法: python3 leg_database.py [--out docs/analysis/legs.csv] [--skip-huge 8]
  --skip-huge N  跳过 >N GB 的 bag（默认 8，避免深度流大 bag 拖垮扫描）
"""

import argparse
import csv
import glob
import math
import os
import sys

import numpy as np

try:
    import rosbag
    from rosbag import ROSBagUnindexedException
except ImportError:
    sys.stderr.write("需要 ROS1 环境\n")
    sys.exit(1)

BIRTH = (1.01, 0.98)
WORLDS = {
    'v1': [(3.5, 1.0, -1.5, 1.0, 0, 1.8), (5.0, 1.5, -2.5, 1.0, 0, 1.2),
           (4.5, 1.0, -3.5, 1.0, 0, 2.2)],
    'v2': [(3.5, 1.0, -1.5, 1.0, 0, 1.8), (5.0, 1.5, -2.5, 1.0, 0, 1.2),
           (4.5, 1.0, -3.5, 1.0, 0, 2.2), (6.4, 1.0, -2.0, 1.0, 0, 2.8),
           (6.4, 1.0, 0.5, 1.0, 0, 2.8)],
}

# 代码版本映射（main 提交时间轴，粗粒度按日期+时段）
def code_version(path, bag_start):
    d = path
    if '2026-09-26' in d or bag_start.startswith('2026-09-26'):
        return 'pre-T3 (A1-A7 era)'
    if 'V1_' in d or 'V2' in d:
        return 'T3-W2 experiment stack (0de090e-)'
    if 'W7' in d or '2leg' in d:
        return 'T3 v4 stack (095f554: yaw90 + odom reseed)'
    if '2026-09-28' in d or bag_start.startswith('2026-09-28'):
        return 'T3 v4 stack (095f554)'
    if 'teleport' in d:
        return 'T3 v4 stack'
    return 'unknown'


def dist_point_box(p, b):
    cx, sx, cy, sy, z0, z1 = b[0], b[1], b[2], b[3], b[4], b[5]
    dx = max(abs(p[0] - cx) - sx / 2, 0)
    dy = max(abs(p[1] - cy) - sy / 2, 0)
    dz = 0 if z0 <= p[2] <= z1 else min(abs(p[2] - z0), abs(p[2] - z1))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def analyze_bag(path):
    row = {'bag': path.replace(os.path.expanduser('~') + '/', ''),
           'size_GB': round(os.path.getsize(path) / 2**30, 2)}
    goals, ts, pos, vel = [], [], [], []
    with rosbag.Bag(path) as bag:
        st = bag.get_start_time()
        row['date'] = __import__('datetime').datetime.fromtimestamp(
            st).strftime('%Y-%m-%d %H:%M')
        row['version'] = code_version(path, row['date'])
        for topic, m, t in bag.read_messages(
                topics=['/move_base_simple/goal', '/gazebo/model_states',
                        '/mavros/local_position/odom']):
            tsx = t.to_sec()
            if topic == '/move_base_simple/goal':
                goals.append((tsx, m.pose.position.x, m.pose.position.y,
                              m.pose.position.z))
            elif topic == '/gazebo/model_states':
                idx = [k for k, n in enumerate(m.name) if 'iris' in n]
                if not idx:
                    continue
                i = idx[0]
                p = m.pose[i].position
                w = m.twist[i].linear
                ts.append(tsx)
                pos.append((p.x - BIRTH[0], p.y - BIRTH[1], p.z))
                vel.append(math.sqrt(w.x**2 + w.y**2 + w.z**2))
    if len(ts) < 100:
        row['note'] = 'no-truth'
        return row
    ts = np.array(ts)
    pos = np.array(pos)
    vel = np.array(vel)
    row['dur_s'] = round(ts[-1] - ts[0], 0)
    # 目标：末批首条
    if goals:
        goals.sort()
        batches = [[goals[0]]]
        for g in goals[1:]:
            if g[0] - batches[-1][-1][0] < 10.0:
                batches[-1].append(g)
            else:
                batches.append([g])
        g = batches[-1][0]
        row['goal'] = '(%g,%g,%g)' % (g[1], g[2], g[3])
        m = ts > g[0]
        d = np.linalg.norm(pos - np.array(g[1:]), axis=1)
        arr = np.where(m & (d < 0.5))[0]
        row['arrival_m'] = round(float(d[m].min()), 3) if m.any() else None
        row['arrived'] = 'Y' if len(arr) else 'N'
        if len(arr):
            row['conv_s'] = round(ts[arr[0]] - g[0], 1)
        # 路径比（末批 goal→到位 或 bag 末）
        end = ts[arr[0]] if len(arr) else min(ts[-1], g[0] + 150)
        seg = (ts >= g[0]) & (ts <= end)
        if seg.sum() > 10:
            path_len = np.diff(pos[seg], axis=0)
            pl = float(np.linalg.norm(path_len, axis=1).sum())
            straight = float(np.linalg.norm(pos[seg][-1] - pos[seg][0]))
            row['path_ratio'] = round(pl / max(straight, 0.1), 2)
        # 世界推断：路径是否接近 D/E 箱（v2 特有）
        near_de = min(min(dist_point_box(p, b) for b in WORLDS['v2'][3:])
                      for p in pos[seg if goals else slice(None)]) \
            if goals and seg.sum() > 10 else 999
        row['world'] = 'v2?' if near_de < 1.5 else 'v1'
    # 避障（飞行段）与速度峰值
    fly = pos[:, 2] > 0.3
    if fly.any():
        for wname in ('v1', 'v2'):
            dmin = min(min(dist_point_box(p, b) for b in WORLDS[wname])
                       for p in pos[fly])
            row['mindist_%s' % wname] = round(dmin, 3)
        row['vmax'] = round(float(vel[fly].max()), 2)
        # 发散签名：真值 |xy|>10m 或 z<-1
        div = (np.linalg.norm(pos[fly][:, :2], axis=1) > 10) | (pos[fly][:, 2] < -1)
        row['diverged'] = 'Y' if div.any() else 'N'
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser(
        '~/catkin_ws/docs/analysis/legs.csv'))
    ap.add_argument('--skip-huge', type=float, default=8.0)
    args = ap.parse_args()
    home = os.path.expanduser('~')
    bags = []
    for pat in ('%s/sitl_sim/bags/*.bag' % home,
                '%s/sitl_sim/smoke_runs/*/flight.bag' % home,
                '%s/sitl_sim/t3_runs/*/flight.bag' % home):
        bags += sorted(glob.glob(pat))
    rows = []
    for p in bags:
        sz = os.path.getsize(p) / 2**30
        if sz > args.skip_huge:
            rows.append({'bag': p.replace(home + '/', ''),
                         'size_GB': round(sz, 2), 'note': 'skipped-huge'})
            continue
        try:
            rows.append(analyze_bag(p))
        except ROSBagUnindexedException:
            rows.append({'bag': p.replace(home + '/', ''),
                         'size_GB': round(sz, 2), 'note': 'unindexed'})
        except Exception as e:
            rows.append({'bag': p.replace(home + '/', ''),
                         'note': 'err:%s' % type(e).__name__})
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    keys = ['date', 'bag', 'version', 'goal', 'world', 'arrival_m',
            'arrived', 'conv_s', 'path_ratio', 'mindist_v1', 'mindist_v2',
            'vmax', 'diverged', 'dur_s', 'size_GB', 'note']
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in keys})
    print('%d bags -> %s' % (len(rows), args.out))
    ok = [r for r in rows if r.get('arrived') is not None]
    print('有效腿 %d（到达 %d / 未到 %d）' % (
        len(ok), sum(1 for r in ok if r['arrived'] == 'Y'),
        sum(1 for r in ok if r['arrived'] == 'N')))


if __name__ == '__main__':
    main()
