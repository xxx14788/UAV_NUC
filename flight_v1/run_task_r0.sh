#!/bin/bash
# R0 自动任务包装：source ROS Noetic / catkin 后运行 task_r0.py。
set +u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
exec python3 "$HOME/catkin_ws/flight_v1/task_r0.py" "$@"
