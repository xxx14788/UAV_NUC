#!/usr/bin/env python3
"""VINS odom vs 真值代理的 ATE 评估（T2-W0-3，W3 矩阵与 W5 验收共用）。

用法: python3 vins_ate_eval.py <bag文件> [--vins-topic T] [--gt-topic T]
                                [--align-sec 5] [--div-thresh 1.0]
                                [--plot PNG] [--out JSON]

真值选择（--gt auto）:
  bag 含 /gazebo/model_states（含 iris 模型）→ 用它（绝对真值；
  VINS 闭环喂 EKF2 时 mavros odom 被污染，只能用这个）；
  否则用 /mavros/local_position/odom（EKF2，VINS 未接管时的真值代理）。

对齐: 取前 --align-sec 秒（默认 5）估计 VINS 与真值的 yaw 主方向差 δ 与
起点平移差，做 SE(2)（绕 z 旋转 δ + 平移）对齐后再算指标——VINS 世界系
yaw 任意，直接作差会把姿态差算成位置误差。

指标: ATE RMSE / max、xyz 各轴 RMSE、yaw 漂移（全程 & 每分钟）、
z 漂移、发散时刻（|pos err| > div-thresh 首次）、速度峰值。
依赖: ROS Noetic python3 + numpy/matplotlib(Agg)
"""
import argparse
import json
import math

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VINS_TOPIC_DEF = "/vins_estimator/imu_propagate"
VINS_TOPIC_ALT = "/vins_estimator/odometry"


def yaw_from_quat(x, y, z, w):
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def load_traj(bag, topic):
    """读 odom 话题 → dict(t, xyz, quat, twist)。"""
    import rosbag
    t, p, q, v = [], [], [], []
    with rosbag.Bag(bag, "r") as b:
        for _, msg, _st in b.read_messages(topics=[topic]):
            t.append(msg.header.stamp.to_sec())
            p.append([msg.pose.pose.position.x, msg.pose.pose.position.y,
                      msg.pose.pose.position.z])
            o = msg.pose.pose.orientation
            q.append([o.x, o.y, o.z, o.w])
            v.append([msg.twist.twist.linear.x, msg.twist.twist.linear.y,
                      msg.twist.twist.linear.z])
    return {"t": np.array(t), "p": np.array(p), "q": np.array(q),
            "v": np.array(v)}


def load_gt_model_states(bag, name_substr="iris"):
    """/gazebo/model_states → iris 模型轨迹。"""
    import rosbag
    from gazebo_msgs.msg import ModelStates  # noqa: F401 消息类型确认
    t, p, q = [], [], []
    with rosbag.Bag(bag, "r") as b:
        for _, msg, _st in b.read_messages(
                topics=["/gazebo/model_states"]):
            for i, nm in enumerate(msg.name):
                if name_substr in nm:
                    t.append(msg.header.stamp.to_sec()
                             if hasattr(msg, "header") and msg.header.stamp.to_sec() > 0
                             else None)
                    p.append([msg.pose[i].position.x, msg.pose[i].position.y,
                              msg.pose[i].position.z])
                    o = msg.pose[i].orientation
                    q.append([o.x, o.y, o.z, o.w])
                    break
    if not t:
        return None
    # model_states 无 header 时用 bag 时间；这里改用消息到达序不可靠，
    # gz 插件通常带 stamp，为空则由调用方回退
    t = np.array([x if x is not None else np.nan for x in t], dtype=float)
    if np.isnan(t).any():
        return None
    out = {"t": t, "p": np.array(p), "q": np.array(q)}
    return out


def bag_has(bag, topic):
    import rosbag
    with rosbag.Bag(bag, "r") as b:
        return topic in b.get_type_and_topic_info().topics


