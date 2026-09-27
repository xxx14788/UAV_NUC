#!/usr/bin/env bash
# U2 累积循环:单 master 下 40 轮全链 boot,监控 connect 时间趋势;>30s 触发捕获(限3次);
# 每 10 轮抓 20s 洪流 pcap。结束 fresh 对照。
HERE="$(cd "$(dirname "$0")" && pwd)"
ROUNDS="${1:-40}"
OUT="$HOME/sitl_sim/t1_evidence/u2loop_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash

clean9() {
  pkill -9 -f "roslaunch.*mavro[s]" 2>/dev/null
  pkill -9 -f "lib/mavros/mavros_nod[e]" 2>/dev/null
  pkill -9 -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null
  pkill -9 -f "px4ctrl_nod[e]" 2>/dev/null
  pkill -9 -f "bin/px[4]" 2>/dev/null
  pkill -9 -f "gzserve[r]" 2>/dev/null
  pkill -9 -f "make px4_sit[l]" 2>/dev/null
  pkill -9 -f "sitl_gazeb[o]" 2>/dev/null
  sleep 3
}

CAPTURED=0
capture() {
  [ "$CAPTURED" -ge 3 ] && return
  CAPTURED=$((CAPTURED+1))
  local L="$1"
  ss -ulnp > "ss_$L.txt" 2>&1
  local MPID; MPID=$(pgrep -f "lib/mavros/mavros_nod[e]" | head -1)
  [ -n "$MPID" ] && timeout 40 gdb -p "$MPID" -batch -ex "thread apply all bt" > "gdb_mavros_$L.txt" 2>&1
  timeout 25 sudo tcpdump -i lo -s 0 -c 4500 -w "flood_$L.pcap" "udp port 14540 or udp port 14580" 2> "tcpdump_$L.txt"
}

echo "round,connect_s" > connect_curve.csv
probe() {
  local L="$1" t0 now
  t0=$(date +%s.%N)
  timeout 240 rostopic echo -p /mavros/state/connected 2>/dev/null | grep --line-buffered -m1 "1$" > "/tmp/hit_$L" || true
  now=$(date +%s.%N)
  if [ -s "/tmp/hit_$L" ]; then
    echo "$L,$(echo "$now $t0" | awk '{printf "%.1f", $1-$2}')" | tee -a connect_curve.csv
  else
    echo "$L,TIMEOUT240" | tee -a connect_curve.csv
  fi
}

pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311

for i in $(seq 1 "$ROUNDS"); do
  echo "=== round$i $(date +%H:%M:%S) ==="
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_r$i.log" 2>&1 & )
  t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
  ss -uln | grep -q ":14580 " || { echo "round$i SITL FAIL"; clean9; continue; }
  sleep 8
  nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557 > "$OUT/mavros_r$i.log" 2>&1 &
  ( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl_r$i.log" 2>&1 & )
  probe "r$i"
  EL=$(tail -1 connect_curve.csv | cut -d, -f2)
  SLOW=$(awk -v e="${EL:-999}" 'BEGIN{print (e+0>30)?1:0}')
  [ "$SLOW" = 1 ] && { echo "round$i SLOW -> capture"; capture "r$i"; }
  if [ $(( i % 10 )) -eq 0 ]; then
    clean9
    timeout 20 sudo tcpdump -i lo -s 0 -c 4000 -w "flood_sample_r$i.pcap" "udp port 14540 or udp port 14580" 2>/dev/null
  else
    clean9
  fi
done
pkill -9 -f "roscore" 2>/dev/null; pkill -9 -f "rosmaste[r]" 2>/dev/null; pkill -9 -f "rosou[t]" 2>/dev/null
sleep 3
roscore > "$OUT/roscoreF.log" 2>&1 &
sleep 4
echo "=== fresh master bootF ==="
( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_bootF.log" 2>&1 & )
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557 > "$OUT/mavros_bootF.log" 2>&1 &
probe "bootF"
clean9
pkill -9 -f "roscore" 2>/dev/null; pkill -9 -f "rosmaste[r]" 2>/dev/null; pkill -9 -f "rosou[t]" 2>/dev/null
echo "=== LOOP DONE $(date) ==="
cat connect_curve.csv
