#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RViz 预期轨迹回传（2026-11-08，用户令：选点后要能看到预期轨迹）。

三路输出（都是可视件，不参与控制）：
  /flight_v1/planned_path    nav_msgs/Path —— 规划器刚发的那条 B 样条（真值，逐点求值）
  /flight_v1/executed_trail  nav_msgs/Path —— /position_cmd 的实际流（跟踪轨迹的尾巴）
  /flight_v1/goal_marker     visualization_msgs/Marker —— 你点的目标点

为什么要单独一个节点：规划器只发 `traj_utils/Bspline`（自定义消息）和 `DataDisp`，
RViz 的 Path 显示吃不了；这个节点做一次 B 样条求值 + 类型转换即可。
"""
import os
import sys

import rospy
from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Path
from visualization_msgs.msg import Marker

PATH_PLAN = "/flight_v1/planned_path"
PATH_TRAIL = "/flight_v1/executed_trail"
GOAL_MARK = "/flight_v1/goal_marker"
BSPLINE = "/drone_0_planning/bspline"
CMD = "/position_cmd"
GOAL = "/flight_v1/goal_gate"

TRAIL_MAX = 3000
SAMPLE_N = 160


def de_boor(u, pts, p, t):
    """求 B 样条在参数 t 处的点（u=节点向量, pts=控制点, p=次数）。"""
    n = len(pts) - 1
    if t <= u[p]:
        k = p
    elif t >= u[n + 1]:
        k = n
    else:
        k = p
        for i in range(p, n + 1):
            if u[i] <= t < u[i + 1]:
                k = i
                break
    d = [[pts[j + k - p].x, pts[j + k - p].y, pts[j + k - p].z] for j in range(p + 1)]
    for r in range(1, p + 1):
        for j in range(p, r - 1, -1):
            den = u[j + 1 + k - r] - u[j + k - p]
            a = 0.0 if abs(den) < 1e-12 else (t - u[j + k - p]) / den
            for i in range(3):
                d[j][i] = (1.0 - a) * d[j - 1][i] + a * d[j][i]
    return d[p]


def main():
    from traj_utils.msg import Bspline
    from quadrotor_msgs.msg import PositionCommand
    rospy.init_node("planned_path_pub")
    pub_plan = rospy.Publisher(PATH_PLAN, Path, queue_size=2, latch=True)
    pub_trail = rospy.Publisher(PATH_TRAIL, Path, queue_size=2, latch=True)
    pub_goal = rospy.Publisher(GOAL_MARK, Marker, queue_size=2, latch=True)
    state = {"plan": None, "trail": [], "goal": None, "last_traj_id": None}
    # 2026-11-11（用户问 1）：节点启动先清一次，避免 RViz 挂着上一个实例的 latch 轨迹
    empty0 = Path()
    empty0.header.frame_id = "world"
    empty0.header.stamp = rospy.Time.now()
    pub_plan.publish(empty0)
    pub_trail.publish(empty0)

    def on_bspline(msg):
        try:
            # 2026-11-11（用户问 1）：规划器重启 -> traj_id 归零，必须清空上一轮轨迹。
            # 两个 publisher 是 latch=True + 1 Hz 重发，不清的话 RViz 永远显示旧轨迹；
            # 而 VINS 重启后世界原点已重锚，旧轨迹连坐标都不对了。
            tid = int(msg.traj_id)
            if state["last_traj_id"] is not None and tid <= state["last_traj_id"]:
                state["plan"] = None
                state["trail"] = []
                empty = Path()
                empty.header.frame_id = "world"
                empty.header.stamp = rospy.Time.now()
                pub_plan.publish(empty)
                pub_trail.publish(empty)
                rospy.loginfo("[path] traj_id %d -> %d：规划器重启，清空上一轮轨迹"
                              % (state["last_traj_id"], tid))
            state["last_traj_id"] = tid
            u = list(msg.knots)
            pts = list(msg.pos_pts)   # 真字段名是 pos_pts（rosmsg show traj_utils/Bspline）
            p = int(msg.order)   # traj_server 就是把 msg.order 当次数传给 UniformBspline
            if len(pts) < p + 1 or len(u) < len(pts) + p + 1:   # 次数 p 最少要 p+1 个控制点
                return
            # 有效参数域：[u_p, u_{n+1}]（n=控制点数-1）。
            # 单位测试实测：EGO 发来的 knots 是归一化的，u_{n+1} 正好是 1.0；
            # 早先误用 u_{m-p} 只采到 2/3 条曲线（终点短 0.38 m），已改。
            t0 = u[p]
            t1 = u[min(len(u) - 1, len(pts))]
            if not (t1 > t0):
                return
            path = Path()
            path.header.frame_id = "world"
            path.header.stamp = rospy.Time.now()
            for i in range(SAMPLE_N + 1):
                t = t0 + (t1 - t0) * i / SAMPLE_N
                x, y, z = de_boor(u, pts, p, t)
                ps = PoseStamped()
                ps.header = path.header
                ps.pose.position = Point(x, y, z)
                ps.pose.orientation.w = 1.0
                path.poses.append(ps)
            state["plan"] = path
            pub_plan.publish(path)
            rospy.loginfo_throttle(5.0, "[path] 新轨迹 %d 点 (dur %.2fs, ctrl %d)"
                                   % (len(path.poses), t1 - t0, len(pts)))
        except Exception as exc:
            rospy.logwarn_throttle(10.0, "[path] B样条求值失败: %r" % (exc,))

    def on_cmd(msg):
        p = msg.position
        state["trail"].append((p.x, p.y, p.z))
        if len(state["trail"]) > TRAIL_MAX:
            del state["trail"][: len(state["trail"]) - TRAIL_MAX]

    def on_goal(msg):
        state["goal"] = (msg.pose.position.x, msg.pose.position.y, msg.pose.position.z)

    def build_trail():
        path = Path()
        path.header.frame_id = "world"
        path.header.stamp = rospy.Time.now()
        for (x, y, z) in state["trail"]:
            ps = PoseStamped()
            ps.header = path.header
            ps.pose.position = Point(x, y, z)
            ps.pose.orientation.w = 1.0
            path.poses.append(ps)
        return path

    def build_goal():
        m = Marker()
        m.header.frame_id = "world"
        m.header.stamp = rospy.Time.now()
        m.ns = "flight_v1_goal"
        m.id = 0
        m.type = Marker.SPHERE
        m.action = Marker.ADD
        m.pose.position = Point(*state["goal"])
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.18
        m.color.r, m.color.g, m.color.b, m.color.a = 0.1, 1.0, 0.2, 0.9
        return m

    rospy.Subscriber(BSPLINE, Bspline, on_bspline)
    rospy.Subscriber(CMD, PositionCommand, on_cmd)
    rospy.Subscriber(GOAL, PoseStamped, on_goal)

    rate = rospy.Rate(1.0)
    while not rospy.is_shutdown():
        if state["trail"]:
            pub_trail.publish(build_trail())
        if state["plan"] is not None:
            pub_plan.publish(state["plan"])
        if state["goal"] is not None:
            pub_goal.publish(build_goal())
        rate.sleep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
