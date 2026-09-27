#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U7 分段误差归因: p2b 型漂移定位到具体运动阶段与主导激励量。

对在线闭环 bag 切 5s 窗, 每窗计算:
  - VINS-vs-真值 误差增长率 (m/s, 线性拟合)
  - 激励特征: |a| 峰/P95 (raw IMU), |ω| 峰/P95, LK 角点存活率, 光流幅值中位
输出每窗一行 + 各特征与误差增长率的相关系数(主导激励量裁决)。

用法: python3 segment_error_attribution.py <bag> [--win 5] [--gt gazebo]
真值: /gazebo/model_states (iris 索引自动探测, 无 header 用 bag 到达时间)
"""
import argparse
import sys

import cv2
import numpy as np
import rosbag

cv2.setNumThreads(2)


def load_all(bag_path, vins_bag=None):
    vins_t, vins_p, vins_q = [], [], []
    imu_t, imu_a, imu_w = [], [], []
    gt_t, gt_p = [], []
    img_l = []  # (bag_arrival_t, stamp, cvimage)
    vins_src = vins_bag or bag_path
    with rosbag.Bag(bag_path, "r") as b, rosbag.Bag(vins_src, "r") as bv:
        # VINS odometry 单独从 vins_src 读(重放模式)
        for topic, msg, t in bv.read_messages(topics=["/vins_estimator/odometry"]):
            vins_t.append(msg.header.stamp.to_sec())
            pp = msg.pose.pose.position
            vins_p.append([pp.x, pp.y, pp.z])
            q = msg.pose.pose.orientation
            vins_q.append([q.x, q.y, q.z, q.w])
        for topic, msg, t in b.read_messages():
            ta = t.to_sec()
            if topic == "/vins_estimator/odometry":
                continue
                vins_t.append(msg.header.stamp.to_sec())
                p = msg.pose.pose.position
                vins_p.append([p.x, p.y, p.z])
                q = msg.pose.pose.orientation
                vins_q.append([q.x, q.y, q.z, q.w])
            elif topic == "/mavros/imu/data_raw":
                imu_t.append(msg.header.stamp.to_sec())
                imu_a.append([msg.linear_acceleration.x, msg.linear_acceleration.y,
                              msg.linear_acceleration.z])
                imu_w.append([msg.angular_velocity.x, msg.angular_velocity.y,
                              msg.angular_velocity.z])
            elif topic == "/gazebo/model_states":
                names = list(msg.name)
                for cand in ("iris", "iris_stereo_vins", "zephyr"):
                    if cand in names:
                        i = names.index(cand)
                        gt_t.append(ta)
                        gt_p.append([msg.pose[i].position.x, msg.pose[i].position.y,
                                     msg.pose[i].position.z])
                        break
            elif topic == "/iris_stereo_vins/vins_cam_left/image_raw":
                arr = np.frombuffer(msg.data, dtype=np.uint8)
                if msg.encoding in ("bgr8", "rgb8"):
                    img = arr.reshape(msg.height, msg.width, 3)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                elif msg.encoding == "mono8":
                    img = arr.reshape(msg.height, msg.width)
                else:
                    img = arr.reshape(msg.height, msg.width)
                img_l.append((ta, msg.header.stamp.to_sec(), img))
    return (np.array(vins_t), np.array(vins_p), np.array(vins_q),
            np.array(imu_t), np.array(imu_a), np.array(imu_w),
            np.array(gt_t), np.array(gt_p), img_l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("--win", type=float, default=5.0)
    ap.add_argument("--vins-bag", default=None,
                    help="VINS 输出所在 bag(重放试验: odom 在私有 master 录制 bag)")
    args = ap.parse_args()

    vt, vp, vq, it, ia, iw, gtt, gtp, imgs = load_all(args.bag, args.vins_bag)
    print("VINS odom %d 帧 [%.2f, %.2f]; IMU %d; GT %d; 左目 %d" %
          (len(vt), vt[0], vt[-1], len(it), len(gtt), len(imgs)))
    assert len(vt) > 50, "VINS odometry 样本不足"

    # VINS 误差(最近邻 GT 配对, 域一致由在线配方保证)
    err = np.linalg.norm(
        np.array([vp[i] - gtp[np.argmin(np.abs(gtt - vt[i]))] for i in range(len(vt))]),
        axis=1)

    # LK 光流/角点存活: 相邻帧前向跟踪
    flow_mag = {}   # img_stamp -> (存活率, 中位流幅)
    prev = None
    for (ta, tstamp, im) in imgs:
        small = cv2.resize(im, (320, 240))
        if prev is not None:
            p0 = cv2.goodFeaturesToTrack(prev, 150, 0.01, 20)
            if p0 is not None and len(p0) >= 10:
                p1, stlk, err_ = cv2.calcOpticalFlowPyrLK(
                    prev, small, p0, None,
                    winSize=(21, 21), maxLevel=3,
                    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
                ok = stlk.ravel() == 1
                if ok.sum() >= 5:
                    d = np.linalg.norm((p1[ok] - p0[ok]).reshape(-1, 2), axis=1)
                    flow_mag[tstamp] = (ok.sum() / len(p0), float(np.median(d)))
        prev = small

    ia_n = np.linalg.norm(ia, axis=1)
    iw_n = np.linalg.norm(iw, axis=1)
    flow_keys = np.array(sorted(flow_mag))

    t0, t1 = vt[0], vt[-1]
    print("\n窗口  起_t   误差起→末(m)  增长率(m/s)  |a|峰  |a|P95  |ω|峰   存活率  流幅(px)")
    rows = []
    w = args.win
    tt = t0
    while tt + w <= t1 + 1e-6:
        sel = (vt >= tt) & (vt < tt + w)
        if sel.sum() >= 5:
            ew = err[sel]
            grow = np.polyfit(vt[sel] - tt, ew, 1)[0] if sel.sum() >= 3 else np.nan
            im_sel = (it >= tt) & (it < tt + w)
            a_pk = ia_n[im_sel].max() if im_sel.any() else np.nan
            a_p95 = np.percentile(ia_n[im_sel], 95) if im_sel.any() else np.nan
            w_pk = iw_n[im_sel].max() if im_sel.any() else np.nan
            fks = flow_keys[(flow_keys >= tt) & (flow_keys < tt + w)]
            surv = np.mean([flow_mag[k][0] for k in fks]) if len(fks) else np.nan
            fm = np.mean([flow_mag[k][1] for k in fks]) if len(fks) else np.nan
            rows.append((tt - t0, ew[0], ew[-1], grow, a_pk, a_p95, w_pk, surv, fm))
            print("%5.0f %6.1f  %7.3f→%7.3f  %8.4f  %6.1f  %6.1f  %6.3f  %6.2f  %6.1f"
                  % (tt - t0, tt, ew[0], ew[-1], grow, a_pk, a_p95, w_pk, surv, fm))
        tt += w

    R = np.array(rows)
    if len(R) >= 5:
        def corr(i):
            x, y = R[:, i], R[:, 3]
            m = np.isfinite(x) & np.isfinite(y)
            return np.corrcoef(x[m], y[m])[0, 1] if m.sum() >= 4 else np.nan
        print("\n误差增长率相关系数: |a|峰=%.2f |a|P95=%.2f |ω|峰=%.2f 存活率=%.2f 流幅=%.2f"
              % (corr(4), corr(5), corr(6), corr(7), corr(8)))
        np.savetxt(args.bag + ".segattr.csv", R, delimiter=",",
                   header="t_rel,err0,err1,grow_mps,a_peak,a_p95,w_peak,lk_survive,flow_px",
                   comments="")
        print("CSV -> %s.segattr.csv" % args.bag)


if __name__ == "__main__":
    main()
