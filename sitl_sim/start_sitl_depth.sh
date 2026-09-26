#!/usr/bin/env bash
# 深度相机模型 SITL 启动（iris_depth_camera，带 ROS 相机话题输出）。
# 前置：roscore 已运行；Xvfb :99 已运行（Ogre 相机渲染需要 X）。
# 关键点（排障结论，2026-09-26）：
#   1) gzserver 需要 DISPLAY 指向可用 X（借 Xvfb），否则相机 sensor 不出帧
#   2) /usr/share/gazebo/setup.sh 把 gazebo-11/plugins 加入库搜索路径
#      （openni 插件依赖 libDepthCameraPlugin.so）
#   3) PATH 前置本目录的 gzserver wrapper，为 gzserver 附加 ROS1 系统插件
#      libgazebo_ros_api_plugin.so（noetic 传感器插件依赖全局 ros::init）
#   4) stdin 接 sleep infinity：PX4 pxh shell 读到 EOF 会无限刷屏撑爆日志
# 用法: nohup bash start_sitl_depth.sh > log 2>&1 &
source /opt/ros/noetic/setup.bash   # 先 source 再 set -u（ROS 环境脚本依赖未定义变量）
source /usr/share/gazebo/setup.sh
set -u
export DISPLAY=:99
export VERBOSE_SIM=1                # gzserver --verbose，保留渲染错误可见性
export PATH="$HOME/sitl_sim:$PATH"  # 前置 gzserver wrapper
cd "$HOME/PX4-Autopilot" || exit 1
sleep infinity | HEADLESS=1 exec make px4_sitl gazebo-classic_iris_depth_camera
