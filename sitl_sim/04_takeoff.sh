#!/usr/bin/env bash
# 触发 px4ctrl 自动起飞（等价于 Fast-Drone-250/shfiles/takeoff.sh）。
set -u
source /opt/ros/noetic/setup.bash
# ★ 必须 source catkin_ws：quadrotor_msgs/TakeoffLand 是本工作空间的消息类型，
#   只 source /opt/ros/noetic 会报 "Cannot load message class for [quadrotor_msgs/TakeoffLand]"
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }
exec rostopic pub -1 /px4ctrl/takeoff_land \
     quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1"
