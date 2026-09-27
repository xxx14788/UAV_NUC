#!/usr/bin/env bash
# U3 v2:R3 投递停滞 + U3d 验收。完整 SITL 重启(PX4+gzserver)后 T+2s 发 takeoff,
# 测 投递成功(fsm triggered 翻转)与 armed 时延;连续 3 轮;窗口内 ss/gdb 取证。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u3v2_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash

sitl_up() {  # 起 SITL 并等 14580
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$1.log" 2>&1 & )
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && return 0; sleep 1; done
  return 1
}
kill_sitl() { pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; pkill -9 -f "sitl_gazeb[o]"; sleep 3; }
land_wait() {  # 发 land 并等 disarmed
  timeout 15 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
  local t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 60 ]; do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: False" && return 0
    sleep 2
  done
  return 1
}
takeoff_probe() {  # $1=label:立即起 pub(20s 长窗) 并测 triggered/armed 时延
  local L="$1" TP AP
  TP=none; AP=none
  ( timeout 25 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 ) &
  local PUBPID=$! t0=$(date +%s.%N)
  while [ $(( $(date +%s) - ${t0%.*} )) -lt 24 ]; do
    F=$(timeout 2 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state 2>/dev/null | head -1)
    if [ "$TP" = none ] && echo "$F" | grep -q "triggered=1"; then
      TP=$(echo "$(date +%s.%N) $t0" | awk '{printf "%.1f",$1-$2}')
    fi
    if timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: True"; then
      AP=$(echo "$(date +%s.%N) $t0" | awk '{printf "%.1f",$1-$2}'); break
    fi
    sleep 0.5
  done
  kill $PUBPID 2>/dev/null
  echo "$L triggered_after=${TP}s armed_after=${AP}s" | tee -a u3v2_results.txt
}

echo "=== U3v2 start $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
sitl_up a || { echo "SITL-a FAIL"; exit 1; }
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
echo "chain up, wait stable 30s"; sleep 30
echo "=== baseline takeoff (chain stable) ==="
takeoff_probe baseline
land_wait; echo "baseline landed"

for R in 1 2 3; do
  echo "=== round $R: kill full SITL $(date +%H:%M:%S) ==="
  kill_sitl
  echo "=== round $R: SITL restart + takeoff@T+2s ==="
  sitl_up "r$R" || { echo "round $R SITL FAIL"; continue; }
  sleep 2
  takeoff_probe "r$R"
  if [ "$R" = 1 ]; then
    ss -tnp 2>/dev/null | grep -E "px4ctrl|11311" > "ss_tcp_r1.txt"
    PXPID=$(pgrep -f "px4ctrl_nod[e]" | head -1)
    [ -n "$PXPID" ] && timeout 25 gdb -p "$PXPID" -batch -ex "thread apply all bt" > "gdb_px4ctrl_r1.txt" 2>&1
  fi
  land_wait && echo "round $R landed" || echo "round $R LAND_TIMEOUT"
  sleep 5
done
echo "=== cleanup ==="
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
kill_sitl
sleep 2; pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U3v2 done $(date) ==="; cat u3v2_results.txt
