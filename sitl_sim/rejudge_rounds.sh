#!/usr/bin/env bash
# rejudge_rounds.sh — 批后补判（T1 v11.13；judge_round v2 修复版逻辑独立化）
# 用法: bash rejudge_rounds.sh <run_dir> [<run_dir> ...]
# 输出: 每轮一行 "TAG|dir|RES|T2fail|neverflew|jump|arrive|disarm|cf|CLASS"
# 依据: x4_batch.sh 9592f96c 的 judge_round（RES 前缀/grep -c 双 0/NEVER local 三 bug 修复后语义）
# 坑位: source ROS 必须在 set -u 之前（ROS profile 链未绑变量爆炸）
source /opt/ros/noetic/setup.bash 2>/dev/null || true
WS="$HOME/catkin_ws"
source "$WS/devel/setup.bash" 2>/dev/null || true
set -u
L="$HOME/sitl_sim"

judge() {
  local D="$1" RES FAILN NEVER JUMP ARR CF WA ANCH DISARM CLS
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL)" "$D/RESULT.txt" 2>/dev/null | head -1 | cut -d= -f2)
  [ -n "$RES" ] || RES="NO-RESULT"
  FAILN=$(grep -c "failure detection" "$D/simvins.log" 2>/dev/null); case "$FAILN" in ''|*[!0-9]*) FAILN=0;; esac
  NEVER=$(grep -c "never-flew" "$D/RESULT.txt" 2>/dev/null); case "$NEVER" in ''|*[!0-9]*) NEVER=0;; esac
  JUMP=$(grep -m1 -oE "pre-post\|[0-9.]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$" || echo 99.9)
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$" || echo -1)
  DISARM=$(grep -m1 -oE "auto_disarm->[01]" "$D/RESULT.txt" 2>/dev/null || echo "?")
  WA=$(python3 "$WS/sitl_sim/analysis/t3_wa_gate.py" --online "$D" 2>/dev/null | grep -m1 "run_")
  CF=$(echo "$WA" | grep -oE "cf=[a-z-]+" | head -1 | cut -d= -f2)
  # 分支预注册（x4_batch 语义）
  if [ "$RES" = "ENV-FAIL" ]; then CLS="env";
  elif [ "$NEVER" -ge 1 ] || [ "$FAILN" -ge 3 ]; then CLS="hostile";
  elif [ "$RES" = "PASS" ]; then CLS="green";
  elif [ "${CF:-}" = "controlled" ]; then CLS="green";
  elif [ "$RES" = "FAIL" ]; then
    local doorok; doorok=$(python3 -c "print(1 if float('$JUMP')<=0.5 and 0.75<=float('$ARR')<=1.2 else 0)" 2>/dev/null || echo 0)
    if [ "$doorok" = "1" ]; then CLS="door"; else CLS="fail"; fi
  else CLS="undetermined"; fi
  echo "$(basename "$D")|$D|RES=$RES|fail=$FAILN|never=$NEVER|jump=$JUMP|arr=$ARR|$DISARM|cf=${CF:-?}|CLASS=$CLS"
}

for d in "$@"; do [ -d "$d" ] && judge "$d" || echo "$(basename "$d")|$d|MISSING-DIR|CLASS=undetermined"; done
