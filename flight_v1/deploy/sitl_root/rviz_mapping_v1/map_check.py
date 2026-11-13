#!/usr/bin/env python3
"""Read-only ROS input/stream audit; optionally write private map parameters."""
import argparse
import json
import math
import signal
import sys
import threading
import time
from pathlib import Path

import numpy as np
import yaml

DEPTH = "/camera/depth/image_rect_raw"
INFO = "/camera/depth/camera_info"
ODOM = "/vins_estimator/imu_propagate"
EXT = "/vins_estimator/extrinsic"
FRAME = "world"
PREFIX = "/drone_0_ego_planner_node"


def parameters(info, depth_frame):
    """Rectified depth uses P; do not substitute RGB intrinsics or guessed center."""
    p = list(info.P)
    fx, fy, cx, cy = p[0], p[5], p[2], p[6]
    if not all(math.isfinite(x) for x in p) or fx <= 0 or fy <= 0:
        raise ValueError("camera_info.P 内参无效")
    # 2026-11-10：投影缓存已改为按图像尺寸动态扩容，此处只做"档位白名单"检查
    if (info.width, info.height) not in ((640, 480), (848, 480), (1280, 720)):
        raise ValueError("深度图分辨率 %dx%d 不在支持档位(640x480/848x480/1280x720)"
                         % (info.width, info.height))
    if abs(p[3]) > 1e-6 or abs(p[7]) > 1e-6:
        raise ValueError("深度参考相机 P 含非零投影平移，需明确几何后适配")
    return {
        "input": {"depth_topic": DEPTH, "odom_topic": ODOM, "extrinsic_topic": EXT,
                  "depth_frame": depth_frame, "max_age": 0.5, "max_skew": 0.04},
        "grid_map": {
            "resolution": 0.15, "map_size_x": 30.0, "map_size_y": 30.0, "map_size_z": 3.0,
            "local_update_range_x": 5.5, "local_update_range_y": 5.5, "local_update_range_z": 4.5,
            "obstacles_inflation": 0.299, "local_map_margin": 10,
            # Viewer includes the floor below the IMU's start origin. Not a flight altitude.
            "ground_height": -0.30, "frame_id": FRAME, "pose_type": 1,
            "fx": fx, "fy": fy, "cx": cx, "cy": cy,
            "use_depth_filter": True, "depth_filter_tolerance": 0.15,
            "depth_filter_maxdist": 5.0, "depth_filter_mindist": 0.2,
            "depth_filter_margin": 2, "k_depth_scaling_factor": 1000.0, "skip_pixel": 2,
            "p_hit": 0.65, "p_miss": 0.35, "p_min": 0.12, "p_max": 0.90, "p_occ": 0.80,
            "min_ray_length": 0.3, "max_ray_length": 5.0,
            "visualization_truncate_height": 2.7, "show_occ_time": False,
        },
    }


