#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W9: px4ctrl 姿态合成三实现离线 A/B 回放（T3 续篇任务书 W9-1 产物）。

从 bag 提取每个控制周期的输入（des_a 来自 /debugPx4ctrl.des_a_*、
des.yaw 与 cmd 位置来自 /position_cmd、odom 四元数/位置来自
/mavros/local_position/odom、imu 四元数来自 /mavros/imu/data），
离线重算三种姿态目标并与实发 des_q 对照：

  A) old     = c4f8c4e 欧拉法：roll/pitch 由 des_acc 按当前 odom-yaw 折算，
               再与 Rz(des.yaw) 组 ZYX 欧拉四元数（历史根因：yaw 误差大时
               倾角方向错向 → 穿倒扣）。
  B) new     = HEAD 向量法：zb = des_acc（z 护栏 0.1g），yb = zb×xc，
               正交 R=[xb,yb,zb]（已入库 0de090e）。
  C) nopatch = 同 B 构造，但发送值不做帧补丁（u.q = q，去掉 imu·odom⁻¹）。

P = imu.q · odom.q⁻¹（帧补丁旋转）。|P| 时间序列与分布 = W7-Y1 直接材料。
实发保真核验：ang(P·qB, des_q) 应 < 1°（否则回放对齐失真，结论作废）。

合格判据（决策表）：倾角方向（机体 zb 的水平投影）与水平期望方向
（cmd_pos − odom_pos）夹角 < 30° 的控制周期占比。

用法（NUC，需 source /opt/ros/noetic/setup.bash）：
  python3 controller_replay.py BAG [BAG...] [--t0 S] [--t1 S] [--out DIR]
      [--g 9.81] [--csv]
时间窗 --t0/--t1 相对 bag 起点（秒），用于裁出飞行段。

输出：
  <out>/<bagname>_replay.csv   逐周期指标（可选 --csv 时才落盘）
  <out>/replay_summary.csv     多 bag 决策表
  stdout                       人读决策表 + 关键统计
"""

import argparse
import math
import os
import sys

import numpy as np

try:
    import rosbag
except ImportError:
    sys.stderr.write("需要 ROS1 环境：source /opt/ros/noetic/setup.bash 后运行\n")
    sys.exit(1)


# ---------- 四元数工具（w,x,y,z 约定，与 Eigen 一致） ----------

def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def quat_conj(q):
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quat_normalize(q):
    n = np.linalg.norm(q)
    return q / n if n > 1e-12 else np.array([1.0, 0.0, 0.0, 0.0])


def quat_rotate(q, v):
    """q 把机体向量 v 旋转到世界系（v' = q v q*）。"""
    qv = np.array([0.0, v[0], v[1], v[2]])
    return quat_mul(quat_mul(q, qv), quat_conj(q))[1:]


def quat_angle_deg(a, b):
    d = abs(np.dot(quat_normalize(a), quat_normalize(b)))
    d = min(1.0, max(-1.0, d))
    return math.degrees(2.0 * math.acos(d))


def quat_to_yaw(q):
    """与 controller.cpp fromQuaternion2yaw 逐字一致。"""
    w, x, y, z = q
    return math.atan2(2 * (x * y + w * z),
                      w * w + x * x - y * y - z * z)


