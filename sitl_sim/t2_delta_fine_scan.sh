#!/usr/bin/env bash
# t2_delta_fine_scan.sh -- T2 v10.7 unit4: delta fine scan to locate the phase-transition point dc
# Prereg (frozen in this header): arm A machinery already established (v11.31 verdict:
#   d<=2ms jump-waterfall band / d>=5ms bit-exact converged state 55.041@104.5 + 11 jumps).
# This scan adds delta in {2,3,4} ms, r1+r2 each = 6 rounds (~1h). Judgement (written BEFORE data):
#   converged-state criterion = BOTH reps terminal <=60.0 AND jumps <=50 (band of the d>=5 family);
#   waterfall-band criterion   = EITHER rep terminal >=75.0 OR jumps >=500 (band of the d<=2 family);
#   dc localization = smallest scanned d whose BOTH reps meet converged criterion; if d=2 meets it,
#   dc <=2 (contradicts v11.31 band -> recorded honestly); if d=4 does not, dc>4, band widens to
#   (4,5). Between-states outcomes recorded as mixed and dc reported as an interval.
# Mechanism hypothesis ranking (pre-registered): H-td-online (td estimator absorbs sub-dc offsets
#   without state perturbation) > H-pairing-threshold (dual-stream pairing gate path). dc value
#   itself is the discriminating evidence: dc near td-estimation noise floor -> H-td-online.
# Side product: real-machine td control domain |td| < dc (quantified).
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
export ROS_HOSTNAME=${ROS_HOSTNAME:-localhost}
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
ED="$L/t2_tools/t2_bag_editor.py"
RP="$L/analysis/t3_replay.sh"
EV="$L/analysis/t3_replay_eval.py"
OUT="$L/t2_results/INPUTFACE/1c_runs/delta_fine_scan.csv"
mkdir -p "$(dirname "$OUT")"
echo "tag,arm,param,rep,j0_end,jumps_n,ate60,alive" > "$OUT"
MA="$L/vins_smoke_runs/run_X4_1e_E8P_035301/flight.bag"
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
TOPIC_L="/iris_stereo_vins/vins_cam_left/image_raw"
TOPIC_R="/iris_stereo_vins/vins_cam_right/image_raw"
PORT=11313

replay_eval_row() {
  local TAG="$1" ARM="$2" PARAM="$3" REP="$4" SRCBAG="$5"
  local RD="$L/t3_results/${TAG}"
  local J0="NA" NJ="NA" ATE="NA" AL="0"
  if [ -f "$RD/vins_out.bag" ]; then
    AL=$(cat "$RD/vins_alive.txt" 2>/dev/null | grep -oE '[01]' | tail -1); [ -n "$AL" ] || AL=0
    python3 - "$RD/vins_out.bag" <<'PYJ0' > /tmp/dfs_j0.txt 2>/dev/null
import sys, rosbag
pts=[]
with rosbag.Bag(sys.argv[1]) as b:
    for tp,m,ts in b.read_messages(topics=['/vins_estimator/odometry']):
        p=m.pose.pose.position; pts.append((p.x,p.y,p.z))
if len(pts)>10:
    a,z=pts[0],pts[-1]
    print("%.4f"%(((z[0]-a[0])**2+(z[1]-a[1])**2+(z[2]-a[2])**2)**0.5))
PYJ0
    J0=$(cat /tmp/dfs_j0.txt 2>/dev/null | grep -oE '^[0-9.]+$' | head -1); [ -n "$J0" ] || J0=NA
    python3 "$EV" "$RD" "$SRCBAG" > /tmp/dfs_eval.txt 2>/dev/null
    NJ=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('frame_jumps','NA'))" 2>/dev/null || echo NA)
    ATE=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('ate_after_tstar','NA'))" 2>/dev/null || echo NA)
  fi
  echo "$TAG,$ARM,$PARAM,$REP,$J0,$NJ,$ATE,$AL" >> "$OUT"
  echo "[$(date +%H:%M:%S)] $TAG j0=$J0 jumps=$NJ ate=$ATE alive=$AL"
}

edit_replay() {
  local TAG="$1" SRCBAG="$2"; shift 2; local ARM="$1" PARAM="$2" REP="$3"; shift 3
  local EDITED="/tmp/dfs_${TAG}_edited.bag"
  echo "[$(date +%H:%M:%S)] == $TAG edit+replay [$*]"
  python3 "$ED" "$SRCBAG" --dry-run --image-topics "$TOPIC_L,$TOPIC_R" --left-topic "$TOPIC_L" --right-topic "$TOPIC_R" "$@" > "/tmp/dfs_${TAG}_dry.log" 2>&1 || { echo "$TAG,dryrun-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG DRY-RUN FAIL"; return; }
  python3 "$ED" "$SRCBAG" "$EDITED" --image-topics "$TOPIC_L,$TOPIC_R" --left-topic "$TOPIC_L" --right-topic "$TOPIC_R" "$@" > "/tmp/dfs_${TAG}_edit.log" 2>&1 || { echo "$TAG,edit-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG EDIT FAIL"; return; }
  bash "$RP" "$TAG" "$EDITED" "$CFG" "$PORT" > "/tmp/dfs_${TAG}.log" 2>&1
  replay_eval_row "$TAG" "$ARM" "$PARAM" "$REP" "$SRCBAG"
  rm -f "$EDITED"
  echo "[$(date +%H:%M:%S)] $TAG edited bag deleted"
}

for REP in 1 2; do
  for D in 2 3 4; do
    edit_replay "DFS_A_MA_d${D}_r${REP}" "$MA" A "delta=${D}ms" "$REP" \
      --mode retstamp --align offset --delta-ms "$D" --stamp-target right
  done
done
echo "[$(date +%H:%M:%S)] [delta-fine-scan] done -> $OUT"
