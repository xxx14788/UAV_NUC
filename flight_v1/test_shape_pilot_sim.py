#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ShapePilot 离线闭环仿真（无 ROS）：验证导引/换点/终点/退出逻辑。

假机身按“朝当前目标 0.03 m/tick”运动；假 mission 在飞机到达最终点后
把 phase 置为 await_goal（等价于 5 s 到位判定）。要求：三种形状都
无异常、pilot.done=True、最终目标≈起飞点、发点数合理。
"""
import importlib.util
import math
import threading
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "fsm", os.path.join(HERE, "flight_shape_mission.py"))
fsm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fsm)


class _V:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class _Q:
    def __init__(self):
        self.w = 1.0


class _Pose:
    def __init__(self):
        self.position = _V()
        self.orientation = _Q()


class _Header:
    def __init__(self):
        self.stamp = 0.0
        self.frame_id = ""


class _PoseStamped:
    def __init__(self):
        self.header = _Header()
        self.pose = _Pose()


class _Odom:
    def __init__(self, p, v):
        self.pose = types.SimpleNamespace(pose=types.SimpleNamespace(position=p))
        self.twist = types.SimpleNamespace(twist=types.SimpleNamespace(linear=v))


class _Ros:
    class Time:
        @staticmethod
        def now():
            return 0.0
    @staticmethod
    def sleep(dt):
        return None
    @staticmethod
    def is_shutdown():
        return False


class FakeFlight:
    def __init__(self):
        self.PoseStamped = _PoseStamped
        self.rospy = _Ros
        self.pos = _V(0.0, 0.0, 0.7)
        self.vel = _V()
        self.target = (0.0, 0.0)
        self.sent = 0
        self.phase = "navigation"
        self.goal_used = True
        self.endpoint_ref = None
        self.adjusted_count = 0
        self.adjusted_max = 0.0
        self.unreachable_count = 0
        self.shape_abort_reason = None
        self.shape_stats = {}
        self.logs = []
        self._state_lock = threading.RLock()

    def _log(self, stage, msg):
        self.logs.append("[%s] %s" % (stage, msg))

    def _odom(self):
        # 先按当前目标推进，再返回状态（等价于控制器跟随）
        dx, dy = self.target[0] - self.pos.x, self.target[1] - self.pos.y
        d = math.hypot(dx, dy)
        step = 0.03
        if d > 1e-9:
            f = min(1.0, step / d)
            self.pos.x += dx * f
            self.pos.y += dy * f
            self.vel.x = dx / d * 0.3
            self.vel.y = dy / d * 0.3
        else:
            self.vel.x = self.vel.y = 0.0
        # 到最终点 -> 模拟 mission 5 s 到位后的 await_goal
        if (math.hypot(self.pos.x, self.pos.y) < 0.03
                and math.hypot(self.target[0], self.target[1]) < 0.03):
            self.phase = "await_goal"
            self.goal_used = False
        return _Odom(self.pos, self.vel)

    def _fsm(self):
        return "CMD_CTRL"

    def _apply_goal(self, msg, quiet=False):
        self.target = (msg.pose.position.x, msg.pose.position.y)
        self.endpoint_ref = self.target
        self.sent += 1
        self.phase = "navigation"
        self.goal_used = True
        return True, ""


def make_args(shape):
    a = types.SimpleNamespace()
    a.shape = shape
    a.speed = 0.30
    a.lookahead = 0.60
    a.min_step = 0.10
    a.laps = 1
    a.rate = 10.0
    a.circle_diameter = 2.2
    a.eight_length = 4.0
    a.eight_width = 2.2
    a.rotate_deg = 0.0
    a.obstacle_xy = (1.0, 0.0)
    a.obstacle_size = 0.5
    a.max_forward = 4.3
    a.max_lateral = 1.6
    a.min_clearance = 0.30
    a.max_time = 60.0
    return a


def run_shape(shape):
    f = FakeFlight()
    p = fsm.ShapePilot(f, make_args(shape))
    p.start()
    p.join(timeout=30.0)
    assert not p.is_alive(), "%s: pilot 未退出" % shape
    assert f.shape_abort_reason is None, "%s: abort=%s" % (shape, f.shape_abort_reason)
    assert p.done, "%s: done=False" % shape
    assert f.sent > 10, "%s: sent=%d" % (shape, f.sent)
    assert math.hypot(f.target[0], f.target[1]) < 0.05, "%s: final target=%s" % (shape, f.target)
    assert p.max_lat < 0.35, "%s: max_lat=%.3f" % (shape, p.max_lat)
    print("PASS %s: sent=%d max_lat=%.3f max_z=%.3f" % (shape, f.sent, p.max_lat, p.max_z))


if __name__ == "__main__":
    for s in ("circle", "eight", "both"):
        run_shape(s)
    print("SHAPE PILOT SIM PASS")
