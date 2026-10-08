#!/usr/bin/env bash
# t1_warmup_campaign_v1131.sh -- T1 v11.31 单元 1c 预热对照批
# prereg: INPUTFACE/1b_bias_route/1b_bias_three_prereg_v1.md §2.3 (frozen)
# 设计: 配对>=8对(同格 A=预热臂/B=无预热臂, 奇数格A先偶数格B先平衡顺序效应)
# 控制变量铁律: 其他批一律不加预热; B 臂=vins_smoke 原形态(零 warmup)
# 1b 验证轮 WU1b_E8P_A1 已计入=E8P-A
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
L="$HOME/sitl_sim"
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
OUT="$L/t1_evidence/v11_31_2026-10-08/unit1_greenrate/warmup_pairs.csv"
echo "cell,arm,tag,verdict,jump,arrive,disarm,warmup_goals" > "$OUT"
CELLS=(
  "E8P 9.010 0.980 sitl_world_plain A_done"
  "S12P 1.010 -11.020 sitl_world_plain B_first"
  "S8O 1.010 -7.020 sitl_world_obstacles A_first"
  "E12O 13.010 0.980 sitl_world_obstacles B_first"
  "NE8O 6.667 6.637 sitl_world_obstacles A_first"
  "N8P 1.010 8.980 sitl_world_plain B_first"
  "E12P 13.010 0.980 sitl_world_plain A_first"
  "S8P 1.010 -7.020 sitl_world_plain B_first"
)
for cell in "${CELLS[@]}"; do
  set -- $cell; C=$1; GX=$2; GY=$3; W=$4; ORD=$5
  if [ "$ORD" = "A_done" ]; then SEQ="B"; else
    case "$ORD" in A_first) SEQ="A B";; B_first) SEQ="B A";; esac
  fi
  for arm in $SEQ; do
    if [ "$arm" = "A" ]; then WFLAG="--warmup"; else WFLAG=""; fi
    TAG="WU_${C}_${arm}"
    echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,1.0) world=$W warmup=$arm"
    bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" 1.0 --tag "$TAG" \
        --budget 300 --stoploss $WFLAG > "/tmp/wu_${C}_${arm}.log" 2>&1
    EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
    RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
    [ -n "$RES" ] || RES="NO-RESULT"
    JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
    ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
    DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
    WG=$(grep -oE "published [0-9]+ goals" "$EV/warmup.log" 2>/dev/null | grep -oE "[0-9]+" || echo 0)
    echo "$C,$arm,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},$WG" >> "$OUT"
  done
done
# E8P-A 补录行(1b 轮)
EV1=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_WU1b_E8P_A1_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
RES1=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV1/RESULT.txt" 2>/dev/null | cut -d= -f2)
JMP1=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV1/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
ARR1=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV1/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
DIS1=$(grep -m1 -oE "auto_disarm->[01]" "$EV1/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
WG1=$(grep -oE "published [0-9]+ goals" "$EV1/warmup.log" 2>/dev/null | grep -oE "[0-9]+" || echo 0)
echo "E8P,A,WU1b_E8P_A1,${RES1:-NA},${JMP1:-NA},${ARR1:-NA},${DIS1:-NA},${WG1:-0}" >> "$OUT"
sort -t, -k1,1 -s "$OUT" -o "$OUT"
echo "[$(date +%H:%M:%S)] [warmup-campaign] done -> $OUT"
