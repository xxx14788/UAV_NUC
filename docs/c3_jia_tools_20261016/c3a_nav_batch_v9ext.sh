#!/bin/bash
# c3a_nav_batch.sh — ③C-甲 统一导航批运行器（Phase B 试录 8 轮 / Phase C 终版 N≥25 共用骨架；2026-10-16）
# 用法: c3a_nav_batch.sh <WVER> <EVDIR> <BUDGET> <TAG:GX:GY ...>
#   WVER  = v8 | v73   （world 版本名→文件名 sitl_world_corridor_${WVER}.world；v73 注意正名非 v7!）
#   EVDIR = 证据目录（战役目录下相对名，如 trial_v8 / final_v8）
# 指纹门（跑前，任一 FAIL 即 ABORT）:
#   world 三处 md5 == 预期 / config == ${C3A_CFG_MD5:-dd9fb372} / vins 栈 cac140b0+80be3cf2 /
#   px4ctrl 59d84e4e / envelope ON / df≥20G / gzserver 残留
#   Phase A 采纳时: C3A_CAM_SDF_MD5 环境变量给模型 SDF 预期 md5（⑤件指纹门）。
# 运行时 world 校验（坑14 防复发）: 每轮轮末 grep 本轮 sitl.log "Loading world file" →
#   对加载文件取 md5 比对预期；不符=轮 VOID 重跑一次；证据行拷贝入 run 目录（world_load_evidence.txt）。
# 红线⑪: 批末源指纹注册表（geom/thrust JSON 逐轮 md5 互异断言，同值=无效重跑该轮提示）。
source /opt/ros/noetic/setup.bash 2>/dev/null
L="$HOME/sitl_sim"; WS="$HOME/catkin_ws"
CAMP="$L/c3_corridor_20261013"
WVER="$1"; EVD="$CAMP/$2"; BZ="$3"; shift 3
SUM="$EVD/trial_report.md"
WA="$L/analysis/t3_wa_gate.py"; GEO="$CAMP/corridor_geom_audit.py"
EXT="$CAMP/h4_rehearsal/h4_thrust_extract.py"
mkdir -p "$EVD"
WF="sitl_world_corridor_${WVER}"
GZ=1.0    # goal z: v9 实验室尺度=0.8(飞行高), 其余=1.0(承旧)
case "$WVER" in
  v8)  EXP_MD5="6ae3d4f3065106e27b47260fa2309f77" ;;
  v73) EXP_MD5="383a301aa5c01bea616411cdf5a795d0" ;;
  v9)  EXP_MD5="5f3d48eb64906c48a02e46ad892115fc"; GZ=0.8 ;;
  *) echo "ABORT unknown WVER $WVER"; exit 9 ;;
esac
w() { echo "[$(date '+%F %T')] $*" | tee -a "$SUM"; }

