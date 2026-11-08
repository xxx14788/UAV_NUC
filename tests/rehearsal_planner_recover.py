#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2（方案 v2 P1+P2）：规划器 "odom/depth 超时" 自愈 —— 隔离栈、零硬件、零桨。

做什么
  1. 私有 ROS master（端口 11312，与实飞栈完全隔离，不碰任何真实话题）
  2. 起真实规划器 launch（地图版），喂**假**的 depth / camera_pose / imu_propagate
  3. 发一个 0.8 m 的目标 -> 断言 /position_cmd 真的动起来
  4. 让 camera_pose 停发 2.5 s -> 断言规划器报 "odom or depth lost"
     （这就是 20261107_223625 那轮的触发条件；改前此处会**永久** EMERGENCY_STOP）
  5. 恢复发流 -> 断言 3 s 内出现 "depth/odom recovered" + "fail-safe re-enabled"
     且 /position_cmd 重新出现运动  = P1/P2 生效
用法（必须先 source ROS）：
  source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
  python3 rehearsal_planner_recover.py
退出码：0=PASS，2=FAIL
"""
import array
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time

MASTER_PORT = 11312
URI = "http://localhost:%d" % MASTER_PORT
LAUNCH = os.path.expanduser("~/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch")
W, H = 640, 480
DEPTH_MM = 3000  # 3 m 处一面"墙"，够远不挡 0.8 m 的目标

results = []


def ok(name, cond, actual=""):
    results.append((name, bool(cond), actual))
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if actual == "" else "  [%s]" % actual),
          flush=True)
    return bool(cond)


class FakeSensors:
    """假 depth/pose/odom；可以随时"停发"pose（模拟 VINS 断流）。"""

    def __init__(self):
        import rospy
        from sensor_msgs.msg import Image
        from geometry_msgs.msg import PoseStamped
        from nav_msgs.msg import Odometry
        rospy.init_node("fake_sensors", anonymous=True, disable_signals=True)
        self.rospy = rospy
        self.pose_enabled = True
        self.depth = Image()
        self.depth.height, self.depth.width = H, W
        self.depth.encoding = "16UC1"
        self.depth.is_bigendian = 0
        self.depth.step = W * 2
        # rospy 的 uint8[] 字段要 bytes（array.array 会抛 SerializationError，
        # 被 _loop 的 except 吞掉 -> 假传感器"静默不发"，第一次排查栽在这）。
        self.depth.data = (array.array("H", [DEPTH_MM]) * (W * H)).tobytes()
        self.pose = PoseStamped()
        self.pose.header.frame_id = "world"
        self.pose.pose.position.z = 0.7
        self.pose.pose.orientation.w = 1.0
        self.odom = Odometry()
        self.odom.header.frame_id = "world"
        self.odom.pose.pose.position.z = 0.7
        self.odom.pose.pose.orientation.w = 1.0
        self.depth_pub = rospy.Publisher("/camera/depth/image_rect_raw", Image, queue_size=2)
        self.pose_pub = rospy.Publisher("/planner/camera_pose", PoseStamped, queue_size=5)
        self.odom_pub = rospy.Publisher("/vins_estimator/imu_propagate", Odometry, queue_size=10)
        self._stop = False
        for rate_hz, fn in ((15.0, self._depth), (15.0, self._pose), (60.0, self._odom)):
            threading.Thread(target=self._loop, args=(rate_hz, fn), daemon=True).start()

    def _loop(self, hz, fn):
        period = 1.0 / hz
        reported = False
        while not self._stop:
            try:
                fn()
            except Exception as exc:
                if not reported:   # 只报一次，但绝不静默（历史上就被静默坑过）
                    print("  !! 假传感器发布失败: %r" % (exc,), flush=True)
                    reported = True
            time.sleep(period)

    def _depth(self):
        self.depth.header.stamp = self.rospy.Time.now()
        self.depth_pub.publish(self.depth)

    def _pose(self):
        if not self.pose_enabled:      # ← 这里就是"停发"开关
            return
        self.pose.header.stamp = self.rospy.Time.now()
        self.pose_pub.publish(self.pose)

    def _odom(self):
        self.odom.header.stamp = self.rospy.Time.now()
        self.odom_pub.publish(self.odom)

    def stop(self):
        self._stop = True


def main():
    # 本进程内的 rospy 节点也必须用私有 master，否则会挂到实飞的 11311 上（第一次跑就栽在这）。
    os.environ["ROS_MASTER_URI"] = URI
    if not os.path.exists(LAUNCH):
        print("!! 找不到 %s" % LAUNCH)
        return 2
    e = dict(os.environ)
    e["ROS_MASTER_URI"] = URI
    if subprocess.run(["bash", "-c", "ss -ltn | grep -q :%d" % MASTER_PORT]).returncode == 0:
        print("!! 端口 %d 已被占用（上次残留？先 pkill '[r]oscore -p %d'）" % (MASTER_PORT, MASTER_PORT))
        return 2
    tmp = tempfile.mkdtemp(prefix="rehearsal_")
    core_log = open(os.path.join(tmp, "roscore.log"), "w")
    plan_log_path = os.path.join(tmp, "planner.log")
    plan_log = open(plan_log_path, "w")

    core = subprocess.Popen(["roscore", "-p", str(MASTER_PORT)], env=e,
                            stdout=core_log, stderr=subprocess.STDOUT,
                            preexec_fn=os.setsid)  # 独立进程组，否则 rosmaster 子进程杀不掉
    time.sleep(4)
    if core.poll() is not None:
        print("!! roscore 起不来（端口 %d 被占？）" % MASTER_PORT)
        return 2

    planner = subprocess.Popen(["roslaunch", "--wait", LAUNCH], env=e,
                               stdout=plan_log, stderr=subprocess.STDOUT,
                               preexec_fn=os.setsid)
    try:
        import rospy
        from geometry_msgs.msg import PoseStamped
        from quadrotor_msgs.msg import PositionCommand

        # 2026-11-08（症状4）：轨迹回传节点也要一起验
        FVdir = os.path.expanduser("~/sitl_realmachine/flight_v1")
        pathpub = subprocess.Popen([sys.executable,
                                    os.path.join(FVdir, "planned_path_pub.py")],
                                   env=e, stdout=open("/tmp/pathpub.log", "w"),
                                   stderr=subprocess.STDOUT)
        sensors = FakeSensors()
        cmd = {"v": 0.0, "p": None, "x": None}

        def on_cmd(msg):
            cmd["v"] = (msg.velocity.x ** 2 + msg.velocity.y ** 2) ** 0.5
            cmd["p"] = (msg.position.x, msg.position.y)
            cmd["x"] = time.time()

        rospy.Subscriber("/position_cmd", PositionCommand, on_cmd, queue_size=50)

        # 等规划器/轨迹服务器就绪
        t0 = time.time()
        while time.time() - t0 < 60:
            nodes = subprocess.run(["rosnode", "list"], env=e, capture_output=True, text=True).stdout
            if "/drone_0_ego_planner_node" in nodes and "/drone_0_traj_server" in nodes:
                break
            time.sleep(1)
        else:
            ok("规划器节点上线", False, "60 s 未见 ego_planner/traj_server")
            return 2   # 2026-11-08 二审 F6：原来是 return ok(...)=False -> exit 0 假绿

        # 注意：traj_server **只在收到 bspline 之后**才发 /position_cmd（今晚实测：
        # 整袋 107 s 里 /position_cmd 只存在于最后 29.6 s = 点目标之后）。
        # 所以这里不能等"先有流"，必须发目标后再断。
        ok("/position_cmd 发目标前无流（符合设计）", not (cmd["x"] and time.time() - cmd["x"] < 1.0),
           "last=%.1f" % (cmd["x"] or 0.0))

        # ---- 发目标（0.8 m）----
        goal = PoseStamped()
        goal.header.frame_id = "world"
        goal.header.stamp = rospy.Time.now()
        goal.pose.position.x = 2.0   # 2 m 目标 -> 轨迹 ~4 s，保证断流发生在**执行中**
        goal.pose.position.y = 0.0
        goal.pose.position.z = 0.0
        goal.pose.orientation.w = 1.0
        pub = rospy.Publisher("/flight_v1/goal_gate", PoseStamped, queue_size=2)
        rospy.sleep(1.0)
        # 连发 3 次：ros 的一发式 publisher 可能在 TCP 连接建立前就发出去而丢包
        # （第一次跑就栽在这：日志里连 "Triggered!" 都没有）。
        for _ in range(3):
            goal.header.stamp = rospy.Time.now()
            pub.publish(goal)
            rospy.sleep(0.5)
        triggered = False
        t0 = time.time()
        while time.time() - t0 < 10:
            plan_log.flush()
            if "Triggered!" in open(plan_log_path, errors="ignore").read():
                triggered = True
                break
            time.sleep(0.3)
        ok("目标被规划器接收(日志出现 Triggered!)", triggered)

        vmax = 0.0
        t0 = time.time()
        while time.time() - t0 < 20:
            vmax = max(vmax, cmd["v"])
            if vmax > 0.05:
                break
            rospy.sleep(0.1)
        ok("目标被消费:/position_cmd 有运动(P1 前置)", vmax > 0.05, "vmax=%.3f" % vmax)
        # 2026-11-08：max_vel 0.15->0.5 之后短轨迹几秒就跑完；
        # 断流必须发生在**还在执行**的时候（否则 FSM 的 checkCollisionCallback 因
        # start_time_ 失效而早退，根本不会进 EMERGENCY_STOP —— 这是测试时序问题，不是代码问题）。
        time.sleep(0.8)

        # ---- 断 pose 2.5 s（模拟 20261107 的 1.885 s 断流）----
        print("  ...停发 camera_pose 2.5 s...", flush=True)
        sensors.pose_enabled = False
        time.sleep(2.5)
        lost = False
        t0 = time.time()
        while time.time() - t0 < 6:
            plan_log.flush()
            txt = open(plan_log_path, errors="ignore").read()
            if "odom or depth lost" in txt:
                lost = True
                break
            time.sleep(0.3)
        ok("断流被识别(odom or depth lost)", lost, "日志见 %s" % plan_log_path)

        # ---- 恢复 ----
        print("  ...恢复 camera_pose...", flush=True)
        sensors.pose_enabled = True
        recovered = failsafe = False
        t0 = time.time()
        while time.time() - t0 < 8:
            plan_log.flush()
            txt = open(plan_log_path, errors="ignore").read()
            recovered = recovered or ("depth/odom recovered" in txt)
            failsafe = failsafe or ("fail-safe re-enabled" in txt)
            if recovered and failsafe:
                break
            time.sleep(0.3)
        ok("P1 生效:超时标志被清零(depth/odom recovered)", recovered)
        ok("P2 生效:fail-safe 重新使能(fail-safe re-enabled)", failsafe)

        # 恢复后应该重新出运动（重规划）
        vmax2 = 0.0
        t0 = time.time()
        while time.time() - t0 < 15:
            vmax2 = max(vmax2, cmd["v"])
            if vmax2 > 0.05:
                break
            rospy.sleep(0.1)
        ok("自愈:/position_cmd 重新有运动", vmax2 > 0.05, "vmax=%.3f" % vmax2)

        # 反证：关掉 pose 后**不恢复**，仍必须保持急停（安全行为不退化）
        # 2026-11-08 二审 F6：只看"这次断流之后"新增的日志，别被第一次的 Depth Lost 蒙过去
        offset = os.path.getsize(plan_log_path)
        sensors.pose_enabled = False
        time.sleep(2.5)
        plan_log.flush()
        with open(plan_log_path, errors="ignore") as fh:
            fh.seek(offset)
            fresh = fh.read()
        ok("持续丢深度仍保持急停(只看本次断流后的新日志)",
           "Depth Lost! EMERGENCY_STOP" in fresh or "odom or depth lost" in fresh,
           "增量 %d 字节" % len(fresh))
        sensors.pose_enabled = True

        # ---- T3b：接缝检查器"活边"层（同一个私有 master，真规划器 + 假传感器）----
        # 只断言新增的三条边（深度活性/位姿活性/时戳对齐）；其余老检查需要真 px4ctrl 节点，
        # 这里不要求（它们的语义在 T1 静态层已覆盖）。
        FV = os.path.expanduser("~/sitl_realmachine/flight_v1")
        chk = subprocess.run([sys.executable, os.path.join(FV, "check_interfaces.py"), "--live",
                              "--contract", os.path.join(FV, "contract", "flight_contract.yaml")],
                             env=e, capture_output=True, text=True)
        try:
            data = json.loads(chk.stdout)
        except Exception:
            data = {"checks": []}
        edge = [c for c in data.get("checks", []) if c["name"].startswith(("边活性", "边对齐"))]
        # ---- T5（症状4）：预期轨迹回传 + RViz 可绘 ----
        from nav_msgs.msg import Path as RosPath
        got = {"n": 0, "start": None, "end": None}

        def on_plan(m):
            if m.poses:
                got["n"] += 1
                got["start"] = (m.poses[0].pose.position.x, m.poses[0].pose.position.y)
                got["end"] = (m.poses[-1].pose.position.x, m.poses[-1].pose.position.y)

        rospy.Subscriber("/flight_v1/planned_path", RosPath, on_plan, queue_size=2)
        rospy.sleep(2.0)
        gx, gy = goal.pose.position.x, goal.pose.position.y
        ok("T5 轨迹回传:/flight_v1/planned_path 有数据", got["n"] > 0, "n=%d" % got["n"])
        if got["start"] and got["end"]:
            # 说明：EGO 重规划时起点=**上一版轨迹上当前时刻的点**（前馈），不是 odom 位置；
            # 所以这里只要求"起点在机体 1.5 m 内、且比终点更远离目标"。
            ok("T5 路径起点合理(重规划起点=轨迹当前点)",
               math.hypot(got["start"][0], got["start"][1]) < 1.5
               and math.hypot(got["start"][0] - gx, got["start"][1] - gy)
               > math.hypot(got["end"][0] - gx, got["end"][1] - gy),
               "start=(%.2f,%.2f)" % got["start"])
            ok("T5 路径终点≈目标点(<=0.5m)",
               math.hypot(got["end"][0] - gx, got["end"][1] - gy) <= 0.5,
               "end=(%.2f,%.2f) 目标=(%.2f,%.2f)" % (got["end"][0], got["end"][1], gx, gy))
        pathpub.kill()

        ok("T3b 活边检查:深度活性/位姿活性/时戳对齐 三条全 PASS",
           len(edge) >= 3 and all(c["ok"] for c in edge),
           "; ".join("%s=%s" % (c["name"].replace("边活性:", "").replace("边对齐:", "")[:18],
                                "ok" if c["ok"] else c["actual"]) for c in edge))

        # ---- F6：live 层负测试（证明 --live 真有牙；静态层覆盖不到）----
        # 停 pose 4 s 后再跑 --live，位姿活性检查必须 FAIL（3 s 窗内 ~0 Hz < 8 Hz）
        sensors.pose_enabled = False
        time.sleep(4.0)
        chk2 = subprocess.run([sys.executable, os.path.join(FV, "check_interfaces.py"), "--live",
                               "--contract", os.path.join(FV, "contract", "flight_contract.yaml")],
                              env=e, capture_output=True, text=True)
        try:
            d2 = json.loads(chk2.stdout)
        except Exception:
            d2 = {"checks": []}
        pose_bad = [c for c in d2.get("checks", [])
                    if c["name"].startswith("边活性:相机位姿") and not c["ok"]]
        ok("F6 负测试:停发位姿后 --live 的位姿活性检查必须 FAIL",
           len(pose_bad) == 1, "命中 %d 条" % len(pose_bad))
        sensors.pose_enabled = True

        sensors.stop()
    finally:
        try:
            os.killpg(os.getpgid(planner.pid), signal.SIGINT)
        except Exception:
            pass
        time.sleep(3)
        try:
            os.killpg(os.getpgid(planner.pid), signal.SIGKILL)
        except Exception:
            pass
        try:
            core.send_signal(signal.SIGINT)
        except Exception:
            pass
        time.sleep(2)
        plan_log.close()
        core_log.close()

    bad = [r for r in results if not r[1]]
    print("\n==== T2 结果：%d/%d PASS ====" % (len(results) - len(bad), len(results)))
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
