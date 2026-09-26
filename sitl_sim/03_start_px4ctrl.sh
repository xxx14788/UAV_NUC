#!/usr/bin/env bash
# 启动 SITL 版 px4ctrl（用新建的 launch + yaml，不影响真机配置）。
set -u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译（先做 M2.0）"; exit 1; }
exec roslaunch px4ctrl run_ctrl_sitl.launch
