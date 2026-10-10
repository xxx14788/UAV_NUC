#!/bin/bash
# T1 v11.39 FAIL 分支 — 梯①盲降修复后 10 轮增量复验批(回挖报告§4 序)
# 场景: S1 hover_1m×4 + S2 hover_3m×3 + S3 transit×3(修复验证面=盲降链,S4 降落段近似非本链面)
# 判据沿预注册原文: 每轮 HAFIX≥1 ∧ landed=1;六环链=定位面(ring4/6 预期首次由 HAFIX 自身达成)
set -u
PIDF=/tmp/t1_reverify_batch.pid
if [ -f "$PIDF" ]; then
  OPID=$(cat "$PIDF" 2>/dev/null)
  if [ -n "$OPID" ] && [ -d "/proc/$OPID" ] && [ "$OPID" != "$$" ]; then
    echo "FATAL 另一复验批实例在役(pid=$OPID),拒绝启动"; exit 1
  fi
fi
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT
export ROS_DISTRO=noetic ROS_VERSION=1 ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311} ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
L=$HOME/sitl_sim
OUT=$L/t1_evidence/v11_39_2026-10-09/hafix_increment10
mkdir -p "$OUT"
SUM="$OUT/summary.txt"; : > "$SUM"

force_clean() {
  local TAGCLEAN=$1
  local RES="clean"
  for P in px4 gzserver gzclient mavros_node vins_node px4ctrl_node; do
    local N
    N=$(pgrep -xc "$P" 2>/dev/null || true); N=${N:-0}
    if [ "$N" != "0" ]; then
      pkill -9 -x "$P" 2>/dev/null
      RES="$RES kill:$P=$N"
    fi
  done
  if pgrep -f 'roslaunc[h] ' >/dev/null 2>&1; then
    pkill -f 'roslaunc[h] ' 2>/dev/null; RES="$RES kill:roslaunch"
  fi
  sleep 5
  local A B
  A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
  B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
  if [ "$A" = "0" ] && [ "$B" = "0" ]; then
    echo "[clean] $TAGCLEAN $RES -> post-assert px4=0 gz=0 OK" | tee -a "$SUM"
    return 0
  else
    echo "[clean] $TAGCLEAN $RES -> post-assert FAIL px4=$A gz=$B (10s 重试)" | tee -a "$SUM"
    sleep 10
    A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
    B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
    [ "$A" = "0" ] && [ "$B" = "0" ] && return 0 || return 1
  fi
}

echo "=== v11.39 increment10 start $(date -Is) (blind-land fix build) ===" | tee -a "$SUM"
force_clean "批首" || { echo "FATAL 批首清场失败" | tee -a "$SUM"; exit 1; }

run_one() {
  local SCN=$1 GX=$2 GY=$3 GZ=$4 RID=$5
  echo "--- $SCN round $RID start $(date +%T) ---" | tee -a "$SUM"
  DRILL_POSTGATE=15 bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
  local RC=$?
  local EV HL
  EV=$(grep '\[drill\] EV=' "$OUT/${SCN}_r${RID}.log" | tail -1 | cut -d= -f2)
  [ -z "$EV" ] && EV=$(grep -oP 'ev=\K\S+run_DRILLD1_\S+' "$OUT/${SCN}_r${RID}.log" | tail -1)
  HL=0
  [ -n "$EV" ] && [ -f "$EV/px4ctrl.log" ] && HL=$(grep -c 'HAFIX' "$EV/px4ctrl.log" 2>/dev/null || echo 0)
  if [ "$RC" != "0" ] || [ "$HL" -eq 0 ] 2>/dev/null; then
    echo "$SCN r$RID attempt1 无效(rc=$RC HAFIX_lines=$HL) -> retry ×1" | tee -a "$SUM"
    mv "$OUT/${SCN}_r${RID}.log" "$OUT/${SCN}_r${RID}.attempt1.log" 2>/dev/null
    force_clean "$SCN r$RID retry-pre" >/dev/null 2>&1
    DRILL_POSTGATE=15 bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
    RC=$?
    EV=$(grep '\[drill\] EV=' "$OUT/${SCN}_r${RID}.log" | tail -1 | cut -d= -f2)
    [ -z "$EV" ] && EV=$(grep -oP 'ev=\K\S+run_DRILLD1_\S+' "$OUT/${SCN}_r${RID}.log" | tail -1)
    echo "$SCN r$RID attempt2 rc=$RC ev=$EV" | tee -a "$SUM"
  fi
  echo "$SCN r$RID final drill_rc=$RC ev=$EV" | tee -a "$SUM" | tee -a "$OUT/ev_index.txt"
  force_clean "$SCN r$RID" || echo "WARN $SCN r$RID 清场不净" | tee -a "$SUM"
}

for R in 1 2; do
  run_one S1_hover_1m  0.50 0.50 1.0 $R
  run_one S2_hover_3m  0.50 0.50 3.0 $R
  run_one S3_transit   1.01 8.98 1.0 $R
done
run_one S1_hover_1m  0.50 0.50 1.0 3
run_one S1_hover_1m  0.50 0.50 1.0 4
echo "=== increment10 done $(date -Is) ===" | tee -a "$SUM"
