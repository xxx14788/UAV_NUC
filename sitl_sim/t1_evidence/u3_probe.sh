#!/usr/bin/env bash
# U3:TCPROS 新建连时延序列测量(只读)。在 SITL 重启窗口内每 2s 建 1 个新 sub,
# 分别测 到px4ctrl的pub(fsm_state) 与 到mavros的pub(state) 的建连时延。
# 用法: u3_probe.sh <label>  (每轮输出一行 CSV)
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u3_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
L="$1"
t_start=$(date +%s.%N)
i=0
while [ $i -lt 90 ]; do
  i=$((i+1))
  t0=$(date +%s.%N)
  FSM=$(timeout 10 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state 2>/dev/null | head -1)
  t1=$(date +%s.%N)
  ST=$(timeout 10 rostopic echo -n1 /mavros/state/connected 2>/dev/null | head -1)
  t2=$(date +%s.%N)
  echo "$L,$i,$(echo "$t_start" | cut -c1-19),$(echo "$t1 $t0" | awk '{printf "%.2f", $1-$2}'),$(echo "$t2 $t1" | awk '{printf "%.2f", $1-$2}'),${FSM:-NONE},${ST:-NONE}" >> u3_probe.csv
  echo "[$L] #$i fsm=$(echo "$t1 $t0" | awk '{printf "%.1f", $1-$2}')s state=$(echo "$t2 $t1" | awk '{printf "%.1f", $1-$2}')s fsm_val=${FSM:-NONE}"
  if [ "$i" = 45 ]; then
    ss -tnp > "u3_ss_mid_$L.txt" 2>&1
    rosnode list > "u3_rosnode_mid_$L.txt" 2>&1
  fi
  sleep 2
done
