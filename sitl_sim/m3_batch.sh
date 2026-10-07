#!/usr/bin/env bash
# m3_batch.sh — M3 绿率复测批跑器 (T1 v11.25 阶段 3;判据=REGEN-PREREG v1.1 冻结)
# 六格×≥3 轮串行;ENV-FAIL 重试≤1/格(prereg);批内栈/config 零变动(md5 每 5 轮复验);
# 输出=~/sitl_sim/t3_results/m3_batch_report.csv + 每轮 vins_smoke_runs/run_M3R*
export ROS_DISTRO=noetic ROS_VERSION=1 \
       ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311} \
       ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
L="$HOME/sitl_sim"
OUT="$L/t3_results/m3_batch_report.csv"
mkdir -p "$(dirname "$OUT")"
echo "cell,round,tag,verdict,jump,arrive,disarm,iqg_rejects" > "$OUT"

CELLS=(
  "E8P 9.010 0.980 1.0 sitl_world_plain"
  "S12P 1.010 -11.020 1.0 sitl_world_plain"
  "S8O 1.010 -7.020 1.0 sitl_world_obstacles"
  "E12O 13.010 0.980 1.0 sitl_world_obstacles"
  "NE8O 6.667 6.637 1.0 sitl_world_obstacles"
  "N8P 1.010 8.980 1.0 sitl_world_obstacles"
)
N_ROUNDS=3
for cell in "${CELLS[@]}"; do
  set -- $cell; C=$1; GX=$2; GY=$3; GZ=$4; W=$5
  RETRY_LEFT=1
  for r in $(seq 1 $N_ROUNDS); do
    TAG="M3R${C}_$r"
    echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,$GZ) world=$W"
    setsid bash "$L/vins_smoke.sh" --world "$W" --goal "$GX" "$GY" "$GZ" \
        --tag "$TAG" --budget 300 --stoploss > "/tmp/m3_${TAG}.log" 2>&1
    EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
    RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
    [ -n "$RES" ] || RES="NO-RESULT"
    JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
    ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
    DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
    IQG=$(grep -c "T2IQG] REJECT" "$EV/simvins.log" 2>/dev/null || echo 0)
    echo "$C,$r,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},$IQG" >> "$OUT"
    echo "  -> $RES jump=${JMP:-NA} arrive=${ARR:-NA} disarm=${DIS:-NA} iqg_rej=$IQG"
    # ENV-FAIL 重试≤1/格
    if [ "$RES" = "ENV-FAIL" ] && [ $RETRY_LEFT -ge 1 ]; then
      RETRY_LEFT=$((RETRY_LEFT-1)); r=$((r-1)); echo "  ENV 重试(余 $RETRY_LEFT)"
    fi
    # 机器死亡保护: gzserver 不在=批中止
    if ! pgrep -x gzserver >/dev/null && [ "$RES" != "PASS" ] && [ "$RES" != "FAIL" ]; then
      echo "[m3] 机器死亡保护触发(RES=$RES)——批中止,如实收卷"; exit 3
    fi
  done
done
echo "[m3] 批毕 -> $OUT"
