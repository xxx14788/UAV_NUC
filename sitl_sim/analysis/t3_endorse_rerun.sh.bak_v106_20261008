#!/usr/bin/env bash
# t3_endorse_rerun.sh — X4 背书链影子重跑器（T3 v10.3 单元 3;2026-10-07）
# 协议（沿用 v9.9 x4_batch_endorsement_20261006 实战版）:
#   goal 参数以 goal.txt 为正源（VRFY2 首次传错 goal 教训;禁手抄位形表）;
#   world 从 round.log 'SITL up (<world>)' 行实读;
#   影子目录独立重跑 round_result+t3_wa_gate+t3_trichotomy,与原 RESULT.txt 逐位比对;
#   门拦截轮必含 GATEHIT-STAT/TRICHOTOMY 链复核（恢复链完整性独立验证=tag 前置第二链）。
# 用法: t3_endorse_rerun.sh <run_dir> [more run_dirs...]
# 输出: stdout=背书表行(markdown)+逐位比对结论;非零退出=任何一位不一致
L="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
source /opt/ros/noetic/setup.bash
source "$WS/devel/setup.bash"
set -u
FAIL=0
for D in "$@"; do
  TAG=$(basename "$D" | sed 's/^run_//')
  [ -d "$D" ] || { echo "| $TAG | DIR-MISSING | - | - | - | ✗ |"; FAIL=1; continue; }
  GOAL=$(awk '/^goal:/{print $2, $3, $4}' "$D/goal.txt" 2>/dev/null)
  L2=$(awk '/^goal:.*leg2:/{for(i=1;i<=NF;i++) if($i=="leg2:"){print $(i+1),$(i+2),$(i+3)}}' "$D/goal.txt" 2>/dev/null)
  [ -n "$GOAL" ] || { echo "| $TAG | GOAL-TXT-MISSING | - | - | - | ✗ |"; FAIL=1; continue; }
  WORLD=$(grep -m1 -oE 'SITL up \([a-z_0-9]+\)' "$D/round.log" 2>/dev/null | grep -oE '\([a-z_0-9]+\)' | tr -d '()')
  [ -n "$WORLD" ] || WORLD="sitl_world_obstacles"
  set -- $GOAL; GX=$1; GY=$2; GZ=$3
  HASL2=0; L2X=0; L2Y=0; L2Z=0
  if [ -n "${L2:-}" ]; then
    set -- $L2
    if [ "$(echo "$1 $2 $3" | tr -d '0. ')" != "" ]; then HASL2=1; L2X=$1; L2Y=$2; L2Z=$3; fi
  fi
  ARR=$(head -1 "$D/arrive_watch.txt" 2>/dev/null || echo "NA")
  # 影子重跑（独立目录;判读输入只读原轮）
  SH="/tmp/t3_shadow_$$/$TAG"; mkdir -p "$SH"
  RR=$(bash "$L/round_result.sh" "$D/flight.bag" "$GX" "$GY" "$GZ" "$WORLD" "$D" "$ARR" "$ARR" "$HASL2" "$L2X" "$L2Y" "$L2Z" 2>&1)
  WA=$(python3 "$WS/sitl_sim/analysis/t3_wa_gate.py" --online "$D" 2>/dev/null | grep -m1 "run_")
  CF=$(echo "$WA" | grep -oE "cf=[a-z-]+" | head -1 | cut -d= -f2)
  TRI=$(python3 "$WS/sitl_sim/analysis/t3_trichotomy.py" "$D" --cf "${CF:-none}" 2>/dev/null)
  # 逐位比对（原 RESULT vs 影子）
  OJ=$(grep -m1 -oE 'pre-post\|=[0-9.]+' "$D/RESULT.txt" 2>/dev/null | grep -oE '[0-9.]+$')
  OA=$(grep -m1 -oE 'leg1 到位\(真值\) min=[0-9.-]+' "$D/RESULT.txt" 2>/dev/null | grep -oE '[0-9.-]+$')
  OR=$(grep -m1 -oE 'RESULT=(PASS|FAIL|ENV-FAIL)' "$D/RESULT.txt" 2>/dev/null | cut -d= -f2)
  NJ=$(echo "$RR" | grep -m1 -oE 'pre-post\|=[0-9.]+' | grep -oE '[0-9.]+$')
  NA=$(echo "$RR" | grep -m1 -oE 'leg1 到位\(真值\) min=[0-9.-]+' | grep -oE '[0-9.-]+$')
  NR=$(echo "$RR" | grep -m1 -oE 'RESULT=(PASS|FAIL|ENV-FAIL)' | cut -d= -f2)
  TG=$(echo "$TRI" | grep -m1 'GATEHIT-STAT')
  TC=$(echo "$TRI" | grep -m1 -oE 'class=[a-z_( ;cf面待wa_gate权威-]*' | cut -d= -f2)
  PF=0  # 轮内逐位标志(末列缺陷修复 v1.1:原版用聚积 FAIL,首失配后后续轮末列全误显)
  OKJ=$([ "$OJ" = "$NJ" ] && echo ✓ || echo ✗); { [ "$OJ" = "$NJ" ] || PF=1; FAIL=1; } 2>/dev/null
  OKA=$([ "$OA" = "$NA" ] && echo ✓ || echo ✗); { [ "$OA" = "$NA" ] || PF=1; FAIL=1; } 2>/dev/null
  OKR=$([ "$OR" = "$NR" ] && echo ✓ || echo ✗); { [ "$OR" = "$NR" ] || PF=1; FAIL=1; } 2>/dev/null
  echo "| $TAG | $GOAL | jump $OJ/$NJ$OKJ arrive $OA/$NA$OKA RES $OR/$NR$OKR | cf=${CF:-?} tri=$TC | $TG | $([ $PF = 0 ] && echo ✓ || echo 见上列) |"
done
rm -rf "/tmp/t3_shadow_$$" 2>/dev/null
exit $FAIL
