#!/bin/bash
# T1 v11.28 单元 3d — HAFIX 多场景多轮验证批 (预注册判据见文末)
# 场景: S1 hover_1m(goal 0.5,0.5,1.0,W25) S2 hover_3m(0.5,0.5,3.0,W25)
#       S3 transit_1m(1.01,8.98,1.0,W25,原D1) S4 land_1m(0.5,0.5,1.0,W75 近似降落段)
# 每场景 5 轮: drill D1 变体 -> 判读 [HAFIX]+landed+disarm
source /opt/ros/noetic/setup.bash
L=$HOME/sitl_sim
OUT=$L/t1_evidence/v11_28_2026-10-07/unit3_3d_hafix_multirun
mkdir -p "$OUT"
SUM="$OUT/summary.txt"; : > "$SUM"
echo "=== 3d batch start $(date -Is) ===" | tee -a "$SUM"

# drill 参数化: sleep 25 -> sleep ${DRILL_WAIT:-25}
if ! grep -q 'DRILL_WAIT' "$L/t1_drill_run.sh"; then
  cp "$L/t1_drill_run.sh" "$L/t1_drill_run.sh.bak_3d"
  sed -i 's/^sleep 25  # pursuit 稳定段/sleep ${DRILL_WAIT:-25}  # pursuit 稳定段(3d 参数化)/' "$L/t1_drill_run.sh"
fi

run_one() {
  local SCN=$1 GX=$2 GY=$3 GZ=$4 WAIT=$5 RID=$6
  echo "--- $SCN round $RID $(date +%T) ---" | tee -a "$SUM"
  DRILL_WAIT=$WAIT bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
  # 判读: 该轮 drill log 内 HAFIX 行 + 最新 run 的 gatehit landed/disarm
  local LOG="$OUT/${SCN}_r${RID}.log"
  local H=$(grep -c '\[HAFIX\]' "$LOG")
  local LASTEV=$(ls -dt $L/vins_smoke_runs/run_DRILLD1_* 2>/dev/null | head -1)
  local LANDED=NA DISARM=NA
  if [ -n "$LASTEV" ] && [ -f "$LASTEV/gatehit.json" ]; then
    LANDED=$(grep -o '"landed": *[0-9]*' "$LASTEV/gatehit.json" | head -1)
    DISARM=$(grep -o '"auto_disarm": *[0-9]*' "$LASTEV/gatehit.json" | head -1)
  fi
  echo "$SCN r$RID HAFIX_lines=$H $LANDED $DISARM" | tee -a "$SUM"
}

for R in 1 2 3 4 5; do
  run_one S1_hover_1m  0.50 0.50 1.0 25 $R
  run_one S2_hover_3m  0.50 0.50 3.0 25 $R
  run_one S3_transit   1.01 8.98 1.0 25 $R
  run_one S4_land_1m   0.50 0.50 1.0 75 $R
done
echo "=== 3d batch done $(date -Is) ===" | tee -a "$SUM"
# 预注册判据: 每轮 HAFIX_lines>=1 ∧ landed=1; 场景 PASS=5/5 轮 PASS; 3d PASS=4 场景全 PASS
grep -cE 'HAFIX_lines=[1-9]' "$SUM" | xargs -I{} echo "rounds_with_hafix {}/20" | tee -a "$SUM"
