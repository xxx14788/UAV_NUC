#!/usr/bin/env bash
# U6.2b:恢复失败定性——杀SITL重启后,抓 px4ctrl fsm 序列 + odom/state 接收位。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u6_diag_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash
sitl_up() {
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$1.log" 2>&1 & )
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && return 0; sleep 1; done
  return 1
}
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
sitl_up a || exit 1
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
sleep 25
echo "=== baseline fsm ==="
timeout 4 rostopic echo -n2 --noarr /debugPx4ctrl/fsm_state 2>/dev/null | head -2
echo "=== kill SITL $(date +%H:%M:%S) ==="
pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; sleep 3
sitl_up b || exit 1
echo "=== SITL back, T+0; fsm 序列(每3s) ==="
for i in $(seq 1 30); do
  F=$(timeout 2 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state 2>/dev/null | head -1)
  C=$(timeout 2 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -o "True\|False")
  echo "T+$(( (i-1)*3 ))s connected=${C:-?} fsm=${F:-NONE}"
  if [ $(( i % 10 )) -eq 5 ]; then
    ( timeout 10 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 ) &
  fi
  if timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: True"; then echo "ARMED at T+$(( (i-1)*3 ))s"; break; fi
  sleep 3
done
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; sleep 2
pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== diag done ==="
