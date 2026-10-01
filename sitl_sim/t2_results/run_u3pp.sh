#!/usr/bin/env bash
# U3pp online verification arms (prereg=prereg_online_u3pp.md da2534e6)
# Order: A5 ground/gates -> A4 hover/base -> A3 hover/gates -> A2 route/base -> A1 route/gates
# Compact-bag recording (no images); every round guarded by pgrep CLEAN + md5 readback.
set -u
F=~/sitl_sim/t2v3_flight.sh
S=~/sitl_sim/t2_results
log(){ echo "[$(date +%H:%M:%S)] $*"; }

md5sum ~/catkin_ws/devel/lib/libvins_lib.so ~/catkin_ws/devel/lib/vins/vins_node > $S/u3pp_stack_md5.txt

run_arm(){ # name mode launch
  local NAME=$1 MODE=$2 LAUNCH=$3
  log "=== ARM $NAME ($MODE, launch=$LAUNCH) start ==="
  if pgrep -f 'gzserver|px4|rosmaster' | head -1 | grep -q .; then
    log "ARM $NAME ABORT: residual processes"; return 1
  fi
  RECORD_COMPACT=1 VINS_LAUNCH=$LAUNCH bash $F $MODE > $S/u3pp_${NAME}_console.log 2>&1
  log "=== ARM $NAME done rc=$? ==="
  sleep 10
}

run_arm A5_ground_gates ground  sim_vins_t2gates.launch
run_arm A4_hover_base   hover   sim_vins.launch
run_arm A3_hover_gates  hover   sim_vins_t2gates.launch
run_arm A2_route_base   route   sim_vins.launch
run_arm A1_route_gates  route   sim_vins_t2gates.launch
log "U3PP_ALL_DONE"
