#!/usr/bin/env bash
# connect 计时探针:从 mavros 启动到第一条 connected:True
# 用法: u2_probe.sh <mavros_log> <timeout_s>
LOG="$1"; TMO="${2:-150}"
t0=$(date +%s.%N)
# 长驻订阅,一次建连持续收(避免每次 echo 新建连受 U3 停滞影响)
( timeout "$TMO" rostopic echo -p /mavros/state/connected 2>/dev/null | grep --line-buffered -m1 "1$" > /tmp/u2_probe_hit.$$ ) &
GREPPID=$!
wait $GREPPID 2>/dev/null
now=$(date +%s.%N)
if [ -s /tmp/u2_probe_hit.$$ ]; then
  echo "PROBE_RESULT=CONNECTED elapsed=$(echo "$now $t0" | awk '{printf "%.1f", $1-$2}')s"
  grep -n "CON:.*[Hh]eartbeat\|TM :" "$LOG" 2>/dev/null | head -5
else
  echo "PROBE_RESULT=TIMEOUT after=${TMO}s"
  grep -n "CON:.*[Hh]eartbeat\|TM :\|CON:" "$LOG" 2>/dev/null | head -8
fi
rm -f /tmp/u2_probe_hit.$$
