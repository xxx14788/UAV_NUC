#!/usr/bin/env bash
# U2 复现编排:同 roscore 连续 3 boot,慢连(>30s)自动触发四路捕获。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u2_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash

clean_sitl() {  # 杀 SITL/mavros/gazebo,保留 roscore
  pkill -f "roslaunch.*mavro[s]" 2>/dev/null
  pkill -f "lib/mavros/mavros_nod[e]" 2>/dev/null
  pkill -f "bin/px[4]" 2>/dev/null
  pkill -f "gzserve[r]" 2>/dev/null
  pkill -f "make px4_sit[l]" 2>/dev/null
  pkill -f "sitl_gazeb[o]" 2>/dev/null
  sleep 5
}

capture() {  # $1=label
  local L="$1"
  ss -ulnp > "ss_$L.txt" 2>&1
  rostopic list -v > "rostopic_v_$L.txt" 2>&1
  rosnode list > "rosnode_$L.txt" 2>&1
  rosparam list > "rosparam_$L.txt" 2>&1
  local MPID
  MPID=$(pgrep -f "lib/mavros/mavros_nod[e]" | head -1)
  if [ -n "$MPID" ]; then
    timeout 40 gdb -p "$MPID" -batch -ex "thread apply all bt" > "gdb_mavros_$L.txt" 2>&1
  fi
  timeout 25 sudo tcpdump -i lo -s 0 -c 4500 -w "flood_$L.pcap" "udp port 14540 or udp port 14580" 2> "tcpdump_$L.txt"
}

echo "=== U2 repro start $(date) HERE=$HERE OUT=$OUT ==="
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311

for B in boot1 boot2 boot3; do
  echo "=== $B $(date +%H:%M:%S) ==="
  bash "$HERE/u2_boot_once.sh" "$B" "$OUT"
  if [ ! -f "probe_$B.txt" ]; then echo "[$B] boot_once failed"; clean_sitl; continue; fi
  EL=$(grep -o "elapsed=[0-9.]*" "probe_$B.txt" 2>/dev/null | cut -d= -f2 | tr -d s)
  SLOW=$(awk -v e="${EL:-999}" 'BEGIN{print (e>30)?1:0}')
  if [ "$SLOW" = 1 ]; then
    echo "=== $B SLOW CONNECT (${EL}s) -> capturing ==="
    capture "$B"
  fi
  clean_sitl
done
pkill -f "roscore" 2>/dev/null; pkill -f "rosmaste[r]" 2>/dev/null; pkill -f "rosou[t]" 2>/dev/null
sleep 3
roscore > "$OUT/roscore2.log" 2>&1 &
sleep 4
echo "=== bootF (fresh master) $(date +%H:%M:%S) ==="
bash "$HERE/u2_boot_once.sh" bootF "$OUT"
clean_sitl
pkill -f "roscore" 2>/dev/null; pkill -f "rosmaste[r]" 2>/dev/null; pkill -f "rosou[t]" 2>/dev/null
echo "=== U2 repro done $(date) ==="
grep -H "PROBE_RESULT" probe_boot*.txt
