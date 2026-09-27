#!/usr/bin/env python3
"""双目渲染同步性四项数值检验（T2-W1，裁决 H-A：双 camera sensor 渲染错拍）。

用法:
  python3 stereo_sync_check.py <bag文件> [--left-topic T] [--right-topic T]
                               [--imu-topic T] [--out 输出目录] [--plot]
  python3 stereo_sync_check.py --live --duration 30 [...]   # 实时流采样后离线分析

四项检验（全部数值法，无目视）:
  1 极线残差: 水平基线 rectified 对的 LK 匹配 dy 应≈0；统计 dy-RMS 时序与
    IMU 角速度模长的相关性（错拍时 dy 随角速度增大且强相关）
  2 静态目标视差稳定性: 图像上半部特征簇的视差在纯旋转段应恒定；
    错拍时视差随旋转抖动（std 增大）
  3 光流-IMU 一致性: 全场稀疏光流 − 陀螺预测光流(f·ω) 的残差 RMS，
    左右目分别做；一只滞后则两目残差时序反相（相关系数为负）
  4 互相关滞后: 调用 stereo_xcorr 的对齐 NCC 投票（stamp 同不代表内容同）

判定: 静止段 vs 运动段（由 IMU 角速度+加计模长分段）量化对比表；
任一检验运动段指标 >5 倍静止段 → H-A 证实；全部平稳 → H-A 排除。

依赖: ROS Noetic python3 + cv2/numpy/scipy/matplotlib(Agg)
"""
import argparse
import json
import os
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import cv2
except ImportError:
    sys.exit("需要 opencv-python (cv2)")

# 离线 bag 模式才 import rosbag（--self-test 不需要）
LEFT_TOPIC_DEF = "/iris_stereo_vins/vins_cam_left/image_raw"
RIGHT_TOPIC_DEF = "/iris_stereo_vins/vins_cam_right/image_raw"
IMU_TOPIC_DEF = "/mavros/imu/data_raw"

STATIC_GYRO_TH = 0.05   # rad/s，|ω| 低于此值判静止帧
STATIC_ACC_TH = 0.15    # m/s^2（相对 9.81 的波动）
MIN_SEG_FRAMES = 5      # 每段最少帧数才纳入统计
HA_RATIO = 5.0          # 运动段/静止段 > 5 → H-A 证实（任务书标准）


# ---------------------------------------------------------------- 基础工具
def to_gray(img_msg):
    """sensor_msgs/Image(compressed 亦可扩展) → 灰度 uint8。"""
    import rosbag  # noqa: F401  延迟导入确认环境
    enc = img_msg.encoding.lower()
    if enc in ("rgb8", "bgr8"):
        arr = np.frombuffer(img_msg.data, dtype=np.uint8).reshape(
            img_msg.height, img_msg.width, 3)
        return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY if enc == "bgr8"
                            else cv2.COLOR_RGB2GRAY)
    if enc == "mono8":
        return np.frombuffer(img_msg.data, dtype=np.uint8).reshape(
            img_msg.height, img_msg.width)
    if enc in ("32FC1",):
        arr = np.frombuffer(img_msg.data, dtype=np.float32).reshape(
            img_msg.height, img_msg.width)
        return cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    raise ValueError(f"不支持的编码: {enc}")


def quat_to_yaw_deg(q):
    """geometry_msgs 四元数 → yaw（度）。"""
    w, x, y, z = q.w, q.x, q.y, q.z
    return np.degrees(np.arctan2(2 * (w * z + x * y),
                                 1 - 2 * (y * y + z * z)))


