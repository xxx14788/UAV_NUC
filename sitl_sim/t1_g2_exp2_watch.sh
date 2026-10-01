#!/usr/bin/env bash
# t1_g2_exp2_watch.sh — C05 慢链路退化签名 EXP-2 白天常驻被动仪表 (T1 2026-10-01 部署)
# 设计依据: plans/directions/C05_slow-link-degradation-signature/DOSSIER.md EXP-2 §(238-252)
# 旁路纪律: 不动任何现有脚本主流程; 0 夜锁(不占 SITL 锁); 探针自计匿名注册数(v3 AMP-1);
#           单探针墙钟超时 600s; 删失/实值分列; 每 rosmaster boot 一轮采集。
# 采集面五项: ①探针墙钟T ②master拓扑/寿命 ③master.log增量 ④D(n)+fd/线程 ⑤RTF伴生
# 用法: nohup bash t1_g2_exp2_watch.sh >/dev/null 2>&1 &   (常驻; 止损=连续3工作日无退化降背景)
set -u
OUT="$HOME/sitl_sim/t1_g2_exp2"
mkdir -p "$OUT"
LOG="$OUT/exp2_ledger.jsonl"
SHELLPY_ROS="source /opt/ros/noetic/setup.bash"
LAST_MASTER_PID=0
DAY0=$(date +%j)

note() { printf '{"t":"%s","boot_pid":%s,"ev":"%s"}\n' "$(date +%F_%T)" "${1:-0}" "$2" >> "$LOG"; }

# ---- 采集一轮(每 master boot 一次) ----
collect() {
  local MPID="$1" TS; TS=$(date +%F_%T)
  local DIR="$OUT/boot_$(date +%F_%H%M%S)_${MPID}"
  mkdir -p "$DIR"
  # ④ D(n) 匿名计数 + fd/线程 (0锁旁路)
  local DN=0 FD=0 TH=0
  DN=$(timeout 5 bash -c "$SHELLPY_ROS; rosnode list 2>/dev/null | wc -l" || echo 0)
  ANON=$(timeout 5 bash -c "$SHELLPY_ROS; rosnode list 2>/dev/null | grep -c 'rostopic_\|rosnode_'" || echo 0)
  if [ -d "/proc/$MPID/fd" ]; then FD=$(ls /proc/$MPID/fd 2>/dev/null | wc -l); TH=$(ls /proc/$MPID/task 2>/dev/null | wc -l); fi
  # ③ master.log 增量归档(sec=/exception= 行)
  local MLOG
  MLOG=$(ls -t ~/.ros/log/*/master.log 2>/dev/null | head -1)
  if [ -n "${MLOG:-}" ] && [ -f "$MLOG" ]; then
    grep -E "sec=|exception" "$MLOG" | tail -200 > "$DIR/master_log_tail.txt" 2>/dev/null
  fi
  # ① 单探针墙钟 T (600s 超时, 删失/实值分列, 自计匿名注册数)
  local PROBE_LOG="$DIR/probe_t.json"
  nohup timeout 600 bash -c "$SHELLPY_ROS; python3 - <<'PY'
import json, time, subprocess, os, xmlrpc.client
t0=time.time(); m=os.environ.get(\"ROS_MASTER_URI\",\"http://localhost:11311\")
try:
    c=xmlrpc.client.ServerProxy(m)
    c.getUri(\"/t1_exp2_probe\")          # 探针注册语义: 一次 getUri 调用(非常驻节点,不入D(n)计数面)
    c.deleteParam(\"/t1_exp2_probe\",\"/nonexistent_probe_key\")  # 二次往返
    val=time.time()-t0
    json.dump({\"T_s\":round(val,3),\"censored\":False,\"uri\":m}, open(\"PROBE_LOG\",\"w\")) 
except Exception as e:
    json.dump({\"T_s\":None,\"censored\":True,\"err\":str(e)[:120],\"elapsed\":round(time.time()-t0,1)}, open(\"PROBE_LOG\",\"w\"))
PY" > /dev/null 2>&1 &
  # 等探针收尾(最多 60s 快路径; 慢路径由 600s timeout 兜底, 下轮 boot 读取)
  sleep 45
  # ⑤ RTF 伴生(gazebo 在跑时) + 拓扑快照
  local RTF="null"
  if pgrep -x gzserver >/dev/null 2>&1; then
    RTF=$(timeout 6 bash -c "$SHELLPY_ROS; timeout 5 rostopic echo -n1 /clock 2>/dev/null" | grep -c sec || echo 0)
  fi
  local TOPO="shared"
  bash -c "$SHELLPY_ROS; rosparam list / >/dev/null 2>&1" || TOPO="unreachable"
  if pgrep -af "rosmaster -p 113" >/dev/null 2>&1; then TOPO="$TOPO+private-port"; fi
  # ② master 拓扑/寿命 + 汇总行
  printf '{"ts":"%s","master_pid":%s,"D_n":%s,"anon":%s,"master_fd":%s,"master_thr":%s,"topo":"%s","rtf_probe":"%s"}\n' \
    "$TS" "$MPID" "${DN:-0}" "${ANON:-0}" "$FD" "$TH" "$TOPO" "$RTF" >> "$OUT/boot_summary.jsonl"
  [ -f "$PROBE_LOG" ] && cp "$PROBE_LOG" "$DIR/probe_final.json" 2>/dev/null
  note "$MPID" "collected"
}

# ---- 主循环: 监视 rosmaster boot 边沿 ----
note 0 "exp2-watch-start"
while true; do
  MPID=$(pgrep -x rosmaster | head -1)
  if [ -n "${MPID:-}" ] && [ "$MPID" != "$LAST_MASTER_PID" ]; then
    if [ "$LAST_MASTER_PID" != 0 ]; then
      note "$MPID" "new-master-boot(last=$LAST_MASTER_PID)"
    fi
    LAST_MASTER_PID=$MPID
    collect "$MPID"
  fi
  # 止损检查: 3 个工作日无退化降背景(简化: 每 7 天提示复核)
  if [ $(( $(date +%j) - DAY0 )) -ge 7 ]; then note 0 "week-rollover-review-due"; DAY0=$(date +%j); fi
  sleep 60
done
