#!/usr/bin/env bash
# t1_l2_baretest.sh — L2 停摆归因对照: 裸 VINS(无 heaptrack)+loop 回放 3min, 验证 heaptrack 交互假说
set -u
export ROS_DISTRO=noetic ROS_MASTER_URI=http://localhost:11312 ROS_VERSION=1 ROS_PACKAGE_PATH=
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
EV="$HOME/sitl_sim/t1_evidence/v113_2026-10-11/memleak_l2/baretest_$(date +%H%M%S)"
mkdir -p "$EV"
for p in $(pgrep -x vins_node); do
  m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
  [ "${m:-x}" = "http://localhost:11312" ] && kill -9 "$p" 2>/dev/null
done
pkill -f "rosbag pla[y].*t2v3_hover" 2>/dev/null; sleep 2
timeout 3 rosnode list >/dev/null 2>&1 || { nohup rosmaster -p 11312 > "$EV/rosmaster.log" 2>&1 & sleep 2; }
rosparam set use_sim_time true
YAML="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
rosparam load "$YAML" /vins_estimator 2>/dev/null || true
cd "$EV"
setsid nohup "$HOME/catkin_ws/devel/.private/vins/lib/vins/vins_node" "$YAML" > "$EV/vins.log" 2>&1 < /dev/null &
sleep 4
BAG="$HOME/sitl_sim/bags/t2v3_hover_134845.bag"
setsid nohup rosbag play "$BAG" --clock --loop --topics /iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw /mavros/imu/data_raw > "$EV/play.log" 2>&1 < /dev/null &
VP=$(pgrep -x vins_node | head -1)
echo "bare vins pid=$VP"
START=$(date +%s); : > "$EV/rss.csv"; echo "wall,res_kb,elapsed" >> "$EV/rss.csv"
while [ $(( $(date +%s) - START )) -lt 200 ]; do
  sleep 20
  P=$(pgrep -x vins_node | head -1)
  [ -z "$P" ] && { echo "$(date -Is),DEAD,$(( $(date +%s) - START ))" >> "$EV/rss.csv"; echo "DIED @$(( $(date +%s) - START ))s"; break; }
  R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
  echo "$(date -Is),${R:-NA},$(( $(date +%s) - START ))" >> "$EV/rss.csv"
done
pkill -f "rosbag pla[y].*t2v3_hover" 2>/dev/null
P=$(pgrep -x vins_node | head -1); [ -n "$P" ] && kill -9 "$P" 2>/dev/null
tail -6 "$EV/rss.csv"; echo "track lines: $(grep -c track "$EV/vins.log")"
