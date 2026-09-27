#!/usr/bin/env bash
## 连接 PX4 SITL 的 onboard/offboard MAVLink 实例。
# fcu_url 目标端口=14580:PX4 v1.17 px4-rc.mavlink 的 offboard 实例监听 14580(-u 14580
# -o 14540,2018-09 7f016b5fd4 起;14557 是更老约定的死端口)。旧值 14557 无人监听,
# 仅靠 libmavconn UDP 的源地址覆盖学习(mavconn udp.cpp async_receive_from 的
# in-out endpoint)在收到 PX4 首包后纠正——首包前的所有上行全部进黑洞。
set -u
source /opt/ros/noetic/setup.bash
exec roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580

