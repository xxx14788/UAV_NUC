#!/usr/bin/env bash
# t2_a1_observe_batch.sh -- T2 v10.7 unit4: candidate A1 observe arm (alarm-not-reject)
# Prereg: INPUTFACE/a1_observe_prereg_v1.md (frozen). Cell=N8P x3 rounds.
# Arm = v2 gate config (gate logic PRESENT) + T2_IQG_OBSERVE=1 (zero rejection, METRIC lines).
# Historical contrast (zero new rounds): M3' N8P base 3/3 PASS vs v2 0/3 (m3p_results.md).
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
GATE_YAML="$L/t2_results/INPUTFACE/regen_v2/gate_params_v2.yaml"
[ -f "$GATE_YAML" ] || { echo "[a1] FATAL gate yaml missing"; exit 7; }
CFG_ARM="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/t2_m3p_v2_arm.yaml"
CFG_SRC="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
cp "$CFG_SRC" "$CFG_ARM"
python3 - "$GATE_YAML" "$CFG_ARM" <<'PY'
import sys, yaml, io
gate = yaml.safe_load(open(sys.argv[1]))
cfg_txt = io.open(sys.argv[2], encoding="utf-8").read()
add = {"t2_input_quality_gate": 1, "t2_iqg_min_stereo_ratio": gate["domains"]["global"]["stereo_r"]["L"]}
lines = ["\n# --- REGEN v2 frozen gate params (T2 v10.7 A1 observe arm; identical to M3' v2 arm config) ---"]
for k, v in add.items(): lines.append("%s: %s" % (k, v))
io.open(sys.argv[2], "w", encoding="utf-8").write(cfg_txt + "\n".join(lines) + "\n")
print("[a1] observe arm config written")
PY
export T2_VINS_CONFIG="$CFG_ARM"
export T2_IQG_OBSERVE=1
OUT="$L/t2_results/INPUTFACE/1c_runs/a1_observe_results.csv"
echo "cell,round,tag,verdict,jump,arrive,disarm" > "$OUT"
for R in 1 2 3; do
  TAG="A1OBS_N8P_r${R}"
  echo "[$(date +%H:%M:%S)] == $TAG (v2 gate config + observe=1, zero reject)"
  bash "$L/vins_smoke.sh" --world sitl_world_plain --goal 1.010 8.980 1.0 --tag "$TAG" \
      --budget 300 --stoploss > "/tmp/a1_${TAG}.log" 2>&1
  EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
  [ -n "$RES" ] || RES="NO-RESULT"
  JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
  DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
  echo "N8P,$R,$TAG,${RES:-NA},${JMP:-NA},${ARR:-NA},${DIS:-NA}" >> "$OUT"
  echo "[$(date +%H:%M:%S)] $TAG -> ${RES:-NA} jump=${JMP:-NA} arrive=${ARR:-NA}"
done
echo "[$(date +%H:%M:%S)] [a1-observe] done -> $OUT"
