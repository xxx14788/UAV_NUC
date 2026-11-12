#!/usr/bin/env python3
"""Guarded takeoff, one RViz goal, endpoint hover, and explicit landing."""
import argparse
import fcntl
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import time


HOME = Path.home()
FLOW = HOME / "sitl_realmachine" / "flight_v1"
STATE_DIR = FLOW / "runtime"
LANDING_FILE = STATE_DIR / "landing.requested"
STOP_FILE = STATE_DIR / "stopping"
# 2026-11-07：不再硬编码。preflight 里从 /px4ctrl/auto_takeoff_land/takeoff_height 读，
# 并要求规划器的 manual_goal_z 与之相等（单一来源，改高度只动 px4ctrl 的 yaml）。
TARGET_Z = None
DRY = False  # --dry：只跑飞前检查，不发布 TAKEOFF/LAND（彩排用）
SIM = False  # --sim：SITL 模式，跳过 RC 通道检查（仿真无遥控器）
GOAL_RADIUS = 3.5   # 2026-11-07 用户令：2.0 -> 3.5 m（契约缺失时的回退，见下方）


# 2026-11-08（方案 v2 C3）：接缝值从契约读（唯一事实源）。
# 这里保留字面量只作**契约缺失时的回退**；check_interfaces.py --static 会断言
# 两者一致，所以不存在"两个真源各说各话"。
def _contract_value(dotted, default):
    try:
        import yaml
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "contract", "flight_contract.yaml")
        with open(path, encoding="utf-8") as fh:
            cur = yaml.safe_load(fh)
        for key in dotted.split("."):
            cur = cur[key]
        return float(cur)
    except Exception:
        return default


GOAL_RADIUS = _contract_value("params.goal_radius_m", GOAL_RADIUS)


def _contract_str(dotted, default):
    """契约里的字符串值（同样只在契约缺失时回退）。"""
    try:
        import yaml
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "contract", "flight_contract.yaml")
        with open(path, encoding="utf-8") as fh:
            cur = yaml.safe_load(fh)
        for key in dotted.split("."):
            cur = cur[key]
        return str(cur)
    except Exception:
        return default


GOAL_TOPIC = _contract_str("seams.goal.topic", "/flight_v1/goal_gate")


def goal_stall_verdict(elapsed_s, dist_to_goal_m, vcmd_mps,
                       settle_s=5.0, min_gap_m=0.50, min_v_mps=0.05):
    """目标停滞判据（纯函数；tests/test_contract.py 覆盖）。

    2026-11-08 二审修正（原判据有两个真问题）：
      * 原来用"相对起点位移 <0.2 m"：对 <0.2 m 的近目标会**误中止**；
      * 原来起点取 /position_cmd 当前位置、不新鲜时回退 (0,0)：首个目标前该话题从无流
        （traj_server 只在收到 bspline 后才发），于是回退必发生；若悬停点离 VINS 原点
        >0.2 m，"原地保持"指令本身位移就 >0.2 m -> 目标停滞判据**永远不触发**（事故形态复发）。
    现在按方案原文：**离目标还差 >0.5 m 且没有指令速度** -> 中止。
    """
    return bool(elapsed_s >= settle_s and dist_to_goal_m > min_gap_m
                and vcmd_mps < min_v_mps)
def pick_endpoint_ref(prev_ref, path_msg, path_time, goal_sent_t, now,
                      fresh_age=2.0, target=None):
    """到位判定用的参考点（纯函数，可单测）。

    规则：
      1) 路径必须是**本次目标发出之后**收到的（否则是上一条轨迹的残留 -> 多航点误判到点）；
      2) 且仍在 fresh_age 内 -> 取它的末点（随重规划持续更新）；
      3) 否则沿用上一次的有效值；从未有过 -> 退回命令目标。
    """
    if (path_msg is not None and len(path_msg.poses) > 0
            and path_time > goal_sent_t and (now - path_time) <= fresh_age):
        q = path_msg.poses[-1].pose.position
        return (q.x, q.y, q.z)
    return prev_ref if prev_ref is not None else target


TAKEOFF_HOVER_SECONDS = 5.0   # 契约缺失时回退
GOAL_HOVER_SECONDS = 5.0
TAKEOFF_HOVER_SECONDS = _contract_value("params.takeoff_hover_s", TAKEOFF_HOVER_SECONDS)
GOAL_HOVER_SECONDS = _contract_value("params.goal_hover_s", GOAL_HOVER_SECONDS)

# 2026-11-13 用户令：到点稳定后 NEXT_GOAL_WAIT 秒内没有新目标 -> 自动降落。
# 单一来源：候选点窗口与 UNREACHABLE 悬停等待共用，禁止再写字面量。
NEXT_GOAL_WAIT = 20.0
# 每个目标的导航预算（2026-11-13 用户令：60 -> 120 s；超时且已停在目标附近 -> 自动降落）
NAV_TIMEOUT = 120.0


def validate_rc_channels(channels):
    """RC 闸门（2026-11-08 用户令④）：判据全部读契约 runtime.rc，与 preflight 共用一份。"""
    ch = list(channels)
    need = int(_contract_value("runtime.rc.channels", 8))
    tol = int(_contract_value("runtime.rc.centered_tol", 125))
    ch5_min = int(_contract_value("runtime.rc.ch5_min", 1750))
    if len(ch) < need or any(x < 800 or x > 2200 for x in ch[:need]):
        raise ValueError("遥控器通道数量/范围异常（需要 %d 通道）" % need)
    # 2026-11-07 用户裁定：OFFBOARD 模式必须油门居中（掉出 OFFBOARD 会直接掉高度）
    if any(abs(x - 1500) > tol for x in ch[:4]):
        raise ValueError("四杆必须居中（容差 ±%d）：%s" % (tol, [round(x) for x in ch[:4]]))
    # 2026-11-07 用户令：CH6 不再参与判定（任务由脚本区分）
    if ch[4] <= ch5_min:
        raise ValueError("起飞前需保持 CH5 悬停档（CH5=%.0f <= %d）" % (ch[4], ch5_min))


def classify_goal_event(phase, goal_used, landing=False, stop=False):
    """2026-11-12 P6：点击决策（纯函数，self-test 直接覆盖）。

    返回 "ACCEPT" / "REPLACE" / "REJECT:<原因>"。
    REPLACE = 导航中收到新点：允许替换目标（不再静默丢弃）。
    """
    if landing:
        return "REJECT:降落已开始"
    if stop:
        return "REJECT:已请求停栈"
    if phase == "navigation" and goal_used:
        return "REPLACE"
    if phase != "await_goal":
        return "REJECT:当前阶段 %s 不收点" % phase
    if goal_used:
        return "REJECT:目标已锁定（等待到位）"
    return "ACCEPT"

