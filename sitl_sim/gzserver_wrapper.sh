#!/usr/bin/env bash
# gzserver 包装：附加 ROS1 系统插件。
# noetic 的 gazebo_ros 传感器插件（openni_kinect 等）依赖全局 ros::init，
# 而 PX4 sitl_run.sh 只在 ROS2 下才注入 init 插件；经 PATH 前置本包装
# 生效，不修改 PX4 上游文件。
exec /usr/bin/gzserver -s libgazebo_ros_api_plugin.so "$@"
