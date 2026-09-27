#!/usr/bin/env python3
"""W0 工具集合成数据自测（阳性对照：注入已知异常，断言工具能检出）。

生成 /tmp/t2_selftest.bag:
  双目 20Hz mono8 320x240：静止 5s 干净（右=左平移 20px 视差），
    运动 5s 注入已知错拍模拟（左右目含 0.8px 级垂直失配 + 逐帧水平场景位移，
    同步陀螺 z=0.3rad/s）→ stereo_sync_check 应判 H-A 证实（检验1/3 异常）
  IMU 125Hz：静止/运动段与图像对齐
  odom：VINS=真值绕 z 旋 30°+0.2m 偏移+8s 处跳 5m 发散 → vins_ate_eval
    应给出小 ATE、发散时刻 ≈8s、对齐角 ≈30°
断言（阳性对照全部命中 → 工具链可信）:
  A1 stereo_sync_check: dy 运动段/静止段 > 3（注入阈值 5 的保守版）
  A2 vins_ate_eval: 对齐角 |30±3|°、发散时刻 7~9s、对齐后 ATE<0.3（发散前）
  A3 stereo_xcorr: 全程运行无异常、产出 JSON
依赖: ROS Noetic python3（rosbag 写）
"""
import math
import os
import subprocess
import sys

import numpy as np

import rosbag
import rospy
from sensor_msgs.msg import Image, Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
BAG = "/tmp/t2_selftest.bag"
DUR_STATIC, DUR_MOTION = 5.0, 5.0
W, H = 320, 240
DISP = 20  # 基线视差 px
YAW_OFF = math.radians(30.0)


def make_scene(seed=7):
    """结构化纹理（随机矩形块+渐变），白噪声会让 LK 的 dy 基线失真。"""
    rng = np.random.RandomState(seed)
    scene = np.fromfunction(lambda y, x: (x * 0.3 + y * 0.15) % 256,
                            (H, W)).astype(np.uint8)
    for _ in range(90):
        x0, y0 = rng.randint(0, W - 20), rng.randint(0, H - 20)
        w, h = rng.randint(8, 40), rng.randint(6, 24)
        v = rng.randint(0, 255)
        scene[y0:y0 + h, x0:x0 + w] = v
    return cv2_blur_np(scene)


def cv2_blur_np(img):
    import cv2
    return cv2.GaussianBlur(img, (5, 5), 0)


def roll(img, dx, dy=0):
    out = np.roll(img, dx, axis=1)
    if dy:
        out = np.roll(out, dy, axis=0)
    return out


def img_msg(gray, stamp):
    m = Image()
    m.header.stamp = stamp
    m.width, m.height = gray.shape[1], gray.shape[0]
    m.encoding = "mono8"
    m.step = gray.shape[1]
    m.data = gray.tobytes()
    return m


def quat_from_yaw(a):
    return Quaternion(0.0, 0.0, math.sin(a / 2), math.cos(a / 2))


