#!/usr/bin/env bash
# U2e 修复验收:fcu_url=14580(02 脚本新版)连续 3 boot,全部 <=10s 判 PASS。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u2fix_2026-09-28"
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
PASS=0
for B in fb1 fb2 fb3; do
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$B.log" 2>&1 & )
  t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
  ss -uln | grep -q ":14580 " || { echo "$B SITL_FAIL"; clean9; continue; }
  sleep 8
  nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros_$B.log" 2>&1 &
  t1=$(date +%s.%N)
  timeout 120 rostopic echo -p /mavros/state/connected 2>/dev/null | grep --line-buffered -m1 "1$" > /tmp/fixhit_$B || true
  t2=$(date +%s.%N)
  if [ -s /tmp/fixhit_$B ]; then
    EL=$(echo "$t2 $t1" | awk '{printf "%.1f", $1-$2}')
    echo "$B connect=${EL}s" | tee -a fix_results.txt
    ok=$(awk -v e="$EL" 'BEGIN{print (e<=10)?1:0}'); PASS=$((PASS+ok))
  else
    echo "$B connect=TIMEOUT120" | tee -a fix_results.txt
  fi
  clean9
done
echo "PASS_COUNT=$PASS/3" | tee -a fix_results.txt