def finite_pose(m):
    p, q = m.pose.pose.position, m.pose.pose.orientation
    a = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
    return all(math.isfinite(v) for v in a) and abs(sum(v*v for v in a[3:]) - 1) <= 0.02


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--allow-armed", action="store_true", help="运行时健康检查允许飞机处于解锁状态")
    ap.add_argument("--watch", type=float, default=6.0)
    a = ap.parse_args()
    if not 2 <= a.watch <= 30:
        ap.error("--watch 范围 2–30 秒")
    signal.signal(signal.SIGALRM, lambda *_: sys.exit("CHECK TIMEOUT：ROS 无响应"))
    signal.alarm(int(a.watch) + 15)
    import rospy
    import tf2_ros
    from geometry_msgs.msg import PoseStamped
    from mavros_msgs.msg import State
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import CameraInfo, Image, PointCloud2
    from std_msgs.msg import String

    rospy.init_node("map_view_check", anonymous=True, disable_signals=True)
    lock = threading.Lock()
    latest, arrivals = {}, {}
    def cb(m, topic):
        with lock:
            latest[topic] = m
            arrivals.setdefault(topic, []).append(time.monotonic())
    subs = []
    for topic, cls in [(DEPTH, Image), (INFO, CameraInfo), (ODOM, Odometry),
                       (EXT, Odometry), ("/mavros/state", State)]:
        subs.append(rospy.Subscriber(topic, cls, cb, callback_args=topic, queue_size=2))
    if a.status:
        for topic, cls in [(PREFIX + "/grid_map/occupancy", PointCloud2),
                           (PREFIX + "/grid_map/occupancy_inflate", PointCloud2)]:
            subs.append(rospy.Subscriber(topic, cls, cb, callback_args=topic, queue_size=2))
        subs.append(rospy.Subscriber("/planner/camera_pose", PoseStamped, cb,
                                     callback_args="/planner/camera_pose", queue_size=2))
    buffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(buffer)
    time.sleep(a.watch)
    failures, checks = [], []
    def check(name, ok, detail):
        checks.append({"item": name, "pass": bool(ok), "detail": detail})
        print(("[PASS] " if ok else "[FAIL] ") + name + ": " + str(detail))
        if not ok:
            failures.append(name)
    now_mono, now_ros = time.monotonic(), rospy.Time.now().to_sec()
    with lock:
        messages = dict(latest)
        received = {k: list(v) for k, v in arrivals.items()}
    check("实机时钟", not rospy.get_param("/use_sim_time", False), "/use_sim_time 应为 false")
    for topic, minimum in [(DEPTH, 15), (ODOM, 40), (EXT, 5)]:
        times = received.get(topic, [])
        hz = (len(times)-1)/(times[-1]-times[0]) if len(times) > 1 and times[-1] > times[0] else 0
        m = messages.get(topic)
        age = now_ros-m.header.stamp.to_sec() if m else None
        alive = times and now_mono-times[-1] < 0.5 and age is not None and -0.05 <= age <= 0.5
        check(topic, hz >= minimum and alive, {"hz": round(hz, 2), "stamp_age_s": age, "min_hz": minimum})
    state = messages.get("/mavros/state")
    state_age = now_ros-state.header.stamp.to_sec() if state else None
    check("飞控连接/地面状态", state and state.connected and (a.allow_armed or not state.armed) and -0.05 <= state_age < 2,
          {"connected": state.connected if state else None, "armed": state.armed if state else None,
           "armed_allowed": a.allow_armed})
    image, info = messages.get(DEPTH), messages.get(INFO)
    check("深度格式", image and image.encoding == "16UC1" and (image.width, image.height) in ((640, 480), (848, 480), (1280, 720)),
          {"encoding": image.encoding, "width": image.width, "height": image.height} if image else "无图像")
    config = None
    if info and image:
        try:
            if info.header.frame_id != image.header.frame_id:
                raise ValueError("camera_info 与深度图 frame 不一致")
            config = parameters(info, image.header.frame_id)
            check("当前深度内参", True, {k: config["grid_map"][k] for k in ("fx", "fy", "cx", "cy")})
        except ValueError as e:
            check("当前深度内参", False, str(e))
        try:
            t = buffer.lookup_transform("camera_infra1_optical_frame", image.header.frame_id, rospy.Time(0))
            p, q = t.transform.translation, t.transform.rotation
            distance = math.sqrt(p.x*p.x+p.y*p.y+p.z*p.z)
            angle = 2*math.acos(min(1, abs(q.w)))
            # Otherwise T_imu_cam0 must be composed with T_cam0_depth explicitly.
            check("深度与VINS左目坐标一致", distance < 1e-4 and angle < 1e-4,
                  {"translation_m": distance, "rotation_rad": angle})
        except tf2_ros.TransformException as e:
            check("深度与VINS左目坐标一致", False, str(e))
    else:
        check("当前深度内参", False, "缺 depth camera_info 或深度图")
    odom, ext = messages.get(ODOM), messages.get(EXT)
    check("VINS位姿", odom and finite_pose(odom) and odom.header.frame_id == FRAME,
          odom.header.frame_id if odom else "VINS 未出流；先在另一终端运行 vins_only.sh，并保持静置")
    check("VINS外参", ext and finite_pose(ext) and sum(getattr(ext.pose.pose.position, k)**2 for k in "xyz") < 1,
          "T_imu_cam0；仅验证有限值、单位四元数和量级，装配准确性仍需量测")
    if a.status:
        pose = messages.get("/planner/camera_pose")
        times = received.get("/planner/camera_pose", [])
        pose_age = now_ros-pose.header.stamp.to_sec() if pose else None
        check("规划器相机位姿持续更新", pose and times and now_mono-times[-1] < 1.0 and pose_age is not None and -0.05 <= pose_age <= 0.5,
              {"stamp_age_s": pose_age, "hz_window": len(times)})
        for topic in [PREFIX + "/grid_map/occupancy", PREFIX + "/grid_map/occupancy_inflate"]:
            m = messages.get(topic)
            times = received.get(topic, [])
            count = m.width*m.height if m else 0
            check(topic, m and count > 0 and m.header.frame_id == FRAME and times and now_mono-times[-1] < 1,
                  {"points": count, "frame": m.header.frame_id if m else None})
        print("注：PointCloud2 时间戳可能为零；同时检查 VINS 相机位姿新鲜度，不能用旧地图证明输入健康。")
    result = {"verdict": "FAIL" if failures else "PASS", "checks": checks, "time": time.time()}
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if not failures and a.config and config:
        a.config.parent.mkdir(parents=True, exist_ok=True)
        a.config.write_text(yaml.safe_dump(config, sort_keys=False))
        print("内参/几何快照已写入 " + str(a.config))
    print("MAP CHECK " + result["verdict"] + "（流与配置检查；实物位置/尺寸仍需现场核对）")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
