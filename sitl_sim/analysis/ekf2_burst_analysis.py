#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1: EKF2 瞬爆爆点的传感器层解剖（T3 EKF2 自主修复线产物）。

对两段式 bag（2legA/B）在爆点窗口提取：
  1. /mavros/imu/data 的线加速度/角速度/姿态(EKF2) vs gazebo 真值姿态
     ——IMU 原始量是否异常、姿态是否同跳
  2. odom(EKF2) z/y 跳变的精确时序与方向序列
  3. 爆点 vs leg2 起步（再加速）时刻对齐
输出每 bag 一张时序表 + 签名总结。

用法: python3 ekf2_burst_analysis.py BAG [BAG...] [--win 25]
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

BIRTH = (1.01, 0.98)


def yaw_of(w, x, y, z):
    return math.atan2(2 * (x * y + w * z), 1 - 2 * (y * y + z * z))


def quat_to_euler(w, x, y, z):
    sinr = 2 * (w * x + y * z)
    cosr = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr, cosr)
    sinp = 2 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 \
        else math.asin(sinp)
    yaw = yaw_of(w, x, y, z)
    return roll, pitch, yaw


def load(path):
    imu, odo, tru = [], [], []
    with rosbag.Bag(path) as bag:
        for topic, m, t in bag.read_messages(
                topics=['/mavros/imu/data',
                        '/mavros/local_position/odom',
                        '/gazebo/model_states']):
            ts = t.to_sec()
            if topic == '/mavros/imu/data':
                a = m.linear_acceleration
                g = m.angular_velocity
                o = m.orientation
                imu.append((ts, a.x, a.y, a.z, g.x, g.y, g.z,
                            o.w, o.x, o.y, o.z))
            elif topic == '/mavros/local_position/odom':
                p = m.pose.pose.position
                o = m.pose.pose.orientation
                odo.append((ts, p.x, p.y, p.z, o.w, o.x, o.y, o.z))
            else:
                idx = [k for k, n in enumerate(m.name) if 'iris' in n]
                if not idx:
                    continue
                p = m.pose[idx[0]].position
                tru.append((ts, p.x - BIRTH[0], p.y - BIRTH[1], p.z))
    return (np.array(imu), np.array(odo), np.array(tru))


def find_burst(odo, t0):
    """odom z 的最大单步跳变（|dz|>0.5 且瞬时速率>5m/s）。"""
    tz = odo[:, 0] - t0
    dz = np.diff(odo[:, 3])
    dt = np.diff(odo[:, 0])
    rate = np.abs(dz) / np.maximum(dt, 1e-3)
    cand = np.where((np.abs(dz) > 0.5) & (rate > 5.0))[0]
    if len(cand) == 0:
        return None
    return cand[np.argmax(np.abs(dz[cand]))]  # index i: 跳变发生在 i→i+1


def analyze(path, win):
    imu, odo, tru = load(path)
    if len(imu) == 0 or len(odo) == 0:
        print('%s: 缺话题' % path)
        return
    t0 = odo[0, 0]
    name = path.split('/')[-2]
    bi = find_burst(odo, t0)
    if bi is None:
        print('%s: 未发现 z 爆点（|dz|>0.5 & >5m/s）' % name)
        return
    tb = odo[bi + 1, 0] - t0
    print('\n===== %s =====' % name)
    print('爆点 t+%.2fs: z %.2f -> %.2f (跳 %.2fm);'
          ' y %.2f -> %.2f' % (
              tb, odo[bi, 3], odo[bi + 1, 3],
              odo[bi + 1, 3] - odo[bi, 3],
              odo[bi, 2], odo[bi + 1, 2]))
    # 前后 y/z 的连环跳（±win 秒内所有 |step|>0.3m）
    lo, hi = max(0, bi - 300), min(len(odo) - 1, bi + 300)
    print('-- 爆点±10s 内 |step|>0.3m 的 odom 跳变序列 --')
    for k in range(lo, hi):
        step = np.linalg.norm(odo[k + 1, 1:4] - odo[k, 1:4])
        if step > 0.3:
            print('  t+%6.2f (%.2f,%.2f,%.2f)->(%.2f,%.2f,%.2f) |d|=%.2f' % (
                odo[k + 1, 0] - t0, *odo[k, 1:4], *odo[k + 1, 1:4], step))
    # IMU 在爆点前后 3s 的形态
    mi = np.searchsorted(imu[:, 0], odo[bi, 0] - 3.0)
    mj = np.searchsorted(imu[:, 0], odo[bi + 1, 0] + 3.0)
    seg = imu[max(0, mi):mj]
    if len(seg):
        print('-- IMU 爆点±3s: |acc| p50=%.2f p95=%.2f max=%.2f (g=9.81);'
              ' |gyro| p95=%.2f rad/s --' % (
                  np.percentile(np.linalg.norm(seg[:, 1:4], axis=1), 50),
                  np.percentile(np.linalg.norm(seg[:, 1:4], axis=1), 95),
                  np.linalg.norm(seg[:, 1:4], axis=1).max(),
                  np.percentile(np.linalg.norm(seg[:, 4:7], axis=1), 95)))
        # EKF2 姿态（IMU 话题携带）在爆点是否跳变
        eul = np.array([quat_to_euler(*seg[k, 7:11]) for k in range(len(seg))])
        de = np.abs(np.diff(eul[:, 0]))  # roll 步进
        kmax = np.argmax(de)
        print('   EKF2姿态 roll 最大单步 %.2f°(t+%.2f), pitch %.2f°,'
              ' yaw %.2f°' % (
                  math.degrees(de[kmax]),
                  seg[kmax + 1, 0] - t0,
                  math.degrees(np.abs(np.diff(eul[:, 1])).max()),
                  math.degrees(np.abs(np.diff(eul[:, 2])).max())))
    # 真值在爆点±2s 是否同跳（真值不该跳——跳=物理真动）
    ti = np.searchsorted(tru[:, 0], odo[bi, 0] - 2.0)
    tj = np.searchsorted(tru[:, 0], odo[bi + 1, 0] + 2.0)
    tseg = tru[max(0, ti):tj]
    if len(tseg) > 5:
        tstep = np.linalg.norm(np.diff(tseg[:, 1:4], axis=0), axis=1)
        # 真值 250Hz，正常运动 <0.02m/步
        print('-- 真值爆点±2s 最大单步 %.3fm（>0.05=物理真动，'
              '<=0.02=纯估计跳）--' % tstep.max())
    # leg2 起步时刻（对齐用）：goal 批次后首个 |v|>0.5
    print('-- 爆点 vs 再加速对齐：见上表时序 --')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bags', nargs='+')
    ap.add_argument('--win', type=float, default=25.0)
    args = ap.parse_args()
    for p in args.bags:
        try:
            analyze(p, args.win)
        except Exception as e:
            print('%s: ERR %s: %s' % (p, type(e).__name__, e))


if __name__ == '__main__':
    main()