def rotz(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def roty(p):
    c, s = math.cos(p), math.sin(p)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rotx(r):
    c, s = math.cos(r), math.sin(r)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def quat_from_rot(R):
    """旋转矩阵 → 四元数（w,x,y,z），与 Eigen Quaterniond(Matrix3d) 一致。"""
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        S = math.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (R[2, 1] - R[1, 2]) / S
        y = (R[0, 2] - R[2, 0]) / S
        z = (R[1, 0] - R[0, 1]) / S
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S
    return quat_normalize(np.array([w, x, y, z]))


# ---------- 三种姿态实现 ----------

def attitude_old(des_acc, yaw_des, odom_q, g):
    """c4f8c4e 欧拉法（历史实现，A/B 决策的 A 臂）。"""
    yaw_odom = quat_to_yaw(odom_q)
    s, c = math.sin(yaw_odom), math.cos(yaw_odom)
    roll = (des_acc[0] * s - des_acc[1] * c) / g
    pitch = (des_acc[0] * c + des_acc[1] * s) / g
    R = rotz(yaw_des) @ roty(pitch) @ rotx(roll)
    return quat_from_rot(R)


def attitude_new(des_acc, yaw_des, g, guard=0.1, deg_guard=True):
    """HEAD 向量法（0de090e 入库，B/C 臂共用构造）。"""
    zb = np.array(des_acc, dtype=float)
    if zb[2] < guard * g:
        zb[2] = guard * g
    n = np.linalg.norm(zb)
    if n < 1e-9:
        zb = np.array([0.0, 0.0, 1.0])
    else:
        zb = zb / n
    xc = np.array([math.cos(yaw_des), math.sin(yaw_des), 0.0])
    yb = np.cross(zb, xc)
    if np.linalg.norm(yb) < 1e-3:
        yb = np.cross(zb, np.array([1.0, 0.0, 0.0]))
    yb = yb / np.linalg.norm(yb)
    xb = np.cross(yb, zb)
    R = np.column_stack([xb, yb, zb])
    return quat_from_rot(R)


# ---------- bag 读取 ----------

def read_bag(path, t0, t1):
    """返回按时间排序的输入流与控制周期时间轴。"""
    debug, cmds, odoms, imus = [], [], [], []
    try:
        bag_ctx = rosbag.Bag(path)
    except rosbag.ROSBagUnindexedException:
        print('  [跳过] %s 未索引(active bag):先 cp 再 rosbag reindex' % path)
        return [], [], [], []
    with bag_ctx as bag:
        t_start = bag.get_start_time()
        lo = t_start + t0
        hi = t_start + t1
        for topic, msg, t in bag.read_messages(
                topics=['/debugPx4ctrl', '/position_cmd',
                        '/mavros/local_position/odom', '/mavros/imu/data']):
            ts = t.to_sec()
            if ts < lo or ts > hi:
                continue
            if topic == '/debugPx4ctrl':
                debug.append((ts,
                              np.array([msg.des_a_x, msg.des_a_y, msg.des_a_z]),
                              np.array([msg.des_q_w, msg.des_q_x,
                                        msg.des_q_y, msg.des_q_z]),
                              np.array([msg.des_v_x, msg.des_v_y,
                                        msg.des_v_z])))
            elif topic == '/position_cmd':
                cmds.append((ts, msg.yaw,
                             np.array([msg.position.x, msg.position.y,
                                       msg.position.z])))
            elif topic == '/mavros/local_position/odom':
                o = msg.pose.pose.orientation
                odoms.append((ts, np.array([o.w, o.x, o.y, o.z]),
                              np.array([msg.pose.pose.position.x,
                                        msg.pose.pose.position.y,
                                        msg.pose.pose.position.z])))
            elif topic == '/mavros/imu/data':
                o = msg.orientation
                imus.append((ts, np.array([o.w, o.x, o.y, o.z])))
    return debug, cmds, odoms, imus


def nearest_before(times, payloads, t):
    """times 单调数组，payloads 同长：取 t'<=t 最近一条（二分），无则 None。"""
    i = np.searchsorted(times, t, side='right') - 1
    return payloads[i] if i >= 0 else None


# ---------- 主回放 ----------

def replay_bag(path, t0, t1, g):
    debug, cmds, odoms, imus = read_bag(path, t0, t1)
    if len(debug) == 0:
        return None
    cmd_t = np.array([c[0] for c in cmds])
    cmd_d = [(c[1], c[2]) for c in cmds]
    odo_t = np.array([o[0] for o in odoms])
    odo_d = [(o[1], o[2]) for o in odoms]
    imu_t = np.array([i[0] for i in imus])
    imu_d = [i[1] for i in imus]
    rows = []
    for k in range(len(debug)):
        ts, des_a, q_actual, des_v = debug[k]
        cmd = nearest_before(cmd_t, cmd_d, ts)
        odo = nearest_before(odo_t, odo_d, ts)
        imu = nearest_before(imu_t, imu_d, ts)
        if odo is None or imu is None:
            continue
        q_odom, p_odom = odo
        q_imu = imu
        if cmd is not None:
            yaw_cmd, p_cmd = cmd
            dxy = p_cmd[:2] - p_odom[:2]
            yaw_src = 'cmd'
        else:
            # 无 position_cmd 的 bag（2026-09-26 录制清单）：yaw 从实发
            # des_q 反解（P 为小量时误差可忽略）；对齐方向用期望速度。
            yaw_cmd = quat_to_yaw(q_actual)
            dxy = des_v[:2]
            yaw_src = 'desq'

        qB = attitude_new(des_a, yaw_cmd, g)
        qA = attitude_old(des_a, yaw_cmd, q_odom, g)
        # C = 与 B 相同构造，发送值不乘帧补丁（数值上 qC=qB，
        # 差别只在最终发送：P·qB vs qB；决策表里用"发送值"对齐率区分）
        qC = qB
        P = quat_mul(q_imu, quat_conj(q_odom))
        P = quat_normalize(P)
        ang_P = quat_angle_deg(P, [1, 0, 0, 0])
        sent_B = quat_mul(P, qB)          # 当前实现实发
        sent_C = qC                        # 去补丁实发

        # 保真核验：回放出的当前实现发送值 vs bag 实发 des_q
        ang_fidelity = quat_angle_deg(sent_B, q_actual)

        # 倾角对齐：各"发送值"的机体 zb（世界系）水平投影 vs 期望机动方向 dxy
        dn = np.linalg.norm(dxy)
        aligns = {}
        for name, q_send in (('A', qA), ('B', sent_B), ('C', sent_C)):
            zb_w = quat_rotate(q_send, np.array([0.0, 0.0, 1.0]))
            zb_xy = zb_w[:2]
            zn = np.linalg.norm(zb_xy)
            if dn < 1e-6 or zn < 1e-6:
                aligns[name] = float('nan')
            else:
                c = float(np.dot(zb_xy / zn, dxy / dn))
                c = min(1.0, max(-1.0, c))
                aligns[name] = math.degrees(math.acos(c))

        rows.append(dict(
            t=ts, ang_AB=quat_angle_deg(qA, qB),
            ang_BC=quat_angle_deg(sent_B, sent_C),
            ang_P=ang_P, fidelity=ang_fidelity,
            align_A=aligns['A'], align_B=aligns['B'], align_C=aligns['C'],
            yaw_cmd=yaw_cmd, yaw_odom=quat_to_yaw(q_odom),
            yaw_imu=quat_to_yaw(q_imu), yaw_src=yaw_src))
    return rows


def summarize(name, rows):
    ang_P = np.array([r['ang_P'] for r in rows])
    fid = np.array([r['fidelity'] for r in rows])
    out = {'bag': name, 'cycles': len(rows)}
    out['fid_med_deg'] = round(float(np.median(fid)), 3) if len(fid) else float('nan')
    out['fid_max_deg'] = round(float(fid.max()), 2) if len(fid) else float('nan')
    for key in ('align_A', 'align_B', 'align_C'):
        v = np.array([r[key] for r in rows])
        v = v[~np.isnan(v)]
        out['%s_ok%%' % key] = round(100.0 * np.mean(v < 30.0), 1) if len(v) else float('nan')
        out['%s_med' % key] = round(float(np.median(v)), 1) if len(v) else float('nan')
    out['P_med_deg'] = round(float(np.median(ang_P)), 2)
    out['P_p95_deg'] = round(float(np.percentile(ang_P, 95)), 2)
    out['P_max_deg'] = round(float(ang_P.max()), 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bags', nargs='+')
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=1e9)
    ap.add_argument('--g', type=float, default=9.81)
    ap.add_argument('--out', default=None)
    ap.add_argument('--csv', action='store_true', help='逐周期 CSV 落盘')
    args = ap.parse_args()

    out_dir = args.out or os.path.dirname(args.bags[0]) or '.'
    os.makedirs(out_dir, exist_ok=True)

    summaries = []
    for path in args.bags:
        rows = replay_bag(path, args.t0, args.t1, args.g)
        rel = '/'.join(path.rstrip('/').split('/')[-2:])
        if not rows:
            print('%-40s 无有效周期（时间窗或话题缺失）' % rel)
            continue
        s = summarize(rel, rows)
        summaries.append(s)
        if args.csv:
            import csv as _csv
            csv_path = os.path.join(
                out_dir, os.path.basename(path).replace('.bag', '_replay.csv'))
            keys = list(rows[0].keys())
            with open(csv_path, 'w', newline='') as f:
                w = _csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(rows)

    if not summaries:
        sys.exit(2)
    cols = ['bag', 'cycles', 'fid_med_deg', 'fid_max_deg',
            'align_A_ok%', 'align_A_med', 'align_B_ok%', 'align_B_med',
            'align_C_ok%', 'align_C_med', 'P_med_deg', 'P_p95_deg', 'P_max_deg']
    print('\n=== W9 三实现回放决策表（对齐率=倾角指向期望方向<30°占比; '
          'A=老欧拉 B=当前含补丁 C=去补丁; fid=回放保真,med<1°可信) ===')
    print('%-40s %7s %9s %9s %9s %8s %9s %8s %9s %8s %9s %9s %8s' % tuple(cols))
    for s in summaries:
        print('%-40s %7d %9s %9s %9s %8s %9s %8s %9s %8s %9s %9s %8s' % (
            s['bag'][:40], s['cycles'],
            s['fid_med_deg'], s['fid_max_deg'],
            s.get('align_A_ok%', '-'), s.get('align_A_med', '-'),
            s.get('align_B_ok%', '-'), s.get('align_B_med', '-'),
            s.get('align_C_ok%', '-'), s.get('align_C_med', '-'),
            s['P_med_deg'], s['P_p95_deg'], s['P_max_deg']))

    import csv as _csv
    sum_path = os.path.join(out_dir, 'replay_summary.csv')
    with open(sum_path, 'w', newline='') as f:
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(summaries)
    print('\n汇总: %s' % sum_path)


if __name__ == '__main__':
    main()
