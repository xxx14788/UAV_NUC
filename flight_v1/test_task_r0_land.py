#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R0 降落路径离线测试：现有 mission 存活时只能发 land_request，不能另起节点。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import math
import task_r0 as r0

OK = FAIL = 0


def check(name, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  PASS %s %s" % (name, extra))
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, extra))


class FakePub(object):
    def __init__(self):
        self.msgs = []

    def publish(self, msg):
        self.msgs.append(msg.data)


class FakeMission(object):
    def __init__(self, rc=None):
        self.rc = rc
        self.returncode = rc

    def poll(self):
        return self.rc


class FakeState(object):
    connected = True


class FakeExt(object):
    landed_state = 2


def make_task(mission_rc=None, armed=True, landed=2):
    t = object.__new__(r0.R0Task)
    t.land_started = False
    t.mission = FakeMission(mission_rc)
    t.state = FakeState()
    t.state.armed = armed
    t.ext = FakeExt()
    t.ext.landed_state = landed
    t.land_request_pub = FakePub()
    t.standalone_called = False

    def standalone():
        t.standalone_called = True

    t._standalone_land = standalone
    return t


_old_sleep = r0.rospy.sleep
r0.rospy.sleep = lambda _s: None
try:
    print("=== R0 单目标：距离 2.0 m ===")
    _tgt = r0.target_vins()
    check("目标距离 2.0 m", abs(math.hypot(*_tgt) - 2.0) < 1e-9,
          "target=(%.4f,%.4f) d=%.6f" % (_tgt[0], _tgt[1], math.hypot(*_tgt)))
    check("目标沿 45° 对角线", abs(_tgt[0] - _tgt[1]) < 1e-9)
    _sx, _sy = 0.20, -0.20
    _gx, _gy = r0.clamp_target(_sx, _sy, _tgt[0], _tgt[1])
    _gd = math.hypot(_gx - _sx, _gy - _sy)
    check("漂移后目标截断到 2.0 m", abs(_gd - 2.0) < 1e-9,
          "current=(%.2f,%.2f) sent=(%.4f,%.4f) d=%.6f"
          % (_sx, _sy, _gx, _gy, _gd))

    print("=== R0 起飞后等待 mission READY ===")
    ready = object.__new__(r0.R0Task)
    ready.mission = None
    ready.mission_ready = True
    ready.wait_mission_ready()
    check("READY 后允许发点", ready.mission_ready)

    exited = object.__new__(r0.R0Task)
    exited.mission = FakeMission(1)
    exited.mission_ready = False
    try:
        exited.wait_mission_ready()
    except RuntimeError:
        exited_ok = True
    else:
        exited_ok = False
    check("mission 提前退出 -> 等待 READY 中止", exited_ok)

    print("=== R0 完整顺序：READY 之前不发目标 ===")
    calls = []
    flow = object.__new__(r0.R0Task)
    flow.mission = None
    flow.last_sent_target = None
    flow.wait_stack = lambda: calls.append("stack")
    flow.start_mission = lambda: calls.append("start_mission")
    flow.wait_takeoff = lambda: calls.append("takeoff")
    def _ready():
        calls.append("wait_ready")
        flow.mission_ready = True
    flow.wait_mission_ready = _ready
    flow._xy = lambda: (0.134, -0.111, 0.70)
    def _send(x, y, label):
        calls.append("send")
        flow.last_sent_target = r0.clamp_target(0.134, -0.111, x, y)
        return "ACCEPTED"
    flow.send_goal = _send
    flow.wait_arrival = lambda x, y, label, timeout=120.0: calls.append("arrival")
    flow.hover = lambda seconds: calls.append("hover")
    flow.land = lambda: calls.append("land")
    flow.run()
    check("发点发生在 READY 之后",
          "wait_ready" in calls and "send" in calls
          and calls.index("wait_ready") < calls.index("send"), "calls=%s" % calls)
    check("整个任务只发一次目标", calls.count("send") == 1, "calls=%s" % calls)
    check("到达后悬停 5 s", "hover" in calls and "land" in calls, "calls=%s" % calls)
    _flow_d = math.hypot(flow.last_sent_target[0] - 0.134,
                         flow.last_sent_target[1] + 0.111)
    check("实际发点距当前 ≤2.0 m", _flow_d <= 2.0 + 1e-9, "d=%.6f" % _flow_d)

    print("=== R0 降落：mission 存活 -> 只发 topic，不新建进程 ===")
    t = make_task(mission_rc=None, armed=True)
    t._wait_grounded = lambda _timeout: True
    t.land()
    check("发送 3 次 land_request", t.land_request_pub.msgs == ["land"] * 3,
          "msgs=%s" % t.land_request_pub.msgs)
    check("不调用独立 land", not t.standalone_called)

    print("=== R0 降落：mission 已退出 -> 才允许独立 land ===")
    t2 = make_task(mission_rc=1, armed=True)
    t2._wait_grounded = lambda _timeout: True
    t2.land()
    check("mission 退出后走独立 land", t2.standalone_called)
    check("不向不存在的 mission 发 topic", not t2.land_request_pub.msgs)

    print("=== R0 降落：已在地面 -> 不发降落请求 ===")
    t3 = make_task(mission_rc=None, armed=False, landed=1)
    t3.land()
    check("已地面直接返回", not t3.land_request_pub.msgs and not t3.standalone_called)
finally:
    r0.rospy.sleep = _old_sleep

print()
print("===== 结果: %d PASS / %d FAIL =====" % (OK, FAIL))
sys.exit(0 if FAIL == 0 else 1)
