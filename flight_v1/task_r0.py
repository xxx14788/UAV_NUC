#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R0 室内自动任务：起飞 -> 飞到距起点 3.49 m 的单目标 -> 悬停 5 s -> 降落。

坐标约定（与场景设计一致）：
  场地原点 = 右下角；+x 从右向左；+y = 从下向上
  每格 0.55 m；起飞点 (1.5,1.5) 格 = (0.825,0.825) m
  方向仍取 S→(6,6) 的对角线，但终点只取到 3.49 m

VINS 原点在起飞点；假设 VINS 初始化时机头指向场地 +x，因此
  目标相对 VINS 原点 = (2.4678,2.4678) m
  场地终点 = (3.2928,3.2928) m

这个脚本负责：
  1. 启动 ~/realflight_mission.sh auto（复用已起好的栈，自动开录）；
  2. 等待飞机起飞并稳定；
  3. 只发一个目标（3.49 m < mission 3.5 m 门限），
     通过 /move_base_simple/goal 交给 mission 校验/转发；
  4. 目标是否在膨胀层内、导航中是否被障碍覆盖，由 mission 自己判断和处理；
  5. 到点后等待 5 s，通过 /flight_v1/land_request 请求现有 mission 降落。

降落必须通知现有 flight_v1_mission 节点；另起 `realflight_mission.sh land`
会创建同名节点，把正在导航的 mission 踢掉。
"""
import argparse
import math
import os
import subprocess
import sys
import threading
import time

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import ExtendedState, State
from nav_msgs.msg import Odometry
from std_msgs.msg import String

CELL = 0.55
START_CELL = 1.5
GOAL_CELL = 6.0          # 只用于确定 S→G 方向；实际距离由 GOAL_DISTANCE 截断
GOAL_DISTANCE = 3.49     # mission 单目标限制 3.5 m，留 1 cm 余量
TARGET_Z = 0.70
HOVER_AFTER_ARRIVAL = 5.0
ARRIVE_RADIUS = 0.20
ARRIVE_SPEED = 0.15
ARRIVE_HOLD = 1.0
MISSION_WRAPPER = os.path.expanduser("~/realflight_mission.sh")
STATE_DIR = os.path.expanduser("~/sitl_realmachine/flight_v1/runtime")
STOP_FILE = os.path.join(STATE_DIR, "stopping")
LANDING_FILE = os.path.join(STATE_DIR, "landing.requested")
LAND_REQUEST_TOPIC = "/flight_v1/land_request"
LAND_REQUEST_TIMEOUT = 150.0


def target_vins():
    """沿 S→(6,6) 方向，取距 VINS 原点 GOAL_DISTANCE 的单个目标。"""
    dx = (GOAL_CELL - START_CELL) * CELL
    dy = (GOAL_CELL - START_CELL) * CELL
    norm = math.hypot(dx, dy)
    if norm <= 0.0:
        raise ValueError("S→G 方向长度为 0")
    scale = GOAL_DISTANCE / norm
    return dx * scale, dy * scale


def log(text):
    print("[R0] " + text, flush=True)


def ros_master_ready(timeout=3.0):
    """快速判断 ROS master 是否在线，避免 rospy.init_node 长时间重试。"""
    try:
        result = subprocess.run(
            ["rostopic", "list"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception:
        return False


class R0Task:
    def __init__(self):
        rospy.init_node("task_r0", anonymous=True)
        self.state = None
        self.ext = None
        self.odom = None
        self.ack_text = None
        self.ack_event = None
        self.mission = None
        self.land_started = False

        rospy.Subscriber("/mavros/state", State, self._state_cb, queue_size=20)
        rospy.Subscriber("/mavros/extended_state", ExtendedState,
                         self._ext_cb, queue_size=20)
        rospy.Subscriber("/vins_estimator/imu_propagate", Odometry,
                         self._odom_cb, queue_size=50)
        rospy.Subscriber("/flight_v1/goal_ack", String,
                         self._ack_cb, queue_size=20)
        self.goal_pub = rospy.Publisher("/move_base_simple/goal", PoseStamped,
                                        queue_size=5)
        self.land_request_pub = rospy.Publisher(
            LAND_REQUEST_TOPIC, String, queue_size=3)

    def _state_cb(self, msg):
        self.state = msg

    def _ext_cb(self, msg):
        self.ext = msg

    def _odom_cb(self, msg):
        self.odom = msg

    def _ack_cb(self, msg):
        self.ack_text = msg.data
        if self.ack_event is not None and (
                msg.data.startswith("ACCEPTED") or msg.data.startswith("REJECTED")):
            self.ack_event.set()

    def _xy(self):
        p = self.odom.pose.pose.position
        return p.x, p.y, p.z

    def _speed_xy(self):
        v = self.odom.twist.twist.linear
        return math.hypot(v.x, v.y)

    def wait_stack(self, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not rospy.is_shutdown():
            if self.state is not None and self.odom is not None:
                return
            rospy.sleep(0.2)
        raise RuntimeError("等待 /mavros/state 与 /vins_estimator/imu_propagate 超时；先起栈")

    def start_mission(self):
        if not os.path.isfile(MISSION_WRAPPER):
            raise RuntimeError("找不到任务入口 %s" % MISSION_WRAPPER)
        if os.path.exists(STOP_FILE):
            raise RuntimeError("检测到 stopping；先清理遗留停栈标志")
        if os.path.exists(LANDING_FILE):
            raise RuntimeError("检测到 landing.requested；先确认飞机在地面并清理")
        log("启动任务入口: bash %s auto" % MISSION_WRAPPER)
        # Inherit stdout/stderr so mission preflight/takeoff output is visible.
        self.mission = subprocess.Popen(
            ["bash", MISSION_WRAPPER, "auto"],
            stdin=subprocess.DEVNULL,
            env=os.environ.copy(),
        )

    def check_mission_alive(self):
        if self.mission is not None and self.mission.poll() is not None:
            raise RuntimeError("任务入口已退出（rc=%s），先看 mission 日志"
                               % (self.mission.returncode,))

    def wait_takeoff(self, timeout=150.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not rospy.is_shutdown():
            self.check_mission_alive()
            if (self.state is not None and self.state.connected and self.state.armed
                    and self.odom is not None and self._xy()[2] > 0.55):
                log("已起飞（armed=True，z=%.2f m）" % self._xy()[2])
                # 再等 1 s，让 mission 进入 hover/收点状态。
                rospy.sleep(1.0)
                return
            rospy.sleep(0.1)
        raise RuntimeError("等待起飞超时；检查 RC/CH5、预检和 mission 输出")

    def _publish_goal(self, x, y):
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "world"
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = TARGET_Z
        msg.pose.orientation.w = 1.0
        self.goal_pub.publish(msg)

    def send_goal(self, x, y, label, max_try=8):
        """Publish until mission accepts/rejects. Returns accepted/reject text."""
        log("%s：发目标 (%.3f, %.3f) m" % (label, x, y))
        for _ in range(max_try):
            self.check_mission_alive()
            self.ack_text = None
            self.ack_event = threading.Event()
            self._publish_goal(x, y)
            if self.ack_event.wait(1.5):
                txt = self.ack_text or ""
                if txt.startswith("ACCEPTED"):
                    log("%s：mission 已接受" % label)
                    return "ACCEPTED"
                if txt.startswith("REJECTED"):
                    # mission 还在 takeoff/hover 阶段时会这样回复；继续等它进入
                    # await_goal，不要把“还没准备好”误判成任务失败。
                    if "当前阶段" in txt or "目标已锁定" in txt:
                        log("%s：mission 尚未进入收点阶段，重试" % label)
                        rospy.sleep(1.0)
                        continue
                    log("%s：mission 拒绝：%s" % (label, txt))
                    return txt
            rospy.sleep(0.5)
        return "NO_ACK"

    def wait_arrival(self, x, y, label, timeout=120.0,
                     radius=ARRIVE_RADIUS, speed=ARRIVE_SPEED):
        deadline = time.monotonic() + timeout
        stable_since = None
        log("%s：等待到点 (%.3f, %.3f) m" % (label, x, y))
        while time.monotonic() < deadline and not rospy.is_shutdown():
            self.check_mission_alive()
            if self.state is not None and (not self.state.connected
                                           or not self.state.armed):
                raise RuntimeError("%s：飞控连接/解锁状态异常" % label)
            if self.odom is None:
                rospy.sleep(0.1)
                continue
            px, py, _ = self._xy()
            d = math.hypot(px - x, py - y)
            v = self._speed_xy()
            if d <= radius and v <= speed:
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= ARRIVE_HOLD:
                    log("%s：到点（d=%.3f m, v=%.3f m/s）" % (label, d, v))
                    return
            else:
                stable_since = None
            rospy.sleep(0.1)
        raise RuntimeError("%s：%.0f s 内未到点" % (label, timeout))

    def hover(self, seconds):
        log("到点后悬停 %.1f s" % seconds)
        t0 = time.monotonic()
        while time.monotonic() - t0 < seconds and not rospy.is_shutdown():
            if self.state is not None and (not self.state.connected
                                           or not self.state.armed):
                raise RuntimeError("悬停期间飞控连接/解锁状态异常")
            rospy.sleep(0.1)

    def _grounded(self):
        return (self.state is not None and self.state.connected
                and not self.state.armed and self.ext is not None
                and self.ext.landed_state == 1)

    def _wait_grounded(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not rospy.is_shutdown():
            if self._grounded():
                log("已确认地面/未解锁")
                return True
            if self.mission is not None and self.mission.poll() is not None:
                return self._grounded()
            rospy.sleep(0.2)
        return False

    def _standalone_land(self):
        """现有 mission 已退出时，才允许用独立 land 入口。"""
        log("现有 mission 已退出，使用独立 land 入口")
        rc = subprocess.run(
            ["bash", MISSION_WRAPPER, "land"],
            env=os.environ.copy(),
            timeout=180,
        ).returncode
        if rc != 0:
            raise RuntimeError("独立 land 入口退出码 %d" % rc)
        if not self._wait_grounded(30.0):
            raise RuntimeError("独立 land 返回后未确认 disarmed/ON_GROUND")

    def land(self):
        if self.land_started:
            return
        self.land_started = True
        if self._grounded():
            log("飞控已是地面/未解锁，无需降落请求")
            return

        mission_alive = self.mission is not None and self.mission.poll() is None
        if mission_alive:
            # 关键：不能另起 realflight_mission.sh land。那会新建同名
            # flight_v1_mission 节点，把正在导航的节点踢掉，随后 FSM 缓存为空。
            # 改为通知现有 mission，由它自己的 navigation_monitor 调 land()。
            log("向现有 mission 发送降落请求：%s" % LAND_REQUEST_TOPIC)
            for _ in range(3):
                self.land_request_pub.publish(String(data="land"))
                rospy.sleep(0.2)
            if self._wait_grounded(LAND_REQUEST_TIMEOUT):
                return
            if self.mission is not None and self.mission.poll() is not None:
                log("mission 已退出但未确认落地，切换独立 land")
            else:
                raise RuntimeError(
                    "现有 mission 未在 %.0f s 内完成降落；保持 CH5 接管"
                    % LAND_REQUEST_TIMEOUT)
        else:
            log("mission 进程不在，走独立 land 入口")

        self._standalone_land()

    def run(self):
        wait_s = 120.0
        target = target_vins()
        start_field = (START_CELL * CELL, START_CELL * CELL)
        goal_field = (start_field[0] + target[0], start_field[1] + target[1])
        log("起飞点格坐标=(%.1f,%.1f) 场地=(%.3f,%.3f) m" %
            (START_CELL, START_CELL, start_field[0], start_field[1]))
        log("方向参考格坐标=(%.1f,%.1f)；单目标距离=%.3f m" %
            (GOAL_CELL, GOAL_CELL, GOAL_DISTANCE))
        log("终点相对 VINS 原点=(%.4f,%.4f) m；场地=(%.4f,%.4f) m" %
            (target[0], target[1], goal_field[0], goal_field[1]))

        self.wait_stack()
        self.start_mission()
        try:
            self.wait_takeoff()
            px, py, _ = self._xy()
            d = math.hypot(target[0] - px, target[1] - py)
            log("起飞后当前位置=(%.3f,%.3f) m；距终点 %.3f m" % (px, py, d))
            if d > 3.50:
                raise RuntimeError("起飞后距终点 %.3f m，已超过 mission 3.5 m 输入门"
                                   % d)

            # 单目标：3.49 m 已经小于 mission 的 3.5 m 门限，不再发近点。
            r = self.send_goal(target[0], target[1], "终点")
            if r != "ACCEPTED":
                raise RuntimeError("终点未被 mission 接受：%s" % r)
            self.wait_arrival(target[0], target[1], "终点", timeout=wait_s)
            self.hover(HOVER_AFTER_ARRIVAL)
            self.land()
        except Exception:
            # 如果已经起飞，走现有 mission 的降落请求，不把飞机留在空中。
            if self.state is not None and self.state.armed:
                try:
                    self.land()
                except Exception as exc:
                    log("异常收口 land 失败：%r" % (exc,))
            raise
        finally:
            if self.mission is not None:
                try:
                    rc = self.mission.wait(timeout=30.0)
                    log("任务入口已退出 rc=%s" % rc)
                except subprocess.TimeoutExpired:
                    log("警告：任务入口仍在运行，检查 record stop / mission 日志")


def main():
    ap = argparse.ArgumentParser(description="R0 室内自动任务")
    ap.add_argument("--check", action="store_true",
                    help="只打印坐标和距离，不启动 mission")
    args = ap.parse_args()
    if args.check:
        target = target_vins()
        start_field = (START_CELL * CELL, START_CELL * CELL)
        goal_field = (start_field[0] + target[0], start_field[1] + target[1])
        print("start_cell=(%.2f,%.2f) -> field=(%.3f,%.3f) m" %
              (START_CELL, START_CELL, start_field[0], start_field[1]))
        print("direction_cell=(%.2f,%.2f) distance=%.6f m" %
              (GOAL_CELL, GOAL_CELL, GOAL_DISTANCE))
        print("goal_vins=(%.4f,%.4f) m distance=%.6f m" %
              (target[0], target[1], math.hypot(*target)))
        print("goal_field=(%.4f,%.4f) m cell_equiv=(%.4f,%.4f)" %
              (goal_field[0], goal_field[1],
               goal_field[0] / CELL, goal_field[1] / CELL))
        return 0
    if not ros_master_ready():
        print("[R0][FAIL] ROS master 未运行；先起栈：bash ~/realflight_stack.sh",
              file=sys.stderr, flush=True)
        return 1
    task = R0Task()
    try:
        task.run()
    except Exception as exc:
        print("[R0][FAIL] %s" % (exc,), file=sys.stderr, flush=True)
        return 1
    print("[R0][DONE] 任务完成", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