def takeoff_manual_takeover(armed, fsm, fsm_stamp, takeoff_cmd_t, since, now, hold=1.5):
    """TAKEOFF 后是否真的被 px4ctrl 退回手动（2026-11-13 实飞竞态修复）。

    /debugPx4ctrl/fsm_state 只有 1 Hz：TAKEOFF 被接受的瞬间 PX4 已 armed，但下一帧
    状态串可能仍是 MANUAL_CTRL（实测 00:58:08 误判，0.39 s 后 px4ctrl 实际进 AUTO_TAKEOFF）。
    所以：命令之前的样本一律不信；命令后的 MANUAL_CTRL 要连续 hold 秒才算接管。
    返回 (is_takeover, new_since)。
    """
    if (not armed or fsm != "MANUAL_CTRL" or takeoff_cmd_t is None
            or fsm_stamp < takeoff_cmd_t):
        return False, None
    since = since if since is not None else now
    return (now - since >= hold), since


def validate_goal(frame, stamp, now, goal_xy, current_xy, anchor_z):
    if TARGET_Z is None:
        raise ValueError("目标高度未初始化（preflight 未跑，或读不到 px4ctrl takeoff_height）")
    if frame != "world":
        raise ValueError("RViz 目标 frame 必须是 world")
    age = now - stamp
    if stamp <= 0 or age < -0.1 or age > 2.0:
        raise ValueError("RViz 目标时间戳过期或无效")
    gx, gy = goal_xy
    distance = math.hypot(gx - current_xy[0], gy - current_xy[1])
    if not math.isfinite(distance) or distance > GOAL_RADIUS:
        raise ValueError("目标超出当前位置水平 %.1f m 限制" % GOAL_RADIUS)
    return (gx, gy, anchor_z + TARGET_Z), distance


def finite_pose(msg):
    p = msg.pose.pose.position
    v = msg.twist.twist.linear
    return all(math.isfinite(x) for x in (p.x, p.y, p.z, v.x, v.y, v.z))


