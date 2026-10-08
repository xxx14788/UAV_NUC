#!/usr/bin/env bash
# t2_reorder_r1_makeup.sh -- makeup round: 3ARM_B_reord2_r1 (killed by editor bug#5:
# dry-run exit code did not exempt reorder-semantics mono-violations; fixed this night,
# re-verified DRY-RC=0). Appends to bc_recovery_results.csv after header-preserving.
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
ED="$L/t2_tools/t2_bag_editor.py"; RP="$L/analysis/t3_replay.sh"
MA="$L/vins_smoke_runs/run_X4_1e_E8P_035301/flight.bag"
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
TL="/iris_stereo_vins/vins_cam_left/image_raw"; TR="/iris_stereo_vins/vins_cam_right/image_raw"
OUT="$L/t2_results/INPUTFACE/1c_runs/bc_recovery_results.csv"
TAG="3ARM_B_reord2_r1"; EDITED="/tmp/bc_${TAG}_edited.bag"
echo "[$(date +%H:%M:%S)] == makeup $TAG"
python3 "$ED" "$MA" --dry-run --image-topics "$TL,$TR" --left-topic "$TL" --right-topic "$TR" --mode retiming --retiming-op reorder --swap-window 2 > "/tmp/bc_${TAG}_dry.log" 2>&1 \
  || { echo "$TAG,dryrun-fail,reorder-win2,1,NA,NA,NA,0" >> "$OUT"; echo dry-fail; exit 1; }
python3 "$ED" "$MA" "$EDITED" --image-topics "$TL,$TR" --left-topic "$TL" --right-topic "$TR" --mode retiming --retiming-op reorder --swap-window 2 > "/tmp/bc_${TAG}_edit.log" 2>&1 \
  || { echo "$TAG,edit-fail,reorder-win2,1,NA,NA,NA,0" >> "$OUT"; echo edit-fail; exit 1; }
bash "$RP" "$TAG" "$EDITED" "$CFG" 11313 > "/tmp/bc_${TAG}.log" 2>&1
RD="$L/t3_results/${TAG}"
J0=NA; NJ=NA; ATE=NA; AL=0
if [ -f "$RD/vins_out.bag" ]; then
  sleep 3
  AL=$(cat "$RD/vins_alive.txt" 2>/dev/null | grep -oE '[01]' | tail -1); [ -n "$AL" ] || AL=0
  J0=$(source /opt/ros/noetic/setup.bash && python3 - "$RD/vins_out.bag" <<'PYJ0' 2>/dev/null | grep -oE '^[0-9.]+$' | head -1
import sys, rosbag
pts=[]
with rosbag.Bag(sys.argv[1]) as b:
    for tp,m,ts in b.read_messages(topics=['/vins_estimator/odometry']):
        p=m.pose.pose.position; pts.append((p.x,p.y,p.z))
if len(pts)>10:
    a,z=pts[0],pts[-1]
    print("%.4f"%(((z[0]-a[0])**2+(z[1]-a[1])**2+(z[2]-a[2])**2)**0.5))
PYJ0
)
  NJ=$(source /opt/ros/noetic/setup.bash && python3 "$L/analysis/t3_replay_eval.py" "$RD" "$MA" >/dev/null 2>&1; python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('frame_jumps','NA'))" 2>/dev/null)
  ATE=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('ate_after_tstar','NA'))" 2>/dev/null)
fi
echo "$TAG,B,reorder-win2,1,$J0,$NJ,$ATE,$AL" >> "$OUT"
echo "[$(date +%H:%M:%S)] $TAG j0=$J0 jumps=$NJ ate=$ATE alive=$AL"
rm -f "$EDITED"
echo "[$(date +%H:%M:%S)] makeup done"