preflight() {
  local M_NODE M_LIB M_CFG M_PX
  M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" 2>/dev/null | cut -d' ' -f1)
  M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" 2>/dev/null | cut -d' ' -f1)
  M_CFG=$(md5sum "$WS/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml" | cut -d' ' -f1)
  [ "${M_NODE:0:8}" = "cac140b0" ] || { w "ABORT vins_node=$M_NODE"; exit 9; }
  [ "${M_LIB:0:8}" = "80be3cf2" ] || { w "ABORT lib=$M_LIB"; exit 9; }
  [ "$M_CFG" = "${C3A_CFG_MD5:-dd9fb37251e447263383e57d21011481}" ] || { w "ABORT cfg=$M_CFG (expect ${C3A_CFG_MD5:-dd9fb372...})"; exit 9; }
  M_PX=$(md5sum "$WS/devel/.private/px4ctrl/lib/px4ctrl/px4ctrl_node" | cut -d' ' -f1)
  [ "${M_PX:0:8}" = "59d84e4e" ] || { w "ABORT px4ctrl=$M_PX"; exit 9; }
  grep -q "takeoff_thrust_cap: 0.80" "$WS/src/px4ctrl/config/ctrl_param_sitl.yaml" || { w "ABORT envelope OFF"; exit 9; }
  if [ -n "${C3A_CAM_SDF_MD5:-}" ]; then
    local M_CAM; M_CAM=$(md5sum "$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/stereo_vins_rig/stereo_vins_rig.sdf" | cut -d' ' -f1)
    [ "$M_CAM" = "$C3A_CAM_SDF_MD5" ] || { w "ABORT cam_sdf=$M_CAM (expect $C3A_CAM_SDF_MD5)"; exit 9; }
    w "cam SDF gate OK (Phase A ⑤件=$M_CAM)"
  fi
  local DF_G; DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
  [ "$DF_G" -lt 20 ] && { w "ABORT_DISK ${DF_G}G"; exit 9; }
  pgrep -x gzserver >/dev/null 2>&1 && { w "ABORT_RESIDUE gzserver alive"; exit 9; }
  local f mw
  for f in "$WS/sitl_sim/worlds/${WF}.world" \
           "$CAMP/${WF}.world" \
           "$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/${WF}.world"; do
    mw=$(md5sum "$f" 2>/dev/null | cut -d' ' -f1) || { w "ABORT_WORLD_MISSING $f"; exit 9; }
    [ "$mw" = "$EXP_MD5" ] || { w "ABORT_WORLD_MD5 $f=$mw"; exit 9; }
  done
  w "preflight OK (world $WVER=$EXP_MD5 三处; px4ctrl=${M_PX:0:8}; cfg=${M_CFG:0:8}; envelope ON; budget $BZ)"
}

verify_world_load() {  # $1=rundir  → 0=OK
  local d="$1" line loaded lw
  line=$(grep -a "Loading world file" "$d/sitl.log" 2>/dev/null | tail -1 | sed 's/\x1b\[[0-9;]*m//g' | grep -o "[^ ]*\.world" | tail -1 | tr -d "[]")
  echo "$line" > "$d/world_load_evidence.txt"
  [ -n "$line" ] || { w "WORLD-VERIFY-FAIL $d: no Loading line"; return 1; }
  loaded=$(md5sum "$line" 2>/dev/null | cut -d' ' -f1)
  [ "$loaded" = "$EXP_MD5" ] || { w "WORLD-LOAD-MISMATCH $d: loaded=$loaded expect=$EXP_MD5 ($line)"; return 1; }
  w "world-load verified $d: $(basename "$line") md5=${loaded:0:8}"
  return 0
}

