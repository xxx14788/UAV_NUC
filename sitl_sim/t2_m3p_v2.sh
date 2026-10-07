#!/usr/bin/env bash
# t2_m3p_v2.sh -- M3prime batch (REGEN v2 frozen arm vs baseline arm)
# usage: t2_m3p_v2.sh <v2|base>   (config md5 NOTE: T2_VINS_CONFIG arm also
# dumps its own md5 into round dir as vins_config_v2.md5 -- smoke.sh md5 file
# still records the default config, cross-check both)
# Prereg: REGEN_PREREG_v2 (frozen) section 4; roster = v1 frozen six cells x3
set -u
L="$HOME/sitl_sim"
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
export ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

ARM="${1:?v2|base}"
GATE_YAML="$L/t2_results/INPUTFACE/regen_v2/gate_params_v2.yaml"
if [ "$ARM" = "v2" ]; then
  [ -f "$GATE_YAML" ] || { echo "[m3p] FATAL gate yaml missing"; exit 7; }
  # build arm config = default config + v2 gate keys appended (YAML flat merge)
  CFG_SRC="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
  CFG_ARM="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/t2_m3p_v2_arm.yaml"
  cp "$CFG_SRC" "$CFG_ARM"
  python3 - "$GATE_YAML" "$CFG_ARM" <<'PY'
import sys, yaml, io
gate = yaml.safe_load(open(sys.argv[1]))
cfg_txt = io.open(sys.argv[2], encoding="utf-8").read()
add = {
  "t2_input_quality_gate": 1,
  "t2_iqg_min_stereo_ratio": gate["domains"]["global"]["stereo_r"]["L"],
}
lines = ["\n# --- REGEN v2 frozen gate params (T2 v10.4 M3prime arm) ---"]
for k, v in add.items():
    lines.append("%s: %s" % (k, v))
io.open(sys.argv[2], "w", encoding="utf-8").write(cfg_txt + "\n".join(lines) + "\n")
print("[m3p] v2 arm config written:", sys.argv[2])
PY
  export T2_VINS_CONFIG="$CFG_ARM"
  md5sum "$CFG_ARM" > "$L/t2_results/INPUTFACE/regen_v2/v2_arm_config.md5"
else
  unset T2_VINS_CONFIG || true
fi

OUT="$L/t3_results/m3p_${ARM}_report.csv"
mkdir -p "$(dirname "$OUT")"
echo "cell,round,tag,verdict,jump,arrive,disarm,iqg_rejects" > "$OUT"
CELLS=(
  "E8P 9.010 0.980 1.0 sitl_world_plain"
  "S12P 1.010 -11.020 1.0 sitl_world_plain"
  "S8O 1.010 -7.020 1.0 sitl_world_obstacles"
  "E12O 13.010 0.980 1.0 sitl_world_obstacles"
  "NE8O 6.667 6.637 1.0 sitl_world_obstacles"
  "N8P 1.010 8.980 1.0 sitl_world_plain"
)
N_ROUNDS=3
for cell in "${CELLS[@]}"; do
  set -- $cell; C=$1; GX=$2; GY=$3; GZ=$4; W=$5
  for r in $(seq 1 "$N_ROUNDS"); do
    TAG="M3p${ARM}_${C}_$r"
    echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,$GZ) world=$W"
    bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" "$GZ" \
        --tag "$TAG" --budget 300 --stoploss > "/tmp/m3p_${TAG}.log" 2>&1
    EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
    [ -n "$EV" ] && cp "$EV/RESULT.txt" "/tmp/m3p_${TAG}_RESULT.txt" 2>/dev/null
    RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
    [ -n "$RES" ] || RES="NO-RESULT"
    JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
    ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
    DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
    IQG=$(grep -c "T2IQG] REJECT" "$EV/simvins.log" 2>/dev/null || echo 0)
    echo "$C,$r,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},$IQG" >> "$OUT"
  done
done
echo "[$(date +%H:%M:%S)] [m3p] arm=$ARM batch done -> $OUT"
