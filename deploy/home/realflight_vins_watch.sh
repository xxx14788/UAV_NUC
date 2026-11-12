#!/bin/bash
# VINS 实时盯盘 v1（只读；Ctrl+C 退出；地面/飞行中随时可开）
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
VL=$(ls -t ~/sitl_realmachine/vins_*.log ~/sitl_realmachine/*/vins_*.log 2>/dev/null | head -1)
if [ -n "$VL" ]; then
  python3 ~/sitl_realmachine/tools/vins_watch_v1.py --vins-log "$VL" "$@"
else
  python3 ~/sitl_realmachine/tools/vins_watch_v1.py "$@"
fi
