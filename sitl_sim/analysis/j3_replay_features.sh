#!/bin/bash
# T4-J-R3② J1.3 特征云离线重放（私有 master，零锁零飞行轮）
# 用法: j3_replay_features.sh <src.bag> <out_dir> [budget_sec]
# 产出: <out_dir>/features.bag = /vins_estimator/point_cloud + /vins_estimator/odometry
# 口径: 与 T2-U2 canonical 冻结一致（devel 现行二进制 + config/sim_stereo/e2_debug_smooth.yaml，
#       md5 见 ~/sitl_sim/t2_u2_freeze.txt）；私有 master 11314（T2 占 11313）。
BAG="${1:?usage: $0 <src.bag> <out_dir> [budget_sec]}"
OUT="${2:?missing out_dir}"
BUDGET="${3:-400}"
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/e2_debug_smooth.yaml"

# 先 source 后 set -u: ROS setup.bash 内有未绑定变量引用, set -u 在前会杀死脚本
source /opt/ros/noetic/setup.bash 2>/dev/null || source /opt/ros/melodic/setup.bash 2>/dev/null
set -u
source "$HOME/catkin_ws/devel/setup.bash"

mkdir -p "$OUT"

# 大 IO 前置: rosbag 双 0 空窗(间隔 5s 两次全 0 才动手).
# 计数走 ps comm 精确进程名: pgrep -f 会被任何含"rosbag"字样的包装命令自命中
# (2026-10-01 夜两次实locale: -x 探不到 python 包装, -f 被外层 bash -c 毒计数)
c1=$(ps -eo comm= | grep -cx rosbag); c1=${c1:-0}
sleep 5
c2=$(ps -eo comm= | grep -cx rosbag); c2=${c2:-0}
if [ "$c1" != "0" ] || [ "$c2" != "0" ]; then
  echo "ABORT: rosbag 非空窗(c1=$c1 c2=$c2)——有人在做回放/录制，改窗口再跑"; exit 3
fi

export ROS_MASTER_URI="http://127.0.0.1:11314/"
roscore -p 11314 > "$OUT/roscore.log" 2>&1 &
P_MASTER=$!
sleep 3
nice -n 10 rosrun vins vins_node "$CFG" > "$OUT/vins.log" 2>&1 &
P_VINS=$!
sleep 5
rosbag play "$BAG" --clock -r 1.0 > "$OUT/play.log" 2>&1 &
P_PLAY=$!
rosbag record -O "$OUT/features.bag" /vins_estimator/point_cloud /vins_estimator/odometry \
  > "$OUT/record.log" 2>&1 &
P_REC=$!

echo "PIDs: master=$P_MASTER vins=$P_VINS play=$P_PLAY rec=$P_REC; 预算 ${BUDGET}s"
SECS=0
while kill -0 "$P_PLAY" 2>/dev/null && [ "$SECS" -lt "$BUDGET" ]; do
  sleep 10; SECS=$((SECS+10))
done
sleep 5  # 尾窗排空
kill -INT "$P_REC" 2>/dev/null; sleep 3
kill -TERM "$P_PLAY" "$P_VINS" 2>/dev/null; sleep 2
kill -TERM "$P_MASTER" 2>/dev/null; sleep 1
kill -9 "$P_PLAY" "$P_VINS" "$P_MASTER" 2>/dev/null

if [ -s "$OUT/features.bag" ]; then
  rosbag info "$OUT/features.bag" 2>/dev/null | grep -E 'duration|messages|point_cloud|odometry' | head -6
  echo "OK: $OUT/features.bag ($(du -h "$OUT/features.bag" | cut -f1))"
  exit 0
else
  echo "FAIL: features.bag 为空/缺失——查 $OUT/{vins,play,record}.log"
  exit 4
fi
