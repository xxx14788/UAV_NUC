#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地面复现：为什么规划器说"the drone is in obstacle"（症状2/3 的疑似真因）。

只起 mavros+相机+VINS+v2m+规划器+relay（**不起 px4ctrl**，螺旋桨不可能转），
然后量化四件事：
  1) 机体位置 / 相机位置（VINS 系）
  2) 膨胀地图里"离机体 0.6 m 内"有多少点、最近多少米
  3) 深度图中心区的分位数（看相机是不是看到了自己/很近的东西）
  4) 发一个 0.8 m 目标后：规划器是否报 "in obstacle"、/position_cmd 是否出流
用法：bash -c 'source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash; python3 probe_map_body.py'
"""
import math
import os
import subprocess
import sys
import time

import numpy as np

BODY = "/vins_estimator/imu_propagate"
CAM = "/planner/camera_pose"
INFLATE = "/drone_0_ego_planner_node/grid_map/occupancy_inflate"
DEPTH = "/camera/depth/image_rect_raw"
PLOG = os.path.expanduser("~/sitl_realmachine/probe_planner.log")


def sh(cmd, wait=True, log=None):
    if log:
        return subprocess.Popen(["bash", "-c", cmd], stdout=log, stderr=subprocess.STDOUT,
                                preexec_fn=os.setsid)
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)


def main():
    import rospy
    from sensor_msgs.msg import Image, PointCloud2
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Odometry
    import sensor_msgs.point_cloud2 as pc2

    procs = []
    logf = open(PLOG, "w")
    try:
        print("== 起 mavros", flush=True)
        procs.append(sh("roslaunch mavros px4.launch fcu_url:=/dev/pixhawk:921600", log=logf))
        time.sleep(8)
        print("== 起相机", flush=True)
        procs.append(sh("roslaunch realsense2_camera rs_camera.launch "
                        "infra_width:=640 infra_height:=480 infra_fps:=30 "
                        "depth_width:=640 depth_height:=480 depth_fps:=30 "
                        "enable_infra1:=true enable_infra2:=true enable_depth:=true "
                        "align_depth:=true", log=logf))
        sh("timeout 40 bash -c 'until rostopic list 2>/dev/null | grep -q %s; do sleep 1; done'" % DEPTH)
        print("== 起 VINS", flush=True)
        procs.append(sh("rosrun vins vins_node ~/sitl_realmachine/03_realmachine_config/"
                        "vins_stereo_realmachine_v0.yaml", log=logf))
        sh("timeout 120 bash -c 'until rostopic hz -w 5 %s 2>/dev/null | grep -q average; do sleep 2; done'" % BODY)
        print("== 起 v2m + 规划器 + relay", flush=True)
        procs.append(sh("rosrun vins_to_mavros vins_to_mavros_node", log=logf))
        procs.append(sh("roslaunch %s" % os.path.expanduser(
            "~/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch"), log=logf))
        time.sleep(3)
        procs.append(sh("python3 %s" % os.path.expanduser(
            "~/sitl_realmachine/flight_v1/camera_pose_relay.py"), log=logf))
        procs.append(sh("python3 %s" % os.path.expanduser(
            "~/sitl_realmachine/flight_v1/planned_path_pub.py"), log=logf))
        sh("timeout 60 bash -c 'until rostopic hz -w 3 %s 2>/dev/null | grep -q average; do sleep 2; done'" % CAM)
        time.sleep(25)  # 让地图积累几十帧

        rospy.init_node("probe_map_body", anonymous=True, disable_signals=True)
        state = {"body": None, "cam": None, "pts": None, "depth": None}

        def on_body(m):
            p = m.pose.pose.position
            state["body"] = (p.x, p.y, p.z)

        def on_cam(m):
            p = m.pose.position
            state["cam"] = (p.x, p.y, p.z)

        def on_occ(m):
            try:
                pts = list(pc2.read_points(m, field_names=("x", "y", "z"), skip_nans=True))
                state["pts"] = np.array(pts) if pts else np.zeros((0, 3))
            except Exception:
                pass

        def on_depth(m):
            try:
                d = np.frombuffer(m.data, dtype=np.uint16).reshape(m.height, m.width // 1)
                state["depth"] = d
            except Exception:
                pass

        rospy.Subscriber(BODY, Odometry, on_body, queue_size=5)
        rospy.Subscriber(CAM, PoseStamped, on_cam, queue_size=5)
        rospy.Subscriber(INFLATE, PointCloud2, on_occ, queue_size=2)
        rospy.Subscriber(DEPTH, Image, on_depth, queue_size=2)
        rospy.sleep(6)

        print("\n===== 1) 位置")
        print("  机体(VINS imu_propagate) =", state["body"])
        print("  相机(/planner/camera_pose) =", state["cam"])

        print("\n===== 2) 膨胀地图 vs 机体")
        pts = state["pts"]
        if pts is None or len(pts) == 0:
            print("  !! 没有收到 occupancy_inflate（地图空？点数 0）")
        else:
            b = np.array(state["body"]) if state["body"] else np.zeros(3)
            d = np.linalg.norm(pts - b, axis=1)
            print("  点数=%d  min|pt-body|=%.3f m  <0.6m 的点=%d  <1.0m 的点=%d"
                  % (len(pts), d.min(), int((d < 0.6).sum()), int((d < 1.0).sum())))
            near = pts[d < 0.6]
            if len(near):
                print("  最近的 5 个点:", np.round(near[np.argsort(d[d < 0.6])[:5]], 3).tolist())
            print("  地图整体范围 x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]"
                  % (pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max(),
                     pts[:, 2].min(), pts[:, 2].max()))

        print("\n===== 3) 深度图（中心区 1/3）")
        dm = state["depth"]
        if dm is None:
            print("  !! 无深度帧")
        else:
            h, w = dm.shape
            c = dm[h // 3:2 * h // 3, w // 3:2 * w // 3]
            valid = c[c > 0]
            print("  中心区: n=%d 有效=%d  有效中位=%.0f mm  p05=%.0f  min>0=%.0f"
                  % (c.size, valid.size, np.median(valid) if valid.size else -1,
                     np.percentile(valid, 5) if valid.size else -1,
                     valid.min() if valid.size else -1))
            print("  全图: 有效占比 %.1f%%  中位=%.0f mm"
                  % (100.0 * (dm > 0).sum() / dm.size, np.median(dm[dm > 0]) if (dm > 0).any() else -1))

        print("\n===== 4) 发目标 0.8 m，看规划器反应")
        b = np.array(state["body"]) if state["body"] else np.zeros(3)
        goal = PoseStamped()
        goal.header.frame_id = "world"
        goal.header.stamp = rospy.Time.now()
        goal.pose.position.x = float(b[0] + 0.8)
        goal.pose.position.y = float(b[1])
        goal.pose.orientation.w = 1.0
        pub = rospy.Publisher("/flight_v1/goal_gate", PoseStamped, queue_size=2)
        rospy.sleep(1.0)
        for _ in range(3):
            goal.header.stamp = rospy.Time.now()
            pub.publish(goal)
            rospy.sleep(0.5)
        plan = {"n": 0, "end": None, "start": None}
        from nav_msgs.msg import Path as RosPath

        def on_plan(m):
            if not m.poses:
                return
            plan["n"] += 1
            plan["start"] = (m.poses[0].pose.position.x, m.poses[0].pose.position.y)
            plan["end"] = (m.poses[-1].pose.position.x, m.poses[-1].pose.position.y)

        rospy.Subscriber("/flight_v1/planned_path", RosPath, on_plan, queue_size=2)
        cmd = {"v": -1.0, "n": 0}

        def on_cmd(m):
            cmd["n"] += 1
            cmd["v"] = max(cmd["v"], math.hypot(m.velocity.x, m.velocity.y))
            cmd["last"] = (m.position.x, m.position.y)

        from quadrotor_msgs.msg import PositionCommand
        rospy.Subscriber("/position_cmd", PositionCommand, on_cmd, queue_size=20)
        rospy.sleep(8)
        txt = open(PLOG, errors="ignore").read()
        print("  'the drone is in obstacle' 出现 %d 次" % txt.count("the drone is in obstacle"))
        print("  'terminal point ... in obstacle' 出现 %d 次" % txt.count("terminal point"))
        print("  'Triggered!' %d 次" % txt.count("Triggered!"))
        print("  /position_cmd 收到 %d 条, 水平|v|max=%.3f" % (cmd["n"], cmd["v"]))
        g = (goal.pose.position.x, goal.pose.position.y)
        if plan["n"] and plan["end"]:
            print("  /flight_v1/planned_path: %d 条  起点=(%.2f,%.2f) 终点=(%.2f,%.2f)  终点到目标=%.2f m"
                  % (plan["n"], plan["start"][0], plan["start"][1],
                     plan["end"][0], plan["end"][1],
                     math.hypot(plan["end"][0] - g[0], plan["end"][1] - g[1])))
        else:
            print("  !! /flight_v1/planned_path 没有数据（轨迹回传没工作）")
        if "last" in cmd:
            print("  指令末位=(%.2f,%.2f)  到目标=%.2f m  (起=%.2f,%.2f 目标=%.2f,%.2f)"
                  % (cmd["last"][0], cmd["last"][1],
                     math.hypot(cmd["last"][0] - g[0], cmd["last"][1] - g[1]),
                     b[0], b[1], g[0], g[1]))
    finally:
        print("\n== 清理", flush=True)
        logf.close()
        for p in reversed(procs):
            try:
                os.killpg(os.getpgid(p.pid), 15)
            except Exception:
                pass
        time.sleep(4)
        for p in reversed(procs):
            try:
                os.killpg(os.getpgid(p.pid), 9)
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
