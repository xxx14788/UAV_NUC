#!/usr/bin/env bash
# ff_record.sh v1.0 — 首飞录袋 standalone 录制器（专项① 单元4，2026-10-11）
# 话题集（沿 r2 经验+position_cmd 复盘必需+px4ctrl 状态）:
#   infra1/infra2 (D435 红外双目) + imu/data_raw + VINS odometry + imu_propagate
#   + mavros/state + battery + position_cmd + debugPx4ctrl/fsm_state + takeoff_land
# 码率预算: 无图像话题≈0.15GB/min（30min≈4.5GB）；infra 双目≈2-4GB/min（磁盘吃紧时去掉）
# 用法: bash ff_record.sh [--no-infra]    # 磁盘紧急时 --no-infra 纯飞行数据
#       再执行一次 = 停止录制（PID 文件互斥）
# 落点: ~/sitl_realmachine/bags/firstflight_YYYYmmdd_NN.bag（自动序号，与 dashboard r 键同命名规则）
# 磁盘预检: 录前 df 检查 avail<6G 拒录（30min 预算 4.5G+1.5G 余量）
source /opt/ros/noetic/setup.bash 2>/dev/null
source "$HOME/catkin_ws/devel/setup.bash" 2>/dev/null
BAG_DIR="$HOME/sitl_realmachine/bags"
PIDF="/tmp/ff_record.pid"

TOPICS="/camera/infra1/image_rect_raw /camera/infra2/image_rect_raw /mavros/imu/data_raw /vins_estimator/odometry /vins_estimator/imu_propagate /mavros/state /mavros/battery /position_cmd /debugPx4ctrl/fsm_state /px4ctrl/takeoff_land /mavros/local_position/odom"
case "$1" in --no-infra) TOPICS=$(echo "$TOPICS" | sed 's|/camera/infra1/image_rect_raw ||; s|/camera/infra2/image_rect_raw ||');; esac

if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "[ff_record] 停止录制 pid=$(cat "$PIDF")"
  PID=$(cat "$PIDF"); kill "$PID" 2>/dev/null; sleep 3; kill -9 "$PID" 2>/dev/null
  rm -f "$PIDF"
  ls -lh --time-style=+%H:%M "$BAG_DIR"/firstflight_*.bag 2>/dev/null | tail -3
  exit 0
fi

AVAIL_GB=$(df --output=avail -B1G "$HOME" 2>/dev/null | tail -1 | tr -d ' ')
if [ "${AVAIL_GB:-0}" -lt 6 ]; then
  echo "[ff_record] 拒录: 磁盘 avail=${AVAIL_GB}G < 6G 门（30min 含图像预算）——用 --no-infra 或清理后重试" >&2
  exit 1
fi

mkdir -p "$BAG_DIR"; cd "$BAG_DIR"
DATE=$(date +%Y%m%d); N=1
while [ -e "firstflight_${DATE}_$(printf '%02d' $N).bag" ]; do N=$((N+1)); done
OUT="firstflight_${DATE}_$(printf '%02d' $N)"
echo "[ff_record] 启动录制 $BAG_DIR/$OUT.bag (avail=${AVAIL_GB}G, infra=$(case "$1" in --no-infra) echo OFF;; *) echo ON;; esac))"
nohup rosbag record -O "$OUT.bag" $TOPICS > "/tmp/${OUT}_record.log" 2>&1 < /dev/null &
echo $! > "$PIDF"
sleep 2
echo "[ff_record] pid=$(cat "$PIDF")；停止=再跑一次本脚本"
