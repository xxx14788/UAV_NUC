#!/usr/bin/env python3
# t1_goal_trace.py — 任务书 v11.17 §1.1d 发作自动留痕（每轮常开,轻量）
# 对表面: bag 侧 /move_base_simple/goal 发布戳 vs planner 侧状态变化代理戳
#   (/position_cmd 首帧=首轨迹生成即 FSM 离开 WAIT_TARGET 的可观测面)
#   + planner.log FSM 心跳在场性/状态转移行数(文本面,无时间戳,如实注记)
# 输出: <round_dir>/goal_trace.tsv  (tab 分分;一行一事件+汇总行)
# 用法: python3 t1_goal_trace.py <round_dir>   (需 ROS env;无 bag=如实登记后退出 0)
import sys, os, subprocess
rd = sys.argv[1]
bag = os.path.join(rd, "flight.bag")
plog = os.path.join(rd, "planner.log")
out = os.path.join(rd, "goal_trace.tsv")
rows = []
def note(kind, t=None, extra=""):
    rows.append(("\t".join([kind, ("" if t is None else "%.3f" % t), extra])).rstrip())
if not os.path.exists(bag):
    note("NO_BAG", extra="flight.bag 缺失=留痕面如实登记")
    open(out, "w").write("\n".join(rows) + "\n"); sys.exit(0)
import rosbag
goals, pos_first, pos_n = [], None, 0
with rosbag.Bag(bag) as b:
    for tp, msg, t in b.read_messages(topics=["/move_base_simple/goal", "/position_cmd"]):
        ts = msg.header.stamp.to_sec() if msg._has_header and msg.header.stamp.to_sec() > 0 else t.to_sec()
        if tp == "/move_base_simple/goal":
            p = msg.pose.position
            goals.append((ts, p.x, p.y, p.z))
        else:
            pos_n += 1
            if pos_first is None: pos_first = ts
for i, (ts, x, y, z) in enumerate(goals):
    note("GOAL", ts, "seq=%d xyz=(%.2f,%.2f,%.2f)" % (i, x, y, z))
note("POSCMD_FIRST", pos_first, "n_poscmd=%d" % pos_n)
if pos_first is not None and goals:
    note("LAG_FIRSTGOAL_TO_FIRSTPOSCMD", pos_first - goals[0][0], "seconds(sim)")
# planner.log 文本面(心跳在场性=事件循环存活取证,任务书 1.1 取证结论联动)
if os.path.exists(plog):
    s = open(plog, errors="replace").read()
    note("FSM_HEARTBEAT_LINES", extra=str(s.count("[FSM]: state:")))
    note("FSM_LEFT_WAIT_TARGET", extra=str(s.count("from WAIT_TARGET to")))
    note("FSM_INIT_TO_WAIT", extra=str(s.count("from INIT to WAIT_TARGET")))
    note("PLANNER_LOG_BYTES", extra=str(os.path.getsize(plog)))
else:
    note("NO_PLANNER_LOG", extra="如实登记")
open(out, "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
