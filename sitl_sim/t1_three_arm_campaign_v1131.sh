#!/usr/bin/env bash
# t1_three_arm_campaign_v1131.sh -- T1 v11.31 单元 1d 三臂实验(历史代号 1c)
# prereg 正源: t2_results/INPUTFACE/1c_design/1c_three_arm_design_prereg_v1.md(冻结)
# 執行偏差登记: 臂A M-A δ 梯度按字面全 9 点{0,±2,±5,±10,±20}(设计件 §3.1 字面梯度
#   vs §4.4 预算 6 点矛盾——梯度字面为准,零增删;预算 34→40 轮如实注记)
# 编排: 预热批完成后 IO 窗;编辑袋用后即删(磁盘策略);回放=t3_replay.sh 私有 master
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
L="$HOME/sitl_sim"
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

ED="$L/t2_tools/t2_bag_editor.py"
RP="$L/analysis/t3_replay.sh"
EV="$L/analysis/t3_replay_eval.py"
RUNS="$L/t2_results/INPUTFACE/1c_runs"
OUT="$L/t1_evidence/v11_31_2026-10-08/unit1_greenrate/three_arm_results.csv"
mkdir -p "$RUNS"
echo "tag,arm,param,rep,j0_end,jumps_n,ate60,alive" > "$OUT"

MA="$L/vins_smoke_runs/run_X4_1e_E8P_035301/flight.bag"
MB="$L/vins_smoke_runs/run_X4_1e_HVNET1_040009/flight.bag"
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
PORT=11313

replay_eval_row() {  # $1=tag $2=arm $3=param $4=rep $5=src_bag(真值袋=源袋)
  local TAG="$1" ARM="$2" PARAM="$3" REP="$4" SRCBAG="$5"
  local RD="$L/t3_results/${TAG}"
  local J0="NA" NJ="NA" ATE="NA" AL="0"
  if [ -f "$RD/vins_out.bag" ]; then
    AL=$(cat "$RD/vins_alive.txt" 2>/dev/null | grep -oE '[01]' | tail -1); [ -n "$AL" ] || AL=0
    python3 - "$RD/vins_out.bag" <<'PYJ0' > /tmp/ta_j0.txt 2>/dev/null
import sys, rosbag
pts=[]
with rosbag.Bag(sys.argv[1]) as b:
    for tp,m,ts in b.read_messages(topics=['/vins_estimator/odometry']):
        p=m.pose.pose.position; pts.append((p.x,p.y,p.z))
if len(pts)>10:
    a,z=pts[0],pts[-1]
    print("%.4f"%(((z[0]-a[0])**2+(z[1]-a[1])**2+(z[2]-a[2])**2)**0.5))
PYJ0
    J0=$(cat /tmp/ta_j0.txt 2>/dev/null | grep -oE '^[0-9.]+$' | head -1); [ -n "$J0" ] || J0=NA
    python3 "$EV" "$RD" "$SRCBAG" > /tmp/ta_eval.txt 2>/dev/null
    NJ=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('frame_jumps','NA'))" 2>/dev/null || echo NA)
    ATE=$(python3 -c "import json;d=json.load(open('$RD/eval.json'));print(d.get('ate_after_tstar','NA'))" 2>/dev/null || echo NA)
  fi
  echo "$TAG,$ARM,$PARAM,$REP,$J0,$NJ,$ATE,$AL" >> "$OUT"
  echo "[$(date +%H:%M:%S)] $TAG j0=$J0 jumps=$NJ ate=$ATE alive=$AL"
}

replay_once() {  # $1=tag $2=bag(=真值袋) $3=arm $4=param $5=rep
  local TAG="$1" BAG="$2"
  echo "[$(date +%H:%M:%S)] == $TAG replay $(basename $BAG)"
  bash "$RP" "$TAG" "$BAG" "$CFG" "$PORT" > "/tmp/ta_${TAG}.log" 2>&1
  replay_eval_row "$TAG" "$3" "$4" "$5" "$BAG"
}

