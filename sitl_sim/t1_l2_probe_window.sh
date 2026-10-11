#!/usr/bin/env bash
# t1_l2_probe_window.sh — L2 探针窗（工程 v1.6 单元2; heaptrack 停摆后自研 mtrace 案）
# 机理: 裸 VINS(heaptrack 会致 init 后停摆——baretest 20236 行对照证)+t1_mtrace.so 轻探针
#       +bag --loop 全速(唯一可测泄漏形态 smoke 620MB/h); SIGBUS 边界死亡随机(baretest 200s 活/首 loopmain 180s 崩)
#       → 窗内死亡自动重启(unbuffered 日志保留), 实例计数; 窗毕产出=分实例 {mtrace.log, msum.log, rss.csv}。
# 用法: t1_l2_probe_window.sh <总预算秒=3600>
set -u
export ROS_DISTRO=noetic ROS_MASTER_URI=http://localhost:11312 ROS_VERSION=1 ROS_PACKAGE_PATH=
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
BUDGET="${1:-3600}"
L="$HOME/sitl_sim"
EVROOT="$L/t1_evidence/v113_2026-10-11/memleak_l2"
EV="$EVROOT/probe_window_$(date +%H%M%S)"
mkdir -p "$EV"
echo "[$(date +%H:%M:%S)] probe window start ev=$EV budget=$BUDGET" >> "$EV/window.log"
BAG="$L/bags/t2v3_hover_134845.bag"
YAML="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
SO="$L/t1_mtrace.so"
[ -f "$SO" ] || { echo "FATAL probe missing" >> "$EV/window.log"; exit 1; }

domkill() {
  for p in $(pgrep -x vins_node); do
    m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    [ "${m:-x}" = "http://localhost:11312" ] && kill -9 "$p" 2>/dev/null
  done
  pkill -f "rosbag pla[y].*t2v3_hover" 2>/dev/null
}
domkill
START=$(date +%s); INST=0
while [ $(( $(date +%s) - START )) -lt "$BUDGET" ]; do
  INST=$((INST+1))
  IEV="$EV/inst$INST"; mkdir -p "$IEV"
  echo "[$(date +%H:%M:%S)] instance $INST start" >> "$EV/window.log"
  rosparam set use_sim_time true 2>/dev/null
  rosparam load "$YAML" /vins_estimator 2>/dev/null || true
  cd "$IEV"
  T1_MTRACE_OUT="$IEV/mtrace.log" T1_MTRACE_SUM="$IEV/msum.log" \
    setsid nohup env LD_PRELOAD="$SO" \
    "$HOME/catkin_ws/devel/.private/vins/lib/vins/vins_node" "$YAML" > "$IEV/vins.log" 2>&1 < /dev/null &
  sleep 4
  setsid nohup rosbag play "$BAG" --clock --loop --topics \
    /iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw /mavros/imu/data_raw \
    > "$IEV/play.log" 2>&1 < /dev/null &
  ISTART=$(date +%s)
  : > "$IEV/rss.csv"; echo "wall,res_kb,elapsed" >> "$IEV/rss.csv"
  while [ $(( $(date +%s) - ISTART )) -lt $(( BUDGET - ($(date +%s) - START) + 20 )) ]; do
    sleep 60
    P=$(pgrep -x vins_node | while read p; do m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -c 11312); [ "$m" = "1" ] && echo $p; done | head -1)
    if [ -z "$P" ]; then
      echo "$(date -Is),DEAD,$(( $(date +%s) - ISTART ))" >> "$IEV/rss.csv"
      echo "[$(date +%H:%M:%S)] instance $INST DEAD @$(( $(date +%s) - ISTART ))s" >> "$EV/window.log"
      break
    fi
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    echo "$(date -Is),${R:-NA},$(( $(date +%s) - ISTART ))" >> "$IEV/rss.csv"
  done
  domkill
  sleep 3
done
echo "[$(date +%H:%M:%S)] window end instances=$INST" >> "$EV/window.log"
# 各实例日志体量+track 行数速览
for d in "$EV"/inst*; do
  echo "$(basename $d): mtrace=$(wc -l < $d/mtrace.log 2>/dev/null || echo 0) 行 sum=$(wc -l < $d/msum.log 2>/dev/null || echo 0) 行 track=$(grep -c track $d/vins.log 2>/dev/null || echo 0) rss尾=$(tail -1 $d/rss.csv)" >> "$EV/window.log"
done
tail -5 "$EV/window.log"
