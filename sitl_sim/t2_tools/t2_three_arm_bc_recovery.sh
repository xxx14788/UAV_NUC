#!/usr/bin/env bash
# t2_three_arm_bc_recovery.sh -- T2 v10.7 unit3: arm B (8 rounds) + arm C (4 rounds) recovery
# prereg: INPUTFACE/1c_design/1c_three_arm_design_prereg_v1.md (frozen; arms B/C unchanged)
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
export ROS_HOSTNAME=${ROS_HOSTNAME:-localhost}
# night_chain 21:35-21:52 ran these with pre-fix editor => all DRY-RUN FAIL. This rerun uses
# the four-bug-fixed t2_bag_editor.py (dry re-verified 03:5x by T2: drop/reorder/repaint all PASS).
# Output: t2_results/INPUTFACE/1c_runs/bc_recovery_results.csv (separate file, T1 csv untouched)
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

ED="$L/t2_tools/t2_bag_editor.py"
RP="$L/analysis/t3_replay.sh"
EV="$L/analysis/t3_replay_eval.py"
RUNS="$L/t2_results/INPUTFACE/1c_runs"
OUT="$RUNS/bc_recovery_results.csv"
mkdir -p "$RUNS"
echo "tag,arm,param,rep,j0_end,jumps_n,ate60,alive" > "$OUT"

MA="$L/vins_smoke_runs/run_X4_1e_E8P_035301/flight.bag"
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
TOPIC_L="/iris_stereo_vins/vins_cam_left/image_raw"
TOPIC_R="/iris_stereo_vins/vins_cam_right/image_raw"
PORT=11313

replay_eval_row() {  # $1=tag $2=arm $3=param $4=rep $5=src_bag
  local TAG="$1" ARM="$2" PARAM="$3" REP="$4" SRCBAG="$5"
  local RD="$L/t3_results/${TAG}"
  local J0="NA" NJ="NA" ATE="NA" AL="0"
  if [ -f "$RD/vins_out.bag" ]; then
    AL=$(cat "$RD/vins_alive.txt" 2>/dev/null | grep -oE '[01]' | tail -1); [ -n "$AL" ] || AL=0
    python3 - "$RD/vins_out.bag" <<'PYJ0' > /tmp/bc_j0.txt 2>/dev/null
import sys, rosbag
pts=[]
with rosbag.Bag(sys.argv[1]) as b:
    for tp,m,ts in b.read_messages(topics=['/vins_estimator/odometry']):
        p=m.pose.pose.position; pts.append((p.x,p.y,p.z))
if len(pts)>10:
    a,z=pts[0],pts[-1]
    print("%.4f"%(((z[0]-a[0])**2+(z[1]-a[1])**2+(z[2]-a[2])**2)**0.5))
PYJ0
    J0=$(cat /tmp/bc_j0.txt 2>/dev/null | grep -oE '^[0-9.]+$' | head -1); [ -n "$J0" ] || J0=NA
    python3 "$EV" "$RD" "$SRCBAG" > /tmp/bc_eval.txt 2>/dev/null
    NJ=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('frame_jumps','NA'))" 2>/dev/null || echo NA)
    ATE=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('ate_after_tstar','NA'))" 2>/dev/null || echo NA)
  fi
  echo "$TAG,$ARM,$PARAM,$REP,$J0,$NJ,$ATE,$AL" >> "$OUT"
  echo "[$(date +%H:%M:%S)] $TAG j0=$J0 jumps=$NJ ate=$ATE alive=$AL"
}

edit_replay() {  # $1=tag $2=srcbag; then arm param rep; then editor args
  local TAG="$1" SRCBAG="$2"; shift 2; local ARM="$1" PARAM="$2" REP="$3"; shift 3
  local EDITED="/tmp/bc_${TAG}_edited.bag"
  echo "[$(date +%H:%M:%S)] == $TAG edit+replay [$*]"
  python3 "$ED" "$SRCBAG" --dry-run --image-topics "$TOPIC_L,$TOPIC_R" --left-topic "$TOPIC_L" --right-topic "$TOPIC_R" "$@" > "/tmp/bc_${TAG}_dry.log" 2>&1 || { echo "$TAG,dryrun-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG DRY-RUN FAIL"; return; }
  python3 "$ED" "$SRCBAG" "$EDITED" --image-topics "$TOPIC_L,$TOPIC_R" --left-topic "$TOPIC_L" --right-topic "$TOPIC_R" "$@" > "/tmp/bc_${TAG}_edit.log" 2>&1 || { echo "$TAG,edit-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG EDIT FAIL"; return; }
  bash "$RP" "$TAG" "$EDITED" "$CFG" "$PORT" > "/tmp/bc_${TAG}.log" 2>&1
  replay_eval_row "$TAG" "$ARM" "$PARAM" "$REP" "$SRCBAG"
  rm -f "$EDITED"
  echo "[$(date +%H:%M:%S)] $TAG edited bag deleted"
}

C_WIN_START=97.88; C_WIN_END=101.88   # frozen from baseline jump band +-2s

for REP in 1 2; do
  edit_replay "3ARM_B_drop3_r${REP}" "$MA" B "drop-periodic-3" "$REP" --mode retiming --retiming-op drop-periodic --drop-every 3
  edit_replay "3ARM_B_drop10_r${REP}" "$MA" B "drop-random-0.10" "$REP" --mode retiming --retiming-op drop-random --drop-frac 0.10 --seed 7
  edit_replay "3ARM_B_down15_r${REP}" "$MA" B "downfreq-15hz" "$REP" --mode retiming --retiming-op downfreq --target-hz 15
  edit_replay "3ARM_B_reord2_r${REP}" "$MA" B "reorder-win2" "$REP" --mode retiming --retiming-op reorder --swap-window 2
done
for REP in 1 2; do
  edit_replay "3ARM_C_ctr_r${REP}" "$MA" C "region=center60" "$REP" --mode repaint --region "0.2,0.2,0.6,0.6" --repaint-mode black --win-start "$C_WIN_START" --win-end "$C_WIN_END"
  edit_replay "3ARM_C_full_r${REP}" "$MA" C "region=full" "$REP" --mode repaint --region "0,0,1,0.999" --repaint-mode black --win-start "$C_WIN_START" --win-end "$C_WIN_END"
done

echo "[$(date +%H:%M:%S)] [bc-recovery] done -> $OUT"
python3 "$L/t2_tools/t1_three_arm_judge.py" > "$RUNS/bc_recovery_judge.txt" 2>&1 || true
echo "[$(date +%H:%M:%S)] [bc-recovery] judge snapshot done"
# v10.10 alive-column fix: batch-tail alive joins from the unified judge output
# (script inline vins_alive.txt read was path-misaligned -> artifact zeros; taskbook v10.10 unit4)
python3 "$L/t2_tools/t2_bc_alive_join.py" "$OUT" "$RUNS/bc_recovery_judge.txt" || true