run_round() {  # tag gx gy
  local tag="$1" gx="$2" gy="$3" d rc=0
  w "---- round $tag goal=($gx,$gy,z=$GZ) world=$WF budget=$BZ ----"
  rm -f "/tmp/c3_delta_${tag}.tsv"
  nohup python3 "$CAMP/c3_delta_probe.py" "/tmp/c3_delta_${tag}.tsv" >/dev/null 2>&1 &
  local PROBE_PID=$!
  T2_IQG_OBSERVE=1 bash "$L/vins_smoke.sh" --world "$WF" --goal "$gx" "$gy" "$GZ" \
       --tag "$tag" --budget "$BZ" 2>&1 | tail -30 | tee -a "$SUM"
  kill "$PROBE_PID" 2>/dev/null
  d=$(ls -dt "$L"/vins_smoke_runs/run_${tag}_* 2>/dev/null | head -1)
  if [ -n "$d" ] && ! verify_world_load "$d"; then
    w "ROUND-VOID $tag (world-load mismatch) → 重跑一次"
    T2_IQG_OBSERVE=1 bash "$L/vins_smoke.sh" --world "$WF" --goal "$gx" "$gy" "$GZ" \
         --tag "${tag}R" --budget "$BZ" 2>&1 | tail -8 | tee -a "$SUM"
    d=$(ls -dt "$L"/vins_smoke_runs/run_${tag}R_* 2>/dev/null | head -1)
    [ -n "$d" ] && verify_world_load "$d" || { w "ROUND-VOID-CONFIRMED $tag (两试均不符, 人工介入)"; }
  fi
  ls -t "$HOME/PX4-Autopilot/build/px4_sitl_default/rootfs/log/"*/*.ulg 2>/dev/null | head -1 > "/tmp/c3_ulg_${tag}.txt"
  w "ulg snapshot for $tag: $(cat /tmp/c3_ulg_${tag}.txt 2>/dev/null)"
}

certify_round() {  # run_dir
  local d="$1"
  local tag; tag=$(basename "$d" | sed 's/^run_//; s/_[0-9]*$//')
  local lane=E; [[ "$tag" == *NE* ]] && lane=NE; [[ "$tag" == *L9* || "$tag" == *F9* ]] && lane=LAB
  w "---- certify $tag (lane=$lane) ----"
  python3 "$GEO" --lane "$lane" --world "$WVER" --json "$EVD/geom_$(basename "$d").json" "$d/flight.bag" 2>&1 | tail -2 | tee -a "$SUM"
  [ ! -f "$d/j0_decomp.json" ] && python3 "$WA" --j0-decomp "$d" >> "$SUM" 2>&1
  local ulog; ulog=$(cat "/tmp/c3_ulg_${tag}.txt" 2>/dev/null)
  if [ -n "$ulog" ] && [ -f "$ulog" ]; then
    python3 "$EXT" "$ulog" "$EVD/thrust_$(basename "$d").json" "$EVD/thrust_$(basename "$d")_curve.csv" | tail -1 | tee -a "$SUM"
    cp -n "$ulog" "$d/" 2>/dev/null
  else
    w "CERTIFY-SKIP $tag: no ulg snapshot"
  fi
  [ -f "/tmp/c3_delta_${tag}.tsv" ] && cp "/tmp/c3_delta_${tag}.tsv" "$d/" 2>/dev/null
  local trigger=0
  grep -q 'NEVER-FLEW' "$d/RESULT.txt" 2>/dev/null && trigger=1
  local mxde; mxde=$(python3 -c "
import json
try: print(json.load(open('$d/j0_decomp.json'))['j0_decomp'].get('max_frame_de_m') or 0)
except Exception: print(0)" 2>/dev/null)
  python3 -c "exit(0 if float('$mxde' or 0) > 0.5 else 1)" 2>/dev/null && trigger=1
  if [ "$trigger" = "1" ]; then
    mkdir -p "$d/forensics"
    [ -n "$ulog" ] && [ -f "$ulog" ] && cp "$ulog" "$d/forensics/" 2>/dev/null
    grep -ia 'bias' "$d/simvins.log" > "$d/forensics/vins_bias_timeline.txt" 2>/dev/null
    local f
    for f in sitl.log takeoff.log px4ctrl.log mavros.log goal.txt arrive_watch.txt; do
      [ -f "$d/$f" ] && cp "$d/$f" "$d/forensics/" 2>/dev/null
    done
    w "forensics collected -> $d/forensics"
  fi
}

source_fp_registry() {  # 红线⑪: 逐轮源指纹 md5 互异断言
  w "---- source fingerprint registry (红线⑪) ----"
  local kind dup
  for kind in geom thrust; do
    dup=$(md5sum "$EVD"/${kind}_run_*.json 2>/dev/null | cut -d' ' -f1 | sort | uniq -d)
    if [ -n "$dup" ]; then
      w "REDLINE11-VIOLATION $kind: 同值源指纹=$dup → 涉事轮无效须重跑"
    else
      w "$kind: $(ls "$EVD"/${kind}_run_*.json 2>/dev/null | wc -l) 轮 md5 全互异 [OK]"
    fi
  done
}

preflight
w "==== C3A batch start (world=$WVER md5=${EXP_MD5:0:8}, rounds=$#, budget=$BZ) ===="
for spec in "$@"; do
  IFS=':' read -r tag gx gy <<< "$spec"
  run_round "$tag" "$gx" "$gy"
done
w "==== certify all rounds ===="
for spec in "$@"; do
  IFS=':' read -r tag gx gy <<< "$spec"
  d=$(ls -dt "$L"/vins_smoke_runs/run_${tag}R_* "$L"/vins_smoke_runs/run_${tag}_* 2>/dev/null | head -1)
  [ -n "$d" ] && certify_round "$d"
done
source_fp_registry
w "==== batch end ===="
