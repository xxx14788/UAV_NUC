#!/usr/bin/env bash
# 建图工具（map_only_node），不是飞行栈。飞行栈唯一入口 = ~/realflight_stack.sh。
set -eo pipefail
source "$(dirname -- "$0")/ros_env.sh"
mkdir -p "$MAP_BUNDLE/runtime"
# Fail before building or changing private ROS parameters when inputs are absent.
python3 "$MAP_BUNDLE/map_check.py" --config "$MAP_BUNDLE/runtime/map.yaml"
if rosnode list 2>/dev/null | grep -qx /mapping_view; then
  echo 'mapping_view 已运行；先 map_status.sh 查看，需清空地图时先 map_stop.sh。'
  exit 1
fi
if [[ ! -x "$MAP_BUNDLE/runtime/build/map_only_node" || "$MAP_BUNDLE/map_only_node.cpp" -nt "$MAP_BUNDLE/runtime/build/map_only_node" || "$MAP_BUNDLE/CMakeLists.txt" -nt "$MAP_BUNDLE/runtime/build/map_only_node" ]]; then
  cmake -S "$MAP_BUNDLE" -B "$MAP_BUNDLE/runtime/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$MAP_BUNDLE/runtime/build" -j2
fi
rosparam load "$MAP_BUNDLE/runtime/map.yaml" /mapping_view
echo '建图已启动，保持此终端；另开 NoMachine 桌面终端运行 map_rviz.sh。Ctrl+C 停止本建图节点。'
exec "$MAP_BUNDLE/runtime/build/map_only_node" __name:=mapping_view
