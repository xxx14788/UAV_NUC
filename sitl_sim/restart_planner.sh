#!/usr/bin/env bash
# 冷启动 planner（run_planner_sitl.launch）。
# 用途：每轮飞行前冷启动 traj_server——轨迹执行过后它会持续发布 /position_cmd，
# 而 px4ctrl 安全检查拒绝"起飞前已有 cmd 输入"（2026-09-26 A4 踩坑）。
# 依赖 kill_planner_all.sh 做可靠清场（comm 截断坑见其注释）。
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
bash "$(dirname "$0")/kill_planner_all.sh" >/dev/null 2>&1
sleep 1
exec roslaunch ego_planner run_planner_sitl.launch
