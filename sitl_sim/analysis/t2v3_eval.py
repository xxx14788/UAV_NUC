#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-v3 W1/W2 在线轮评估: 对齐后 ATE/漂移率/到位双口径/px4ctrl 跟踪。

自适应: 由 GT z>0.3m 判飞行窗口(起飞/降落时刻), 不硬编码时间。
输出 JSON(--out)与控制台摘要。
用法: python3 t2v3_eval.py <bag> [--goal x y z ...(可多次,飞行系)]
"""
import argparse
import json
import sys

import numpy as np
import rosbag


def load(bag):
    vt, vp = [], []
    gt, gp = [], []
    ct, cp = [], []
    with rosbag.Bag(bag, "r") as b:
        for tp, m, t in b.read_messages():
            ts = t.to_sec()
            if tp == "/vins_estimator/imu_propagate":
                vt.append(ts)
                p = m.pose.pose.position
                vp.append([p.x, p.y, p.z])
            elif tp == "/gazebo/model_states":
                names = list(m.name)
                idx = [i for i, x in enumerate(names) if "iris" in x]
                if idx:
                    gt.append(ts)
                    p = m.pose[idx[0]].position
                    gp.append([p.x, p.y, p.z])
            elif tp == "/position_cmd":
                ct.append(ts)
                p = m.position
                cp.append([p.x, p.y, p.z])
    return (np.array(vt), np.array(vp), np.array(gt), np.array(gp),
            np.array(ct), np.array(cp))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("--goal", nargs=3, type=float, action="append", default=[])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    vt, vp, gt, gp, ct, cp = load(a.bag)
    assert len(vt) > 100 and len(gt) > 100, "数据不足"
    t0 = vt[0]

    # VINS-GT 最近邻配对 + 出生点对齐(取首配对差为平移偏移)
    pairs = []
    for k in range(0, len(vt), 10):
        j = int(np.argmin(np.abs(gt - vt[k])))
        if abs(gt[j] - vt[k]) < 0.05:
            pairs.append((vt[k], vp[k], gp[j]))
    off = pairs[0][1] - pairs[0][2]
    ts_ = np.array([p[0] for p in pairs])
    err = np.array([np.linalg.norm(p[1] - p[2] - off) for p in pairs])

    # 飞行窗口: GT z > 0.3(减去出生 z)
    zoff = pairs[0][2][2]
    z = np.array([p[2][2] - zoff for p in pairs])
    fly = z > 0.3
    if fly.any():
        tf0 = ts_[fly][0]
        tf1 = ts_[fly][-1]
    else:
        tf0, tf1 = ts_[0], ts_[-1]
    fsel = (ts_ >= tf0) & (ts_ <= tf1)

    res = {
        "bag": a.bag,
        "t_span": [round(t0, 2), round(vt[-1], 2)],
        "align_offset": [round(x, 3) for x in off],
        "flight_window_rel": [round(tf0 - t0, 1), round(tf1 - t0, 1)],
        "fly_duration": round(tf1 - tf0, 1),
        "err_max_all": round(float(err.max()), 3),
        "err_max_flight": round(float(err[fsel].max()), 3),
        "rmse_flight": round(float(np.sqrt((err[fsel] ** 2).mean())), 3),
    }
    # @60s(飞行起算)
    k60 = (ts_ >= tf0 + 60) & (ts_ < tf0 + 62)
    if k60.any():
        res["ate_at60_flight"] = round(float(err[k60].mean()), 3)
    # 悬停段漂移率: 飞行窗内误差首尾线性率
    if fsel.sum() > 20:
        ef = err[fsel]
        tf = ts_[fsel]
        # 稳态窗: 飞行开始+5s 到 结束-3s
        s2 = (tf >= tf[0] + 5) & (tf <= tf[-1] - 3)
        if s2.sum() > 10:
            p = np.polyfit(tf[s2] - tf[s2][0], ef[s2], 1)[0]
            res["drift_m_per_min"] = round(float(p * 60), 3)
            res["err_flight_end"] = round(float(ef[-3:].mean()), 3)
    # 到位(每个 goal, 双口径): VINS 自报=飞行系直接; 真值=goal+出生平移(世界系)
    for gi, g in enumerate(a.goal):
        gv = np.array(g)
        gw = gv + off + pairs[0][2]  # 近似: 世界系 goal(含平移; 忽略 yaw 差)
        dmin_v = min(np.linalg.norm(vp - gv, axis=1))
        dmin_g = min(np.linalg.norm(gp - gw, axis=1))
        res["goal%d_min_vins" % gi] = round(float(dmin_v), 3)
        res["goal%d_min_gt_approx" % gi] = round(float(dmin_g), 3)
    # px4ctrl 跟踪(VINS odom vs position_cmd)
    if len(ct) > 20:
        tk = []
        for k in range(0, len(ct), 5):
            j = int(np.argmin(np.abs(vt - ct[k])))
            if abs(vt[j] - ct[k]) < 0.05:
                tk.append(np.linalg.norm(vp[j] - cp[k]))
        if tk:
            tk = np.array(tk)
            res["cmd_track_rmse"] = round(float(np.sqrt((tk ** 2).mean())), 3)
            res["cmd_track_max"] = round(float(tk.max()), 3)

    print(json.dumps(res, indent=1, ensure_ascii=False))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
