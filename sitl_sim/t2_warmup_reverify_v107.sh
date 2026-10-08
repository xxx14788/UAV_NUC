#!/usr/bin/env bash
# t2_warmup_reverify_v107.sh -- T2 v10.7 unit2: warmup pair re-verification batch (post goal-fix)
# prereg: 1b_bias_route/1b_bias_three_prereg_v1.md section 2.3 (frozen criteria) +
#         goal_fix_prereg_v1.md (fix W1-W4). 8 pairs x 2 arms, same night, both arms rerun
#         (old B-arm data banned across nights -- env drift on record).
# Differences vs t1_warmup_campaign_v1131.sh: own OUT path (v11.31 csv untouched),
#         no WU1b_E8P_A1 backfill row (old-harness pathological round excluded).
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
export ROS_HOSTNAME=${ROS_HOSTNAME:-localhost}
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
OUT="$L/t2_results/INPUTFACE/1c_runs/warmup_pairs_v107.csv"
mkdir -p "$(dirname "$OUT")"
echo "cell,arm,tag,verdict,jump,arrive,disarm,warmup_goals,goal_adopted" > "$OUT"
CELLS=(
  "E8P 9.010 0.980 sitl_world_plain A_first"
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
  case "$ORD" in A_first) SEQ="A B";; B_first) SEQ="B A";; esac
  for arm in $SEQ; do
    if [ "$arm" = "A" ]; then WFLAG="--warmup"; else WFLAG=""; fi
    TAG="WU2_${C}_${arm}"
    echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,1.0) world=$W warmup=$arm"
    bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" 1.0 --tag "$TAG" \
        --budget 300 --stoploss $WFLAG > "/tmp/wu2_${C}_${arm}.log" 2>&1
    EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
    RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
    [ -n "$RES" ] || RES="NO-RESULT"
    JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
    ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
    DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
    WG=$(grep -oE "published [0-9]+ goals" "$EV/warmup.log" 2>/dev/null | grep -oE "[0-9]+" || echo 0)
    GA="NA"
    if [ "$arm" = "A" ]; then
      GA=$(grep -m1 -oE "W[0-9]-(PASS|ADOPTED|RESTART|NO-EVIDENCE|READY-TIMEOUT)" "$EV/warmup_goal_adopted.txt" 2>/dev/null | head -1)
      [ -n "$GA" ] || GA="NO-WFILE"
    fi
    echo "$C,$arm,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},$WG,$GA" >> "$OUT"
  done
done
sort -t, -k1,1 -s "$OUT" -o "$OUT"
echo "[$(date +%H:%M:%S)] [warmup-reverify] done -> $OUT"
