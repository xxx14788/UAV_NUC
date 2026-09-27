#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7-Y2/Y3 偏航闭环离线裁决（T3 续篇任务书 W7 产物）。

Y2: traj_server last_yaw_ 初始化缺陷——新轨迹到达瞬间 yaw 目标从上一
    轨迹残留值跳到路径方向。检验：/position_cmd.yaw 相邻消息阶跃
    （>20deg/周期）时刻与 trajectory_id 变化时刻的对齐率与阶跃幅分布。
    （/drone_0_planning/bspline 话题未录制，用 trajectory_id 变化作
    replan 事件代理；W8 已把 bspline 加入录制清单，后续 bag 可直验。）

Y3: PX4 yaw 速率控制带宽不足——机体跟不上高 yaw_dot 指令。检验：
    cmd_yaw_dot vs 实际 yaw 率（odom yaw 差分）的分段跟踪滞后
    （互相关最大滞后），按指令幅值分桶（|cmd|>90deg/s 为高桶）。
    判据：高桶相位滞后 >100ms → Y3 成立（限速即修复）。

用法（NUC，需 source /opt/ros/noetic/setup.bash）：
  python3 yaw_closure_analysis.py BAG [BAG...] [--t0 S] [--t1 S]
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


def yaw_from_q(w, x, y, z):
    return math.atan2(2 * (x * y + w * z),
                      w * w + x * x - y * y - z * z)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def read_streams(path, t0, t1):
    cmds, odoms = [], []
    with rosbag.Bag(path) as bag:
        lo = bag.get_start_time() + t0
        hi = bag.get_start_time() + t1
        for topic, msg, t in bag.read_messages(
                topics=['/position_cmd', '/mavros/local_position/odom']):
            ts = t.to_sec()
            if ts < lo or ts > hi:
                continue
            if topic == '/position_cmd':
                cmds.append((ts, msg.yaw, msg.yaw_dot, msg.trajectory_id))
            else:
                o = msg.pose.pose.orientation
                odoms.append((ts, yaw_from_q(o.w, o.x, o.y, o.z)))
    return cmds, odoms


