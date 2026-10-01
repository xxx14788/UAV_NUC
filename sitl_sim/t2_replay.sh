#!/usr/bin/env bash
# T2-W3 离线重放单试验：bag × 配置 → VINS 输出 bag + ATE 报告。
# 用法: t2_replay.sh <试验号如E01> <bag> <配置目录>
# 输出: ~/sitl_sim/t2_results/<试验号>_<bag名>/ 下 vins_out.bag / ate.json / vins.log
#
# 隔离：私有 ROS_MASTER_URI=:11312（与 T1/T3 的活动会话互不干扰，
#       use_sim_time 只作用于本 master）。
set -u
export ROS_DISTRO=${ROS_DISTRO:-noetic}  # T2-R1.5: set -u 与 setup.bash 兼容(vins_smoke 08518f2 同修)
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11312}
export ROS_VERSION=${ROS_VERSION:-1}
export ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

EXP="${1:?试验号}"
BAG="$(readlink -f "${2:?bag}")"
CFG="$(readlink -f "${3:?配置目录}")"
YAML="$CFG/sim_stereo_imu_config.yaml"

OUT="$HOME/sitl_sim/t2_results/${EXP}_$(basename "$BAG" .bag)"
mkdir -p "$OUT"
export ROS_MASTER_URI=http://localhost:11312

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

# 私有 roscore
if ! rosnode list >/dev/null 2>&1; then
  nohup rosmaster -p 11312 > "$OUT/rosmaster.log" 2>&1 &
  CORE_PID=$!
  sleep 2
fi
rosparam set use_sim_time true
rosparam load "$YAML" /vins_estimator 2>/dev/null || true   # 仅为可见性，非必需

# T2-R1.4: 清残留 vins_node(多实例顶号教训: shutdown "new node registered with same name"
# 吞掉 E23 三 cell)。pgrep 全匹配仅限本私有 master 场景, 飞行会话勿用本脚本。
for _pid in $(pgrep -f 'devel/lib/vins/vins_node'); do kill -KILL $_pid 2>/dev/null; done
sleep 1
# VINS 节点（崩溃即止，日志留档）
nohup rosrun vins vins_node "$YAML" > "$OUT/vins.log" 2>&1 &
VINS_PID=$!
sleep 3

# 输出录制（imu_propagate 高频 + odometry）
nohup rosbag record -O "$OUT/vins_out" \
  /vins_estimator/odometry /vins_estimator/imu_propagate \
  > "$OUT/record.log" 2>&1 &
REC_PID=$!
sleep 2

# 重放（--clock 提供仿真时间；结束即试验结束）
# T2-R4: T2_PLAY_EXTRA 注入 play 参数(如 "-s 30" 模拟运动中重启起跑),默认空
rosbag play "$BAG" --clock ${T2_PLAY_EXTRA:-} --topics /iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw /mavros/imu/data_raw > "$OUT/play.log" 2>&1 &
PLAY_PID=$!
PLAY_START=$(date +%s)
BAG_LEN=$(rosbag info --yaml "$BAG" | grep duration | awk '{print int($2)+3}')
echo "[t2_replay] bag 长度 ${BAG_LEN}s（含 3s 裕量），播放开始"

# 等播放结束或 VINS 崩溃
while kill -0 "$PLAY_PID" 2>/dev/null && kill -0 "$VINS_PID" 2>/dev/null; do
  sleep 2
  NOW=$(date +%s)
  if [ $((NOW - PLAY_START)) -gt $((BAG_LEN + 60)) ]; then
    echo "[t2_replay] 超时保护触发"; break
  fi
done
VINS_ALIVE=$(kill -0 "$VINS_PID" 2>/dev/null && echo 1 || echo 0)
sleep 5   # 尾部帧落盘

kill -INT "$REC_PID" 2>/dev/null; sleep 2
kill -INT "$VINS_PID" 2>/dev/null; sleep 2
kill -KILL "$VINS_PID" 2>/dev/null

echo "[t2_replay] VINS 存活=$VINS_ALIVE  输出: $OUT"
echo "$VINS_ALIVE" > "$OUT/vins_alive.txt"
ls -la "$OUT"
