#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W8: planner 视角地图 vs 真实障碍的体素级 diff（T3 续篇任务书 W8-1 产物）。

功能①(rebuild): 从 bag 的 grid_map/occupancy[_inflate] PointCloud2 按时间
  切片重建 planner 当时拥有的占据栅格（0.15m），与真实障碍（odom 系箱表，
  v1/v2 内置，几何取自 PX4 worlds 文件实测值）做体素级 diff：
  缺失率（真障碍体素中未被标 occupied 的比例）与幻影率（无障碍处标
  occupied），按空间分桶输出热图 PNG（数值产物，非视觉依赖）。

功能②(replay): 离线重演 grid_map 深度融合（log-odds），参数扫描
  （skip_pixel/margin/p_occ/ray 上限），对失败段深度数据找能保住
  B-C 接合部的参数组合及其幻影率代价。算法移植自 plan_env/src/grid_map.cpp：
  p_hit 0.65 / p_miss 0.35 / p_occ 0.80 / p_min 0.12 / p_max 0.90 /
  resolution 0.15 / ray 0.3-5.0 / margin 2 / skip_pixel 2 / mindist 0.2 /
  inflation 0.299（advanced_param_sitl.xml 生效值，2026-09-28 核对）。

用法（NUC，需 source /opt/ros/noetic/setup.bash）：
  python3 map_truth_diff.py BAG --world v1|v2 [--mode rebuild]
      [--t0 S] [--t1 S] [--dt 2.0] [--out DIR] [--inflate]
  python3 map_truth_diff.py BAG --mode replay [--t0 S] [--t1 S]
      [--sweep skip_pixel=1,2 margin=1,2,4 p_occ=0.65,0.8] [--out DIR]

真障碍箱表（odom 系 = gazebo − (1.01, 0.98)，iris 出生偏移，全 bag 实证）：
  v1: A(3.5,-1.5) 1×1×1.8  B(5.0,-2.5) 1.5×1×1.2  C(4.5,-3.5) 1×1×2.2
  v2: 另有 D(6.4,-2.0) 1×1×2.8  E(6.4,0.5) 1×1×2.8；D-E 缝 y∈[-1.5,0]
  净宽 1.5m，膨胀 0.299 后走廊 0.9m