def se2_align(est, gt, align_sec):
    """前 align_sec 秒: yaw 主方向差 δ + 起点平移差 → SE(2) 对齐 est。"""
    m = est["t"] - est["t"][0] <= align_sec
    if m.sum() < 5:
        m = slice(None)
    yaw_e = np.array([yaw_from_quat(*est["q"][i]) for i in
                      range(len(est["q"]))])
    yaw_g = np.array([yaw_from_quat(*gt["q"][i]) for i in
                      range(len(gt["q"]))])
    # 对齐窗内 yaw 差的圆均值（处理 ±π 缠绕）
    if isinstance(m, np.ndarray):
        d = np.arctan2(np.sin(yaw_e[m] - yaw_g[m]), np.cos(yaw_e[m] - yaw_g[m]))
        delta = math.atan2(np.mean(np.sin(d)), np.mean(np.cos(d)))
        p0_e, p0_g = est["p"][m].mean(axis=0), gt["p"][m].mean(axis=0)
    else:
        d = np.arctan2(np.sin(yaw_e - yaw_g), np.cos(yaw_e - yaw_g))
        delta = math.atan2(np.mean(np.sin(d)), np.mean(np.cos(d)))
        p0_e, p0_g = est["p"].mean(axis=0), gt["p"].mean(axis=0)
    # est 世界系 = gt 世界系绕 z 旋 delta（est.p ≈ R(delta)·gt.p），
    # 对齐需施加逆旋转 R(-delta)
    c, s = math.cos(delta), math.sin(delta)
    R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    p_aligned = (R @ (est["p"] - p0_e).T).T + p0_g
    yaw_aligned = yaw_e - delta
    return p_aligned, yaw_aligned, delta, yaw_g


def interp_gt(gt, t_est):
    """真值插值到估计时刻。"""
    p = np.stack([np.interp(t_est, gt["t"], gt["p"][:, k]) for k in range(3)], 1)
    yaw = np.unwrap([yaw_from_quat(*q) for q in gt["q"]])
    y = np.interp(t_est, gt["t"], yaw)
    return p, y


