#!/usr/bin/env bash
# T1 v11.7 单元5 供给轮战役(B 臂=默认配置;X1prime型x2+hover型x2;栈校验+banner 核验)
set -u
L="$HOME/sitl_sim"
SUM="$L/t1_evidence/v11_7_2026-10-05/supply_campaign.log"
EXPECT_NODE="b7de133d"; EXPECT_LIB="59548c6a"
mkdir -p "$(dirname "$SUM")"
echo "=== T1 v11.7 supply campaign start $(date '+%F %T') stack=$EXPECT_NODE/$EXPECT_LIB ===" >> "$SUM"
run_round() {
  local TAG="$1"; shift
  local M_NODE M_LIB
  M_NODE=$(md5sum "$HOME/catkin_ws/devel/.private/vins/lib/vins/vins_node" | cut -c1-8)
  M_LIB=$(md5sum "$HOME/catkin_ws/devel/lib/libvins_lib.so" | cut -c1-8)
  if [ "$M_NODE" != "$EXPECT_NODE" ] || [ "$M_LIB" != "$EXPECT_LIB" ]; then
    echo "[$(date +%H:%M:%S)] $TAG ABORT stack drift node=$M_NODE lib=$M_LIB" >> "$SUM"; exit 9; fi
  echo "[$(date +%H:%M:%S)] $TAG start md5=$M_NODE/$M_LIB args=$*" >> "$SUM"
  bash $L/vins_smoke.sh "$@" --tag "$TAG" </dev/null > "/tmp/${TAG}_console.log" 2>&1
  local RC=$? EV
  EV=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1)
  if [ -z "$EV" ]; then echo "[$(date +%H:%M:%S)] $TAG rc=$RC NO-RUNDIR" >> "$SUM"; return; fi
  local FAILN ANCH RES SG DISARM
  FAILN=$(grep -c 'T2fail' "$EV/simvins.log" 2>/dev/null || echo 0)
  ANCH=$(grep -m1 'DUAL-ANCHOR' "$EV/RESULT.txt" 2>/dev/null | cut -c1-120)
  RES=$(grep -m1 'RESULT=' "$EV/RESULT.txt" 2>/dev/null | cut -c1-60)
  SG=$(grep -m1 -oE '\[T2SGCFG\][^]]*' "$EV/simvins.log" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
  DISARM=$(grep -m1 'auto_disarm' "$EV/RESULT.txt" 2>/dev/null)
  echo "[$(date +%H:%M:%S)] $TAG rc=$RC dir=$(basename "$EV") T2fail=$FAILN $DISARM | $SG | ${RES:-NO-RESULT}" >> "$SUM"
  echo "    ${ANCH:-no-dual-anchor-line}" >> "$SUM"
  sleep 20
}
run_round SUPX1a --world sitl_world_obstacles --goal 7.0 -4.0 1.0 --budget 180 --probecheck
run_round SUPX1b --world sitl_world_obstacles --goal 7.0 -4.0 1.0 --budget 180
run_round SUPHVa --world sitl_world_obstacles --goal 0 0 1 --budget 60
run_round SUPHVb --world sitl_world_obstacles --goal 0 0 1 --budget 60 --probecheck
echo "=== supply campaign end $(date '+%F %T') ===" >> "$SUM"
