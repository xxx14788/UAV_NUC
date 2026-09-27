#!/usr/bin/env bash
# U6.2:最终栈恢复测试:杀 PX4+gzserver→重启→04 takeoff(重试制),连续 3 轮。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u6_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash
sitl_up() {
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$1.log" 2>&1 & )
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && return 0; sleep 1; done
  return 1
}
kill_sitl() { pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; pkill -9 -f "sitl_gazeb[o]"; sleep 3; }
echo "=== U6.2 recovery test $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
sitl_up base || exit 1
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
sleep 25
PASS=0
for R in 1 2 3; do
  echo "--- round $R: kill SITL $(date +%H:%M:%S) ---"
  kill_sitl
  sitl_up r$R || { echo "round $R SITL FAIL"; continue; }
  sleep 2
  if timeout 95 ~/sitl_sim/04_takeoff.sh 95 >> "$OUT/tk_r$R.log" 2>&1; then
    echo "round $R RECOVERED" | tee -a recovery_results.txt; PASS=$((PASS+1))
    timeout 25 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
    sleep 8
  else
    echo "round $R FAILED" | tee -a recovery_results.txt
  fi
done
echo "RECOVERY_PASS=$PASS/3" | tee -a recovery_results.txt
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
kill_sitl; sleep 2; pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== done $(date) ==="
