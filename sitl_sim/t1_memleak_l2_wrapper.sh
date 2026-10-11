#!/usr/bin/env bash
# t1_memleak_l2_wrapper.sh — L2 loopmain+重启包装（工程 v1.6 单元2; slowmain 停摆后切换案）
# 机理: bag --loop 全速=唯一同时可测泄漏(smoke 620MB/h)且连续处理的模式; SIGBUS 随机死亡由本包装
#       循环重启兜底; 每实例 L2 脚本自管 teardown+interpret; 窗毕聚合各实例 PEAK 面。
# 用法: t1_memleak_l2_wrapper.sh <总预算秒,默认 6000>
set -u
BUDGET_TOTAL="${1:-6000}"
L="$HOME/sitl_sim"
EVROOT="$L/t1_evidence/v113_2026-10-11/memleak_l2"
mkdir -p "$EVROOT"
START=$(date +%s)
N=0
while [ $(( $(date +%s) - START )) -lt $(( BUDGET_TOTAL - 300 )) ]; do
  N=$((N+1))
  echo "[wrap $(date +%H:%M:%S)] instance $N start (budget left $(( BUDGET_TOTAL - ($(date +%s) - START) ))s)"
  C1_L2_MODE=loopmain C1_L2_DUR=600 bash "$L/t1_memleak_l2.sh" > "$EVROOT/wrap_inst${N}_outer.log" 2>&1
  RC=$?
  echo "[wrap $(date +%H:%M:%S)] instance $N end rc=$RC"
  # 实例间清残留(master 域内)
  for p in $(pgrep -x vins_node); do
    m=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    [ "${m:-x}" = "http://localhost:11312" ] && kill -9 "$p" 2>/dev/null
  done
  pkill -f "rosbag pla[y].*t2v3_hover" 2>/dev/null
  sleep 3
done
echo "[wrap $(date +%H:%M:%S)] budget end; instances=$N"
# ---------- 聚合: 各实例 PEAK 面合并 ----------
AGG="$EVROOT/l2_aggregate_$(date +%H%M%S).txt"
{
  echo "=== L2 loopmain wrapper 聚合 $(date -Is) instances=$N ==="
  for d in "$EVROOT"/l2_loopmain_*; do
    HT=$(ls "$d"/heaptrack.vins_node.*.gz 2>/dev/null | head -1)
    [ -z "$HT" ] && continue
    SZ=$(stat -c%s "$HT")
    echo "--- $(basename $d) heaptrack=${SZ}B rss_tail: $(tail -2 $d/rss.csv | head -1)"
    if [ -f "$d/heaptrack_interpret.txt" ]; then
      sed -n "/PEAK MEMORY CONSUMERS/,/MOST TEMPORARY/p" "$d/heaptrack_interpret.txt" | head -40
    else
      timeout 300 heaptrack_print "$HT" 2>/dev/null | sed -n "/PEAK MEMORY CONSUMERS/,/MOST TEMPORARY/p" | head -40
    fi
  done
} > "$AGG" 2>&1
echo "[wrap] aggregate -> $AGG ($(wc -l < "$AGG") 行)"
