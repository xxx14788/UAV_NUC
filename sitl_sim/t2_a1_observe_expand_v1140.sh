#!/bin/bash
# t2_a1_observe_expand_v1140.sh -- 工程合并册单元3: A1 observe 扩批(已授权,12 轮)
# 上位预注册: INPUTFACE/a1_observe_prereg_v1.md (FROZEN; 本批=其"1/3-2/3 混合带→扩批条款"分支)
# 编排: N8P observe r1-r6(判据带按 6 轮折算: 绿≥4/6=base 带[≥2/3]; 0/6=门计算副作用;
#        中带=格子×时序敏感如实注记) + E8P base r1-r3 + S8O base r1-r3(同夜同栈 base 对照)
# E8P 毒域当夜耗尽注记(预承 T2 C-6): E8P 3 轮可能复现双败/断流 — 判读按实况,
#   该格证据面结构性缺失=格级如实注记,非扩批执行失败
# v11.40 新件: ①VINSMD5=libvins_lib.so(代码在共享库,node 薄壳——T1 v11.2 勘误承袭)
#   ②j0_decomp 步内置(每轮,unit5 分型面通道;失败不阻塞轮判读)
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
GATE_YAML="$L/t2_results/INPUTFACE/regen_v2/gate_params_v2.yaml"
[ -f "$GATE_YAML" ] || { echo "[a1x] FATAL gate yaml missing"; exit 7; }
CFG_ARM="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/t2_m3p_v2_arm.yaml"
CFG_SRC="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
cp "$CFG_SRC" "$CFG_ARM"
python3 - "$GATE_YAML" "$CFG_ARM" <<'PY'
import sys, yaml, io
gate = yaml.safe_load(open(sys.argv[1]))
cfg_txt = io.open(sys.argv[2], encoding="utf-8").read()
add = {"t2_input_quality_gate": 1, "t2_iqg_min_stereo_ratio": gate["domains"]["global"]["stereo_r"]["L"]}
lines = ["\n# --- REGEN v2 frozen gate params (observe arm; identical to original a1 batch) ---"]
for k, v in add.items(): lines.append("%s: %s" % (k, v))
io.open(sys.argv[2], "w", encoding="utf-8").write(cfg_txt + "\n".join(lines) + "\n")
print("[a1x] observe arm config written")
PY
LIBVINS=$(find "$HOME/catkin_ws/devel" -name 'libvins_lib.so' 2>/dev/null | head -1)
VINSMD5=$(md5sum "$LIBVINS" | cut -d' ' -f1)
echo "[$(date +%H:%M:%S)] [a1x] start libvins_lib.so md5=$VINSMD5 ($(basename "$LIBVINS"))"
OUT="$L/t2_results/INPUTFACE/1c_runs/a1_observe_expand_v1140.csv"
echo "cell,arm,round,tag,verdict,jump,arrive,disarm,vinsmd5" > "$OUT"

run_round() {
  local C=$1 ARM=$2 R=$3 GX=$4 GY=$5 W=$6
  local TAG="A1X_${C}_${ARM}_r${R}"
  if [ "$ARM" = "base" ]; then
    unset T2_VINS_CONFIG T2_IQG_OBSERVE
  else
    export T2_VINS_CONFIG="$CFG_ARM"
    export T2_IQG_OBSERVE=1
  fi
  echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,1.0) world=$W arm=$ARM"
  bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" 1.0 --tag "$TAG" \
      --budget 300 --stoploss > "/tmp/a1x_${TAG}.log" 2>&1
  local EV RES JMP ARR DIS
  EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
  [ -n "$RES" ] || RES="NO-RESULT"
  JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
  DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
  # j0_decomp 步内置(v11.40; 失败不阻塞轮判读)
  [ -n "$EV" ] && [ -d "$EV" ] && python3 "$HOME/catkin_ws/sitl_sim/analysis/t3_wa_gate.py" --j0-decomp "$EV" >/dev/null 2>&1 || true
  echo "$C,$ARM,$R,$TAG,${RES:-NA},${JMP:-NA},${ARR:-NA},${DIS:-NA},$VINSMD5" >> "$OUT"
  echo "[$(date +%H:%M:%S)] $TAG -> ${RES:-NA} jump=${JMP:-NA} arrive=${ARR:-NA} disarm=${DIS:-NA}"
}

for R in 1 2 3 4 5 6; do run_round N8P observe $R 1.010 8.980 sitl_world_plain; done
for R in 1 2 3; do run_round E8P base $R 9.010 0.980 sitl_world_plain; done
for R in 1 2 3; do run_round S8O base $R 1.010 -7.020 sitl_world_obstacles; done
unset T2_VINS_CONFIG T2_IQG_OBSERVE
echo "[$(date +%H:%M:%S)] [a1x] done -> $OUT (判读: N8P observe 绿带 ≥4/6=base 带; E8P 毒域按实况注记)"
