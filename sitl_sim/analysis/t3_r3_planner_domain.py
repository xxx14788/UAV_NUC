#!/usr/bin/env python3
"""t3_r3_planner_domain.py — R3 规划域证据包取证（T3 任务书 v8.3 单元 1）

预注册判据（2026-10-02 01:15 冻结，先于任何执行）：
  签名三分类（DoD）：
    sig-A 自洽追漂: poscmd 在 odom 系内健康（G1-G4 全不违）→ 漂移由 odom 驱动
    sig-B 输出病态: poscmd 在 odom 系内病态（G1-G4 任一触发）
    sig-C 混合: 时间分段 A/B 并存（记录切换时刻，人工读 timeline 判）
  poscmd 健康四门（odom=imu_propagate 系，planner 实际输入框架）：
    G1 限幅: |vel|>0.55 (=1.1*max_vel, launch 钉 0.5) 帧占比>5% → 违
    G2 goal 指向: cos(vel, goal-pos) 中位数(距 goal>1m 段)<0.5 → 违
    G3 前瞻: |poscmd.pos-odom_pos(同刻)| p95>5m → 违
    G4 跳变: implied |Δpos|/Δt>1.65 (=3*0.55) 事件密度>1/min → 违
  漂移时间轴（出生点对齐: 起飞前静置段 位置均值平移对齐, 无尺度——
    一阶口径: 慢漂主分量为平移; yaw 漂移留作残余风险注记）：
    odom_drift(t)=|odom - truth_aligned|; 首漂档 drift>0.5 / >1.0
  输出: <out>_timeline.csv(1Hz) + <out>_summary.json
"""
import csv
import json
import math
import sys
from collections import defaultdict

import numpy as np
import rosbag

VEL_LIM, COS_GATE, AHEAD_GATE, JUMP_V = 0.55, 0.5, 5.0, 1.65


