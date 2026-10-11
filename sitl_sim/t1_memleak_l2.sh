#!/usr/bin/env bash
# t1_memleak_l2.sh — 内存泄漏 L2 符号级取证（工程合并 v1.6 单元2）
# 设计: 3090 回放源(t2v3_hover_134845.bag 左右目+IMU) + 第二 VINS 实例(私有 master :11312 隔离,
#       config 原生话题零重映射) + heaptrack(分配点符号级归属) + 采窗(RSS csv 每 60s)。
# 用法: C1_L2_MODE=smoke(默认, 5min: 验证 bag 循环时戳回归下 VINS 存活性+heaptrack 管线)
#             =loopmain(2h, rate 1.0 --loop; 前提=smoke 证 VINS 活过回归)
#             =slowmain(2h, rate 0.019 单遍; 回归不耐受时兜底, 帧数少但零回归)
# 产出: $EV/{vins.log,play.log,heaptrack.*.zst,rss.csv,heaptrack_interpret.txt}
# 判据预注册: 归属判决 = heaptrack 总分配/泄漏前列调用点中, 与帧处理节奏成比例的分配点
#             (40KB/帧量子候选) 归属到代码面(VINS 自身/OpenCV/Eigen/SDK 层); 泄漏速率以 RSS 斜率复核。
set -u
export ROS_DISTRO=${ROS_DISTRO:-noetic}
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11312}
export ROS_VERSION=${ROS_VERSION:-1}
export ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
L="$HOME/sitl_sim"
MODE="${C1_L2_MODE:-smoke}"
BAG="$L/bags/t2v3_hover_134845.bag"
YAML="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
EVROOT="$L/t1_evidence/v113_2026-10-11/memleak_l2"
EV="$EVROOT/l2_${MODE}_$(date +%H%M%S)"
mkdir -p "$EV"
LOG() { echo "[$(date +%H:%M:%S)] $*"; tee -a "$EV/l2run.log" >/dev/null; }
echo "[$(date +%H:%M:%S)] L2 mode=$MODE ev=$EV" >> "$EV/l2run.log"

[ -f "$BAG" ] || { LOG "FATAL bag missing"; exit 1; }
command -v heaptrack >/dev/null || { LOG "FATAL heaptrack missing"; exit 1; }

# 域过滤杀残留(仅本 master 的 vins)
kill_vins_my_domain() {
  for p in $(pgrep -f "lib/vins/vins_nod[e]" 2>/dev/null); do
    m=$(tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    [ "${m:-x}" = "$ROS_MASTER_URI" ] && kill -9 "$p" 2>/dev/null
  done
}
kill_vins_my_domain
# 私有 master
if ! timeout 3 rosnode list >/dev/null 2>&1; then
  nohup rosmaster -p 11312 > "$EV/rosmaster.log" 2>&1 &
  sleep 2
fi
rosparam set use_sim_time true
rosparam load "$YAML" /vins_estimator 2>/dev/null || true

# VINS under heaptrack（直包二进制——rosrun 是 python 脚本, ROS 工具链剥 LD_PRELOAD → 4K 空文件事故）
cd "$EV"
VINSBIN="$HOME/catkin_ws/devel/.private/vins/lib/vins/vins_node"
setsid nohup heaptrack "$VINSBIN" "$YAML" > "$EV/vins.log" 2>&1 < /dev/null &
sleep 5
VPID=$(pgrep -x vins_node | while read p; do m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -c "11312"); [ "$m" = "1" ] && echo $p; done | head -1)
[ -n "$VPID" ] || { LOG "FATAL VINS 未起(见 vins.log)"; tail -5 "$EV/vins.log"; exit 1; }
LOG "VINS up pid=$VPID (heaptrack wrapped)"

# 回放
TOPICS="/iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw /mavros/imu/data_raw"
case "$MODE" in
  smoke)    DUR=300; PLAY="rosbag play $BAG --clock --loop --topics $TOPICS";;
  supp)     DUR=175; PLAY="rosbag play $BAG --clock --topics $TOPICS";;   # 单遍全速: 零时戳回归, 137s 帧满速
  loopmain) DUR=7200; PLAY="rosbag play $BAG --clock --loop --topics $TOPICS";;
  slowmain) DUR=7200; PLAY="rosbag play $BAG --clock -r 0.019 --topics $TOPICS";;
  *) LOG "FATAL unknown mode"; exit 2;;
esac
DUR="${C1_L2_DUR:-$DUR}"   # 包装器单实例时长覆盖(loopmain 重启包装用)
setsid nohup $PLAY > "$EV/play.log" 2>&1 < /dev/null &
PPID_=$!
LOG "play up ($MODE, ${DUR}s): $PLAY"

# RSS 采样器 + 存活监视
START=$(date +%s)
: > "$EV/rss.csv"; echo "wall,res_kb,vsz_kb,elapsed_s" >> "$EV/rss.csv"
while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
  sleep 60
  NOW=$(pgrep -x vins_node | while read p; do m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -c "11312"); [ "$m" = "1" ] && echo $p; done | head -1)
  if [ -z "$NOW" ]; then
    echo "$(date -Is),DEAD,$(( $(date +%s) - START ))" >> "$EV/rss.csv"
    LOG "WARN VINS 死亡 @$(( $(date +%s) - START ))s — 分析现存 heaptrack 文件(部分窗)"
    break
  fi
  R=$(awk '/VmRSS/{print $2}' /proc/$NOW/status 2>/dev/null)
  V=$(awk '/VmSize/{print $2}' /proc/$NOW/status 2>/dev/null)
  echo "$(date -Is),${R:-NA},${V:-NA},$(( $(date +%s) - START ))" >> "$EV/rss.csv"
done

# 收卷: 先停 play 再优雅停 VINS(heaptrack 落盘)
pkill -f "rosbag pla[y] $BAG" 2>/dev/null; kill $PPID_ 2>/dev/null
VP=$(pgrep -x vins_node | while read p; do m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -c "11312"); [ "$m" = "1" ] && echo $p; done | head -1)
[ -n "$VP" ] && { kill -INT $VP 2>/dev/null; sleep 8; kill -9 $VP 2>/dev/null; }
sleep 5
LOG "heaptrack 文件: $(ls -sh "$EV"/heaptrack.* 2>/dev/null | tr '\n' ' ')"

# 解读(符号级归属面; heaptrack 1.1 无 interpret 子命令, 用 heaptrack_print; 文件为 .gz)
HT=$(ls -t "$EV"/heaptrack.vins_node.*.gz "$EV"/heaptrack.*.gz 2>/dev/null | grep -v rosrun | head -1)
if [ -n "$HT" ]; then
  timeout 600 heaptrack_print "$HT" > "$EV/heaptrack_interpret.txt" 2>&1 \
    && LOG "interpret 毕 ($(wc -l < "$EV/heaptrack_interpret.txt") 行)" \
    || LOG "WARN interpret 失败/超时(原始 gz 留档)"
fi
echo "=== rss.csv tail ==="; tail -5 "$EV/rss.csv"
LOG "L2 窗毕 mode=$MODE"
