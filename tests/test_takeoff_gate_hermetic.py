#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4：起飞门自证 —— 健康系统必须让 `check_interfaces.py --task` **全绿**。

为什么单独做这条：起飞门要是误拦（false negative），飞机根本飞不起来。
本测试用**私有 master（11314）+ 真规划器 + 假传感器 + 假 px4ctrl 节点 + 真参数**，
把起飞那一刻的接线/参数/活边全部搭出来，然后跑一把 `--task`，断言 verdict=PASS。

不碰真机：私有 master、无 mavros、无 px4ctrl 真进程、无桨。
用法（先 source ROS）：
  source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
  python3 test_takeoff_gate_hermetic.py
退出码 0=PASS 2=FAIL
"""
import array
import json
import os
import signal
import subprocess
import sys
import threading
import time

PORT = 11314
URI = "http://localhost:%d" % PORT
FV = os.path.expanduser("~/sitl_realmachine/flight_v1")
LAUNCH = os.path.join(FV, "run_planner_realmachine_map_v1.launch")
W, H = 1280, 720


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
    # px4ctrl 的参数（真机上由 roslaunch px4ctrl 从 yaml 灌进来；这里直接灌同一个值）
    subprocess.run(["rosparam", "set", "/px4ctrl/auto_takeoff_land/takeoff_height", "0.7"], env=e)
    subprocess.run(["rosparam", "set", "/px4ctrl/low_voltage", "13.2"], env=e)

    planner = subprocess.Popen(["roslaunch", "--wait", LAUNCH], env=e,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               preexec_fn=os.setsid)
    fake_px4 = None
    try:
        import rospy
        from sensor_msgs.msg import Image
        from geometry_msgs.msg import PoseStamped
        from nav_msgs.msg import Odometry
        # 注意：位姿发布者**必须**叫 /planner_camera_pose_relay（检查器会核这个名字）
        rospy.init_node("planner_camera_pose_relay", anonymous=False, disable_signals=True)
        dp = rospy.Publisher("/camera/depth/image_rect_raw", Image, queue_size=2)
        pp = rospy.Publisher("/planner/camera_pose", PoseStamped, queue_size=5)
        op = rospy.Publisher("/vins_estimator/imu_propagate", Odometry, queue_size=10)
        img = Image()
        img.height, img.width, img.encoding, img.is_bigendian, img.step = H, W, "16UC1", 0, W * 2
        img.data = (array.array("H", [3000]) * (W * H)).tobytes()
        pose = PoseStamped()
        pose.pose.position.z = 0.7
        pose.pose.orientation.w = 1.0
        pose.header.frame_id = "world"
        od = Odometry()
        od.pose.pose.position.z = 0.7
        od.pose.pose.orientation.w = 1.0
        stop = {"v": False}

        def loop():
            while not stop["v"]:
                img.header.stamp = rospy.Time.now()
                dp.publish(img)
                pose.header.stamp = rospy.Time.now()
                pp.publish(pose)
                od.header.stamp = rospy.Time.now()
                op.publish(od)
                rospy.sleep(0.066)

        threading.Thread(target=loop, daemon=True).start()

        # 假 px4ctrl：只负责"订阅存在"（检查器核 /px4ctrl 的接线）
        fake_px4 = subprocess.Popen(
            [sys.executable, "-c",
             "import rospy,sys;from sensor_msgs.msg import Imu;from nav_msgs.msg import Odometry;"
             "rospy.init_node('px4ctrl');"
             "[rospy.Subscriber(t,Imu,lambda m:None) for t in ('/mavros/imu/data','/mavros/imu/data_raw')];"
             "[rospy.Subscriber(t,Odometry,lambda m:None) for t in "
             "('/vins_estimator/imu_propagate','/position_cmd')];"
             "rospy.spin()"],
            env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 等规划器 + traj_server + 假 px4ctrl 都在
        t0 = time.time()
        while time.time() - t0 < 60:
            nodes = subprocess.run(["rosnode", "list"], env=e, capture_output=True, text=True).stdout
            if all(n in nodes for n in ("/drone_0_ego_planner_node", "/drone_0_traj_server", "/px4ctrl")):
                break
            time.sleep(1)
        time.sleep(6)  # 让活边采样有数据（hz 窗口 3 s + 抖动余量）

        out = subprocess.run([sys.executable, os.path.join(FV, "check_interfaces.py"), "--task"],
                             env=e, capture_output=True, text=True, timeout=90)
        try:
            data = json.loads(out.stdout)
        except Exception:
            print("!! 输出不可解析：\n%s\n%s" % (out.stdout[-800:], out.stderr[-800:]))
            return 2
        bad = [c for c in data["checks"] if not c["ok"]]
        for c in data["checks"]:
            print(("  PASS  " if c["ok"] else "  FAIL  ") + c["name"]
                  + ("" if c["ok"] else "  [%s]" % (c.get("actual"),)))
        print("\n==== T4 起飞门自证：%d/%d PASS，verdict=%s ===="
              % (len(data["checks"]) - len(bad), len(data["checks"]), data["verdict"]))
        return 0 if data["verdict"] == "PASS" else 2
    finally:
        try:
            os.killpg(os.getpgid(planner.pid), signal.SIGKILL)
        except Exception:
            pass
        if fake_px4:
            fake_px4.kill()
        time.sleep(2)
        try:
            os.killpg(os.getpgid(core.pid), signal.SIGKILL)
        except Exception:
            core.kill()


if __name__ == "__main__":
    sys.exit(main())
