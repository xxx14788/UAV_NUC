#!/usr/bin/env bash
# A7 仿真 VINS 传感器模型启动（iris_stereo_vins：深度+双目+IMU）。
# 前置与排障结论同 start_sitl_depth.sh（roscore、Xvfb:99、gazebo 库路径、
# gzserver wrapper、pxh stdin 五个坑）。
# 用法: nohup bash start_sitl_vins.sh > log 2>&1 &
#       SITL_WORLD=sitl_world_obstacles 可选避障 world
source /opt/ros/noetic/setup.bash   # 先 source 再 set -u（ROS 环境脚本依赖未定义变量）
source /usr/share/gazebo/setup.sh
set -u
export DISPLAY=:99
export VERBOSE_SIM=1
export PATH="$HOME/sitl_sim:$PATH"  # 前置 gzserver wrapper
export PX4_SITL_WORLD="${SITL_WORLD:-}"
cd "$HOME/PX4-Autopilot" || exit 1
sleep infinity | HEADLESS=1 exec make px4_sitl gazebo-classic_iris_stereo_vins
