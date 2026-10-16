#!/bin/bash
# c3a_hover_batch.sh — Phase A 悬停轮批（③C-甲 §二配对实验；预注册 C65 件）
# 用法: c3a_hover_batch.sh <tagPrefix> <n>      例: c3a_hover_batch.sh C3A2B 3 → C3A2B1/2/3
# 配方（锁定）: world=sitl_world_corridor_v73（正名!）goal=1.51 0.98 1.0 budget=90; δ探针随轮; 判读=c3a_hover_judge.py
# 每轮附加: j0d 证书（wa_gate --j0-decomp, 观察面不设门）; ulg 快照指针。
source /opt/ros/noetic/setup.bash 2>/dev/null
L="$HOME/sitl_sim"; WS="$HOME/catkin_ws"
CAMP="$L/c3_corridor_20261013"
SUM="$CAMP/phaseA_hover_report.md"
WA="$L/analysis/t3_wa_gate.py"
w() { echo "[$(date '+%F %T')] $*" | tee -a "$SUM"; }
PFX="$1"; N="${2:-3}"
w "==== hover sub-batch $PFX x$N start (world v73 正名, budget 90) ===="
for i in $(seq 1 "$N"); do
  tag="${PFX}${i}"
  w "---- hover round $tag ----"
  rm -f "/tmp/c3_delta_${tag}.tsv"
  nohup python3 "$CAMP/c3_delta_probe.py" "/tmp/c3_delta_${tag}.tsv" >/dev/null 2>&1 &
  PROBE_PID=$!
  T2_IQG_OBSERVE=1 bash "$L/vins_smoke.sh" --world sitl_world_corridor_${C3A_HOVER_WORLD:-v73} --goal 1.51 0.98 1.0 \
       --tag "$tag" --budget 90 2>&1 | tail -4 | tee -a "$SUM"
  kill "$PROBE_PID" 2>/dev/null
  d=$(ls -dt "$L"/vins_smoke_runs/run_${tag}_* 2>/dev/null | head -1)
  if [ -n "$d" ] && [ -f "$d/flight.bag" ]; then
    python3 "$CAMP/c3a_hover_judge.py" "$d" 2>&1 | tee -a "$SUM"
    [ -f "/tmp/c3_delta_${tag}.tsv" ] && cp "/tmp/c3_delta_${tag}.tsv" "$d/" 2>/dev/null
    [ ! -f "$d/j0_decomp.json" ] && python3 "$WA" --j0-decomp "$d" >> "$SUM" 2>&1
    ls -t "$HOME/PX4-Autopilot/build/px4_sitl_default/rootfs/log/"*/*.ulg 2>/dev/null | head -1 > "/tmp/c3_ulg_${tag}.txt"
    w "ulg snapshot for $tag: $(cat /tmp/c3_ulg_${tag}.txt 2>/dev/null)"
  else
    w "WARN: no run dir/bag for $tag"
  fi
done
w "==== $PFX sub-batch end ===="
