#!/usr/bin/env bash
# t2_bias_box_arm_v1010.sh -- T2 v10.10 unit2: constraint-2a box arm batch
# prereg: 1b_bias_route/bias_constraint2_design_v1.md (c16f59c1 frozen) +
#         1b_bias_route/box_arm_batch_prereg_v1010.md (three-layer preset, pre-batch)
# 8 pairs x 2 arms, same night same stack. A = env T2_BIAS_BOX=1 (box on),
# B = no env (default 0 = zero bounds = legacy). ONE config file both arms
# (control-variable iron rule); arm identity carried by env + [T2BIASBOX] banner.
# ENV-FAIL / NO-RESULT = one environmental retry per round (X-line precedent).
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
export ROS_HOSTNAME=${ROS_HOSTNAME:-localhost}
unset T2_BIAS_BOX   # belt-and-braces: batch-level default = off
export SMOKE_OWNER="T2-v1010-BX"   # lock owner prefix: clear line ownership (default T3- misleading)
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
OUT="$L/t2_results/INPUTFACE/1b_bias_route/box_pairs_v1010.csv"
mkdir -p "$(dirname "$OUT")"
VINSMD5=$(md5sum "$HOME/catkin_ws/devel/lib/vins/vins_node" | cut -d' ' -f1)
echo "cell,arm,tag,verdict,jump,arrive,disarm,indom_pct,dbadt,max_bas,tic0_drift,box_banner,vins_md5" > "$OUT"
echo "[$(date +%H:%M:%S)] [box-arm] start vins_node_md5=$VINSMD5"
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
    TAG="BX_${C}_${arm}"
    if [ "$arm" = "A" ]; then export T2_BIAS_BOX=1; else unset T2_BIAS_BOX; fi
    for ATTEMPT in 1 2; do
      if [ "$ATTEMPT" = "2" ]; then TAG="${TAG}_r2"; echo "[$(date +%H:%M:%S)] retry $TAG (env rule: 1/round)"; fi
      echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,1.0) world=$W box=$arm"
      bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" 1.0 --tag "$TAG" \
          --budget 300 --stoploss > "/tmp/bx_${C}_${arm}.log" 2>&1
      EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
      RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
      [ -n "$RES" ] || RES="NO-RESULT"
      # env-retry clause: ENV-FAIL / NO-RESULT -> one retry; judged rounds never re-run
      case "$RES" in ENV-FAIL|NO-RESULT) [ "$ATTEMPT" = "1" ] && continue;; esac
      break
    done
    JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
    ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
    DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
    DIAG=$(python3 "$L/t2_tools/t2_box_diag.py" "$EV" 2>/dev/null)
    [ -n "$DIAG" ] || DIAG="NA,NA,NA,NA,NA,NA,NA"
    BAN=$(grep -c "\[T2BIASBOX\] box=1" "$EV/simvins.log" 2>/dev/null); [ "$BAN" -ge 1 ] 2>/dev/null && BAN=1 || BAN=0
    echo "$C,$arm,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},$DIAG,$BAN,$VINSMD5" >> "$OUT"
  done
done
sort -t, -k1,1 -s "$OUT" -o "$OUT"
unset T2_BIAS_BOX
echo "[$(date +%H:%M:%S)] [box-arm] done -> $OUT"