edit_replay() {  # $1=tag $2=srcbag $3..=editor args; 追加: arm param rep
  local TAG="$1" SRCBAG="$2"; shift 2; local ARM="$1" PARAM="$2" REP="$3"; shift 3
  local EDITED="/tmp/ta_${TAG}_edited.bag"
  echo "[$(date +%H:%M:%S)] == $TAG edit+replay [$*]"
  python3 "$ED" "$SRCBAG" --dry-run "$@" > "/tmp/ta_${TAG}_dry.log" 2>&1 || { echo "$TAG,dryrun-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG DRY-RUN FAIL"; return; }
  python3 "$ED" "$SRCBAG" "$EDITED" "$@" > "/tmp/ta_${TAG}_edit.log" 2>&1 || { echo "$TAG,edit-fail,$PARAM,$REP,NA,NA,NA,0" >> "$OUT"; echo "[$(date +%H:%M:%S)] $TAG EDIT FAIL"; return; }
  bash "$RP" "$TAG" "$EDITED" "$CFG" "$PORT" > "/tmp/ta_${TAG}.log" 2>&1
  replay_eval_row "$TAG" "$ARM" "$PARAM" "$REP" "$SRCBAG"
  rm -f "$EDITED"   # 磁盘策略: 用后即删
  echo "[$(date +%H:%M:%S)] $TAG edited bag deleted"
}

STAGE="${STAGE:-all}"   # all=base+A+B+C; base=仅阶段0; arms_ab=阶段1+2; arm_c=阶段3(需C_WIN_*)
if [ "$STAGE" = "base" ] || [ "$STAGE" = "all" ]; then
# ---------- 阶段 0: baseline 2x2 (§4.0 复现门) ----------
replay_once 3ARM_base_MA_r1 "$MA" base MA r1
replay_once 3ARM_base_MA_r2 "$MA" base MA r2
replay_once 3ARM_base_MB_r1 "$MB" base MB r1
replay_once 3ARM_base_MB_r2 "$MB" base MB r2
fi

if [ "$STAGE" = "arms_ab" ] || [ "$STAGE" = "all" ]; then
# ---------- 阶段 1: 臂 A 标戳重写 (M-A 全梯度 9 点 + M-B 3 点) ----------
for REP in 1 2; do
  for D in 0 +2 -2 +5 -5 +10 -10 +20 -20; do
    if [ "$D" = "0" ]; then ALIGN="same"; else ALIGN="offset"; fi
    edit_replay "3ARM_A_MA_d${D}_r${REP}" "$MA" A "delta=${D}ms" "$REP" \
      --mode retstamp --align "$ALIGN" --delta-ms "$D" --stamp-target right
  done
  for D in 0 +10 -10; do
    if [ "$D" = "0" ]; then ALIGN="same"; else ALIGN="offset"; fi
    edit_replay "3ARM_A_MB_d${D}_r${REP}" "$MB" A "delta=${D}ms" "$REP" \
      --mode retstamp --align "$ALIGN" --delta-ms "$D" --stamp-target right
  done
done

# ---------- 阶段 2: 臂 B 帧节奏四操作 (M-A) ----------
for REP in 1 2; do
  edit_replay "3ARM_B_drop3_r${REP}" "$MA" B "drop-periodic-3" "$REP" --mode retiming --retiming-op drop-periodic --drop-every 3
  edit_replay "3ARM_B_drop10_r${REP}" "$MA" B "drop-random-0.10" "$REP" --mode retiming --retiming-op drop-random --drop-frac 0.10 --seed 7
  edit_replay "3ARM_B_down15_r${REP}" "$MA" B "downfreq-15hz" "$REP" --mode retiming --retiming-op downfreq --target-hz 15
  edit_replay "3ARM_B_reord2_r${REP}" "$MA" B "reorder-win2" "$REP" --mode retiming --retiming-op reorder --swap-window 2
done

fi

if [ "$STAGE" = "arm_c" ] || [ "$STAGE" = "all" ]; then
# ---------- 阶段 3: 臂 C 帧内容替换 (M-A; 窗=baseline 跳变带±2s 冻结值) ----------
# 环境变量 C_WIN_START/C_WIN_END 必须在启动前设置(从 baseline 结果抄录冻结), 否则跳过
for REP in 1 2; do
  if [ -n "${C_WIN_START:-}" ] && [ -n "${C_WIN_END:-}" ]; then
    edit_replay "3ARM_C_ctr_r${REP}" "$MA" C "region=center60" "$REP" --mode repaint --region "0.2,0.2,0.6,0.6" --repaint-mode black --win-start "$C_WIN_START" --win-end "$C_WIN_END"
    edit_replay "3ARM_C_full_r${REP}" "$MA" C "region=full" "$REP" --mode repaint --region "0,0,1,0.999" --repaint-mode black --win-start "$C_WIN_START" --win-end "$C_WIN_END"
  else
    echo "3ARM_C_ctr_r${REP},C,SKIPPED_NO_WINDOW,$REP,NA,NA,NA,0" >> "$OUT"
    echo "3ARM_C_full_r${REP},C,SKIPPED_NO_WINDOW,$REP,NA,NA,NA,0" >> "$OUT"
  fi
done

echo "[$(date +%H:%M:%S)] [three-arm] done -> $OUT"
fi
