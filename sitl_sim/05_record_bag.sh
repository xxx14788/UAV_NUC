#!/usr/bin/env bash
# 录制一次完整飞行（起飞 → 悬停 → 降落）的 ROS bag。
# ★ 必须在起飞前启动；降落 disarm 后由 Ctrl-C 停止。
set -u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

BAG_DIR="$HOME/sitl_sim/bags"
mkdir -p "$BAG_DIR"
BAG="$BAG_DIR/flight_$(date +%F_%H%M%S).bag"

echo "录制到：$BAG"
echo "起飞前启动，降落完成后按 Ctrl-C 停止。"

exec rosbag record -O "$BAG" \
     /debugPx4ctrl \
     /px4ctrl/takeoff_land \
     /mavros/state \
     /mavros/extended_state \
     /mavros/local_position/odom \
     /mavros/local_position/velocity_local \
     /mavros/imu/data \
     /mavros/setpoint_raw/attitude \
     /mavros/setpoint_raw/local \
     /mavros/battery \
     /gazebo/model_states \
     /rosout
