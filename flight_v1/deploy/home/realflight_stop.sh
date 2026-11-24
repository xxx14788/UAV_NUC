#!/bin/bash
# =============================================================================
# realflight_stop.sh — 停掉实飞全栈，给 bag 回放让路。
#
# 用法:
#   bash ~/realflight_stop.sh
#
# 行为:
#   1) 已解锁 / 正在回放 bag -> 拒绝，避免空中杀栈或误杀回放；
#   2) 调用现有 flight.sh stop：地面断言、录包收尾、节点/roslaunch/rosmaster 清理；
#   3) 清掉 flight.sh stop 不管的盯盘/任务包装（vins_watch、flight_mission、
#      realflight_mission 等）；
#   4) 核验 mavros/vins/px4ctrl/ego_planner/traj_server 与 rosmaster 均已退出。
#
# 注意: 本脚本会停当前 ROS master。回放 bag 前先停飞栈；回放中不要运行。
# =============================================================================
set +u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -uo pipefail

FLOW="$HOME/sitl_realmachine/flight_v1"
STOP="$FLOW/flight.sh"
[ -x "$STOP" ] || { echo "✗ 找不到 $STOP" >&2; exit 1; }

# 回放已在跑就不要误杀（flight.sh stop 会杀 rosmaster）
if pgrep -af 'bag_replay\.sh|rosbag play|rqt_bag' >/dev/null 2>&1; then
  echo "✗ 检测到 bag 回放进程；先停回放再停飞栈（本脚本会杀 rosmaster）" >&2
  pgrep -af 'bag_replay\.sh|rosbag play|rqt_bag' >&2 || true
  exit 1
fi

# 已解锁拒绝（与 realflight_stack.sh 清场同一安全门）
if pgrep -x rosmaster >/dev/null 2>&1 || pgrep -x roscore >/dev/null 2>&1; then
  state=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null) || state=""
  case $state in
    *"armed: True"*)
      echo "✗ 飞控已解锁——拒绝停栈（先落地、上锁）" >&2
      exit 1
      ;;
  esac
fi

# 正式停栈：落地断言、录包收尾、节点/roslaunch/rosmaster 清理都在这里
bash "$STOP" stop
rc=$?

# flight.sh stop 不清盯盘/任务包装；只按名字清，不碰别的 master
pkill -TERM -f '[v]ins_watch_v1\.py' 2>/dev/null || true
pkill -TERM -f '[f]light_mission\.py' 2>/dev/null || true
pkill -TERM -f '[f]light_shape_mission\.py' 2>/dev/null || true
pkill -TERM -f '[r]ealflight_mission\.sh' 2>/dev/null || true
sleep 1
pkill -KILL -f '[v]ins_watch_v1\.py' 2>/dev/null || true
pkill -KILL -f '[f]light_mission\.py' 2>/dev/null || true
pkill -KILL -f '[f]light_shape_mission\.py' 2>/dev/null || true
pkill -KILL -f '[r]ealflight_mission\.sh' 2>/dev/null || true

# 核验核心飞栈
left=$(pgrep -af '(^|/)(mavros_node|vins_node|px4ctrl_node|ego_planner_node|traj_server)([[:space:]]|$)' 2>/dev/null || true)
if [ -n "$left" ]; then
  echo "✗ 仍有飞栈进程：" >&2
  printf '%s\n' "$left" >&2
  exit 1
fi
if pgrep -x rosmaster >/dev/null 2>&1 || pgrep -x roscore >/dev/null 2>&1; then
  echo "✗ rosmaster/roscore 仍在" >&2
  exit 1
fi

echo "===== 飞栈已停，rosmaster 0 残留，可回放 bag ====="
exit "$rc"