def analyze(path, t0, t1, verbose=True):
    cmds, odoms = read_streams(path, t0, t1)
    if len(cmds) < 10 or len(odoms) < 10:
        return None
    res = {'bag': path.split('/')[-2] + '/' + path.split('/')[-1]}

    # ---- Y2: yaw 阶跃 vs trajectory_id 变化 ----
    tc = np.array([c[0] for c in cmds])
    yaw = np.array([c[1] for c in cmds])
    ydot = np.nan_to_num(np.array([c[2] for c in cmds]))
    tid = np.array([c[3] for c in cmds])
    dyaw = np.array([wrap(yaw[i] - yaw[i - 1])
                     for i in range(1, len(yaw))])
    dt_cmd = np.diff(tc)
    # 阶跃定义：相邻 cmd 折算瞬时速率 >150deg/s（YAW_DOT_MAX=PI 限速下
    # 的"硬甩"事件；240deg/s 实测 @49Hz cmd 流 = 4.9deg/步，不能按幅值卡）
    inst_rate = np.abs(dyaw) / np.maximum(dt_cmd, 1e-3)
    step_idx = np.where(inst_rate > math.radians(150))[0] + 1
    # trajectory_id 变化点
    tid_chg = np.where(np.diff(tid) != 0)[0] + 1

    # 对齐率：阶跃点是否落在 tid 变化点 ±0.1s
    def near(a, B, tol=0.1):
        return any(abs(a - b) <= tol for b in B)
    n_at_replan = sum(1 for i in step_idx if near(tc[i], tc[tid_chg])) \
        if len(tid_chg) else 0
    # 反向：replan 点中有多少伴随阶跃
    n_replan_with_step = sum(1 for j in tid_chg
                             if any(abs(tc[j] - tc[i]) <= 0.1
                                    for i in step_idx)) if len(step_idx) else 0

    res['n_steps'] = len(step_idx)
    res['n_replans'] = len(tid_chg)
    res['step_at_replan%'] = round(100 * n_at_replan / len(step_idx), 1) \
        if len(step_idx) else 0.0
    res['replan_has_step%'] = round(100 * n_replan_with_step / len(tid_chg), 1) \
        if len(tid_chg) else 0.0
    if len(step_idx):
        step_deg = np.degrees(np.abs(dyaw[step_idx - 1]))
        res['step_max_deg'] = round(float(step_deg.max()), 1)
        res['step_med_deg'] = round(float(np.median(step_deg)), 1)
        # 折算瞬时速率峰值（=任务书"实测瞬时 240deg/s"复核）
        rate = np.abs(dyaw[step_idx - 1]) / np.maximum(dt_cmd[step_idx - 1], 1e-3)
        res['step_rate_max_dps'] = round(float(np.degrees(rate.max())), 0)

    # ---- Y3: yaw 率跟踪滞后（互相关）----
    to = np.array([o[0] for o in odoms])
    oyaw = np.array([o[1] for o in odoms])
    # 实际 yaw 率：非均匀采样，用 5 点局部线性拟合斜率
    o_rate = np.zeros(len(to))
    for i in range(2, len(to) - 2):
        k = slice(i - 2, i + 3)
        sl = np.polyfit(to[k] - to[i], wrap_series(oyaw[k]), 1)[0]
        o_rate[i] = sl

    # cmd 分桶：|cmd_yaw_dot|>90deg/s 高桶，30-90 中桶
    hi_m = np.abs(ydot) > math.radians(90)
    md_m = (np.abs(ydot) > math.radians(30)) & ~hi_m

    def xcorr_lag(mask):
        if mask.sum() < 50:
            return None
        # 对 cmd 与 o_rate 都做 50ms 重采样后互相关
        tt = np.arange(tc[mask][0], min(tc[mask][-1], to[-2]), 0.05)
        c_rs = np.interp(tt, tc[mask], ydot[mask])
        o_rs = np.interp(tt, to, o_rate)
        c = c_rs - c_rs.mean()
        o = o_rs - o_rs.mean()
        denom = math.sqrt((c * c).sum() * (o * o).sum())
        if denom < 1e-9:
            return None
        lags = np.arange(-20, 21)  # ±1.0s @ 50ms
        best, best_r = 0, -2
        for L in lags:
            if L >= 0:
                a, b = c[:len(c) - L], o[L:]
            else:
                a, b = c[-L:], o[:len(o) + L]
            if len(a) < 50:
                continue
            r = float((a * b).sum()) / math.sqrt((a * a).sum() * (b * b).sum())
            if r > best_r:
                best_r, best = r, L
        return best * 0.05 * 1000, best_r  # ms, r

    for name, mask in (('hi', hi_m), ('mid', md_m)):
        out = xcorr_lag(mask)
        if out:
            res['lag_%s_ms' % name] = round(out[0], 0)
            res['r_%s' % name] = round(out[1], 3)

    # 指令幅值覆盖（判断该 bag 是否含高幅段）
    res['hi_cov_s'] = round(float(hi_m.sum() / 49.0), 1)
    return res


def wrap_series(a):
    out = np.copy(a)
    for i in range(1, len(a)):
        out[i] = out[i - 1] + wrap(a[i] - a[i - 1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bags', nargs='+')
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=1e9)
    args = ap.parse_args()
    rows = []
    for p in args.bags:
        r = analyze(p, args.t0, args.t1)
        if r:
            rows.append(r)
    if not rows:
        print('无有效数据')
        return
    cols = ['bag', 'n_replans', 'n_steps', 'replan_has_step%',
            'step_at_replan%', 'step_med_deg', 'step_max_deg',
            'step_rate_max_dps', 'hi_cov_s', 'lag_hi_ms', 'r_hi',
            'lag_mid_ms', 'r_mid']
    print('\n=== W7-Y2/Y3 偏航闭环裁决表 ===')
    print('Y2: replan_has_step%高=新轨迹首条cmd即大阶跃(last_yaw_残留成立)')
    print('Y3: lag_hi_ms>100=高幅指令跟踪滞后超限(限速即修复)')
    print('%-28s %9s %7s %14s %13s %11s %11s %15s %8s %10s %6s %10s %6s'
          % tuple(cols))
    for r in rows:
        print('%-28s %9s %7s %14s %13s %11s %11s %15s %8s %10s %6s %10s %6s' % (
            r['bag'][:28], r['n_replans'], r['n_steps'],
            r.get('replan_has_step%', '-'), r.get('step_at_replan%', '-'),
            r.get('step_med_deg', '-'), r.get('step_max_deg', '-'),
            r.get('step_rate_max_dps', '-'), r.get('hi_cov_s', '-'),
            r.get('lag_hi_ms', '-'), r.get('r_hi', '-'),
            r.get('lag_mid_ms', '-'), r.get('r_mid', '-')))


if __name__ == '__main__':
    main()
