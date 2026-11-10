#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T6：grid_map 深度过滤 off-by-one 的**功能测试**（真规划器，无桨）。

原理：发一张"1 像素宽的 2 m 竖条 + 其余全是 0"的深度图。
  * 修前（off-by-one）：每个竖条像素的**右邻居**是 0 -> depth 被改写成 max_ray+0.1
    当自由空间 -> 竖条被从地图上侵蚀掉 -> 地图里 2 m 处几乎没有点。
  * 修后：判的是本像素 -> 竖条保留 -> 地图里 2 m 处应有一片点。

判据（预注册）：2.0±0.5 m 处的点数 >= 20（修前为 0~个位数）。

用法：source ROS 后  python3 test_depth_offbyone.py
"""
import array
import os
import signal
import subprocess
import sys
import threading
import time

PORT = 11316
URI = "http://localhost:%d" % PORT
FV = os.path.expanduser("~/sitl_realmachine/flight_v1")
LAUNCH = os.path.join(FV, "run_planner_realmachine_map_v1.launch")
W, H = 1280, 720
STRIPE_MM = 2000


def main():
    os.environ["ROS_MASTER_URI"] = URI
    e = dict(os.environ)
    e["ROS_MASTER_URI"] = URI
    if subprocess.run(["bash", "-c", "ss -ltn | grep -q :%d" % PORT]).returncode == 0:
        print("!! 端口 %d 被占用（残留？）" % PORT)
        return 2
    core = subprocess.Popen(["roscore", "-p", str(PORT)], env=e,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            preexec_fn=os.setsid)
    time.sleep(4)
    planner = subprocess.Popen(["roslaunch", "--wait", LAUNCH], env=e,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               preexec_fn=os.setsid)
    try:
        import rospy
        from sensor_msgs.msg import Image, PointCloud2
        from geometry_msgs.msg import PoseStamped
        from nav_msgs.msg import Odometry
        import sensor_msgs.point_cloud2 as pc2

        rospy.init_node("test_offbyone", anonymous=True, disable_signals=True)
        # 深度图：中间一列 2 m，其余全 0
        img = Image()
        img.height, img.width, img.encoding, img.is_bigendian, img.step = H, W, "16UC1", 0, W * 2
        buf = array.array("H", [0]) * (W * H)
        col = W // 2
        # skip_pixel 可能是 2 -> 竖条做 2 像素宽，保证至少被采到一列
        for v in range(H):
            buf[v * W + col] = STRIPE_MM
            buf[v * W + col + 1] = STRIPE_MM
        img.data = buf.tobytes()
        dp = rospy.Publisher("/camera/depth/image_rect_raw", Image, queue_size=2)
        pose = PoseStamped()
        pose.header.frame_id = "world"
        pose.pose.position.z = 0.7
        # 2026-11-10（1280 升档复核发现）：原 w=1 使光轴指向世界 +z，2m 深度点落到
        # 地图顶(1.5m)之外 → 地图恒空、测试恒 FAIL。绕 y 转 90° 把光轴转到 +x。
        pose.pose.orientation.w = 0.7071067811865476
        pose.pose.orientation.y = 0.7071067811865476
        pp = rospy.Publisher("/planner/camera_pose", PoseStamped, queue_size=5)
        od = Odometry()
        od.header.frame_id = "world"
        od.pose.pose.position.z = 0.7
        od.pose.pose.orientation.w = 1.0
        op = rospy.Publisher("/vins_estimator/imu_propagate", Odometry, queue_size=10)
        state = {"pts": None}

        err = {"n": 0}

        def on_occ(m):
            try:
                state["pts"] = list(pc2.read_points(m, field_names=("x", "y", "z"),
                                                    skip_nans=True))
            except Exception as exc:
                if err["n"] < 1:
                    print("  !! read_points 失败: %r" % (exc,))
                    err["n"] += 1

        # occupancy 与 occupancy_inflate 都订（前者更"真"，后者确认节点在发）
        rospy.Subscriber("/drone_0_ego_planner_node/grid_map/occupancy_inflate", PointCloud2,
                         on_occ, queue_size=2)
        state2 = {"n": 0}

        state2 = {"n": 0}
        stop = {"v": False}

        def loop():
            while not stop["v"]:
                t = rospy.Time.now()
                img.header.stamp = t
                pose.header.stamp = t
                od.header.stamp = t
                dp.publish(img)
                pp.publish(pose)
                op.publish(od)
                rospy.sleep(0.066)

        threading.Thread(target=loop, daemon=True).start()
        # 等规划器节点 + 地图发布
        for _ in range(40):
            nodes = subprocess.run(["rosnode", "list"], env=e, capture_output=True, text=True).stdout
            if "/drone_0_ego_planner_node" in nodes and state2["n"] > 0:
                break
            rospy.sleep(1)
        rospy.sleep(6)
        print("occupancy_inflate 收到 %d 帧" % state2["n"])
        pts = state["pts"]
        if not pts:
            print("!! 没有收到 occupancy（occupancy_inflate %d 帧）" % state2["n"])
            return 2
        # 相机在世界原点、光轴沿 +x（cam0 光学系 z 向前，grid_map 用 pose 旋转投影）
        near = [p for p in pts if 1.5 <= p[0] <= 2.5]
        print("地图点数=%d，其中 x∈[1.5,2.5] 的点=%d" % (len(pts), len(near)))
        if near:
            xs = [p[0] for p in near]
            print("  这些点 x 中位=%.2f m（应≈2.00）" % sorted(xs)[len(xs) // 2])
        tol = 20
        ok = len(near) >= tol
        print(("\n==== T6 %s：竖条保留 %d 点（门 >=%d）====" %
               ("PASS" if ok else "FAIL", len(near), tol)))
        return 0 if ok else 2
    finally:
        stop_ok = True
        try:
            os.killpg(os.getpgid(planner.pid), signal.SIGKILL)
        except Exception:
            pass
        time.sleep(2)
        try:
            os.killpg(os.getpgid(core.pid), signal.SIGKILL)
        except Exception:
            core.kill()
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
