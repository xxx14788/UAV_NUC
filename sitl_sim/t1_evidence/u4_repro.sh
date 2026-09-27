#!/usr/bin/env bash
# U4b:磁污染复发实验。sitl_north world 起飞一轮(触发 disarm 回写)→ 默认 world 再起
# → 查 CAL_MAG*/EKF2_MAG_DECL 是否污染/复发。全程参数经 mavros param 服务读。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u4_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash

pget() { rosservice call /mavros/param/get "param_id: '$1'" 2>/dev/null | grep -o "value: .*" | head -1; }
dump_mag() {
  echo "--- $(date +%H:%M:%S) $1 ---" >> u4_params.log
  for p in CAL_MAG0_ID CAL_MAG0_XOFF CAL_MAG1_ID EKF2_MAG_DECL EKF2_DECL_TYPE; do
    echo "$p = $(pget $p)" >> u4_params.log
  done
}
sitl_up() {
  ( cd "$HOME/sitl_sim" && PX4_SITL_WORLD="$2" setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$1.log" 2>&1 & )
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && return 0; sleep 1; done
  return 1
}
kill_sitl() { pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; pkill -9 -f "sitl_gazeb[o]"; sleep 3; }

echo "=== U4b start $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311

echo "--- phase 1: sitl_north world + takeoff round ---"
sitl_up n1 sitl_north || { echo "SITL-n1 FAIL"; exit 1; }
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
sleep 12
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
sleep 10
dump_mag "n1 boot (pre-flight)"
timeout 60 ~/sitl_sim/04_takeoff.sh 60
sleep 12
dump_mag "n1 flying/hover"
timeout 20 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
sleep 15
dump_mag "n1 post-land (disarm writeback window)"
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
kill_sitl

echo "--- phase 2: default world boot, read params ---"
sitl_up d1 "" || { echo "SITL-d1 FAIL"; exit 1; }
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros_d.log" 2>&1 &
sleep 15
dump_mag "d1 default world boot"
timeout 60 ~/sitl_sim/04_takeoff.sh 60 && sleep 12 && dump_mag "d1 hover" && \
timeout 20 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 && \
sleep 15 && dump_mag "d1 post-land"
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
kill_sitl
sleep 2; pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U4b done $(date) ==="
cat u4_params.log