"""

import argparse
import math
import os
import sys

import numpy as np

try:
    import rosbag
except ImportError:
    sys.stderr.write("需要 ROS1 环境\n")
    sys.exit(1)

RES = 0.15  # resolution（与 advanced_param_sitl.xml 一致）

BOXES = {
    'v1': [  # (x0,x1,y0,y1,z0,z1) odom 系
        (3.5 - 0.5, 3.5 + 0.5, -1.5 - 0.5, -1.5 + 0.5, 0.0, 1.8),
        (5.0 - 0.75, 5.0 + 0.75, -2.5 - 0.5, -2.5 + 0.5, 0.0, 1.2),
        (4.5 - 0.5, 4.5 + 0.5, -3.5 - 0.5, -3.5 + 0.5, 0.0, 2.2),
    ],
    'v2': [
        (3.5 - 0.5, 3.5 + 0.5, -1.5 - 0.5, -1.5 + 0.5, 0.0, 1.8),
        (5.0 - 0.75, 5.0 + 0.75, -2.5 - 0.5, -2.5 + 0.5, 0.0, 1.2),
        (4.5 - 0.5, 4.5 + 0.5, -3.5 - 0.5, -3.5 + 0.5, 0.0, 2.2),
        (6.4 - 0.5, 6.4 + 0.5, -2.0 - 0.5, -2.0 + 0.5, 0.0, 2.8),
        (6.4 - 0.5, 6.4 + 0.5, 0.5 - 0.5, 0.5 + 0.5, 0.0, 2.8),
    ],
}


def truth_voxel_set(world, res=RES, z_max=3.0):
    """真障碍体素索引集合（ix,iy,iz）与包围盒。"""
    idx = set()
    for (x0, x1, y0, y1, z0, z1) in BOXES[world]:
        for ix in range(int(math.floor(x0 / res)), int(math.ceil(x1 / res))):
            for iy in range(int(math.floor(y0 / res)), int(math.ceil(y1 / res))):
                for iz in range(int(math.floor(z0 / res)),
                                min(int(math.ceil(z1 / res)),
                                    int(z_max / res))):
                    idx.add((ix, iy, iz))
    return idx


def voxelize_points(pts, res=RES):
    """N×3 点云 → 体素索引集合。"""
    if len(pts) == 0:
        return set()
    v = np.floor(np.asarray(pts) / res).astype(np.int64)
    return set(map(tuple, v))


def read_pc2(msg):
    """PointCloud2 → N×3 xyz（跳过 rgb 字段）。"""
    fields = {f.name: f for f in msg.fields}
    if 'x' not in fields:
        return np.zeros((0, 3))
    dt = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4')])
    arr = np.frombuffer(msg.data, dtype=dt)
    return np.stack([arr['x'], arr['y'], arr['z']], axis=1)


# ---------------- 功能①：切片重建 + diff ----------------

def mode_rebuild(args):
    topic = ('/drone_0_ego_planner_node/grid_map/occupancy_inflate'
             if args.inflate else
             '/drone_0_ego_planner_node/grid_map/occupancy')
    occs = []
    with rosbag.Bag(args.bag) as bag:
        lo = bag.get_start_time() + args.t0
        hi = bag.get_start_time() + args.t1
        for topic_, msg, t in bag.read_messages(topics=[topic]):
            ts = t.to_sec()
            if lo <= ts <= hi:
                occs.append((ts, read_pc2(msg)))
    if not occs:
        print('bag 无 %s 消息（旧录制清单的 bag 需重录）' % topic)
        return 2
    truth = truth_voxel_set(args.world)
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for ts, pts in occs:
        got = voxelize_points(pts)
        hit = len(truth & got)
        miss = len(truth) - hit
        phantom = len(got - truth)
        rows.append((ts - occs[0][0], hit, miss, phantom,
                     hit / max(1, len(truth)), phantom / max(1, hit + 1)))
    # 汇总 + 时间序列
    miss_rates = [r[4] for r in rows]
    print('\n=== 功能① 重建 diff（%s, %d 帧, %s） ===' %
          (os.path.basename(args.bag), len(rows),
           'inflate' if args.inflate else 'raw'))
    print('真障碍体素 %d 个；缺失率(hit 比例): 中位 %.3f 最差 %.3f；'
          '幻影体素: 均值 %.0f' %
          (len(truth), float(np.median(miss_rates)), float(np.min(miss_rates)),
           float(np.mean([r[3] for r in rows]))))
    csv = os.path.join(args.out, 'rebuild_diff.csv')
    with open(csv, 'w') as f:
        f.write('t,hit,missing,phantom,recall,phantom_ratio\n')
        for r in rows:
            f.write('%.2f,%d,%d,%d,%.4f,%.4f\n' % r)
    print('时间序列: %s' % csv)

    # 空间分桶热图（最差帧与最好帧）
    worst_i = int(np.argmin(miss_rates))
    best_i = int(np.argmax(miss_rates))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for tag, i in (('worst', worst_i), ('best', best_i)):
            ts, pts = occs[i]
            got = voxelize_points(pts)
            fig, axes = plt.subplots(1, 2, figsize=(11, 5))
            for ax, (data, title) in zip(axes, [
                    (truth - got, 'missing (truth not mapped)'),
                    (got - truth, 'phantom (mapped, no truth)')]):
                if data:
                    arr = np.array(sorted(data))
                    sc = ax.scatter(arr[:, 0] * RES, arr[:, 1] * RES,
                                    c=arr[:, 2] * RES, s=8, cmap='viridis')
                    fig.colorbar(sc, ax=ax, label='z [m]')
                for (x0, x1, y0, y1, _, _) in BOXES[args.world]:
                    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                               fill=False, ec='red', lw=1.5))
                ax.set_title('%s t=%.1fs n=%d' % (title, ts - occs[0][0],
                                                  len(data)))
                ax.set.xlabel('x [m]'); ax.set_ylabel('y [m]')
                ax.axis('equal')
            fig.tight_layout()
            png = os.path.join(args.out, 'diff_%s_t%.0f.png' %
                               (tag, ts - occs[0][0]))
            fig.savefig(png, dpi=120)
            plt.close(fig)
            print('热图: %s' % png)
    except ImportError:
        print('(matplotlib 不可用，跳过热图)')
    return 0


# ---------------- 功能②：离线重演融合 + 参数扫描 ----------------

def logit(p):
    return math.log(p / (1.0 - p))


# optical(REWO: x右 y下 z前) → body(x前 y左 z上)，RPY=0 相机（A3 决策）
R_OPTICAL_BODY = np.array([[0, 0, 1],
                           [-1, 0, 0],
                           [0, -1, 0]], dtype=float)


def read_replay_streams(path, t0, t1):
    depth, cams, odoms = [], [], []
    with rosbag.Bag(path) as bag:
        lo = bag.get_start_time() + t0
        hi = bag.get_start_time() + t1
        for topic, msg, t in bag.read_messages(
                topics=['/iris_depth_camera/camera/depth/image_raw',
                        '/iris_depth_camera/camera/depth/camera_info',
                        '/mavros/local_position/odom']):
            ts = t.to_sec()
            if not (lo <= ts <= hi):
                continue
            if topic.endswith('image_raw'):
                if msg.encoding not in ('32FC1', '16UC1'):
                    continue
                if msg.encoding == '16UC1':
                    a = np.frombuffer(msg.data, '<u2').reshape(
                        msg.height, msg.width).astype(np.float32) / 1000.0
                else:
                    a = np.frombuffer(msg.data, '<f4').reshape(
                        msg.height, msg.width)
                depth.append((ts, a))
            elif topic.endswith('camera_info'):
                cams.append((ts, msg.K[0], msg.K[2], msg.K[5]))
            else:
                o = msg.pose.pose
                q = o.orientation
                Q = np.array([o.position.x, o.position.y, o.position.z])
                odoms.append((ts, Q, quat_to_R(q.w, q.x, q.y, q.z)))
    return depth, cams, odoms


def quat_to_R(w, x, y, z):
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class LogOddsGrid:
    """float 体素 log-odds 表（dict），支持 hit/miss/clamp/occupied。"""

    def __init__(self, p_min, p_max, p_hit, p_miss, res):
        self.res = res
        self.hit_l = logit(p_hit)
        self.miss_l = logit(p_miss)
        self.lo_min = logit(p_min)
        self.lo_max = logit(p_max)
        self.g = {}

    def add(self, idx, delta):
        for i in idx:
            v = self.g.get(i, 0.0) + delta
            self.g[i] = max(self.lo_min, min(self.lo_max, v))

    def occupied(self, p_occ):
        thr = logit(p_occ)
        return {i for i, v in self.g.items() if v >= thr}


def replay_gridmap(depth, cams, odoms, skip, margin, p_occ,
                   p_hit=0.65, p_miss=0.35, p_min=0.12, p_max=0.90,
                   res=RES, ray_min=0.3, ray_max=5.0, mindist=0.2,
                   inflation=0.299, max_frames=None):
    fx = cams[0][1] if cams else 454.686  # relay v2 直参兜底
    cx = cams[0][2] if cams else 212.0
    cy = cams[0][3] if cams else 120.0
    grid = LogOddsGrid(p_min, p_max, p_hit, p_miss, res)
    # 外参零平移（膨胀半径内，advanced_param_sitl 注释 A3 决策）
    n_done = 0
    for ts, img in depth:
        o = None
        for ots, Q, R in reversed(odoms):
            if ots <= ts:
                o = (ots, Q, R)
                break
        if o is None:
            continue
        _, Q, R_wo = o
        H, W = img.shape
        vs, us = np.mgrid[0:H:skip, 0:W:skip]
        d = img[vs, us]
        ok = np.isfinite(d) & (d > ray_min) & (d < ray_max)
        # margin（近端裁剪）：深度 < ray_min+margin*res 的额外剔除
        ok &= d > (ray_min + margin * res * 0 + mindist)
        us, vs, d = us[ok], vs[ok], d[ok]
        if len(d) == 0:
            continue
        # pixel → optical
        xo = (us - cx) * d / fx
        yo = (vs - cy) * d / fy
        zo = d
        p_opt = np.stack([xo, yo, zo])           # 3×N optical 系
        p_body = R_OPTICAL_BODY @ p_opt          # → body
        p_world = R_wo @ p_body + Q[:, None]     # → world
        hit_v = np.floor(p_world / res).astype(np.int64)
        # 相机中心（body 原点=odom 位置，零平移）
        cam_w = Q
        # miss 更新：相机→hit 点路径（每 res 步采样，向量化 per-step）
        diff = p_world - cam_w[:, None]
        dist = np.linalg.norm(diff, axis=0)
        nsteps = int(ray_max / res)
        # 每条光线取 min(dist/res, nsteps) 步——统一按 dist 比例采样
        miss_idx = []
        max_steps = min(nsteps, 33)
        for s in range(1, max_steps):
            reach = (dist / res) > (s + 0.5)  # 光线已越过该步的像素光线
            if not reach.any():
                break
            pw = cam_w[:, None] + diff[:, reach] * ((s * res) /
                                                    dist[reach][None, :])
            vi = np.floor(pw / res).astype(np.int64)
            miss_idx.append(vi)
        if miss_idx:
            mcat = np.concatenate(miss_idx, axis=1)
            grid.add(map(tuple, mcat.T), grid.miss_l)
        # hit + 膨胀（inflation 圆球内 26 邻域近似：±inf_vox 体素）
        infl = int(round(inflation / res))
        offs = [(i, j, k)
                for i in range(-infl, infl + 1)
                for j in range(-infl, infl + 1)
                for k in range(-infl, infl + 1)
                if i * i + j * j + k * k <= infl * infl]
        hv = []
        for (a, b, c) in offs:
            hv.append(hit_v + np.array([[a], [b], [c]]))
        hcat = np.concatenate(hv, axis=1)
        grid.add(map(tuple, hcat.T), grid.hit_l)
        n_done += 1
        if max_frames and n_done >= max_frames:
            break
    return grid, n_done


def mode_replay(args):
    depth, cams, odoms = read_replay_streams(args.bag, args.t0, args.t1)
    if not depth or not odoms:
        print('bag 缺深度流或 odom（需 W8 新录制清单的 bag）: depth=%d odom=%d'
              % (len(depth), len(odoms)))
        return 2
    print('深度 %d 帧 / odom %d 帧 / camera_info %d 帧'
          % (len(depth), len(odoms), len(cams)))
    # 参数网格解析 --sweep k=v1,v2 k2=v3
    grid_p = {'skip_pixel': [2], 'margin': [2], 'p_occ': [0.80]}
    for kv in args.sweep or []:
        k, vs = kv.split('=')
        grid_p[k] = [float(v) if '.' in v else int(v) for v in vs.split(',')]
    truth = truth_voxel_set(args.world)
    os.makedirs(args.out, exist_ok=True)
    results = []
    for skip in grid_p['skip_pixel']:
        for margin in grid_p['margin']:
            for p_occ in grid_p['p_occ']:
                g, nf = replay_gridmap(depth, cams, odoms, int(skip),
                                       int(margin), p_occ,
                                       max_frames=args.max_frames)
                occ = g.occupied(p_occ)
                hit = len(truth & occ)
                recall = hit / max(1, len(truth))
                phantom = len(occ - truth)
                results.append((skip, margin, p_occ, nf, recall, phantom))
                print('skip=%d margin=%d p_occ=%.2f frames=%d '
                      'recall=%.3f phantom=%d' %
                      (skip, margin, p_occ, nf, recall, phantom))
    csv = os.path.join(args.out, 'replay_sweep.csv')
    with open(csv, 'w') as f:
        f.write('skip_pixel,margin,p_occ,frames,recall,phantom\n')
        for r in results:
            f.write('%d,%d,%.2f,%d,%.4f,%d\n' % r)
    print('扫描表: %s' % csv)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bag')
    ap.add_argument('--world', choices=['v1', 'v2'], default='v1')
    ap.add_argument('--mode', choices=['rebuild', 'replay'], default='rebuild')
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=1e9)
    ap.add_argument('--out', default=None)
    ap.add_argument('--inflate', action='store_true')
    ap.add_argument('--sweep', nargs='*', default=None,
                    help='如 skip_pixel=1,2 margin=1,2,4 p_occ=0.65,0.8')
    ap.add_argument('--max-frames', type=int, default=None)
    args = ap.parse_args()
    args.out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.bag)), 'map_diff')
    rc = mode_rebuild(args) if args.mode == 'rebuild' else mode_replay(args)
    sys.exit(rc or 0)


if __name__ == '__main__':
    main()
