#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "$0")/ros_env.sh"
# Ubuntu's /usr/bin/rviz can mix its ROS libraries with the Noetic overlay.
# Require the RViz binary from the same ROS distribution as this workspace.
RVIZ_BIN=/opt/ros/noetic/lib/rviz/rviz
if [[ ! -x "$RVIZ_BIN" ]] || ! rospack find rviz >/dev/null 2>&1 || ! rospack find media_export >/dev/null 2>&1; then
  echo '缺少 ROS Noetic RViz 或资源包，请先安装：' >&2
  echo 'sudo apt-get install ros-noetic-rviz ros-noetic-media-export' >&2
  exit 1
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo '请在 NoMachine 桌面里打开终端运行本脚本；当前 SSH 终端没有 DISPLAY。' >&2
  exit 1
fi
echo "启动 Noetic RViz：$RVIZ_BIN（DISPLAY=$DISPLAY）"
exec "$RVIZ_BIN" -d "$MAP_BUNDLE/mapping.rviz" __name:=mapping_rviz
