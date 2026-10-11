#!/usr/bin/env bash
## 连接 PX4 SITL 的 onboard/offboard MAVLink 实例。
# fcu_url 目标端口=14580:PX4 v1.17 px4-rc.mavlink 的 offboard 实例监听 14580(-u 14580
# -o 14540,2018-09 7f016b5fd4 起;14557 是更老约定的死端口)。旧值 14557 无人监听,
# 仅靠 libmavconn UDP 的源地址覆盖学习(mavconn udp.cpp async_receive_from 的
# in-out endpoint)在收到 PX4 首包后纠正——首包前的所有上行全部进黑洞。
# v2 (2026-10-11 收官册 E8P 毒域修复): mavros_nomission.launch 包装——
# mission 插件入黑名单(硬编码全局话题 /move_base_simple/goal=libmavros.so 二进制实证,
# 与 harness goal 同名冲突; PX4 任务消息触发时发 UTM 帧毒 goal[六轮七帧 642719.x,
# 4671811.x 实证]=E8P/S8P 毒域根因)。本栈五件套零使用 /mavros/mission/*。
# 注: roslaunch CLI 空值 gcs_url:= 不算 set → 包装 launch 内 value="" 传递(实测坑)。
# 恢复旧行为: roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580
set -u
source /opt/ros/noetic/setup.bash
exec roslaunch "$HOME/sitl_sim/mavros_nomission.launch"