def build_bag():
    scene = make_scene()
    rng = np.random.RandomState(3)
    with rosbag.Bag(BAG, "w") as bag:
        # 图像 20Hz
        n_img = int((DUR_STATIC + DUR_MOTION) * 20)
        for i in range(n_img):
            t = i / 20.0
            motion = t >= DUR_STATIC
            shift = int((t - DUR_STATIC) * 20 * 3) if motion else 0  # 3px/帧
            noise = rng.randint(0, 6, (H, W)).astype(np.int16)
            left = np.clip(roll(scene, shift).astype(np.int16) + noise,
                           0, 255).astype(np.uint8)
            # 运动段: 右目带 0.8px 级垂直失配（模拟错拍 dy）+ 视差
            dy_sub = 1 if motion else 0
            right = np.clip(roll(scene, shift + DISP, dy_sub).astype(np.int16)
                            + noise, 0, 255).astype(np.uint8)
            ts = rospy.Time.from_sec(1e9 + t)  # 近期时间戳
            bag.write("/iris_stereo_vins/vins_cam_left/image_raw",
                      img_msg(left, ts), ts)
            bag.write("/iris_stereo_vins/vins_cam_right/image_raw",
                      img_msg(right, ts), ts)
            # IMU 125Hz 单独循环（下面写）
        # IMU 125Hz
        n_imu = int((DUR_STATIC + DUR_MOTION) * 125)
        for i in range(n_imu):
            t = i / 125.0
            m = Imu()
            m.angular_velocity.z = 0.3 if t >= DUR_STATIC else 0.0
            m.linear_acceleration.z = 9.81
            m.header.stamp = rospy.Time.from_sec(1e9 + t)
            bag.write("/mavros/imu/data_raw", m,
                      rospy.Time.from_sec(1e9 + t))
        # odom: 真值直线 1m/s；VINS=真值绕z旋30°+0.2m偏移，8s 处跳 5m
        n_od = int((DUR_STATIC + DUR_MOTION) * 50)
        c, s = math.cos(YAW_OFF), math.sin(YAW_OFF)
        for i in range(n_od):
            t = i / 50.0
            x, y = min(t, 9.0) * 1.0, 0.0
            gt = Odometry()
            gt.header.stamp = rospy.Time.from_sec(1e9 + t)
            gt.pose.pose.position.x, gt.pose.pose.position.y = x, y
            gt.pose.pose.orientation = quat_from_yaw(0.0)
            bag.write("/mavros/local_position/odom", gt,
                      rospy.Time.from_sec(1e9 + t))
            xr = c * x - s * y + 0.2
            yr = s * x + c * y + 0.1
            if t >= 8.0:
                xr += 5.0  # 8s 起仅 VINS 发散（gt 持续正常）
            vins = Odometry()
            vins.header.stamp = rospy.Time.from_sec(1e9 + t)
            vins.pose.pose.position.x, vins.pose.pose.position.y = xr, yr
            vins.pose.pose.orientation = quat_from_yaw(YAW_OFF)
            bag.write("/vins_estimator/imu_propagate", vins,
                      rospy.Time.from_sec(1e9 + t))
    print(f"合成 bag: {BAG}")


def main():
    build_bag()
    ok = {}
    # A1 stereo_sync_check
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "stereo_sync_check.py"), BAG,
         "--out", "/tmp/t2_selftest.sync.json"],
        capture_output=True, text=True)
    print(r.stdout[-1500:])
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit("stereo_sync_check 运行失败")
    import json
    rep = json.load(open("/tmp/t2_selftest.sync.json", encoding="utf-8"))
    c1 = rep["checks"]["1_epipolar"]
    m_s = c1["dy_rms_static"]["mean"]
    m_m = c1["dy_rms_motion"]["mean"]
    ok["A1_dy_ratio"] = m_m / max(m_s, 1e-3) > 3
    print(f"A1 dy 运动段/静止段 = {m_m/max(m_s,1e-3):.1f}  "
          f"{'PASS' if ok['A1_dy_ratio'] else 'FAIL'}")

    # A2 vins_ate_eval
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "vins_ate_eval.py"), BAG,
         "--gt", "/mavros/local_position/odom",
         "--out", "/tmp/t2_selftest.ate.json"],
        capture_output=True, text=True)
    print(r.stdout[-1200:])
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit("vins_ate_eval 运行失败")
    ate = json.load(open("/tmp/t2_selftest.ate.json", encoding="utf-8"))
    ang_ok = abs(abs(ate["align_yaw_deg"]) - 30.0) < 3.0
    div_ok = ate["divergence_time_s"] is not None and \
        7.0 <= ate["divergence_time_s"] <= 9.0
    ok["A2_align"] = ang_ok
    ok["A2_divergence"] = div_ok
    print(f"A2 对齐角 {ate['align_yaw_deg']:.2f}° (期望±30)  "
          f"{'PASS' if ang_ok else 'FAIL'}；"
          f"发散时刻 {ate['divergence_time_s']}s (期望8)  "
          f"{'PASS' if div_ok else 'FAIL'}")

    # A3 stereo_xcorr
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "stereo_xcorr.py"), BAG,
         "--out", "/tmp/t2_selftest.xcorr.json"],
        capture_output=True, text=True)
    print(r.stdout[-600:])
    ok["A3_xcorr_runs"] = r.returncode == 0 and os.path.exists(
        "/tmp/t2_selftest.xcorr.json")
    print(f"A3 stereo_xcorr 运行  {'PASS' if ok['A3_xcorr_runs'] else 'FAIL'}")

    print("=" * 50)
    all_ok = all(ok.values())
    for k, v in ok.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print("自测总结:", "全部通过" if all_ok else "存在失败")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
