#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROS 级集成测试：真实 RosFlight._apply_goal + ShapePilot，假 mavros/VINS。

自己起 roscore(:11316)；假话题提供 State/RC/FSM/odom；假 mission 在最终点把
phase 置 await_goal。断言：无 abort、pilot.done、goal_gate 收到 >10 个目标、
终点≈起飞点、RC/FSM/时戳校验真实走过（这正是“一直被遥控器接管”类错误的防线）。
"""
import math
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["ROS_MASTER_URI"] = "http://localhost:11316"
os.environ["ROS_HOSTNAME"] = "localhost"
import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State, RCIn
from nav_msgs.msg import Odometry
from std_msgs.msg import String

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "fsm", os.path.join(HERE, "flight_shape_mission.py"))
fsm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fsm)

TMP = tempfile.mkdtemp(prefix="shape_ros_")
fsm.LANDING_FILE = Path(TMP) / "landing.requested"
fsm.STOP_FILE = Path(TMP) / "stopping"
fsm.TARGET_Z = 0.70


class Sim(object):
    def __init__(self):
        self.pos = [0.0, 0.0, 0.70]
        self.vel = [0.0, 0.0, 0.0]
        self.target = (0.0, 0.0)
        self.goals = []

    def goal_cb(self, msg):
        self.target = (msg.pose.position.x, msg.pose.position.y)
        self.goals.append(self.target)

    def step(self):
        tx, ty = self.target
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        d = math.hypot(dx, dy)
        step = 0.05                     # 20 Hz -> 1.0 m/s（测试用；不追求跟踪精度）
        if d > 1e-9:
            f = min(1.0, step / d)
            self.pos[0] += dx * f
            self.pos[1] += dy * f
            self.vel[0] = dx / d * 1.0
            self.vel[1] = dy / d * 1.0
        else:
            self.vel[0] = self.vel[1] = 0.0
        return self.pos, self.vel


def wait_master(port=11316, timeout=15.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", port), 1.0)
            s.close()
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _pub(pub_state, pub_rc, pub_fsm, pub_odom, p, v):
    now = rospy.Time.now()
    st = State()
    st.header.stamp = now
    st.connected = True
    st.armed = True
    st.mode = "OFFBOARD"
    pub_state.publish(st)
    rc = RCIn()
    rc.header.stamp = now
    rc.channels = [1500, 1500, 1500, 1500, 2000, 1500, 1500, 1500]
    pub_rc.publish(rc)
    pub_fsm.publish(String(data="CMD_CTRL"))
    od = Odometry()
    od.header.stamp = now
    od.header.frame_id = "world"
    od.pose.pose.position.x, od.pose.pose.position.y, od.pose.pose.position.z = p
    od.twist.twist.linear.x, od.twist.twist.linear.y = v[0], v[1]
    pub_odom.publish(od)


def main():
    proc = subprocess.Popen(["roscore", "-p", "11316"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert wait_master(), "roscore 未起来"
        # 注意：RosFlight.__init__ 会 rospy.init_node；本进程不能再 init 第二次。
        flight = fsm.RosFlight()
        flight.anchor = 0.0
        flight.anchor_xy = (0.0, 0.0)
        flight.phase = "await_goal"
        flight.goal_used = False

        sim = Sim()
        pub_state = rospy.Publisher("/mavros/state", State, queue_size=10)
        pub_rc = rospy.Publisher("/mavros/rc/in", RCIn, queue_size=10)
        pub_fsm = rospy.Publisher("/debugPx4ctrl/fsm_state", String, queue_size=10)
        pub_odom = rospy.Publisher("/vins_estimator/imu_propagate", Odometry, queue_size=10)
        rospy.Subscriber("/flight_v1/goal_gate", PoseStamped, sim.goal_cb, queue_size=50)

        args = type("A", (), dict(
            shape="circle", speed=0.30, lookahead=0.60, min_step=0.10, laps=1,
            rate=10.0, circle_diameter=2.2, eight_length=4.0, eight_width=2.2,
            rotate_deg=0.0, obstacle_xy=(1.0, 0.0), obstacle_size=0.5,
            max_forward=4.3, max_lateral=1.6, min_clearance=0.30, max_time=60.0))()

        t0 = time.time()
        rate = rospy.Rate(20)
        # 先喂几帧话题，保证 _odom/_state/_fsm/_rc 新鲜
        for _ in range(10):
            p, v = sim.step()
            _pub(pub_state, pub_rc, pub_fsm, pub_odom, p, v)
            rate.sleep()
        pilot = fsm.ShapePilot(flight, args)
        pilot.start()
        while pilot.is_alive() and time.time() - t0 < 60.0 and not rospy.is_shutdown():
            p, v = sim.step()
            # 假 mission 到位判定：最终点=起飞点，且当前目标也是它
            if (math.hypot(p[0], p[1]) < 0.06
                    and math.hypot(sim.target[0], sim.target[1]) < 0.06):
                flight.phase = "await_goal"
                flight.goal_used = False
            _pub(pub_state, pub_rc, pub_fsm, pub_odom, p, v)
            rate.sleep()
        pilot.stop()
        assert not pilot.is_alive(), "pilot 未退出"
        assert flight.shape_abort_reason is None, "abort=%s" % flight.shape_abort_reason
        assert pilot.done, "pilot.done=False"
        assert len(sim.goals) > 10, "goal_gate 只收到 %d 个目标" % len(sim.goals)
        assert math.hypot(sim.target[0], sim.target[1]) < 0.06, "最终目标=%s" % (sim.target,)
        assert flight.unreachable_count == 0
        print("ROS INTEGRATION PASS: goals=%d max_lat=%.3f done=%s"
              % (len(sim.goals), pilot.max_lat, pilot.done))
        rospy.signal_shutdown("done")
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
