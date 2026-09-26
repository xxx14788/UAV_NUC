#!/usr/bin/env bash
# 重启 planner（run_planner_sitl.launch）。
# 用途：每轮飞行前冷启动 traj_server——轨迹执行过后它会持续发布 /position_cmd，
# 而 px4ctrl 安全检查拒绝"起飞前已有 cmd 输入"（2026-09-26 A4 踩坑）。
# 用法: bash restart_planner.sh > log 2>&1 （或 nohup 后台）
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
# 杀旧：roslaunch 主进程 + 两个 node 可执行名
for p in $(pgrep -f "roslaunch.*run_planner_sitl"); do kill -9 "$p" 2>/dev/null; done
for p in $(pgrep -x ego_planner_node);           do kill -9 "$p" 2>/dev/null; done
for p in $(pgrep -x traj_server);                do kill -9 "$p" 2>/dev/null; done
sleep 2
exec roslaunch ego_planner run_planner_sitl.launch
