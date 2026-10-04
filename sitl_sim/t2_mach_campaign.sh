#!/usr/bin/env bash
# t2_mach_campaign.sh — T2 v9.3 §1 机器对照实验 12 轮串行驱动（3090）
# prereg_machine_ab 纪律：每轮双 md5 实读+banner 四行核验+紧凑袋归档+逐轮摘要行
set -u
L="$HOME/sitl_sim"
SUM="$L/t2_results/R2_dissect/mach_campaign_summary.log"
echo "=== T2 machine-AB campaign start $(date '+%F %T') host=$(hostname) ===" >> "$SUM"
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  TAG="T2MACH${i}"
  # 每轮起飞前双 md5 实读（ prereg §2：偏离即停）
  M_NODE=$(md5sum "$HOME/catkin_ws/devel/.private/vins/lib/vins/vins_node" | cut -c1-8)
  M_LIB=$(md5sum "$HOME/catkin_ws/devel/lib/libvins_lib.so" | cut -c1-8)
  if [ "$M_NODE" != "2ad9676e" ] || [ "$M_LIB" != "8c3453c0" ]; then
    echo "[$(date +%H:%M:%S)] $TAG ABORT: stack drift node=$M_NODE lib=$M_LIB (expect 2ad9676e/8c3453c0)" >> "$SUM"
    exit 9
  fi
  IMGENV=""
  # 带图轮: MACH3/MACH8 (prereg §2 可选 2-3 轮, 供 T4 判读/T1 图像面)
  if [ "$i" = "3" ] || [ "$i" = "8" ]; then IMGENV="VINS_SMOKE_IMAGES=1"; fi
  echo "[$(date +%H:%M:%S)] $TAG start md5=$M_NODE/$M_LIB images=${i}${IMGENV:++img}" >> "$SUM"
  eval "$IMGENV bash $L/vins_smoke.sh --world sitl_world_obstacles --goal 7.0 -4.0 1.0 --budget 180 --tag $TAG" \
    </dev/null > "/tmp/${TAG}_console.log" 2>&1
  RC=$?
  # 轮产物摘要（run dir 名=着陆时刻, 按 tag 最新匹配）
  EV=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1)
  if [ -z "$EV" ]; then
    echo "[$(date +%H:%M:%S)] $TAG rc=$RC NO-RUNDIR" >> "$SUM"; continue
  fi
  FAILN=$(grep -c 'T2fail' "$EV/simvins.log" 2>/dev/null || echo 0)
  ANCH=$(grep -oE '\|pre-post\|=[0-9.]+ m' "$EV/RESULT.txt" 2>/dev/null | head -1)
  NVR=$(grep -c 'never-flew' "$EV/RESULT.txt" 2>/dev/null || echo 0)
  RES=$(grep -m1 'RESULT=' "$EV/RESULT.txt" 2>/dev/null | cut -c1-100)
  B1=$(grep -m1 -oE 'loss=[0-9]+ cauchy=[0-9.]+' "$EV/simvins.log" 2>/dev/null)
  B2=$(grep -m1 -oE '\[T2GATECFG\][^]]*' "$EV/simvins.log" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
  B3=$(grep -m1 -oE '\[T2RFIXCFG\][^]]*' "$EV/simvins.log" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
  B4=$(grep -m1 -oE '\[T2PDROPCFG\][^]]*' "$EV/simvins.log" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
  echo "[$(date +%H:%M:%S)] $TAG rc=$RC dir=$(basename "$EV") T2fail=$FAILN neverflew=$NVR ${ANCH:-no-anchor} | $B1 | $B2 | $B3 | $B4 | ${RES:-NO-RESULT}" >> "$SUM"
  sleep 20
done
echo "=== campaign end $(date '+%F %T') ===" >> "$SUM"