def main():
    bag_path, out_prefix = sys.argv[1], sys.argv[2]
    topics = ['/position_cmd', '/vins_estimator/imu_propagate', '/vins_estimator/odometry',
              '/move_base_simple/goal', '/gazebo/model_states', '/px4ctrl/takeoff_land']
    d = defaultdict(list)
    iris_idx, model_names = None, None
    with rosbag.Bag(bag_path) as bag:
        t0 = bag.get_start_time()
        for topic, msg, t in bag.read_messages(topics=topics):
            try:
                ts = msg.header.stamp.to_sec()
            except AttributeError:
                ts = t.to_sec()
            if topic == '/gazebo/model_states':
                if model_names is None:
                    model_names = list(msg.name)
                    iris_idx = next((i for i, n in enumerate(model_names) if 'iris' in n), None)
                if iris_idx is not None:
                    p, q = msg.pose[iris_idx].position, msg.pose[iris_idx].orientation
                    d['truth'].append((ts, p.x, p.y, p.z, q.x, q.y, q.z, q.w))
            elif topic == '/position_cmd':
                p, v = msg.position, msg.velocity
                d['poscmd'].append((ts, p.x, p.y, p.z, v.x, v.y, v.z, msg.yaw,
                                    int(msg.trajectory_id), int(msg.trajectory_flag)))
            elif topic == '/vins_estimator/imu_propagate':
                p = msg.pose.pose.position
                d['odom'].append((ts, p.x, p.y, p.z))
            elif topic == '/vins_estimator/odometry':
                p = msg.pose.pose.position
                d['odom_v'].append((ts, p.x, p.y, p.z))
            elif topic == '/move_base_simple/goal':
                p = msg.pose.position
                d['goal'].append((ts, p.x, p.y, p.z))
            elif topic == '/px4ctrl/takeoff_land':
                d['tk'].append((ts, int(msg.takeoff_land_cmd)))
    S = {}
    S['bag'] = bag_path
    S['truth_model'] = model_names[iris_idx] if iris_idx is not None else None
    S['n'] = {k: len(v) for k, v in d.items()}
    tk_t = d['tk'][0][0] if d['tk'] else (d['odom'][0][0] if d['odom'] else t0)
    S['takeoff_t_rel'] = round(tk_t - t0, 2)
    odom = np.array([(x[0], x[1], x[2], x[3]) for x in d['odom']], dtype=float)
    truth = np.array([x for x in d['truth']], dtype=float) if d['truth'] else np.zeros((0, 8))
    poscmd = np.array([x for x in d['poscmd']], dtype=float) if d['poscmd'] else np.zeros((0, 10))
    # traj_id 分段: 每 id 的首末时刻+均值 vel —— 区分飞行段/悬停段, 供 G 门分段评
    if len(poscmd):
        ids = poscmd[:, 8].astype(int)
        segs = []
        for tid in np.unique(ids):
            m = ids == tid
            seg_t0, seg_t1 = poscmd[m, 0].min(), poscmd[m, 0].max()
            sv = np.linalg.norm(poscmd[m, 4:7], axis=1)
            segs.append({'traj_id': int(tid), 'flag_last': int(poscmd[m][-1, 9]),
                         't_rel': [round(seg_t0 - t0, 1), round(seg_t1 - t0, 1)],
                         'dur_s': round(seg_t1 - seg_t0, 1),
                         'vel_p50': round(float(np.percentile(sv, 50)), 3),
                         'vel_max': round(float(sv.max()), 3), 'n': int(m.sum())})
        S['traj_segments'] = segs
        S['traj_id_count'] = len(segs)
    seg = lambda A, lo, hi: A[(A[:, 0] >= lo) & (A[:, 0] < hi)]
    trans = np.zeros(3)
    if len(odom) and len(truth):
        lo = max(odom[0, 0], tk_t - 6.0)
        hi = tk_t - 0.5
        if hi - lo < 2.0:
            lo = hi - 2.0
        o_seg, t_seg = seg(odom, lo, hi), seg(truth, lo, hi)
        if len(o_seg) > 10 and len(t_seg) > 10:
            trans = o_seg[:, 1:4].mean(0) - t_seg[:, 1:4].mean(0)
    S['align_trans'] = [round(x, 3) for x in trans.tolist()]
    drift = None
    tdr = None
    if len(truth):
        ti = np.searchsorted(truth[:, 0], odom[:, 0], side='right') - 1
        ok = (ti >= 0) & (ti < len(truth))
        if ok.any():
            tr = truth[ti[ok], 1:4] + trans
            drift = np.linalg.norm(odom[ok, 1:4] - tr, axis=1)
            tdr = odom[ok, 0]
            for thr in (0.5, 1.0):
                hit = np.where(drift > thr)[0]
                S['odom_drift_first_%s' % thr] = round(tdr[hit[0]] - t0, 2) if len(hit) else None
            S['odom_drift_max'] = round(float(drift.max()), 2)
            S['odom_drift_p95'] = round(float(np.percentile(drift, 95)), 2)
    if len(truth) > 2:
        dtt = np.diff(truth[:, 0])
        vx = np.linalg.norm(np.diff(truth[:, 1:4], axis=0), axis=1) / np.maximum(dtt, 1e-3)
        S['truth_vmax'] = round(float(vx.max()), 2)
        S['truth_v_p95'] = round(float(np.percentile(vx, 95)), 3)
    if len(poscmd):
        ot = odom[:, 0]
        dtc = np.diff(poscmd[:, 0])
        S['poscmd_hz_p50'] = round(1 / np.percentile(dtc, 50), 1)
        S['poscmd_gap_p95_s'] = round(float(np.percentile(dtc, 95)), 3)
        S['poscmd_gap_max_s'] = round(float(dtc.max()), 3)
        # 预注册补条: G 门评估域=活跃段(该 traj_id 段 vel_p50>0.05)帧;
        # 悬停分支(traj_server hover-when-finish) vel≡0 属设计行为不评 G1/G2
        ids = poscmd[:, 8].astype(int)
        active = np.zeros(len(poscmd), dtype=bool)
        for tid in np.unique(ids):
            m = ids == tid
            if np.percentile(np.linalg.norm(poscmd[m, 4:7], axis=1), 50) > 0.05:
                active[m] = True
        S['active_frac'] = round(float(active.mean()), 3)
        vmag = np.linalg.norm(poscmd[:, 4:7], axis=1)
        S['vel_mag_p50'] = round(float(np.percentile(vmag, 50)), 3)
        S['vel_mag_p95'] = round(float(np.percentile(vmag, 95)), 3)
        S['vel_mag_max'] = round(float(vmag.max()), 3)
        S['G1_over_frac'] = round(float((vmag[active] > VEL_LIM).mean()) if active.any() else 0.0, 4)
        ii = np.searchsorted(ot, poscmd[:, 0], side='right') - 1
        ok = (ii >= 0) & (ii < len(odom))
        ahead = np.linalg.norm(poscmd[ok, 1:4] - odom[ii[ok], 1:4], axis=1)
        S['ahead_p50'] = round(float(np.percentile(ahead, 50)), 3)
        S['ahead_p95'] = round(float(np.percentile(ahead, 95)), 3)
        act_ok = ok.copy()
        act_ok[ok] = active[ok.nonzero()[0]] if ok.any() else act_ok
        ahead_a = np.linalg.norm(poscmd[act_ok, 1:4] - odom[ii[act_ok], 1:4], axis=1) if act_ok.any() else np.array([0.0])
        S['ahead_active_p50'] = round(float(np.percentile(ahead_a, 50)), 3)
        S['ahead_active_p95'] = round(float(np.percentile(ahead_a, 95)), 3)
        S['G3_ahead_viol'] = bool(S['ahead_active_p95'] > AHEAD_GATE)
        implied = np.linalg.norm(np.diff(poscmd[:, 1:4], axis=0), axis=1) / np.maximum(dtc, 1e-3)
        jumps = implied > JUMP_V
        S['G4_jump_n'] = int(jumps.sum())
        S['G4_jump_per_min'] = round(float(jumps.sum() / max(poscmd[-1, 0] - poscmd[0, 0], 1) * 60), 2)
        g = np.array([x for x in d['goal']], dtype=float)
        if len(g):
            gi = np.searchsorted(g[:, 0], poscmd[:, 0], side='right') - 1
            idx = np.where((gi >= 0) & active)[0]
            if len(idx):
                gv = g[gi[idx], 1:4] - poscmd[idx, 1:4]
                dist = np.linalg.norm(gv, axis=1)
                nv = np.linalg.norm(poscmd[idx, 4:7], axis=1)
                m = (dist > 1.0) & (nv > 0.02)
                if m.any():
                    cc = (poscmd[idx[m], 4:7] * gv[m]).sum(1) / (nv[m] * dist[m])
                    S['G2_goal_cos_p50'] = round(float(np.percentile(cc, 50)), 3)
                    S['G2_goal_cos_p10'] = round(float(np.percentile(cc, 10)), 3)
        S['G1_viol'] = bool(S['G1_over_frac'] > 0.05)
        S['G2_viol'] = bool(S.get('G2_goal_cos_p50', 1.0) < COS_GATE)
        S['G4_viol'] = bool(S['G4_jump_per_min'] > 1.0)
        S['sig_B_viol'] = bool(S['G1_viol'] or S['G2_viol'] or S['G3_ahead_viol'] or S['G4_viol'])
    else:
        S['poscmd_absent'] = True
    rows = []
    if len(odom) and drift is not None:
        t_end = max(odom[-1, 0], truth[-1, 0] if len(truth) else odom[-1, 0])
        for sec in np.arange(t0, t_end, 1.0):
            r = {'t_rel': round(sec - t0, 1)}
            for name, A in (('odom', odom), ('truth', truth), ('poscmd', poscmd)):
                if len(A):
                    k = np.searchsorted(A[:, 0], sec, side='right') - 1
                    if 0 <= k < len(A):
                        r[name + '_x'] = round(A[k, 1], 2)
                        r[name + '_y'] = round(A[k, 2], 2)
                        r[name + '_z'] = round(A[k, 3], 2)
                        if name == 'poscmd':
                            r['poscmd_vm'] = round(float(np.linalg.norm(A[k, 4:7])), 3)
            if tdr is not None:
                j = np.searchsorted(tdr, sec, side='right') - 1
                if j >= 0:
                    r['drift'] = round(float(drift[j]), 3)
            rows.append(r)
    keys = sorted({k for r in rows for k in r})
    with open(out_prefix + '_timeline.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with open(out_prefix + '_summary.json', 'w') as f:
        json.dump(S, f, indent=1, ensure_ascii=False)
    print(json.dumps(S, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
