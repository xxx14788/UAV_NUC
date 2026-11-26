#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R0 室内自动任务：起飞 -> 飞到 (6格,6格) -> 悬停 5 s -> 降落。

坐标约定（与场景设计一致）：
  场地原点 = 右下角；+x 从右向左；+y 从下向上
  每格 0.55 m；起飞点 (1.5,1.5) 格 = (0.825,0.825) m
  终点 (6,6) 格 = (3.300,3.300) m

VINS 原点在起飞点；假设 VINS 初始化时机头指向场地 +x，因此
  目标相对 VINS 原点 = (2.475,2.475) m

这个脚本负责：
  1. 启动 ~/realflight_mission.sh auto（复用已起好的栈，自动开录）；
  2. 等待飞机起飞并稳定；
  3. 通过 /move_base_simple/goal 交给 mission 校验/转发；
  4. 到点后等待 5 s，调用 ~/realflight_mission.sh land 直接降落。

注意：6 格目标相对起飞点的直线距离是 3.50018 m，略大于 mission 的 3.5 m
单目标半径。脚本会先发一个 3.20 m 的近点（距终点约 30 cm），再发精确终点；
最终仍停在 (6格,6格)，只是避免 mission 的 3.5 m 输入门把任务卡死。
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
GOAL_CELL = 6.0
TARGET_Z = 0.70
HOVER_AFTER_ARRIVAL = 5.0
ARRIVE_RADIUS = 0.20
ARRIVE_SPEED = 0.15
ARRIVE_HOLD = 1.0
MISSION_WRAPPER = os.path.expanduser("~/realflight_mission.sh")
STATE_DIR = os.path.expanduser("~/sitl_realmachine/flight_v1/runtime")
STOP_FILE = os.path.join(STATE_DIR, "stopping")
LANDING_FILE = os.path.join(STATE_DIR, "landing.requested")


def log(text):
    print("[R0] " + text, flush=True)


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

    def land(self):
        if self.land_started:
            return
        self.land_started = True
        log("启动降落：bash %s land" % MISSION_WRAPPER)
        rc = subprocess.run(
            ["bash", MISSION_WRAPPER, "land"],
            env=os.environ.copy(),
            timeout=180,
        ).returncode
        if rc != 0:
            raise RuntimeError("land 入口退出码 %d" % rc)
        # Wait for disarm/on-ground; land itself normally waits, this is final check.
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline and not rospy.is_shutdown():
            if (self.state is not None and self.state.connected
                    and not self.state.armed and self.ext is not None
                    and self.ext.landed_state == 1):
                log("已确认地面/未解锁")
                return
            rospy.sleep(0.2)
        log("警告：land 返回后 30 s 内未确认 disarmed/ON_GROUND")

    def run(self):
        wait_s = 120.0
        target = ((GOAL_CELL - START_CELL) * CELL,
                  (GOAL_CELL - START_CELL) * CELL)
        log("起飞点格坐标=(%.1f,%.1f) 场地=(%.3f,%.3f) m" %
            (START_CELL, START_CELL, START_CELL * CELL, START_CELL * CELL))
        log("终点格坐标=(%.1f,%.1f) 场地=(%.3f,%.3f) m" %
            (GOAL_CELL, GOAL_CELL, GOAL_CELL * CELL, GOAL_CELL * CELL))
        log("终点相对 VINS 原点=(%.3f,%.3f) m；直线距离=%.3f m" %
            (target[0], target[1], math.hypot(*target)))

        self.wait_stack()
        self.start_mission()
        self.wait_takeoff()
        px, py, _ = self._xy()
        d = math.hypot(target[0] - px, target[1] - py)
        log("起飞后当前位置=(%.3f,%.3f) m；距终点 %.3f m" % (px, py, d))

        stage = None
        # mission 的单目标半径是 3.5 m。6 格对角线为 3.50018 m；先发一个
        # 3.20 m 的近点，再发精确终点。这样终点前还有约 0.30 m 的实际运动，
        # 最终到点判据不会被“近点已经在终点 0.25 m 内”直接满足。
        if d > 3.45:
            scale = 3.20 / d
            stage = (px + (target[0] - px) * scale,
                     py + (target[1] - py) * scale)
            log("终点超出 mission 3.5 m 输入余量，先发 3.20 m 近点 (%.3f,%.3f)" % stage)

        try:
            if stage is not None:
                r = self.send_goal(stage[0], stage[1], "近点")
                if r != "ACCEPTED":
                    raise RuntimeError("近点未被 mission 接受：%s" % r)
                self.wait_arrival(stage[0], stage[1], "近点", timeout=wait_s,
                                  radius=0.30, speed=0.20)

            r = self.send_goal(target[0], target[1], "终点")
            if r != "ACCEPTED":
                raise RuntimeError("终点未被 mission 接受：%s" % r)
            self.wait_arrival(target[0], target[1], "终点", timeout=wait_s)
            self.hover(HOVER_AFTER_ARRIVAL)
            self.land()
        except Exception:
            # 如果已经起飞，尽量走正式 land 路径，不把飞机留在空中。
            if self.state is not None and self.state.armed:
                try:
                    self.land()
                except Exception as exc:
                    log("异常收口 land 失败：%r" % (exc,))
            raise

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
        target = ((GOAL_CELL - START_CELL) * CELL,
                  (GOAL_CELL - START_CELL) * CELL)
        print("start_cell=(%.2f,%.2f) -> field=(%.3f,%.3f) m" %
              (START_CELL, START_CELL, START_CELL * CELL, START_CELL * CELL))
        print("goal_cell=(%.2f,%.2f) -> field=(%.3f,%.3f) m" %
              (GOAL_CELL, GOAL_CELL, GOAL_CELL * CELL, GOAL_CELL * CELL))
        print("goal_vins=(%.3f,%.3f) m distance=%.6f m" %
              (target[0], target[1], math.hypot(*target)))
        return 0
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
