#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-J-R3② J1.3 特征点三区密度判读（vision_materials.md §3 口径）+ 偏移实测校准.

两种模式:
  --mode offset  校准: 读原始袋 gazebo/model_states + vins_estimator/odometry 首段,
                 实测 VINS 系相对 gazebo 系平移(替代"出生点硬编码假设", T2b-U9 教训).
  --mode density 判读: 读重放特征袋 point_cloud(VINS world 系, visualization.cpp
                 w_pts_i 实证) + odometry, 按 §3 三区(障碍面/地面/空域)输出点数与密度.

区划口径(§3): 障碍盒 AABB 膨胀 0.5m=障碍区; z<地面+0.1m 带内=地面; 其余=空域.
密度分母(dry-run 标定候选, 正式轮前定一): 障碍区报 点/m³(膨胀体积)与 点/m²(膨胀
表面积)双口径; 地面报 点/m²(观测 x-y 外接框+0.5m pad); 空域报 点/m³(观测包络体积).

用法:
  python3 j3_feature_density.py --mode offset --bag orig.bag
  python3 j3_feature_density.py --mode density --bag features.bag \
      [--world-boxes "4.51,-0.52,0.9,1.0,1.0,1.8" ...] [--shift 1.01,0.98,0.104]
"""
import argparse
import json
import sys

import numpy as np
import rosbag
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud


def cmd_offset(args):
    """首段实测: vins odom 首 Pose vs gazebo iris 首 Pose(同为 world 静止期)."""
    gv, vv = None, None
    with rosbag.Bag(args.bag, 'r') as bag:
        for topic, msg, _ in bag.read_messages(
                topics=['/gazebo/model_states', '/vins_estimator/odometry']):
            if topic == '/gazebo/model_states' and gv is None:
                names = [i for i, n in enumerate(msg.name) if 'iris' in n]
                if names:
                    p = msg.pose[names[0]].position
                    gv = np.array([p.x, p.y, p.z])
            elif topic == '/vins_estimator/odometry' and vv is None:
                p = msg.pose.pose.position
                vv = np.array([p.x, p.y, p.z])
            if gv is not None and vv is not None:
                break
    if gv is None or vv is None:
        print('FAIL: 话题缺失(model_states=%s vins_odom=%s)' % (gv is not None, vv is not None))
        return 1
    shift = gv - vv
    print('gazebo_iris_first = %s' % np.round(gv, 4).tolist())
    print('vins_odom_first   = %s' % np.round(vv, 4).tolist())
    print('shift(gazebo-vins)= %s' % np.round(shift, 4).tolist())
    print('漂移校验: 起飞前两源应近静止, shift 与出生点(1.01,0.98,0.104)差即 yaw/漂移一阶项')
    return 0


def parse_boxes(specs, shift):
    """gazebo 系中心+size -> vins 系 AABB(x1,y1,z1,x2,y2,z2)."""
    out = []
    s = np.array(shift)
    for sp in specs:
        v = [float(x) for x in sp.split(',')]
        cx, cy, cz, sx, sy, sz = v
        lo = np.array([cx - sx / 2, cy - sy / 2, cz - sz / 2]) - s
        hi = np.array([cx + sx / 2, cy + sy / 2, cz + sz / 2]) - s
        out.append((lo, hi, 'box@gazebo(%.2f,%.2f,%.2f)+size(%.1f,%.1f,%.1f)' % tuple(v)))
    return out


def cmd_density(args):
    shift = [float(x) for x in args.shift.split(',')]
    boxes = parse_boxes(args.world_boxes, shift) if args.world_boxes else []
    inflate = args.inflate
    ground_plane_z = -shift[2]  # gazebo z=0 地面 -> vins 系
    ground_top = ground_plane_z + args.ground_band
    pts_all, n_msgs, odo_n = [], 0, 0
    per_msg_n = []
    t0 = t1 = None
    with rosbag.Bag(args.bag, 'r') as bag:
        for topic, msg, _ in bag.read_messages(
                topics=['/vins_estimator/point_cloud', '/vins_estimator/odometry']):
            if topic == '/vins_estimator/odometry':
                odo_n += 1
                continue
            n = len(msg.points)
            if n == 0:
                continue
            n_msgs += 1
            per_msg_n.append(n)
            st = msg.header.stamp.to_sec()
            t0 = st if t0 is None else t0
            t1 = st
            arr = np.empty((n, 3), dtype=np.float64)
            for i, p in enumerate(msg.points):
                arr[i] = (p.x, p.y, p.z)
            pts_all.append(arr)
    if not pts_all:
        print('FAIL: 特征袋无 point_cloud 消息(重放失败? 查 replay 日志)')
        return 1
    P = np.vstack(pts_all)

    in_obs = np.zeros(len(P), dtype=bool)
    for lo, hi, _ in boxes:
        m = np.all((P >= lo - inflate) & (P <= hi + inflate), axis=1)
        in_obs |= m
    in_gnd = (P[:, 2] <= ground_top) & (~in_obs)
    in_air = ~(in_obs | in_gnd)

    def trimmed_bbox_vol(A, pad=0.0):
        """P1-P99 修剪外接框体积: 全量 bbox 被远点/噪声点污染(袋1实测 139x139m 失真),
        修剪后才是观测包络的有效分母."""
        if len(A) < 10:
            return 0.0
        lo = np.percentile(A, 1, axis=0)
        hi = np.percentile(A, 99, axis=0)
        ext = np.maximum(hi - lo + 2 * pad, 1e-3)
        return float(np.prod(ext))

    def trimmed_bbox_area(A, pad=0.0):
        if len(A) < 10:
            return 0.0
        lo = np.percentile(A[:, :2], 1, axis=0)
        hi = np.percentile(A[:, :2], 99, axis=0)
        ext = np.maximum(hi - lo + 2 * pad, 1e-3)
        return float(ext[0] * ext[1])

    def face_area(lo, hi):
        dx, dy, dz = hi - lo
        return float(2 * (dx * dy + dx * dz + dy * dz))

    obs_area = sum(face_area(lo - inflate, hi + inflate) for lo, hi, _ in boxes) if boxes else 0.0
    obs_vol = sum(float(np.prod((hi - lo) + 2 * inflate)) for lo, hi, _ in boxes) if boxes else 0.0
    g = P[in_gnd]
    g_area = trimmed_bbox_area(g, pad=0.5)
    a = P[in_air]
    a_vol = trimmed_bbox_vol(a)

    per_msg_n = np.array(per_msg_n)
    res = {
        'mode': 'density', 'bag': args.bag, 'dry_run': True,
        'boxes_gazebo': args.world_boxes, 'shift': shift, 'inflate_m': inflate,
        'ground_top_vins': round(ground_top, 4),
        'msgs': n_msgs, 'odom_msgs': odo_n,
        'duration_s': round(t1 - t0, 1) if t0 else None,
        'points_total': int(len(P)),
        'per_msg_points': {'p50': float(np.percentile(per_msg_n, 50)),
                           'p90': float(np.percentile(per_msg_n, 90)),
                           'max': int(per_msg_n.max())},
        'zones': {
            'obstacle': {'n': int(in_obs.sum()), 'vol_m3': round(obs_vol, 2),
                         'face_area_m2': round(obs_area, 2),
                         'per_m3': round(float(in_obs.sum()) / obs_vol, 2) if obs_vol else None,
                         'per_m2_face': round(float(in_obs.sum()) / obs_area, 2) if obs_area else None},
            'ground': {'n': int(in_gnd.sum()), 'area_m2': round(g_area, 2),
                       'per_m2': round(float(in_gnd.sum()) / g_area, 2) if g_area else None},
            'air': {'n': int(in_air.sum()), 'vol_m3': round(a_vol, 2),
                    'per_m3': round(float(in_air.sum()) / a_vol, 2) if a_vol else None},
        },
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['offset', 'density'], required=True)
    ap.add_argument('--bag', required=True)
    ap.add_argument('--world-boxes', nargs='*',
                    default=['4.51,-0.52,0.9,1.0,1.0,1.8',
                             '6.01,-1.52,0.6,1.5,1.0,1.2',
                             '5.51,-2.52,1.1,1.0,1.0,2.2'],
                    help='gazebo 系 中心x,y,z+尺寸x,y,z(缺省=sitl_world_obstacles 三盒, '
                         'sitl_sim/worlds/sitl_world_obstacles.world:50-92)')
    ap.add_argument('--shift', default='1.01,0.98,0.104',
                    help='gazebo->vins 平移(先验出生点; 以 --mode offset 实测为准)')
    ap.add_argument('--inflate', type=float, default=0.5)
    ap.add_argument('--ground-band', type=float, default=0.1)
    args = ap.parse_args()
    if args.mode == 'offset':
        sys.exit(cmd_offset(args))
    sys.exit(cmd_density(args))


if __name__ == '__main__':
    main()