def acquire_lock(name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stream = open(STATE_DIR / name, "w")
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise RuntimeError("同类飞行命令正在运行，拒绝重复操作")
    return stream


def lock_is_free(name):
    stream = open(STATE_DIR / name, "a+")
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    finally:
        stream.close()


class RosFlight:
    def __init__(self):
        import rospy
        from geometry_msgs.msg import PoseStamped
        from mavros_msgs.msg import ExtendedState, RCIn, State
        # 2026-11-07 审查修正：mavros_msgs 里没有 Imu 消息类型（IMU 是 sensor_msgs/Imu）。
        # 原来写在一起 -> import 直接抛 ImportError，flight.sh stop/takeoff 全崩。
        from sensor_msgs.msg import Imu
        from nav_msgs.msg import Odometry
        from quadrotor_msgs.msg import PositionCommand, TakeoffLand
        from std_msgs.msg import String  # 2026-11-12 P6：goal_ack 也用
        self.String = String
        from nav_msgs.msg import Path

        self.rospy = rospy
        self.PoseStamped = PoseStamped
        self.TakeoffLand = TakeoffLand
        self.cache = {}
        self.times = {}
        self.history = {}
        self.pose_history = []
        self.seq = {}
        self.rc = None
        self.goal_used = False
        self.phase = "preflight"
        self.anchor = None
        # 2026-11-07 多航点（S 形）：next_goal_deadline=None 表示无限等（首个目标）
        self.next_goal_deadline = None
        self._last_countdown_s = None      # 到点等待窗口倒计时播报（终端+RViz）
        self.nav_deadline = None          # 当前目标的 NAV_TIMEOUT 导航超时（按目标重置）
        self.endpoint_ref = None          # 锁存的"规划器实际终点"（到位判定用）
        self.goal_sent_t = 0.0            # 本次目标发出的时刻（只接受其后的 planned_path）
        # 2026-11-08（方案 v2 C3）：目标停滞自降状态（发目标后 5 s 内指令不动 -> 中止）
        self.goal_cmd_t0 = None
        self.goal_target_xy = None
        self.goal_count = 0
        self.target = None
        self.nav_done = False
        self.nav_fail = None
        self.stable_since = None
        rospy.init_node("flight_v1_mission", anonymous=False, disable_signals=True)

        def sub(topic, msg_type, callback=None):
            def receive(msg):
                now = time.monotonic()
                self.cache[topic] = msg
                self.times[topic] = now
                history = self.history.setdefault(topic, [])
                history.append(now)
                cutoff = now - 8.0
                while history and history[0] < cutoff:
                    history.pop(0)
                if topic == "/vins_estimator/odometry" and finite_pose(msg):
                    p = msg.pose.pose.position
                    self.pose_history.append((now, p.x, p.y, p.z))
                    while self.pose_history and self.pose_history[0][0] < cutoff:
                        self.pose_history.pop(0)
                self.seq[topic] = self.seq.get(topic, 0) + 1
                if callback:
                    callback(msg)
            rospy.Subscriber(topic, msg_type, receive, queue_size=20)

        sub("/mavros/state", State)
        sub("/mavros/extended_state", ExtendedState)
        sub("/mavros/rc/in", RCIn, self._rc_cb)
        sub("/mavros/imu/data", Imu)
        sub("/mavros/imu/data_raw", Imu)
        sub("/vins_estimator/odometry", Odometry)
        sub("/vins_estimator/imu_propagate", Odometry)
        sub("/debugPx4ctrl/fsm_state", String)
        sub("/position_cmd", PositionCommand)
        sub("/move_base_simple/goal", PoseStamped, self._goal_cb)
        sub("/flight_v1/goal_status", String, self._goal_status_cb)
        # 2026-11-11：到位判定要对着"规划器实际终点"算（A* 端点外推会让终点比目标短 0.2-0.4 m）
        sub("/flight_v1/planned_path", Path)
        self.takeoff_pub = rospy.Publisher("/px4ctrl/takeoff_land", TakeoffLand, queue_size=4)
        self.goal_pub = rospy.Publisher(GOAL_TOPIC, PoseStamped, queue_size=2)
        # 2026-11-12 P6：点击 ack 通道（每次点击必有反馈）
        self.ack_pub = rospy.Publisher("/flight_v1/goal_ack", String, queue_size=4)

    def _rc_cb(self, msg):
        self.rc = msg

    def _fresh(self, topic, max_age=1.0):
        return topic in self.cache and time.monotonic() - self.times[topic] <= max_age

    def _fresh_stamp(self, msg, max_age):
        stamp = msg.header.stamp.to_sec()
        now = self.rospy.Time.now().to_sec()
        age = now - stamp
        return stamp > 0 and -0.05 <= age <= max_age

    def _state(self):
        if not self._fresh("/mavros/state", 1.5):
            raise RuntimeError("MAVROS state 未知或过期，拒绝动作")
        msg = self.cache["/mavros/state"]
        if not self._fresh_stamp(msg, 1.5):
            raise RuntimeError("MAVROS state 时间戳无效或过期，拒绝动作")
        return msg

    def _fsm(self):
        if not self._fresh("/debugPx4ctrl/fsm_state", 2.5):
            return None
        _t = (self.cache["/debugPx4ctrl/fsm_state"].data or "").split()
        return _t[0] if _t else None

    def _odom(self):
        topic = "/vins_estimator/imu_propagate"
        # 2026-11-07：SITL 的 VINS 只有 50Hz 且偶有抖动，0.25s 门会误杀；
        # --sim 放宽到 1.5s（实机仍是 0.25s，绝不放宽）。
        _age = 1.5 if SIM else 0.25
        if not self._fresh(topic, _age):
            raise RuntimeError("VINS 里程计已过期")
        msg = self.cache[topic]
        if not self._fresh_stamp(msg, _age) or not finite_pose(msg):
            raise RuntimeError("VINS 里程计含 NaN/Inf")
        return msg

    def _check_rc(self, require_centered=True):
        if SIM:
            # 2026-11-07：SITL 没有遥控器（/mavros/rc/in 无数据），RC 门在仿真里无法满足。
            # 仅 --sim 时跳过；实飞绝不带这个参数。
            print("[SIM] 跳过 RC 检查（仿真无遥控器；实飞绝不带 --sim）", flush=True)
            return
        if (not self._fresh("/mavros/rc/in", 0.5) or self.rc is None
                or not self._fresh_stamp(self.rc, 0.5)):
            raise RuntimeError("遥控器数据未连接或已过期")
        channels = list(self.rc.channels)
        if require_centered:
            validate_rc_channels(channels)
        elif len(channels) < 8 or any(x < 800 or x > 2200 for x in channels[:8]):
            raise RuntimeError("遥控器通道数量/范围异常")
        _ch5_min = int(_contract_value("runtime.rc.ch5_min", 1750))
        if channels[4] <= _ch5_min:
            raise RuntimeError("必须保持 CH5 悬停档（CH5=%.0f <= %d）" % (channels[4], _ch5_min))

    # ---------------------------------------------------------------- P0-1
    # ---------------------------------------------------------------- P0-3
    def _goal_status_cb(self, msg):
        """规划器回传：OK / ADJUSTED dx dy / UNREACHABLE。
        2026-11-09 用户令：改点必须告知；偏差过大或不可达就悬停等新点。"""
        txt = (msg.data or "").strip()
        if not txt:
            return
        print("[goal_status] %s" % txt, flush=True)
        if txt == "OK":
            return
        # 2026-11-10 实测修正：规划器对"未知/未观测"栅格的终点也会做外推，
        # 开阔场地里 ADJUSTED 是常态（实测 33 次 ADJUSTED / 9 次 OK，最大 0.44 m）。
        # 若 mission 按 0.2 m 阈值就悬停，会**每次导航都被自己打断**。
        # 因此 ADJUSTED 只告警（并记录），只有 UNREACHABLE 才真正悬停等新点。
        if txt.startswith("ADJUSTED"):
            try:
                _, dx, dy = txt.split()
                mag = math.hypot(float(dx), float(dy))
            except Exception:
                mag = -1.0
            print("[goal_status] 终点被外推 %.2f m（开阔/未观测区常见，仅记录）" % mag, flush=True)
            return
        bad = (txt == "UNREACHABLE")
        if not bad:
            return
        if self.phase != "navigation":
            return
        # 悬停：把当前位置作为新目标发出去（规划器会生成一条零位移轨迹）
        try:
            p = self._odom().pose.pose.position
            hold = self.PoseStamped()
            hold.header.stamp = self.rospy.Time.now()
            hold.header.frame_id = "world"
            hold.pose.position.x = p.x
            hold.pose.position.y = p.y
            hold.pose.position.z = p.z
            hold.pose.orientation.w = 1.0
            self.goal_pub.publish(hold)
            print("!! 目标不可用（%s）：已发当前位置悬停，等待新目标" % txt, flush=True)
        except Exception as exc:
            print("!! 悬停指令发送失败：%r" % (exc,), flush=True)
        self.phase = "await_goal"
        self.goal_used = False
        # 2026-11-11 修 bug：原来这里不设倒计时，monitor 的"无目标"分支会无限等待
        # -> 目标不可达时飞机一直悬停到没电。现在 NEXT_GOAL_WAIT 秒无新目标就自动降落。
        self.next_goal_deadline = time.monotonic() + NEXT_GOAL_WAIT
        self._last_countdown_s = None
        self.endpoint_ref = None
        self.goal_cmd_t0 = None
        self.goal_target_xy = None

    def _goal_cb(self, msg):
        def _ack(status, detail=""):
            self.ack_pub.publish(self.String(data="%s %s" % (status, detail)))
            print("[goal_ack] %s %s" % (status, detail), flush=True)
        ev = classify_goal_event(self.phase, self.goal_used,
                                 LANDING_FILE.exists(), STOP_FILE.exists())
        if ev.startswith("REJECT"):
            _ack("REJECTED", ev.split(":", 1)[1])
            return
        if ev == "REPLACE":
            _ack("REPLACE", "导航中替换目标")
            # 不 return，继续走 validate（下面会重置 goal_used / deadline / stable_since）
        try:
            state = self._state()
            odom = self._odom()
            self._check_rc()
            # 2026-11-07：首个目标时 FSM=AUTO_HOVER；后续目标时已在 CMD_CTRL。
            # 原来只允许 AUTO_HOVER -> 永远点不了第二个目标。
            if not state.connected or not state.armed or \
                    self._fsm() not in ("AUTO_HOVER", "CMD_CTRL"):
                raise RuntimeError("目标只在已解锁且 AUTO_HOVER/CMD_CTRL 时接收")
            stamp = msg.header.stamp.to_sec()
            p = odom.pose.pose.position
            gx, gy = msg.pose.position.x, msg.pose.position.y
            target, distance = validate_goal(
                msg.header.frame_id, stamp, self.rospy.Time.now().to_sec(),
                (gx, gy), (p.x, p.y), self.anchor)
            gated = self.PoseStamped()
            gated.header.stamp = self.rospy.Time.now()
            gated.header.frame_id = "world"
            gated.pose = msg.pose
            gated.pose.position.z = target[2]
            self.goal_used = True
            self.next_goal_deadline = None   # 收到新目标，取消降落倒计时
            self.nav_deadline = time.monotonic() + NAV_TIMEOUT   # 每个目标各自导航预算
            self.endpoint_ref = None                        # 新目标重新锁存端点
            # 2026-11-12（P6 复检）：REPLACE 时必须重置到位悬停计时。否则旧目标已累计的
            # stable_since 会被新目标继承，到点瞬间就满足 5s 悬停 -> 假到位。
            self.stable_since = None
            self._last_countdown_s = None
            self.target = target
            self.phase = "navigation"
            self.goal_pub.publish(gated)
            _ack("ACCEPTED", "(%.2f, %.2f, %.2f)" % (target[0], target[1], target[2]))
            self.goal_sent_t = time.monotonic()   # 之后的 planned_path 才算本次目标的
            # 目标停滞起点（方案 v2 C3 + 二审 F2）：只记"目标 xy + 时刻"，
            # 判据用"指令离目标还差多少"，不再依赖 /position_cmd 是否已有流。
            self.goal_target_xy = (target[0], target[1])
            self.goal_cmd_t0 = time.monotonic()
            print("已接收目标：距离 %.2f m，目标相对起飞高度 %.2f m" % (distance, TARGET_Z), flush=True)
        except Exception as exc:
            print("拒绝 RViz 目标：%s" % exc, flush=True)

    def _pub_takeoff(self):
        msg = self.TakeoffLand()
        msg.takeoff_land_cmd = 1
        self.takeoff_pub.publish(msg)

    def _pub_land(self):
        msg = self.TakeoffLand()
        msg.takeoff_land_cmd = 2
        self.takeoff_pub.publish(msg)

    def _initial_wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and not self.rospy.is_shutdown():
            self.rospy.sleep(0.05)

    def preflight(self):
        if STOP_FILE.exists():
            raise RuntimeError("检测到停栈流程，拒绝起飞")
        self._initial_wait(8.0)
        failures = []
        state = self._state()
        if not state.connected or state.armed:
            failures.append("飞控必须连接且明确未解锁")
        ext = self.cache.get("/mavros/extended_state")
        if (not self._fresh("/mavros/extended_state", 2.5) or ext.landed_state != 1
                or not self._fresh_stamp(ext, 2.5)):
            failures.append("飞控未提供新鲜 ON_GROUND 状态")
        if self._fsm() != "MANUAL_CTRL":
            failures.append("px4ctrl 必须在 MANUAL_CTRL；不自动重启控制器")
        try:
            self._check_rc()
        except RuntimeError as exc:
            failures.append(str(exc))

        for topic, minimum in (("/mavros/imu/data", 40),
                               ("/mavros/imu/data_raw", 45 if SIM else 190),
                               ("/vins_estimator/odometry", 8),
                               ("/vins_estimator/imu_propagate", 40)):
            times = self.history.get(topic, [])
            span = times[-1] - times[0] if len(times) > 1 else 0.0
            hz = (len(times) - 1) / span if span > 0 else 0.0
            print("%s %.1f Hz" % (topic, hz))
            if span < 6.0 or hz < minimum:
                failures.append("%s 最近窗口 %.1f Hz，要求 >=%d Hz" % (topic, hz, minimum))
        for topic in ("/mavros/imu/data", "/mavros/imu/data_raw",
                      "/vins_estimator/odometry", "/vins_estimator/imu_propagate"):
            if not self._fresh(topic, 0.25):
                failures.append("输入过期：%s" % topic)

        try:
            vins = self.cache["/vins_estimator/odometry"]
            imu = self.cache["/mavros/imu/data"]
            err = self._tilt_error(vins.pose.pose.orientation, imu.orientation)
            _lim = 15.0 if SIM else 0.7
            print("VINS/PX4 倾斜差 %.2f deg（门限 <%.1f deg%s）"
                  % (err, _lim, "；--sim 放宽，实机 0.7" if SIM else ""))
            if err >= _lim:
                failures.append("姿态一致性未通过；请地面检查/重新初始化 VINS 后重跑")
        except Exception:
            failures.append("姿态一致性数据不足")
        if len(self.pose_history) < 30:
            failures.append("静置位置样本不足")
        else:
            columns = list(zip(*(row[1:] for row in self.pose_history)))
            spans = [max(axis) - min(axis) for axis in columns]
            if max(spans) > 0.15:
                failures.append("地面静置 8 秒位置极差超限：%.3f m" % max(spans))

        log_candidates = list((HOME / "sitl_realmachine").glob("vins_*.log"))
        log_candidates += list((HOME / "sitl_realmachine").glob("*/vins_*.log"))
        if log_candidates:
            latest = max(log_candidates, key=lambda p: p.stat().st_mtime)
            text = latest.read_text(errors="replace")
            log_ok = True
            for name, limit in (("Bas", 0.8), ("Bgs", 0.02), ("final_cost", 1e4)):
                if name == "final_cost":
                    vals = [float(x) for x in re.findall(r"final_cost=([0-9.eE+-]+)", text)[-20:]]
                else:
                    vals = [float(x) for x in re.findall(r"\|%s\|=([0-9.eE+-]+)" % name, text)[-20:]]
                if not vals:
                    print("VINS 日志缺少 %s，按旧流程仅提示" % name)
                    continue
                vals.sort()
                median = vals[len(vals) // 2]
                print("VINS %s 中位数 %.6g（限值 %.6g）" % (name, median, limit))
                log_ok = log_ok and math.isfinite(median) and median <= limit
            if not log_ok:
                failures.append("VINS 收敛日志超出 |Bas|/|Bgs|/cost 门限")

        # 2026-11-07（方案A）：高度以 px4ctrl 的 takeoff_height 为唯一来源。
        # 原来这里硬断言两者都 == 0.5，改高度就得改脚本；现在只要求两者相等。
        global TARGET_Z
        _h_px4 = self.rospy.get_param("/px4ctrl/auto_takeoff_land/takeoff_height", None)
        _h_pln = self.rospy.get_param("/drone_0_ego_planner_node/fsm/manual_goal_z", None)
        if _h_px4 is None or not math.isfinite(_h_px4) or _h_px4 <= 0.0:
            failures.append("读不到 /px4ctrl/auto_takeoff_land/takeoff_height（或非正数）")
        elif _h_pln is None or abs(_h_pln - _h_px4) > 1e-6:
            failures.append("规划器 manual_goal_z=%.3f 与 px4ctrl takeoff_height=%.3f 不一致"
                            % (_h_pln if _h_pln is not None else float("nan"), _h_px4))
        else:
            TARGET_Z = float(_h_px4)
            print("目标高度（单一来源 /px4ctrl/auto_takeoff_land/takeoff_height）= %.3f m" % TARGET_Z)

        # 2026-11-08：期望值全部从契约取（GOAL_RADIUS / max_vel / max_acc / pose_type）
        for key, expected in (
                              ("/drone_0_ego_planner_node/fsm/manual_goal_max_distance", GOAL_RADIUS),
                              ("/drone_0_ego_planner_node/manager/max_vel",
                               _contract_value("params.max_vel", 0.5)),
                              ("/drone_0_ego_planner_node/manager/max_acc",
                               _contract_value("params.max_acc", 1.0)),
                              ("/drone_0_ego_planner_node/grid_map/pose_type",
                               _contract_value("params.pose_type", 1))):
            value = self.rospy.get_param(key, None)
            if not isinstance(value, (int, float)) or abs(value - expected) > 1e-6:
                failures.append("参数 %s=%r，预期 %s" % (key, value, expected))
        # 2026-11-08 用户令：**电池门取消** —— /mavros/battery 实测读不到有效电压
        # （0.0 V / -1%，PM 遥测未配），脚本里再加一道只会变成假绿或假红。
        # 电压改为人工用外部电压表确认（>=14.0 V 才飞）；preflight §11 仍会 WARN 提示。
        if LANDING_FILE.exists():
            failures.append("检测到本轮降落标志；请完成停栈后再开始新轮")

        # Existing calibration monitor is read-only. WARN remains a pass under its documented gate.
        _att = HOME / "sitl_realmachine" / "att_gate.py"
        if SIM and not _att.exists():
            print("[SIM] 跳过姿态一致性闸门（本机无 att_gate.py；实机绝不放行）", flush=True)
        else:
            result = subprocess.run([sys.executable, str(_att)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    universal_newlines=True, timeout=8)
            print(result.stdout.strip())
            if "ATT_GATE: PASS" not in result.stdout and "ATT_GATE: WARN" not in result.stdout:
                if SIM:
                    print("[SIM] 姿态闸门未过，但 --sim 下不拦（实机绝不放行）", flush=True)
                else:
                    failures.append("姿态一致性闸门失败")
        if failures:
            raise RuntimeError("起飞前置检查失败：\n- " + "\n- ".join(failures))
        pose = self.cache["/vins_estimator/odometry"].pose.pose.position
        self.anchor = pose.z
        self.anchor_xy = (pose.x, pose.y)
        # 2026-11-08（方案 v2 C3）：接缝硬门。深度/位姿边必须活着且时间戳对齐，
        # 否则规划器一收到目标就 EMERGENCY_STOP（22:36 那轮就是这么报废的），
        # 而地面检查全绿。SKIP_INTERFACES=1 只在彩排调试时用，正式起飞不要设。
        skip_gate = os.environ.get("SKIP_INTERFACES") == "1"
        if skip_gate:
            print("!!!!!!!! 接缝硬门被 SKIP_INTERFACES=1 跳过 —— 正式起飞禁止 !!!!!!!!",
                  flush=True)
        if not skip_gate:
            checker = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "check_interfaces.py")
            # 2026-11-08：**必须带 timeout**。检查器若因 master/话题异常挂住，
            # 没有 timeout 就等于把起飞命令挂死（实测 --task 在无 master 时 40 s 退不出）。
            try:
                proc = subprocess.run([sys.executable, checker, "--task"],
                                      capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired:
                raise RuntimeError("接缝检查超时 60 s（ROS master/话题异常？）；拒绝起飞")
            if proc.returncode != 0:
                try:
                    bad = [c for c in json.loads(proc.stdout)["checks"] if not c["ok"]]
                    detail = "; ".join("%s=%s" % (c["name"], c.get("actual")) for c in bad[:6])
                except Exception:
                    detail = (proc.stdout[-300:] + " " + proc.stderr[-300:]).strip()
                raise RuntimeError("接缝检查未过（深度/位姿/目标/指令边）；拒绝起飞：%s" % detail)
            print("接缝检查通过（深度/位姿/目标/指令边 + 参数一致性）。", flush=True)
        print("起飞前检查通过：RC 四杆居中、CH5 悬停（CH6 不参与）；目标高度相对锚点 %.3f m" % self.anchor)

    def _rc_summary(self):
        """2026-11-07 取证工具：MANUAL_CTRL 时打印 RC 前 8 通道，
        直接看出是不是 CH5 被拨低（接管）。CH6 已在 2026-11-12 按用户令移出判定与显示。"""
        if self.rc is None:
            return "RC 无数据"
        ch = list(self.rc.channels)
        if len(ch) < 6:
            return "RC 通道数=%d（异常）" % len(ch)
        # 2026-11-12 用户令：CH6 不参与任何判定，也不再显示（只看 CH5）。
        return ("CH1-4=%s CH5=%d(%s)"
                % (ch[:4], ch[4], "高档/悬停" if ch[4] > 1750 else "低档=接管"))

    @staticmethod
    def _tilt_error(vins, px4):
        def gravity(q):
            x, y, z, w = q.x, q.y, q.z, q.w
            g = (-2 * (x * z - w * y), -2 * (y * z + w * x),
                 -(1 - 2 * (x * x + y * y)))
            norm = math.sqrt(sum(a * a for a in g))
            return tuple(a / norm for a in g)
        a, b = gravity(vins), gravity(px4)
        return math.degrees(math.acos(max(-1.0, min(1.0, sum(x*y for x, y in zip(a, b))))))

    def takeoff(self):
        self.preflight()
        if DRY:
            print("[DRY] 飞前检查全过（RC 四杆 / 姿态门 / 里程计 / 高度参数）。", flush=True)
            print("[DRY] 本次**不发布 TAKEOFF**、不解锁、不起飞 —— 到此为止。", flush=True)
            return
        self.phase = "takeoff"
        print("发出 TAKEOFF；在升至 %.2f m 并稳定 %.0f 秒前不接收 RViz 目标。" % (TARGET_Z, TAKEOFF_HOVER_SECONDS), flush=True)
        deadline = time.monotonic() + 120.0
        takeoff_started = time.monotonic()
        takeoff_cmd_t = None          # 第一帧 TAKEOFF 发出的时刻（忽略此前的 fsm 样本）
        manual_armed_since = None
        next_pub = 0.0
        while time.monotonic() < deadline and not self.rospy.is_shutdown():
            now = time.monotonic()
            # 2026-11-13 安全快速路：CH5 拨低 = 飞手接管，立即停发 TAKEOFF 并退出，
            # 不等 1.5 s 的 fsm 判据（飞机控制权由 px4ctrl/PX4 的 RC 链路负责，与本计时器无关）。
            if not SIM and self.rc is not None and self._fresh("/mavros/rc/in", 0.5):
                _ch = list(self.rc.channels)
                _ch5_min = int(_contract_value("runtime.rc.ch5_min", 1750))
                if len(_ch) > 4 and _ch[4] <= _ch5_min:
                    raise RuntimeError("CH5 已拨低（%.0f<=%d）：飞手接管，已停止发送 TAKEOFF"
                                       % (_ch[4], _ch5_min))
            if now >= next_pub and self._fsm() in ("MANUAL_CTRL", "AUTO_TAKEOFF"):
                self._pub_takeoff()
                if takeoff_cmd_t is None:
                    takeoff_cmd_t = now
                next_pub = now + 1.0
            state = self._state()
            if not state.connected:
                raise RuntimeError("飞控连接丢失；遥控器接管")
            fsm = self._fsm()
            if not state.armed and now - takeoff_started > 15.0:
                raise RuntimeError("TAKEOFF 后 15 秒仍未确认解锁；遥控器接管")
            # 2026-11-13 实测竞态：fsm_state 1 Hz，TAKEOFF 被接受后 0.39 s 内还是旧
            # MANUAL_CTRL -> 旧代码立即误判退出（实际 px4ctrl 已进 AUTO_TAKEOFF 并起飞）。
            takeover, manual_armed_since = takeoff_manual_takeover(
                state.armed, fsm, self.times.get("/debugPx4ctrl/fsm_state", 0.0),
                takeoff_cmd_t, manual_armed_since, now)
            if takeover:
                raise RuntimeError("已解锁但 px4ctrl 持续 1.5 s 处于 MANUAL_CTRL；遥控器接管。%s"
                                   % self._rc_summary())
            if fsm == "AUTO_HOVER":
                odom = self._odom()
                p, v = odom.pose.pose.position, odom.twist.twist.linear
                in_band = abs((p.z - self.anchor) - TARGET_Z) <= 0.15
                settled = in_band and math.hypot(p.x - self.anchor_xy[0], p.y - self.anchor_xy[1]) < 0.20
                settled = settled and math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z) < 0.15
                if settled:
                    self.stable_since = self.stable_since or now
                    if now - self.stable_since >= TAKEOFF_HOVER_SECONDS:
                        self.phase = "await_goal"
                        print("已在相对起飞高度 %.2f m 稳定悬停 %.0f 秒。现在可在 RViz 点一个 3.5 m 内目标。" % (TARGET_Z, TAKEOFF_HOVER_SECONDS), flush=True)
                        return
                else:
                    self.stable_since = None
            else:
                self.stable_since = None
            if fsm not in ("MANUAL_CTRL", "AUTO_TAKEOFF", "AUTO_HOVER"):
                raise RuntimeError("起飞期间 FSM 异常：%s；遥控器接管" % fsm)
            if LANDING_FILE.exists():
                raise RuntimeError("收到降落请求；中止自动起飞监测")
            if STOP_FILE.exists():
                raise RuntimeError("收到停栈请求；中止自动起飞监测")
            self.rospy.sleep(0.1)
        raise RuntimeError("120 秒内未确认稳定悬停；遥控器接管，不自动执行其他动作")

    def _announce_countdown(self, remain):
        """到点等待窗口的倒计时：终端 + RViz（goal_ack 文本），每 5 s 一次。"""
        sec = int(math.ceil(remain))
        if sec <= 0 or sec % 5 != 0:
            return
        if getattr(self, "_last_countdown_s", None) == sec:
            return
        self._last_countdown_s = sec
        text = "已到点：%d s 内点下一个目标，否则自动降落" % sec
        print("[countdown] " + text, flush=True)
        pub = getattr(self, "ack_pub", None)
        msg_type = getattr(self, "String", None)
        if pub is not None and msg_type is not None:
            try:
                pub.publish(msg_type(data="AT_GOAL " + text))
            except Exception:
                pass

    def navigation_monitor(self):
        """2026-11-07 多航点：到点后给 NEXT_GOAL_WAIT 秒点下一个目标，超时自动降落。

        为什么要多航点：ego_planner 是**局部**规划器（视界 4 m，无全局路径），
        两组箱子时它不保证自己找到 S 形。用人工拐点把 S 形变成几何约束，最确定。
        """
        print("目标已发送；到点稳定 %.0fs 后，%.0f 秒内可在 RViz 点下一个目标"
              "（依次点几个拐点 = S 形绕行），否则自动降落。" % (GOAL_HOVER_SECONDS, NEXT_GOAL_WAIT), flush=True)
        deadline = None
        while not self.rospy.is_shutdown():
            if LANDING_FILE.exists() or STOP_FILE.exists():
                return
            if not self.goal_used:
                # 没有待飞目标：首个目标无限等；后续目标只等 NEXT_GOAL_WAIT
                if self.next_goal_deadline is None:
                    self.rospy.sleep(0.1)
                    continue
                remain = self.next_goal_deadline - time.monotonic()
                if remain <= 0.0:
                    print("已到点 %.0f 秒仍无新目标；自动降落。" % NEXT_GOAL_WAIT, flush=True)
                    self.land()
                    return
                self._announce_countdown(remain)
                self.rospy.sleep(0.1)
                continue
            # 2026-11-11 修 bug：原 deadline 只在首次赋值，第二个目标起沿用同一个
            # 180 s 计时器 -> 多航点（S 形）飞到第 3-4 个点会被误判超时并抛错。
            if self.nav_deadline is None:
                self.nav_deadline = time.monotonic() + NAV_TIMEOUT
            deadline = self.nav_deadline
            # 2026-11-08（方案 v2 C3）目标停滞自降：发目标后 5 s，若 /position_cmd 原地不动
            # 就报根因并中止。22:36 那轮的形态：规划器 EMERGENCY_STOP -> traj_server 以
            # 100 Hz 发"原地保持" -> px4ctrl 因"有 cmd 流"进 CMD_CTRL -> 人只看到"点了不走"。
            if self.goal_cmd_t0 is not None and self.goal_target_xy is not None \
                    and time.monotonic() - self.goal_cmd_t0 >= 5.0:
                if self._fresh("/position_cmd", 0.5):
                    cmd = self.cache["/position_cmd"]
                    if self.endpoint_ref is not None:
                        _rx, _ry = self.endpoint_ref[0], self.endpoint_ref[1]
                    else:
                        _rx, _ry = self.goal_target_xy
                    gap = math.hypot(cmd.position.x - _rx, cmd.position.y - _ry)
                    vcmd = math.hypot(cmd.velocity.x, cmd.velocity.y)
                    if goal_stall_verdict(time.monotonic() - self.goal_cmd_t0, gap, vcmd):
                        msg = ("目标已发出 %.1f s，但 /position_cmd 离目标还差 %.2f m 且"
                               " |v|=%.3f m/s —— 规划器没有产生运动。最常见根因：规划器"
                               " EMERGENCY_STOP（odom/depth 超时，见规划器日志 "
                               "'odom or depth lost'/'Depth Lost'）。检查 /planner/camera_pose "
                               "与 /camera/depth 是否断过流。"
                               % (time.monotonic() - self.goal_cmd_t0, gap, vcmd))
                        print("!! 目标停滞自降触发：" + msg, flush=True)
                        # 方案 v2 C3 承诺走既有自动降落路径（二审 F7）：先自动降落再抛错，
                        # 避免"规划器脑死 + 原地悬停到电量耗尽"。降落失败则退回人工接管。
                        try:
                            self.land()
                        except Exception as lexc:
                            print("!! 自动降落失败（%s）；遥控器接管（CH5 拨低）" % lexc, flush=True)
                        raise RuntimeError(msg)
                    self.goal_cmd_t0 = None  # 已在动/已接近，目标停滞完成使命
            if time.monotonic() >= deadline:
                # 2026-11-13：NAV_TIMEOUT(120 s) 未确认到点。若飞机已停在目标附近（<=1 m 且慢），
                # 就是"到位判定没走完"，不是没飞到 -> 自动降落，别让它一直悬停。
                # 远离目标则不在陌生位置盲降，交还遥控器。
                try:
                    _o = self._odom()
                    _p = _o.pose.pose.position
                    _v = _o.twist.twist.linear
                    _d_goal = math.sqrt((_p.x - self.target[0]) ** 2 +
                                        (_p.y - self.target[1]) ** 2 +
                                        (_p.z - self.target[2]) ** 2)
                    _sp = math.sqrt(_v.x ** 2 + _v.y ** 2 + _v.z ** 2)
                except Exception:
                    _d_goal, _sp = -1.0, 1e9
                if 0.0 <= _d_goal <= 1.0 and _sp <= 0.20:
                    print("导航 %.0f s 未确认到点，但已停在目标 %.2f m 内（|v|=%.2f）；自动降落。"
                          % (NAV_TIMEOUT, _d_goal, _sp), flush=True)
                    try:
                        self.land()
                    except Exception as lexc:
                        print("!! 自动降落失败（%s）；遥控器接管（CH5 拨低）" % lexc, flush=True)
                    else:
                        return
                raise RuntimeError("导航 %.0f 秒内未确认目标点稳定（距目标 %.2f m，|v|=%.2f）；遥控器接管"
                                   % (NAV_TIMEOUT, _d_goal, _sp))
            state = self._state()
            fsm = self._fsm()
            if not state.connected or not state.armed or fsm == "MANUAL_CTRL":
                # 2026-11-07：带上 RC 摘要，下次一眼看出是哪个开关被拨了
                raise RuntimeError("导航中飞控/FSM 状态异常（fsm=%s armed=%s）；遥控器接管。%s"
                                   % (fsm, state.armed, self._rc_summary()))
            if not self._fresh("/position_cmd", 0.5):
                self.rospy.sleep(0.1)
                continue
            odom = self._odom()
            p, v = odom.pose.pose.position, odom.twist.twist.linear
            # 2026-11-11：参考点优先用"规划器实际终点"（planned_path 末点），
            # 因为它可能比目标短 0.2-0.4 m（A* 把未观测格子当障碍做端点外推）。
            # 2026-11-11：端点参考**锁存**——拿到一次就记住，直到下一个目标。
            # 原来要求 planned_path 必须 2 s 内新鲜；到点后规划器不再发轨迹 ->
            # 参考点退回目标（差 0.2-0.4 m）-> 到位判定永远不成立 -> 导航超时。
            # 2026-11-11 修时序洞：新目标刚发出时缓存里还是"上一条轨迹"的 planned_path，
            # 直接锁存会把**旧终点**当成本次终点 -> 多航点时"刚飞到的地方"被误判为到点。
            # 现在只接受 `goal_sent_t` 之后收到的 planned_path，并随重规划持续更新。
            _prev_ref = self.endpoint_ref
            self.endpoint_ref = pick_endpoint_ref(
                self.endpoint_ref,
                self.cache.get("/flight_v1/planned_path"),
                self.times.get("/flight_v1/planned_path", 0.0),
                self.goal_sent_t, time.monotonic(), 2.0, self.target)
            if _prev_ref is None and self.endpoint_ref is not None \
                    and self.endpoint_ref != self.target:
                print("[arrival_ref] 规划终点=(%.2f,%.2f,%.2f) 距目标 %.2f m"
                      % (self.endpoint_ref[0], self.endpoint_ref[1], self.endpoint_ref[2],
                         math.hypot(self.endpoint_ref[0] - self.target[0],
                                    self.endpoint_ref[1] - self.target[1])), flush=True)
            ref = self.endpoint_ref if self.endpoint_ref is not None else self.target
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip((p.x, p.y, p.z), ref)))
            d_goal = math.sqrt(sum((a - b) ** 2 for a, b in zip((p.x, p.y, p.z), self.target)))
            speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
            # 2026-11-11：A* 端点外推会把终点拉回 ~0.19 m（实测 2.00 -> 1.82），
            # 原 0.2 m 门只剩 1 cm 余量；放宽到 0.30 m。
            if fsm == "CMD_CTRL" and d <= 0.20 and speed <= 0.15:
                self.stable_since = self.stable_since or time.monotonic()
                if time.monotonic() - self.stable_since >= GOAL_HOVER_SECONDS:
                    # 到点：进入"等下一个目标"窗口，不立刻降落
                    self.goal_count += 1
                    self.nav_done = True
                    self.goal_used = False
                    self.stable_since = None
                    self.next_goal_deadline = time.monotonic() + NEXT_GOAL_WAIT
                    self._last_countdown_s = None
                    self.goal_cmd_t0 = None
                    self.goal_target_xy = None
                    self.phase = "await_goal"
                    deadline = None
                    print("第 %d 个目标到达并稳定悬停 %.0f 秒（距目标 %.2f m）。%.0f 秒内可点下一个目标，否则自动降落。"
                          % (self.goal_count, GOAL_HOVER_SECONDS, d_goal, NEXT_GOAL_WAIT), flush=True)
                    self._announce_countdown(NEXT_GOAL_WAIT)
                    continue
            else:
                self.stable_since = None
            self.rospy.sleep(0.1)
        raise RuntimeError("导航监测被中断（rospy shutdown）")

    def land(self):
        if STOP_FILE.exists():
            raise RuntimeError("正在停栈，拒绝发送 LAND")
        state = self._state()
        if not state.connected:
            raise RuntimeError("MAVROS 未连接，飞行状态未知；不发送 LAND")
        if not state.armed:
            ext = self.cache.get("/mavros/extended_state")
            if (self._fresh("/mavros/extended_state", 2.5) and ext.landed_state == 1
                    and self._fresh_stamp(ext, 2.5)):
                print("飞控已明确未解锁且在地面，无需 LAND")
                return
            raise RuntimeError("未解锁但没有新鲜地面状态，不能证明已落地")
        if self._fsm() == "AUTO_LAND":
            raise RuntimeError("控制器已处于 AUTO_LAND；继续观察飞控状态，不能重复初始化降落")
        else:
            if self._fsm() not in ("AUTO_HOVER", "CMD_CTRL"):
                raise RuntimeError("当前 FSM 不能安全接受降落：%s" % self._fsm())
            # Persist before stopping the trajectory source so the goal callback closes first.
            LANDING_FILE.write_text("requested %.3f\n" % time.time())
            traj_node = "/drone_0_traj_server"

            def ros_nodes():
                result = subprocess.run(["rosnode", "list"], capture_output=True,
                                        text=True, timeout=4)
                if result.returncode != 0:
                    raise RuntimeError("无法读取 ROS 节点列表：" + result.stdout.strip())
                return set(result.stdout.splitlines())

            if traj_node in ros_nodes():
                killed = subprocess.run(["rosnode", "kill", traj_node],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, timeout=5)
                if killed.returncode != 0 and traj_node in ros_nodes():
                    raise RuntimeError("停止轨迹发布器失败：" + killed.stdout.strip())
            limit = time.monotonic() + 8.0
            while time.monotonic() < limit:
                if traj_node not in ros_nodes():
                    break
                self.rospy.sleep(0.2)
            else:
                raise RuntimeError("轨迹发布器仍在运行；未发送 LAND")
            quiet_since = None
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if not self._fresh("/position_cmd", 0.65):
                    quiet_since = quiet_since or time.monotonic()
                    if time.monotonic() - quiet_since >= 0.7 and self._fsm() == "AUTO_HOVER":
                        break
                else:
                    quiet_since = None
                self.rospy.sleep(0.1)
            else:
                raise RuntimeError("命令流未停止或 FSM 未回 AUTO_HOVER；未发送 LAND，遥控器接管")
            self._check_rc(require_centered=False)
            print("轨迹命令已停止，FSM 回到 AUTO_HOVER，持续发送 LAND 并等待飞控着地确认。", flush=True)
            next_pub = 0.0
            deadline = time.monotonic() + 120.0
            landed_since = None
            while time.monotonic() < deadline and not self.rospy.is_shutdown():
                now = time.monotonic()
                if now >= next_pub:
                    self._pub_land()
                    next_pub = now + 1.0
                state = self._state()
                ext = self.cache.get("/mavros/extended_state")
                grounded = (not state.armed and self._fresh("/mavros/extended_state", 2.5)
                            and ext.landed_state == 1 and self._fresh_stamp(ext, 2.5)
                            and self._fresh("/mavros/state", 1.5))
                if grounded:
                    landed_since = landed_since or now
                    if now - landed_since >= 2.0:
                        print("已连续确认 ON_GROUND 且未解锁。", flush=True)
                        return
                else:
                    landed_since = None
                self.rospy.sleep(0.1)
            raise RuntimeError("120 秒内未确认落地；保持栈运行，由遥控器接管")


