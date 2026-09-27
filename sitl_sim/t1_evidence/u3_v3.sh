#!/usr/bin/env bash
# U3 v3:投递概率矩阵。稳态 vs SITL重启窗口,各连续 6 个短 pub(6s),统计 armed 翻转率。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u3v3_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash

try_pub() {  # $1=label:一个 6s pub 尝试,输出 0/1(armed 翻转)
  local L="$1" t0=$(date +%s.%N) ok=0
  ( timeout 6 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 ) &
  local P=$!
  while [ $(( $(date +%s) - ${t0%.*} )) -lt 10 ]; do
    if timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: True"; then ok=1; break; fi
    sleep 0.5
  done
  kill $P 2>/dev/null; wait $P 2>/dev/null
  echo "$L ok=$ok t=$(echo "$(date +%s.%N) $t0" | awk '{printf "%.1f",$1-$2}')s" | tee -a u3v3_matrix.txt
  if [ "$ok" = 1 ]; then
    timeout 20 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
    sleep 6
  fi
}
sitl_up() {
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$1.log" 2>&1 & )
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && return 0; sleep 1; done
  return 1
}
kill_sitl() { pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; pkill -9 -f "sitl_gazeb[o]"; sleep 3; }

echo "=== U3v3 $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
sitl_up a || exit 1
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
sleep 30
echo "--- stable-state pubs ---"
for i in 1 2 3 4; do try_pub "stable$i"; done
echo "--- restart window pubs ---"
kill_sitl
sitl_up b || exit 1
sleep 2
for i in 1 2 3 4; do try_pub "restart$i"; done
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
kill_sitl; sleep 2
pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U3v3 done $(date) ==="; cat u3v3_matrix.txt
