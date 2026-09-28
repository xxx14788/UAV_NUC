#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3-D2 回放评估:对 t3_replay.sh 的输出按 D2 三判据打分
  1. ATE:t*(首跳>0.1m,排除真机动)后 60s odom-真值(刚体 Umeyama 对齐,无尺度)
  2. 帧跳变数:odom 帧间 |dp|>0.1m 且真值同窗位移<0.1m 的次数
  3. 特征存活率:feature_pts 每帧点数,t* 前 5s 均值 vs t* 后 60s 均值之比
用法: t3_replay_eval.py <replay_out_dir> <src_bag_with_truth>
输出: <replay_out_dir>/eval.json + stdout 一行判决
"""
import sys, os, json, math
from bisect import bisect_left

JUMP_M = 0.10


def read_all(replay_dir, src_bag):
    import rosbag
    odom, feat = [], []
    with rosbag.Bag(os.path.join(replay_dir, "vins_out.bag"), "r") as b:
        for topic, msg, ts in b.read_messages():
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            if topic == "/vins_estimator/odometry":
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                odom.append((t, p.x, p.y, p.z, q.x, q.y, q.z, q.w))
            elif topic == "/vins_estimator/feature_pts":
                feat.append((t, len(msg.points)))
    truth = []
    with rosbag.Bag(src_bag, "r") as b:
        for topic, msg, ts in b.read_messages(topics=["/gazebo/model_states"]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            for name, pose in zip(msg.name, msg.pose):
                if "iris" in name:
                    p = pose.position
                    truth.append((t, p.x, p.y, p.z))
                    break
    return odom, feat, truth


def nearest_idx(stamps, t):
    i = bisect_left(stamps, t)
    cands = []
    if i < len(stamps):
        cands.append(i)
    if i > 0:
        cands.append(i - 1)
    return min(cands, key=lambda j: abs(stamps[j] - t))


def umeyama_ate(est, gt):
    """est/gt: [(x,y,z)...]; 刚体(R,t 最小二乘)对齐后 RMS。"""
    n = len(est)
    if n < 10:
        return None
    mx = [sum(p[i] for p in est) / n for i in range(3)]
    my = [sum(p[i] for p in gt) for i in range(3)]
    my = [v / n for v in my]
    # 协方差
    H = [[0.0] * 3 for _ in range(3)]
    for a, b in zip(est, gt):
        da = [a[i] - mx[i] for i in range(3)]
        db = [b[i] - my[i] for i in range(3)]
        for i in range(3):
            for j in range(3):
                H[i][j] += da[i] * db[j]
    # SVD 3x3 via numpy-free jacobi? 直接用简单幂迭代太脆——借 numpy
    import numpy as np
    U, S, Vt = np.linalg.svd(np.array(H))
    d = np.sign(np.linalg.det(U) * np.linalg.det(Vt))
    D = np.diag([1, 1, d])
    R = U @ D @ Vt
    t = np.array(my) - R @ np.array(mx)
    sq = 0.0
    for a, b in zip(est, gt):
        p = R @ np.array(a) + t
        sq += sum((p[i] - b[i]) ** 2 for i in range(3))
    return math.sqrt(sq / n)


def main():
    replay_dir, src_bag = sys.argv[1], sys.argv[2]
    odom, feat, truth = read_all(replay_dir, src_bag)
    rep = {"n_odom": len(odom), "n_feat": len(feat)}
    if not odom:
        rep["verdict"] = "无 odometry(VINS 未起或崩)"
        json.dump(rep, open(os.path.join(replay_dir, "eval.json"), "w"), ensure_ascii=False, indent=1)
        print(json.dumps(rep, ensure_ascii=False))
        return
    t0 = odom[0][0]
    ts_o = [r[0] for r in odom]
    ts_t = [r[0] for r in truth] if truth else []

    # t*:首跳(真值同窗位移<0.1m)
    t_star, jumps = None, 0
    for i in range(1, len(odom)):
        dp = math.sqrt(sum((odom[i][k] - odom[i-1][k]) ** 2 for k in (1, 2, 3)))
        if dp > JUMP_M:
            tm = None
            if ts_t:
                j0, j1 = nearest_idx(ts_t, odom[i-1][0]), nearest_idx(ts_t, odom[i][0])
                tm = math.sqrt(sum((truth[j1][k] - truth[j0][k]) ** 2 for k in (1, 2, 3)))
            if tm is not None and tm > JUMP_M:
                continue  # 真机动
            jumps += 1
            if t_star is None:
                t_star = odom[i][0]
    rep["t_star_s"] = round(t_star - t0, 1) if t_star else None
    rep["frame_jumps"] = jumps

    # ATE:t*(或末段)后 60s
    if ts_t:
        win_from = t_star if t_star else odom[-1][0] - 60
        pairs = []
        for o in odom:
            if win_from <= o[0] <= win_from + 60:
                j = nearest_idx(ts_t, o[0])
                if abs(ts_t[j] - o[0]) < 0.05:
                    pairs.append(((o[1], o[2], o[3]), (truth[j][1], truth[j][2], truth[j][3])))
        rep["ate_post60_m"] = round(umeyama_ate([a for a, _ in pairs], [b for _, b in pairs]), 3) if len(pairs) >= 10 else None
        rep["ate_n_pairs"] = len(pairs)
    # 特征存活率
    if feat:
        ts_f = [f[0] for f in feat]
        ref = t_star if t_star else ts_f[0]
        pre = [f[1] for f in feat if ref - 5 <= f[0] < ref]
        post = [f[1] for f in feat if ref <= f[0] <= ref + 60]
        if pre and post:
            rep["feat_pre_avg"] = round(sum(pre) / len(pre), 1)
            rep["feat_post60_avg"] = round(sum(post) / len(post), 1)
            rep["feat_survival"] = round((sum(post) / len(post)) / max(1e-6, sum(pre) / len(pre)), 3)
    # 判决
    ok = (rep.get("ate_post60_m") is not None and rep["ate_post60_m"] < 0.5
          and jumps == 0 and rep.get("feat_survival", 1) > 0.5)
    rep["pass"] = bool(ok)
    json.dump(rep, open(os.path.join(replay_dir, "eval.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