def evaluate(est, gt, align_sec, div_thresh):
    p_al, yaw_al, delta, yaw_g_raw = se2_align(est, gt, align_sec)
    gt_p, gt_yaw = interp_gt(gt, est["t"])
    err = p_al - gt_p
    err_n = np.linalg.norm(err, axis=1)
    dur = est["t"][-1] - est["t"][0]
    dyaw = np.degrees(yaw_al - gt_yaw)  # 已 SE2 对齐，残余即漂移
    # 发散时刻: 连续 5 帧超阈
    div_t = None
    over = err_n > div_thresh
    for i in range(len(over) - 5):
        if over[i:i + 5].all():
            div_t = est["t"][i] - est["t"][0]
            break
    res = {
        "duration_s": dur,
        "align_yaw_deg": math.degrees(delta),
        "ate_rmse": float(np.sqrt(np.mean(err_n ** 2))),
        "ate_max": float(np.max(err_n)),
        "rmse_x": float(np.sqrt(np.mean(err[:, 0] ** 2))),
        "rmse_y": float(np.sqrt(np.mean(err[:, 1] ** 2))),
        "rmse_z": float(np.sqrt(np.mean(err[:, 2] ** 2))),
        "z_drift_end": float(err[-1, 2]),
        "yaw_drift_deg_end": float(dyaw[-1]),
        "yaw_drift_deg_per_min": float(dyaw[-1] / dur * 60) if dur > 0 else 0.0,
        "divergence_time_s": div_t,
        "vins_speed_max": float(np.max(np.linalg.norm(est["v"], axis=1)))
        if len(est["v"]) else float("nan"),
        "n_est": len(est["t"]), "n_gt": len(gt["t"]),
    }
    return res, err, err_n, dyaw, p_al, gt_p


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bagfile")
    ap.add_argument("--vins-topic", default=VINS_TOPIC_DEF,
                    help=f"默认 {VINS_TOPIC_DEF}，无则回退 {VINS_TOPIC_ALT}")
    ap.add_argument("--gt", default="auto",
                    help="auto|/mavros/local_position/odom|gazebo")
    ap.add_argument("--align-sec", type=float, default=5.0)
    ap.add_argument("--div-thresh", type=float, default=1.0)
    ap.add_argument("--plot", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not bag_has(args.bagfile, args.vins_topic):
        if bag_has(args.bagfile, VINS_TOPIC_ALT):
            print(f"[INFO] {args.vins_topic} 不在 bag 中，回退 {VINS_TOPIC_ALT}")
            args.vins_topic = VINS_TOPIC_ALT
        else:
            raise SystemExit(f"bag 中既无 {args.vins_topic} 也无 {VINS_TOPIC_ALT}")
    est = load_traj(args.bagfile, args.vins_topic)
    if len(est["t"]) < 10:
        raise SystemExit("VINS odom 样本不足")

    gt_src = args.gt
    if gt_src == "auto":
        if bag_has(args.bagfile, "/gazebo/model_states"):
            gt_src = "gazebo"
        elif bag_has(args.bagfile, "/mavros/local_position/odom"):
            gt_src = "/mavros/local_position/odom"
        else:
            raise SystemExit("bag 中无可用真值话题")
    if gt_src == "gazebo":
        gt = load_gt_model_states(args.bagfile)
        if gt is None:
            print("[WARN] model_states 无 stamp/无 iris，回退 mavros odom")
            gt_src = "/mavros/local_position/odom"
            gt = load_traj(args.bagfile, gt_src)
        else:
            gt["q"] = gt.get("q", np.zeros((len(gt["t"]), 4)))
            if len(gt["q"]) and not gt["q"].any():
                gt["q"] = np.tile([0, 0, 0, 1], (len(gt["t"]), 1))
    else:
        gt = load_traj(args.bagfile, gt_src)
    if len(gt["t"]) < 10:
        raise SystemExit("真值样本不足")

    # 时间窗交集
    t0, t1 = max(est["t"][0], gt["t"][0]), min(est["t"][-1], gt["t"][-1])
    est = {k: v[(est["t"] >= t0) & (est["t"] <= t1)] for k, v in est.items()}
    gt = {k: v[(gt["t"] >= t0) & (gt["t"] <= t1)] for k, v in gt.items()}

    res, err, err_n, dyaw, p_al, gt_p = evaluate(
        est, gt, args.align_sec, args.div_thresh)
    res["vins_topic"] = args.vins_topic
    res["gt_source"] = gt_src
    print("=" * 64)
    print(f"ATE 评估  {args.bagfile}")
    print(f"  vins: {args.vins_topic} ({res['n_est']} 帧)   "
          f"gt: {gt_src} ({res['n_gt']} 帧)   时长 {res['duration_s']:.1f}s")
    print(f"  SE(2) 对齐 yaw = {res['align_yaw_deg']:.2f}°  "
          f"(前 {args.align_sec}s 主方向差)")
    print(f"  ATE RMSE = {res['ate_rmse']:.3f} m   max = {res['ate_max']:.3f} m")
    print(f"  轴向 RMSE  x={res['rmse_x']:.3f}  y={res['rmse_y']:.3f}  "
          f"z={res['rmse_z']:.3f}  (z 末端漂移 {res['z_drift_end']:+.3f} m)")
    print(f"  yaw 漂移 末端 {res['yaw_drift_deg_end']:+.2f}°  "
          f"({res['yaw_drift_deg_per_min']:+.2f}°/min)")
    print(f"  发散时刻 (> {args.div_thresh}m 持续 5 帧): "
          f"{res['divergence_time_s'] if res['divergence_time_s'] is not None else '无'}")
    print(f"  VINS 速度峰值 {res['vins_speed_max']:.2f} m/s")
    print("=" * 64)

    out = args.out or (args.bagfile + ".ate.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"JSON: {out}")

    if args.plot:
        t_rel = est["t"] - est["t"][0]
        fig, ax = plt.subplots(2, 2, figsize=(12, 8))
        ax[0, 0].plot(gt_p[:, 0], gt_p[:, 1], "k-", lw=1.2, label="GT")
        ax[0, 0].plot(p_al[:, 0], p_al[:, 1], "b-", lw=0.8, label="VINS(对齐)")
        ax[0, 0].axis("equal"); ax[0, 0].legend(); ax[0, 0].grid(alpha=0.3)
        ax[0, 0].set_title("XY 轨迹")
        ax[0, 1].plot(t_rel, err_n, "r-", lw=0.8)
        ax[0, 1].axhline(args.div_thresh, color="k", ls="--", lw=0.7)
        ax[0, 1].set_ylabel("|pos err| m"); ax[0, 1].grid(alpha=0.3)
        ax[0, 1].set_title(f"ATE  RMSE={res['ate_rmse']:.3f}m")
        ax[1, 0].plot(t_rel, err[:, 0], label="x")
        ax[1, 0].plot(t_rel, err[:, 1], label="y")
        ax[1, 0].plot(t_rel, err[:, 2], label="z")
        ax[1, 0].legend(); ax[1, 0].grid(alpha=0.3)
        ax[1, 0].set_title("各轴误差")
        ax[1, 1].plot(t_rel, dyaw, "g-", lw=0.8)
        ax[1, 1].set_ylabel("yaw err °"); ax[1, 1].grid(alpha=0.3)
        ax[1, 1].set_title(f"yaw 漂移 末端 {res['yaw_drift_deg_end']:+.1f}°")
        fig.suptitle(f"{args.bagfile.split('/')[-1]}  gt={gt_src}")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=110)
        plt.close(fig)
        print(f"PNG: {args.plot}")


if __name__ == "__main__":
    main()
