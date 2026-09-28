#!/usr/bin/env bash
# T3-D2 离线重放(t2_replay.sh 的 T3 扩展,不动 T2 原件):
#   1) 输出录制加 /vins_estimator/feature_pts(D2 特征存活率判据)
#   2) master 端口参数化(默认 11313,避开 T2 的 11312,可多实例并行)
#   3) 输出目录 ~/sitl_sim/t3_results/
# 用法: t3_replay.sh <试验号如T01> <bag> <配置目录> [port=11313]
# 输出: ~/sitl_sim/t3_results/<试验号>_<bag名>/ 下 vins_out.bag / vins.log / vins_alive.txt
set -u
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

EXP="${1:?试验号}"
BAG="$(readlink -f "${2:?bag}")"
CFG="$(readlink -f "${3:?配置目录}")"
PORT="${4:-11313}"
YAML="$CFG/sim_stereo_imu_config.yaml"

OUT="$HOME/sitl_sim/t3_results/${EXP}_$(basename "$BAG" .bag)"
mkdir -p "$OUT"
export ROS_MASTER_URI=http://localhost:$PORT

cleanup() {
  [ -n "${PLAY_PID:-}" ] && kill -INT "$PLAY_PID" 2>/dev/null
  [ -n "${REC_PID:-}" ] && kill -INT "$REC_PID" 2>/dev/null
  sleep 1
  [ -n "${VINS_PID:-}" ] && kill -INT "$VINS_PID" 2>/dev/null
  sleep 2
  [ -n "${CORE_PID:-}" ] && kill "$CORE_PID" 2>/dev/null
  [ -n "${VINS_PID:-}" ] && kill -KILL "$VINS_PID" 2>/dev/null
}
trap cleanup EXIT

if ! rosnode list >/dev/null 2>&1; then
  nohup rosmaster -p "$PORT" > "$OUT/rosmaster.log" 2>&1 &
  CORE_PID=$!
  sleep 2
fi
rosparam set use_sim_time true
rosparam load "$YAML" /vins_estimator 2>/dev/null || true

nohup rosrun vins vins_node "$YAML" > "$OUT/vins.log" 2>&1 &
VINS_PID=$!
sleep 3

nohup rosbag record -O "$OUT/vins_out" \
  /vins_estimator/odometry /vins_estimator/imu_propagate /vins_estimator/feature_pts \
  > "$OUT/record.log" 2>&1 &
REC_PID=$!
sleep 2

rosbag play "$BAG" --clock > "$OUT/play.log" 2>&1 &
PLAY_PID=$!
PLAY_START=$(date +%s)
BAG_LEN=$(rosbag info --yaml "$BAG" | grep duration | awk '{print int($2)+3}')
echo "[t3_replay] $EXP bag ${BAG_LEN}s 端口 $PORT 开始"

while kill -0 "$PLAY_PID" 2>/dev/null && kill -0 "$VINS_PID" 2>/dev/null; do
  sleep 2
  NOW=$(date +%s)
  if [ $((NOW - PLAY_START)) -gt $((BAG_LEN + 60)) ]; then
    echo "[t3_replay] 超时保护触发"; break
  fi
done
VINS_ALIVE=$(kill -0 "$VINS_PID" 2>/dev/null && echo 1 || echo 0)
sleep 5

kill -INT "$REC_PID" 2>/dev/null; sleep 2
kill -INT "$VINS_PID" 2>/dev/null; sleep 2
kill -KILL "$VINS_PID" 2>/dev/null

echo "[t3_replay] $EXP VINS 存活=$VINS_ALIVE 输出: $OUT"
echo "$VINS_ALIVE" > "$OUT/vins_alive.txt"
