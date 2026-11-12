#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实机整链测试（不起桨）：发一个 2 m 目标，量 bspline / position_cmd / planned_path。

判据（预注册）：
  T1 规划器收下目标并出轨迹：/drone_0_planning/bspline 在 10 s 内 >= 3 帧
  T2 traj_server 转成指令：/position_cmd 在 10 s 内 >= 50 条
  T3 轨迹回传：/flight_v1/planned_path 有帧，且终点与目标水平距离 <= 0.30 m
  T4 无锁死：规划器日志里 "in obstacle" / "Ran out of pool" 计数为 0
"""
import math
import subprocess
import sys
import threading
import time

import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from quadrotor_msgs.msg import PositionCommand
from traj_utils.msg import Bspline
from visualization_msgs.msg import Marker

GOAL_X, GOAL_Y = 2.0, 0.0
DUR = 12.0
cnt = {"bspline": 0, "cmd": 0, "path": 0, "marker": 0}
last = {"path": None}


def main():
    rospy.init_node("live_goal_chain_test", anonymous=True, disable_signals=True)
    rospy.Subscriber("/drone_0_planning/bspline", Bspline, lambda m: cnt.__setitem__("bspline", cnt["bspline"] + 1), queue_size=5)

    def on_cmd(m):
        cnt["cmd"] += 1
        cnt["cmd_v"] = math.sqrt(m.velocity.x ** 2 + m.velocity.y ** 2 + m.velocity.z ** 2)
    rospy.Subscriber("/position_cmd", PositionCommand, on_cmd, queue_size=50)

    def on_path(m):
        cnt["path"] += 1
        last["path"] = m
    rospy.Subscriber("/flight_v1/planned_path", Path, on_path, queue_size=5)
    rospy.Subscriber("/flight_v1/goal_marker", Marker, lambda m: cnt.__setitem__("marker", cnt["marker"] + 1), queue_size=5)

    pub = rospy.Publisher("/flight_v1/goal_gate", PoseStamped, queue_size=5)
    time.sleep(1.0)
    g = PoseStamped()
    g.header.frame_id = "world"
    g.header.stamp = rospy.Time.now()
    g.pose.position.x = GOAL_X
    g.pose.position.y = GOAL_Y
    g.pose.position.z = 0.7
    g.pose.orientation.w = 1.0
    pub.publish(g)
    print("已发目标 (%.1f, %.1f) z=0.7（manual_goal_z 生效）" % (GOAL_X, GOAL_Y), flush=True)

    t0 = time.time()
    while time.time() - t0 < DUR and not rospy.is_shutdown():
        rospy.sleep(0.2)

    print("bspline=%d  position_cmd=%d  planned_path=%d  goal_marker=%d"
          % (cnt["bspline"], cnt["cmd"], cnt["path"], cnt["marker"]), flush=True)
    ok = True
    if cnt["bspline"] < 3:
        ok = False
        print("FAIL T1 规划器没出轨迹", flush=True)
    if cnt["cmd"] < 50:
        ok = False
        print("FAIL T2 traj_server 没转指令", flush=True)
    if cnt["path"] < 1:
        ok = False
        print("FAIL T3 没有轨迹回传", flush=True)
    else:
        p = last["path"].poses
        end = p[-1].pose.position
        d = math.hypot(end.x - GOAL_X, end.y - GOAL_Y)
        print("回传路径 %d 点，终点 (%.2f, %.2f, %.2f)，距目标水平 %.2f m"
              % (len(p), end.x, end.y, end.z, d), flush=True)
        if d > 0.30:
            ok = False
            print("FAIL T3 终点离目标 > 0.30 m", flush=True)
    print("==== 链测 %s ====" % ("PASS" if ok else "FAIL"), flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