# ---------------------------------------------------------------- 检验 1: 极线残差
def epipolar_dy(left, right):
    """一对图像的 LK 匹配 dy 统计。

    Shi-Tomasi 角点在左目提取，金字塔 LK 跟到右目，双向检查剔除外点；
    返回 (dy_rms, n_inlier)。水平基线下 dy≈0，错拍（含俯仰/横滚角速度）
    时 dy 与角速度成正比。
    """
    pts = cv2.goodFeaturesToTrack(
        left, maxCorners=200, qualityLevel=0.01, minDistance=10, blockSize=7)
    if pts is None or len(pts) < 10:
        return np.nan, 0
    p0 = pts.reshape(-1, 2)
    p1, st1, err1 = cv2.calcOpticalFlowPyrLK(
        left, right, p0.astype(np.float32), None,
        winSize=(31, 31), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    p1 = p1.reshape(-1, 2)
    p0b, st2, _ = cv2.calcOpticalFlowPyrLK(
        right, left, p1, None, winSize=(31, 31), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    p0b = p0b.reshape(-1, 2)
    keep = ((st1 == 1) & (st2 == 1)).ravel()
    if keep.sum() < 10:
        return np.nan, int(keep.sum())
    bid_err = np.linalg.norm(p0b[keep] - p0[keep], axis=1)
    inl = bid_err < 1.0  # 双向 1px 内为内点
    if inl.sum() < 10:
        return np.nan, int(inl.sum())
    dy = p1[keep][inl][:, 1] - p0[keep][inl][:, 1]
    return float(np.sqrt(np.mean(dy ** 2))), int(inl.sum())


# ---------------------------------------------------------------- 检验 2: 视差稳定性
def cluster_disparity_std(left, right, roi_slice):
    """图像上半部（远景/障碍箱）特征簇的视差 std。

    rectified 对上视差 = 左右特征 x 之差；同一静态簇在纯旋转时视差恒定，
    错拍时一帧的错位让视差整体抖动 → 帧间视差 std 放大。
    返回 (视差中位, 帧内视差 std)。
    """
    l_roi = left[roi_slice]
    r_roi = right[roi_slice]
    pts = cv2.goodFeaturesToTrack(
        l_roi, maxCorners=120, qualityLevel=0.01, minDistance=8, blockSize=7)
    if pts is None or len(pts) < 8:
        return np.nan, np.nan
    p0 = pts.reshape(-1, 2).astype(np.float32)
    p1, st, _ = cv2.calcOpticalFlowPyrLK(
        l_roi, r_roi, p0, None, winSize=(41, 41), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    p1 = p1.reshape(-1, 2)
    keep = st.ravel() == 1
    if keep.sum() < 8:
        return np.nan, np.nan
    disp = p0[keep][:, 0] - p1[keep][:, 0]
    med = float(np.median(disp))
    # 剔除视差离群（匹配噪声）后再求 std
    inl = np.abs(disp - med) < 3.0
    if inl.sum() < 8:
        return med, float(np.std(disp))
    return med, float(np.std(disp[inl]))


# ---------------------------------------------------------------- 检验 3: 光流-IMU
# 光流预测: 相机光学系 (x右 y下 z前)，纯旋转下静态点像素速度
#   du = s*( f*ωy_opt - ωz_opt*v ) ; dv = s*( ωz_opt*u - f*ωx_opt )
# s=±1 两种符号约定（世界系 vs 相机系旋转方向），对每目数据取残差更小的符号。
def gyro_to_optical(gyro_body, R_body_T_cam):
    """body 系角速度 → 光学系（ω_cam = R^T ω_body，R=body_T_cam 旋转块）。"""
    return R_body_T_cam.T @ gyro_body


def flow_predict(u, v, fx, fy, cx, cy, w_opt, sign):
    """陀螺预测光流（像素/帧间隔）。u,v 为像素坐标数组。"""
    du = sign * (fx * w_opt[1] - w_opt[2] * (v - cy))
    dv = sign * (w_opt[2] * (u - cx) - fx * w_opt[0])
    return du, dv


def flow_imu_residual(imgs_prev, imgs_next, w_body_dt, R, fx, cx, cy):
    """单目光流残差: 稀疏 LK 全场光流与陀螺预测之差的 RMS（含最优符号）。"""
    pts = cv2.goodFeaturesToTrack(
        imgs_prev, maxCorners=150, qualityLevel=0.01, minDistance=12,
        blockSize=7)
    if pts is None or len(pts) < 15:
        return np.nan, np.nan
    p0 = pts.reshape(-1, 2).astype(np.float32)
    p1, st, _ = cv2.calcOpticalFlowPyrLK(
        imgs_prev, imgs_next, p0, None, winSize=(21, 21), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.02))
    p1 = p1.reshape(-1, 2)
    keep = st.ravel() == 1
    if keep.sum() < 15:
        return np.nan, np.nan
    u, v = p0[keep][:, 0], p0[keep][:, 1]
    meas_u = p1[keep][:, 0] - u
    meas_v = p1[keep][:, 1] - v
    w_opt = gyro_to_optical(w_body_dt[:3], R)
    best = (np.inf, np.nan)
    for sign in (+1.0, -1.0):
        du, dv = flow_predict(u, v, fx, fx, cx, cy, w_opt, sign)
        r = np.concatenate([(meas_u - du), (meas_v - dv)])
        rms = float(np.sqrt(np.mean(r ** 2)))
        if rms < best[0]:
            best = (rms, sign)
    return best[0], best[1]


# ---------------------------------------------------------------- 检验 4: 互相关滞后
def xcorr_votes(pairs, align_disp=None):
    """(t, left_t, right_t, right_t_next) → 每帧 NCC 投票。

    用整体视差对齐右目后计算 NCC(l_t, r_t) 与 NCC(l_t, r_{t+1})，
    r_{t+1} 更相关 → 该帧存在一帧错拍。返回逐帧 lag(+1/0) 与两 NCC 差。
    """
    votes, margins = [], []
    for t, lt, rt, rtn in pairs:
        if align_disp:
            M = np.float32([[1, 0, -align_disp], [0, 1, 0]])
            rt_a = cv2.warpAffine(rt, M, (rt.shape[1], rt.shape[0]))
            rtn_a = cv2.warpAffine(rtn, M, (rtn.shape[1], rtn.shape[0]))
        else:
            rt_a, rtn_a = rt, rtn
        c0 = ncc(lt, rt_a)
        c1 = ncc(lt, rtn_a)
        if c0 is None or c1 is None:
            continue
        votes.append(1 if c1 > c0 else 0)
        margins.append(float(c1 - c0))
    return votes, margins


def ncc(a, b):
    """归一化互相关（去均值）。"""
    a = a.astype(np.float64) - np.mean(a)
    b = b.astype(np.float64) - np.mean(b)
    d = np.sqrt(np.sum(a * a) * np.sum(b * b))
    if d < 1e-9:
        return None
    return float(np.sum(a * b) / d)


# ---------------------------------------------------------------- 数据装载
def load_bag(bagfile, left_topic, right_topic, imu_topic, max_imgs=900):
    """读 bag: 返回 frames=[(t, left, right)], imu=[(t, ω3)], accel 模长。

    配对用双向缓冲按 stamp 最近邻匹配（不依赖 bag 内左右消息顺序），
    容差 5ms，超时 0.5s 丢弃未匹配帧。
    """
    import rosbag
    from collections import deque
    frames, imu = [], []
    n_l = n_r = 0
    pend_l = deque()  # [(t, gray)]
    pend_r = deque()
    TOL, STALE = 0.005, 0.5

    def try_match(now):
        while pend_l and pend_r:
            dt = pend_l[0][0] - pend_r[0][0]
            if abs(dt) <= TOL:
                t, lg = pend_l.popleft()
                _, rg = pend_r.popleft()
                frames.append((t, lg, rg))
            elif dt > 0:      # 左比右新 → 右太老，等新右（先丢超龄）
                if now - pend_r[0][0] > STALE:
                    pend_r.popleft()
                else:
                    break
            else:             # 右比左新
                if now - pend_l[0][0] > STALE:
                    pend_l.popleft()
                else:
                    break

    with rosbag.Bag(bagfile, "r") as bag:
        for _, msg, t in bag.read_messages(
                topics=[left_topic, right_topic, imu_topic]):
            ts = msg.header.stamp.to_sec()
            if _ == imu_topic:
                imu.append((ts,
                            np.array([msg.angular_velocity.x,
                                      msg.angular_velocity.y,
                                      msg.angular_velocity.z]),
                            np.array([msg.linear_acceleration.x,
                                      msg.linear_acceleration.y,
                                      msg.linear_acceleration.z])))
            elif _ == left_topic:
                n_l += 1
                pend_l.append((ts, to_gray(msg)))
            else:
                n_r += 1
                pend_r.append((ts, to_gray(msg)))
            try_match(ts)
            if len(frames) >= max_imgs:
                break
    imu.sort(key=lambda x: x[0])
    return frames, imu, n_l, n_r


def load_live(duration, left_topic, right_topic, imu_topic):
    """实时订阅 duration 秒，配对后返回同 load_bag 结构。"""
    import rospy
    from sensor_msgs.msg import Image, Imu
    frames, imu = [], []
    buf = {"l": None, "r": None}

    def on_left(m):
        buf["l"] = (m.header.stamp.to_sec(), to_gray(m))

    def on_right(m):
        buf["r"] = (m.header.stamp.to_sec(), to_gray(m))

    def on_imu(m):
        imu.append((m.header.stamp.to_sec(),
                    np.array([m.angular_velocity.x, m.angular_velocity.y,
                              m.angular_velocity.z]),
                    np.array([m.linear_acceleration.x,
                              m.linear_acceleration.y,
                              m.linear_acceleration.z])))

    rospy.init_node("stereo_sync_check_live", anonymous=True, disable_signals=True)
    rospy.Subscriber(left_topic, Image, on_left, queue_size=2)
    rospy.Subscriber(right_topic, Image, on_right, queue_size=2)
    rospy.Subscriber(imu_topic, Imu, on_imu, queue_size=50)
    r = rospy.Rate(50)
    t_end = rospy.get_time() + duration
    while rospy.get_time() < t_end and not rospy.is_shutdown():
        if buf["l"] and buf["r"] and abs(buf["l"][0] - buf["r"][0]) < 0.005:
            frames.append((buf["l"][0], buf["l"][1], buf["r"][1]))
            buf["l"] = buf["r"] = None
        r.sleep()
    imu.sort(key=lambda x: x[0])
    return frames, imu, len(frames), len(frames)


# ---------------------------------------------------------------- 主分析
def analyze(frames, imu, fx=467.74, cx=320.5, cy=240.5, roi_top=(0, 200),
            R_body_T_cam=None, make_plot=None, out_json=None):
    """跑四项检验并输出报告。R_body_T_cam 默认用 sim_stereo 配置值。"""
    if R_body_T_cam is None:
        R_body_T_cam = np.array([[0.0, 0.0, 1.0],
                                 [-1.0, 0.0, 0.0],
                                 [0.0, -1.0, 0.0]])
    gyro_t = np.array([x[0] for x in imu])
    gyro_w = np.array([x[1] for x in imu])
    accel = np.array([x[2] for x in imu])
    gyro_dt = np.diff(gyro_t, prepend=gyro_t[0] - 0.01)

    res = {"n_frames": len(frames), "n_imu": len(imu), "checks": {}}

    # --- 分段: 静止/运动（按图像时刻插值 IMU）
    ts = np.array([f[0] for f in frames])
    w_body = np.stack([np.interp(ts, gyro_t, gyro_w[:, k]) for k in range(3)], 1)
    w_norm = np.linalg.norm(w_body, axis=1)
    a_norm = np.linalg.norm(
        np.stack([np.interp(ts, gyro_t, accel[:, k]) for k in range(3)], 1),
        axis=1)
    static = (w_norm < STATIC_GYRO_TH) & (np.abs(a_norm - 9.81) < STATIC_ACC_TH)
    res["n_static"] = int(static.sum())
    res["n_motion"] = int((~static).sum())

    if static.sum() < MIN_SEG_FRAMES or (~static).sum() < MIN_SEG_FRAMES:
        print(f"[WARN] 段样本不足 static={static.sum()} "
              f"motion={(~static).sum()}，对比表可靠性有限")

    # --- 检验 1: 极线残差
    dy_series = []
    for t, lt, rt in frames:
        rms, _ = epipolar_dy(lt, rt)
        dy_series.append(rms)
    dy_series = np.array(dy_series, dtype=float)
    valid = ~np.isnan(dy_series)
    corr_dy_gyro = safe_pearson(dy_series[valid], w_norm[valid])
    res["checks"]["1_epipolar"] = {
        "dy_rms_static": seg_stat(dy_series, static),
        "dy_rms_motion": seg_stat(dy_series, ~static),
        "corr_dy_vs_gyro": corr_dy_gyro,
    }

    # --- 检验 2: 视差稳定性（图像上半 ROI）
    roi = slice(roi_top[0], roi_top[1]), slice(None)
    disp_med, disp_std = [], []
    for t, lt, rt in frames:
        m, s = cluster_disparity_std(lt, rt, roi)
        disp_med.append(m)
        disp_std.append(s)
    disp_std = np.array(disp_std, dtype=float)
    disp_med = np.array(disp_med, dtype=float)
    # 帧间视差中位变化（错拍时视差整体抖动 → 帧间 |Δ| 大）
    dmed_step = np.abs(np.diff(disp_med, prepend=disp_med[0]))
    res["checks"]["2_disparity"] = {
        "intra_std_static": seg_stat(disp_std, static),
        "intra_std_motion": seg_stat(disp_std, ~static),
        "median_step_static": seg_stat(dmed_step, static),
        "median_step_motion": seg_stat(dmed_step, ~static),
    }

    # --- 检验 3: 光流-IMU 一致性（左右目分别）
    res_l, res_r, t3 = [], [], []
    for i in range(len(frames) - 1):
        t, lt, rt = frames[i]
        _, lt2, rt2 = frames[i + 1]
        # 帧间隔内的平均角速度×帧间隔 = 角增量积分近似
        t0, t1 = frames[i][0], frames[i + 1][0]
        i0 = np.searchsorted(gyro_t, t0, "right") - 1
        i1 = max(np.searchsorted(gyro_t, t1, "right"), i0 + 1)
        w_mean = gyro_w[max(i0, 0):i1].mean(axis=0) if i1 > i0 else gyro_w[max(i0, 0)]
        dt = t1 - t0
        w_body_dt = np.concatenate([w_mean * dt, [dt]])  # 前三位=角度增量
        rl, _ = flow_imu_residual(lt, lt2, w_body_dt, R_body_T_cam, fx, cx, cy)
        rr, _ = flow_imu_residual(rt, rt2, w_body_dt, R_body_T_cam, fx, cx, cy)
        res_l.append(rl)
        res_r.append(rr)
        t3.append(t1)
    res_l = np.array(res_l, dtype=float)
    res_r = np.array(res_r, dtype=float)
    st3 = static[1:len(res_l) + 1]
    lr_corr = safe_pearson(res_l[~np.isnan(res_l)], res_r[~np.isnan(res_r)])
    res["checks"]["3_flow_imu"] = {
        "residual_rms_left_static": seg_stat(res_l, st3),
        "residual_rms_left_motion": seg_stat(res_l, ~st3),
        "residual_rms_right_static": seg_stat(res_r, st3),
        "residual_rms_right_motion": seg_stat(res_r, ~st3),
        "lr_residual_corr": lr_corr,
    }

    # --- 检验 4: 互相关滞后（对齐后 NCC 投票）
    quads = []
    for i in range(len(frames) - 1):
        t, lt, rt = frames[i]
        _, _, rtn = frames[i + 1]
        quads.append((t, lt, rt, rtn))
    # 整体视差: 用 phase correlation 在首帧估计水平偏移（中位滚动）
    disp0 = 0.0
    try:
        r = cv2.phaseCorrelate(np.float32(frames[0][1]), np.float32(frames[0][2]))
        first = r[0]
        disp0 = float(first[0] if hasattr(first, "__len__") else first)
    except (cv2.error, TypeError, IndexError):
        pass
    votes, margins = xcorr_votes(quads, align_disp=disp0)
    votes = np.array(votes, dtype=float)
    # 错拍帧更易出现在运动段
    st4 = static[:len(votes)]
    lag_static = float(np.mean(votes[st4])) if st4.sum() else np.nan
    lag_motion = float(np.mean(votes[~st4])) if (~st4).sum() else np.nan
    res["checks"]["4_xcorr"] = {
        "global_shift_px": disp0,
        "lag_vote_rate_static": lag_static,
        "lag_vote_rate_motion": lag_motion,
        "margin_mean_static": float(np.mean(np.array(margins)[st4]))
        if st4.sum() and margins else np.nan,
        "margin_mean_motion": float(np.mean(np.array(margins)[~st4]))
        if (~st4).sum() and margins else np.nan,
    }

    report(res, frames, dy_series, w_norm, static, res_l, res_r, votes,
           make_plot)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, default=float)
        print(f"JSON 报告: {out_json}")
    return res


def seg_stat(series, mask):
    """段的均值/std（忽略 NaN）。mask 长于 series 时截到 series 长度。"""
    s = np.asarray(series, dtype=float)
    m = np.asarray(mask, dtype=bool)[:len(s)]
    sel = s[m & ~np.isnan(s)]
    if len(sel) == 0:
        return {"mean": float("nan"), "std": float("nan"), "n": 0}
    return {"mean": float(np.mean(sel)), "std": float(np.std(sel)),
            "n": int(len(sel))}


def safe_pearson(a, b):
    if len(a) != len(b) or len(a) < 3:
        return float("nan")
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 3 or np.std(a[ok]) < 1e-9 or np.std(b[ok]) < 1e-9:
        return float("nan")
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def report(res, frames, dy_series, w_norm, static, res_l, res_r, votes,
           make_plot):
    """终端四项检验表 + H-A 裁决。"""
    c1 = res["checks"]["1_epipolar"]
    c2 = res["checks"]["2_disparity"]
    c3 = res["checks"]["3_flow_imu"]
    c4 = res["checks"]["4_xcorr"]

    def ratio(m_s, m_m):
        if not np.isfinite(m_s) or m_s <= 1e-6 or not np.isfinite(m_m):
            return float("inf") if (np.isfinite(m_m) and m_m > 1e-6) else float("nan")
        return m_m / m_s

    r1 = ratio(c1["dy_rms_static"]["mean"], c1["dy_rms_motion"]["mean"])
    r2 = ratio(c2["median_step_static"]["mean"], c2["median_step_motion"]["mean"])
    r3l = ratio(c3["residual_rms_left_static"]["mean"],
                c3["residual_rms_left_motion"]["mean"])
    r3r = ratio(c3["residual_rms_right_static"]["mean"],
                c3["residual_rms_right_motion"]["mean"])
    verdicts = {
        "1_epipolar": r1 > HA_RATIO and abs(c1["corr_dy_vs_gyro"] or 0) > 0.5,
        "2_disparity": r2 > HA_RATIO,
        "3_flow_imu": max(r3l, r3r) > HA_RATIO or (c3["lr_residual_corr"] or 1) < -0.3,
        "4_xcorr": (c4["lag_vote_rate_motion"] or 0) > max(
            0.10, 3 * (c4["lag_vote_rate_static"] or 0)),
    }
    n_pos = sum(verdicts.values())
    ha = "证实" if n_pos >= 1 else "排除"
    print("=" * 72)
    print(f"双目同步性四项检验  frames={res['n_frames']}  "
          f"static={res['n_static']}  motion={res['n_motion']}")
    print("-" * 72)
    print(f"{'检验':<28}{'静止段':>12}{'运动段':>12}{'比值':>8}  判定")
    print(f"{'1 dy-RMS (px)':<28}{c1['dy_rms_static']['mean']:>12.3f}"
          f"{c1['dy_rms_motion']['mean']:>12.3f}{r1:>8.1f}  "
          f"{'异常' if verdicts['1_epipolar'] else '平稳'}"
          f"  corr(dy,|ω|)={c1['corr_dy_vs_gyro']:.2f}")
    print(f"{'2 视差中位帧间步进 (px)':<28}"
          f"{c2['median_step_static']['mean']:>12.3f}"
          f"{c2['median_step_motion']['mean']:>12.3f}{r2:>8.1f}  "
          f"{'异常' if verdicts['2_disparity'] else '平稳'}")
    print(f"{'3 光流-IMU 残差 L (px)':<28}"
          f"{c3['residual_rms_left_static']['mean']:>12.3f}"
          f"{c3['residual_rms_left_motion']['mean']:>12.3f}{r3l:>8.1f}")
    print(f"{'3 光流-IMU 残差 R (px)':<28}"
          f"{c3['residual_rms_right_static']['mean']:>12.3f}"
          f"{c3['residual_rms_right_motion']['mean']:>12.3f}{r3r:>8.1f}  "
          f"{'异常' if verdicts['3_flow_imu'] else '平稳'}"
          f"  corr(L残差,R残差)={c3['lr_residual_corr']:.2f}")
    print(f"{'4 错拍投票率 (帧占比)':<28}"
          f"{c4['lag_vote_rate_static']:>12.3f}"
          f"{c4['lag_vote_rate_motion']:>12.3f}{'':>8}  "
          f"{'异常' if verdicts['4_xcorr'] else '平稳'}")
    print("-" * 72)
    print(f"H-A 裁决: {ha}（{n_pos}/4 项运动段异常>5倍静止段）")
    print("=" * 72)
    res["verdicts"] = {k: bool(v) for k, v in verdicts.items()}
    res["H_A"] = ha

    if make_plot:
        ts = np.array([f[0] for f in frames])
        t0 = ts[0]
        fig, ax = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
        for a, y, lbl in [
                (ax[0], dy_series, "1 dy-RMS (px)"),
                (ax[0], w_norm, "|ω| (rad/s)  [右轴×100]")]:
            if a is ax[0] and lbl.startswith("|"):
                a2 = a.twinx()
                a2.plot(ts - t0, y * 100, "r-", alpha=0.5, lw=0.8)
            else:
                a.plot(ts - t0, y, "b.-", ms=2, lw=0.7)
        ax[0].set_ylabel("dy-RMS px / |ω|×100")
        ax[0].set_title("检验1 极线残差 vs IMU 角速度")
        t3 = ts[1:len(res_l) + 1] - t0
        ax[1].plot(t3, res_l, "b-", lw=0.8, label="left")
        ax[1].plot(t3, res_r, "g-", lw=0.8, label="right")
        ax[1].legend(); ax[1].set_ylabel("残差 RMS px")
        ax[1].set_title("检验3 光流-IMU 残差（左右目）")
        for i in np.where(static)[0]:
            for a in ax:
                a.axvline(ts[i] - t0, color="k", alpha=0.05, lw=0.5)
        ax[2].step(ts - t0, np.arange(len(ts)) * 0 + np.nan, lw=0)  # 占位
        ax[2].clear()
        v_t = ts[:len(votes)] - t0
        ax[2].plot(v_t, votes, "r.", ms=3)
        ax[2].set_ylim(-0.1, 1.1); ax[2].set_ylabel("lag vote")
        ax[2].set_title("检验4 互相关错拍投票（1=错拍帧）")
        ax[3].plot(ts - t0, static.astype(int), "k-", lw=0.8)
        ax[3].set_ylabel("static=1"); ax[3].set_xlabel("t (s)")
        ax[3].set_title("分段（静止/运动，IMU 判定）")
        fig.tight_layout()
        fig.savefig(make_plot, dpi=110)
        print(f"图: {make_plot}")
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bagfile", nargs="?", help="bag 文件（省略则需 --live）")
    ap.add_argument("--live", action="store_true", help="实时流模式")
    ap.add_argument("--duration", type=float, default=30, help="live 模式采样秒数")
    ap.add_argument("--left-topic", default=LEFT_TOPIC_DEF)
    ap.add_argument("--right-topic", default=RIGHT_TOPIC_DEF)
    ap.add_argument("--imu-topic", default=IMU_TOPIC_DEF)
    ap.add_argument("--fx", type=float, default=467.74, help="焦距像素（SDF hfov=1.2）")
    ap.add_argument("--cx", type=float, default=320.5)
    ap.add_argument("--cy", type=float, default=240.5)
    ap.add_argument("--out", default=None, help="JSON 报告输出路径")
    ap.add_argument("--plot", default=None, help="PNG 输出路径")
    ap.add_argument("--max-imgs", type=int, default=900)
    args = ap.parse_args()

    if args.live:
        frames, imu, n_l, n_r = load_live(
            args.duration, args.left_topic, args.right_topic, args.imu_topic)
    else:
        if not args.bagfile:
            ap.error("需要 bag 文件或 --live")
        print(f"读取 {args.bagfile} ...")
        frames, imu, n_l, n_r = load_bag(
            args.bagfile, args.left_topic, args.right_topic, args.imu_topic,
            args.max_imgs)
    print(f"配对帧 {len(frames)}（左 {n_l} / 右 {n_r}），IMU {len(imu)} 条")
    if len(frames) < 20 or len(imu) < 100:
        sys.exit("数据量不足（<20 帧 或 <100 IMU），退出")
    out_json = args.out or (args.bagfile + ".sync.json" if args.bagfile
                            else "stereo_sync_report.json")
    plot = args.plot or (out_json.replace(".json", ".png"))
    analyze(frames, imu, fx=args.fx, cx=args.cx, cy=args.cy,
            make_plot=plot, out_json=out_json)


if __name__ == "__main__":
    main()
