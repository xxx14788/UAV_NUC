#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_mission_logic.py -- 任务脚本逻辑离线验证（不接 ROS、不起飞）

为什么要它：flight_mission.py 的整条任务流程（起飞->导航->到点->等下一个目标->自动降落）
必须在 RViz 点目标才能跑；RViz 要桌面，而且真跑会真的起飞。
这里用 mock 把"导航状态机"单独抽出来跑，验证多航点(S 形)逻辑与所有纯函数。
"""
import sys, os, math, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flight_mission as fm

import signal
signal.alarm(30)   # 卡死快速失败
OK = FAIL = 0
def check(name, cond, extra=""):
    global OK, FAIL
    if cond: OK += 1; print("  PASS %s %s" % (name, extra))
    else:    FAIL += 1; print("  FAIL %s %s" % (name, extra))

def expect_raise(name, fn, exc=Exception):
    global OK, FAIL
    try:
        fn()
    except exc as e:
        OK += 1; print("  PASS %s -> %s: %s" % (name, type(e).__name__, e)); return
    except Exception as e:
        FAIL += 1; print("  FAIL %s -> 抛了 %s: %s" % (name, type(e).__name__, e)); return
    FAIL += 1; print("  FAIL %s -> 没有抛异常" % name)

class Clock:
    def __init__(self): self.t = 0.0; self.cb = None
    def monotonic(self): return self.t
    def sleep(self, s):
        self.t += s
        if self.cb: self.cb(self.t)

class Obj: pass

def mk_odom(pos, spd=0.0):
    o = Obj(); o.pose = Obj(); o.pose.pose = Obj(); o.twist = Obj(); o.twist.twist = Obj()
    o.pose.pose.position = Obj(); o.twist.twist.linear = Obj()
    o.pose.pose.position.x, o.pose.pose.position.y, o.pose.pose.position.z = pos
    o.twist.twist.linear.x = o.twist.twist.linear.y = 0.0
    o.twist.twist.linear.z = spd
    return o

def mk_state(connected=True, armed=True):
    s = Obj(); s.connected = connected; s.armed = armed; return s

def build(clock, world, fsm="CMD_CTRL", state=None):
    fm.time = clock          # 关键：模块级 time 也换成假时钟，否则 20s/180s 要真等
    f = object.__new__(fm.RosFlight)
    f.rospy = Obj(); f.rospy.sleep = clock.sleep; f.rospy.is_shutdown = lambda: False
    f.goal_used = True; f.next_goal_deadline = None; f.goal_count = 0
    f.target = world["target"]; f.nav_done = False; f.nav_fail = None
    # 2026-11-13：补齐 11-11 新增字段（此前缺 nav_deadline，测试一直崩）
    f.nav_deadline = None; f.goal_sent_t = 0.0; f.endpoint_ref = None
    f.goal_cmd_t0 = None; f.goal_target_xy = None; f.cache = {}; f.times = {}
    f._last_countdown_s = None
    f.stable_since = None; f.phase = "navigation"; f.anchor = 0.0
    f.rc = None          # 2026-11-07 测试修正：RosFlight 新增 RC 取证字段（__init__ 置 None）
    f._state = lambda: (state or mk_state())
    f._fsm = lambda: fsm
    f._fresh = lambda topic, age=1.0: True
    f._odom = lambda: mk_odom(world["pos"])
    f.landed = []
    f.land = lambda: f.landed.append(clock.t)
    return f

print("=== T0 import 面：真执行源码 RosFlight.__init__ 里的每条 import ===")
# 为什么需要它：2026-11-07 实战踩过——源码写了 `from mavros_msgs.msg import Imu`，
# 而 mavros_msgs 里没有 Imu 类型 -> flight.sh stop/takeoff 一 import 就崩。
# 用 object.__new__ 造实例的测试绕过 __init__，抓不到这类错，所以单独 AST 扫一遍。
import ast
# -I 会丢掉 PYTHONPATH，这里把 ROS 与 catkin 的 python 路径显式补回
for _p in ("/opt/ros/noetic/lib/python3/dist-packages",
           os.path.expanduser("~/catkin_ws/devel/lib/python3/dist-packages")):
    if _p not in sys.path:
        sys.path.append(_p)
_tree = ast.parse(Path(fm.__file__).read_text(encoding="utf-8"))
_cls = next(n for n in _tree.body if isinstance(n, ast.ClassDef) and n.name == "RosFlight")
_init = next(n for n in _cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
_imp = [n for n in ast.walk(_init) if isinstance(n, ast.ImportFrom)]
_errs = []
for n in _imp:
    names = ", ".join(a.name for a in n.names)
    try:
        exec("from %s import %s" % (n.module, names), {})
    except Exception as e:
        _errs.append("%s <- %s" % (names, type(e).__name__ + ": " + str(e)))
check("T0 %d 条 import 全部可执行" % len(_imp), not _errs, "; ".join(_errs))

print("=== T1 到点后进入等待窗口，无新目标 -> 超时自动降落 ===")
fm.LANDING_FILE = Path("/tmp/__t_nonexist_landing")
fm.STOP_FILE    = Path("/tmp/__t_nonexist_stopping")
c = Clock(); w = {"target": (1.0, 0.0, 0.7), "pos": (1.0, 0.0, 0.7)}
f = build(c, w)
f.navigation_monitor()
check("T1 到达计数", f.goal_count == 1, "goal_count=%d" % f.goal_count)
check("T1 进入等待窗口", f.phase == "await_goal", "phase=%s" % f.phase)
check("T1 自动降落一次", len(f.landed) == 1, "land@t=%.1fs" % (f.landed[0] if f.landed else -1))
check("T1 等满 20s 才降", f.landed and f.landed[0] >= 5.0 + 20.0 - 0.2, "t=%.1f (>=25)" % (f.landed[0] if f.landed else -1))

print("=== T2 等待窗口内来第二个目标 -> 继续飞 -> 再超时降落（S 形基础） ===")
c2 = Clock(); w2 = {"target": (1.0, 0.0, 0.7), "pos": (1.0, 0.0, 0.7)}
f2 = build(c2, w2)
def inject(t):
    if f2.phase == "await_goal" and f2.goal_count == 1 and f2.next_goal_deadline is not None:
        f2.goal_used = True; f2.next_goal_deadline = None
        f2.nav_deadline = None
        # 真 _goal_cb 会重置 endpoint_ref/stable_since；注入必须同口径，否则
        # 端点仍锁在旧目标上，d 永远 >0.2（2026-11-13 测试抓出）。
        f2.endpoint_ref = None; f2.stable_since = None
        f2.target = (2.0, 0.0, 0.7); f2.phase = "navigation"
        w2["pos"] = (2.0, 0.0, 0.7)
c2.cb = inject
f2.navigation_monitor()
check("T2 两个目标都到", f2.goal_count == 2, "goal_count=%d" % f2.goal_count)
check("T2 最终自动降落", len(f2.landed) == 1, "land@t=%.1fs" % (f2.landed[0] if f2.landed else -1))
# 时间线：t≈5.2 到目标1 -> 注入目标2 -> t≈10.4 到目标2 -> 等 20s -> t≈30.4 降落
check("T2 第二个目标后才降", f2.landed and 30.0 <= f2.landed[0] <= 31.5,
      "t=%.1f (期望 30.0~31.5 = 到点2@10.4 + 20s 窗口)" % (f2.landed[0] if f2.landed else -1))

print("=== T3 遥控器接管(MANUAL_CTRL) -> 抛错，不静默继续 ===")
c3 = Clock(); w3 = {"target": (5.0, 0.0, 0.7), "pos": (0.0, 0.0, 0.7)}
f3 = build(c3, w3, fsm="MANUAL_CTRL")
expect_raise("T3 接管即抛错", f3.navigation_monitor, RuntimeError)

print("=== T4 180s 到不了 -> 抛错 ===")
c4 = Clock(); w4 = {"target": (9.0, 0.0, 0.7), "pos": (0.0, 0.0, 0.7)}
f4 = build(c4, w4)
expect_raise("T4 超时抛错", f4.navigation_monitor, RuntimeError)
check("T4 未误触发降落", len(f4.landed) == 0, "landed=%d" % len(f4.landed))

print("=== T7 60s 未确认到点但已停在目标附近 -> 自动降落 ===")
c6 = Clock(); w6 = {"target": (0.5, 0.0, 0.7), "pos": (0.5, 0.0, 0.7)}
f6 = build(c6, w6, fsm="AUTO_HOVER")   # CMD_CTRL 不成立 -> 5 s 到位判定永远不走完
try:
    f6.navigation_monitor()
except RuntimeError:
    pass
check("T7 超时后自动降落一次", len(f6.landed) == 1, "land@t=%.1fs" % (f6.landed[0] if f6.landed else -1))
check("T7 约 60s 触发", bool(f6.landed) and 59.0 <= f6.landed[0] <= 61.5,
      "t=%.1f" % (f6.landed[0] if f6.landed else -1))

print("=== T5 遥控器通道校验 ===")
good = [1500, 1500, 999, 1500, 1800, 1800, 1000, 1000]
# 2026-11-07 用户裁定：油门必须居中 -> 「油门在底」现在必须被拒
expect_raise("T5a 油门在底 -> 拒（OFFBOARD 要求居中）",
             lambda: fm.validate_rc_channels(good), ValueError)
good2 = [1500, 1500, 1500, 1500, 1800, 1800, 1000, 1000]
check("T5b 油门居中=合法", (lambda: (fm.validate_rc_channels(good2), True)[1])())
expect_raise("T5c 副翼偏 -> 拒", lambda: fm.validate_rc_channels([1200,1500,999,1500,1800,1800,1000,1000]), ValueError)
expect_raise("T5d 方向偏 -> 拒", lambda: fm.validate_rc_channels([1500,1500,999,1200,1800,1800,1000,1000]), ValueError)
expect_raise("T5e CH5 低 -> 拒", lambda: fm.validate_rc_channels([1500,1500,999,1500,1000,1800,1000,1000]), ValueError)
expect_raise("T5f CH6 低 -> 拒", lambda: fm.validate_rc_channels([1500,1500,999,1500,1800,1000,1000,1000]), ValueError)
expect_raise("T5g 通道数不足 -> 拒", lambda: fm.validate_rc_channels([1500,1500,999,1500]), ValueError)

print("=== T6 目标点校验 ===")
fm.TARGET_Z = 0.7
import time as _t
now = _t.time()
check("T6a 合法目标", fm.validate_goal("world", now-0.1, now, (2.0,0.0), (0.0,0.0), 0.0) == ((2.0,0.0,0.7), 2.0))
expect_raise("T6b 超 3.5m -> 拒", lambda: fm.validate_goal("world", now-0.1, now, (4.0,0.0), (0.0,0.0), 0.0), ValueError)
expect_raise("T6c frame 非 world -> 拒", lambda: fm.validate_goal("map", now-0.1, now, (1.0,0.0), (0.0,0.0), 0.0), ValueError)
expect_raise("T6d 时间戳过期 -> 拒", lambda: fm.validate_goal("world", now-5.0, now, (1.0,0.0), (0.0,0.0), 0.0), ValueError)
expect_raise("T6e 时间戳为 0 -> 拒", lambda: fm.validate_goal("world", 0.0, now, (1.0,0.0), (0.0,0.0), 0.0), ValueError)
fm.TARGET_Z = None
expect_raise("T6f TARGET_Z 未初始化 -> 明确报错", lambda: fm.validate_goal("world", now-0.1, now, (1.0,0.0), (0.0,0.0), 0.0), ValueError)

print()
print("===== 结果: %d PASS / %d FAIL =====" % (OK, FAIL))
sys.exit(0 if FAIL == 0 else 1)
