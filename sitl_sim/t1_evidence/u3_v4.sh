#!/usr/bin/env bash
# U3 v4:px4ctrl 的 roscpp DEBUG 日志对比——stable1(预期成功)vs stable2(预期失败)。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u3v4_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash
try_pub() {
  local L="$1" t0=$(date +%s.%N) ok=0
  ( timeout 6 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 ) &
  local P=$!
  while [ $(( $(date +%s) - ${t0%.*} )) -lt 10 ]; do
    if timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: True"; then ok=1; break; fi
    sleep 0.5
  done
  kill $P 2>/dev/null; wait $P 2>/dev/null
  echo "$L ok=$ok t=$(echo "$(date +%s.%N) $t0" | awk '{printf "%.1f",$1-$2}')s"
  if [ "$ok" = 1 ]; then
    timeout 20 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
    sleep 6
  fi
  return 0
}
echo "=== U3v4 $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl.log" 2>&1 & )
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
sleep 30
rosservice call /px4ctrl/set_logger_level "logger: 'roscpp'
level: 'debug'" >/dev/null 2>&1
echo "--- probe 1 (marker: PROBE1_BEGIN) ---" >> "$OUT/px4ctrl.log"
try_pub p1 | tee -a u3v4_result.txt
echo "--- marker: PROBE1_END ---" >> "$OUT/px4ctrl.log"
echo "--- probe 2 (marker: PROBE2_BEGIN) ---" >> "$OUT/px4ctrl.log"
try_pub p2 | tee -a u3v4_result.txt
echo "--- marker: PROBE2_END ---" >> "$OUT/px4ctrl.log"
echo "--- probe 3 ---"
try_pub p3 | tee -a u3v4_result.txt
rosservice call /px4ctrl/set_logger_level "logger: 'roscpp'
level: 'info'" >/dev/null 2>&1
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; sleep 2
pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U3v4 done $(date) ==="