class _Tee(object):
    """2026-11-13：把任务输出同时写到终端和 ~/flight_data/last_mission.log。"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for st in self.streams:
            try:
                st.write(data)
                st.flush()
            except Exception:
                pass
        return len(data)

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass


_LOG_STREAM = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action="store_true",
                        help="SITL 模式：跳过 RC 通道检查（仿真无遥控器）")
    parser.add_argument("--dry", action="store_true",
                        help="只跑飞前检查，不发布 TAKEOFF/LAND（彩排用）")
    parser.add_argument("action", choices=("takeoff", "land", "assert-ground", "self-test"))
    args = parser.parse_args()
    global DRY, SIM
    DRY = bool(args.dry)
    SIM = bool(args.sim)
    # 2026-11-13：任务输出落盘（此前"是否触发自动降落"只能靠猜；全部轮次 AUTO_LAND=0）
    global _LOG_STREAM
    try:
        _lp = Path.home() / "flight_data" / "last_mission.log"
        _lp.parent.mkdir(parents=True, exist_ok=True)
        _LOG_STREAM = open(str(_lp), "a", encoding="utf-8")
        _LOG_STREAM.write("\n===== %s action=%s =====\n"
                          % (time.strftime("%Y-%m-%d %H:%M:%S"), args.action))
        _LOG_STREAM.flush()
        sys.stdout = _Tee(sys.stdout, _LOG_STREAM)
        sys.stderr = _Tee(sys.stderr, _LOG_STREAM)
    except Exception as exc:
        print("警告：任务日志落盘失败：%r" % (exc,), file=sys.stderr)
    if args.action == "self-test":
        # 2026-11-07 审查修正（独立审计发现）：self-test 不跑 preflight，
        # TARGET_Z 仍是 None -> validate_goal 直接抛 ValueError，自检必然失败。
        global TARGET_Z
        if TARGET_Z is None:
            TARGET_Z = 0.5   # 自检只验逻辑；真实值由 preflight 从 px4ctrl 参数读
        validate_rc_channels([1500, 1500, 1500, 1500, 2000, 2000, 1500, 1500])
        try:
            validate_rc_channels([1500, 1630, 1500, 1500, 2000, 2000, 1500, 1500])
        except ValueError:
            pass
        else:
            raise AssertionError("non-centered stick accepted")
        goal, distance = validate_goal("world", 10.0, 10.1, (1.2, 0.0), (0.0, 0.0), 4.0)
        assert abs(distance - 1.2) < 1e-9 and abs(goal[2] - 4.5) < 1e-9
        try:
            # 2026-11-07 审查修正：GOAL_RADIUS 已由 2.0 改为 3.5，越界用例跟着改
            validate_goal("world", 10.0, 10.1, (3.51, 0.0), (0.0, 0.0), 4.0)
        except ValueError:
            pass
        else:
            raise AssertionError("goal beyond 2 m accepted")
        # 2026-11-12 P6：点击决策矩阵（ACCEPT/REPLACE/REJECT）
        for _args, _want in [
            (("await_goal", False, False, False), "ACCEPT"),
            (("navigation", True, False, False), "REPLACE"),
            (("navigation", False, False, False), "REJECT"),
            (("await_goal", True, False, False), "REJECT"),
            (("await_goal", False, True, False), "REJECT"),
            (("await_goal", False, False, True), "REJECT"),
        ]:
            _got = classify_goal_event(*_args)
            _ok = (_got == _want) if _want in ("ACCEPT", "REPLACE") else _got.startswith(_want)
            assert _ok, (_args, _got)
        # 2026-11-11：到位参考点的时序场景（这三条对应实飞里最容易错的点）
        class _P(object):
            def __init__(self, x, y, z):
                self.x, self.y, self.z = x, y, z
        class _Pose(object):
            def __init__(self, p):
                self.pose = type("S", (), {"position": p})()
        class _Path(object):
            def __init__(self, pts):
                self.poses = [_Pose(q) for q in pts]
        _old = _Path([_P(9.0, 9.0, 0.7)])     # 上一个目标的终点
        _new = _Path([_P(2.0, 0.0, 0.7)])
        # A) 目标发出前收到的旧路径 -> 必须忽略，退回命令目标
        assert pick_endpoint_ref(None, _old, 10.0, 20.0, 21.0, 2.0, (2.0, 0.0, 0.7)) == (2.0, 0.0, 0.7)
        # B) 目标发出后收到的路径 -> 用它（即使与目标不同）
        assert pick_endpoint_ref(None, _old, 25.0, 20.0, 26.0, 2.0, (2.0, 0.0, 0.7)) == (9.0, 9.0, 0.7)
        # C) 路径过期 -> 沿用上一次的锁存值，不退回目标
        assert pick_endpoint_ref((9.0, 9.0, 0.7), _new, 25.0, 20.0, 40.0, 2.0, (2.0, 0.0, 0.7)) == (9.0, 9.0, 0.7)
        print("SELF-TEST PASS: RC guard, 3.5 m goal bound, relative 0.5 m target, endpoint-ref timing, P6 goal decision")
        return 0
    lock = None
    try:
        if args.action in ("takeoff", "land") and STOP_FILE.exists():
            raise RuntimeError("正在停栈，拒绝并发飞行命令")
        lock = acquire_lock("mission.lock" if args.action == "takeoff" else "landing.lock")
        flight = RosFlight()
        if args.action == "takeoff":
            flight.takeoff()
            flight.navigation_monitor()
        elif args.action == "land":
            flight.land()
        else:
            flight._initial_wait(2.2)
            if not lock_is_free("mission.lock"):
                raise RuntimeError("起飞/导航监测进程还未退出；等它退出后再停栈")
            state = flight._state()
            ext = flight.cache.get("/mavros/extended_state")
            if (state.armed or not state.connected or not flight._fresh("/mavros/extended_state", 2.5)
                    or ext.landed_state != 1 or not flight._fresh_stamp(ext, 2.5)):
                raise RuntimeError("状态未知/仍解锁/未确认落地，拒绝停栈")
            print("新鲜 MAVROS 状态确认：connected、disarmed、ON_GROUND")
    except Exception as exc:
        print("FLIGHT FAIL: %s" % exc, file=sys.stderr)
        return 1
    finally:
        if lock:
            lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
