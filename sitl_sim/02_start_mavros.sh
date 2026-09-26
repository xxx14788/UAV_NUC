#!/usr/bin/env bash
# 连接 PX4 SITL 的 onboard/offboard MAVLink 实例。
set -u
source /opt/ros/noetic/setup.bash
exec roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557

