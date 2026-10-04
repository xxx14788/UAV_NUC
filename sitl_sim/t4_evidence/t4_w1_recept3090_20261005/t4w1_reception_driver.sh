#!/bin/bash
# T4-W1 reception chain driver (3090, 2026-10-05)
# Reception set: T2 machine-AB campaign bags MACH1-12 (run_T2MACH*) + t2v3_hover_134845.bag
# Compact bags (zero image, verified by rosbag info): registration face only (md5 here).
# Image bags (MACH3/MACH8/hover_134845): six-leg real verification chain.
# Gates: double-0 empty window (ps comm rosbag/gzserver) + df>=25G; 3 x sleep 600, then SUSPEND leg (no force).
WS=/tmp/t4w1_reception
LOG=$WS/chain.log
A=/home/ghj/catkin_ws/sitl_sim/analysis
BAGS=/home/ghj/sitl_sim/bags
VS=/home/ghj/sitl_sim/vins_smoke_runs
CFG=/home/ghj/catkin_ws/src/VINS-Fusion/config/sim_stereo/e2_debug_smooth.yaml

say(){ echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }

set +u
source /opt/ros/noetic/setup.bash
source /home/ghj/catkin_ws/devel/setup.bash
set -u

say "=== T4-W1 driver start ==="
say "CONFIG_MD5 $(md5sum "$CFG" 2>&1)"
dfg(){ df --output=avail -BG /home/ghj | tail -1 | tr -dc '0-9'; }

gate(){
  local label="$1" tries=0 c1 c2 g
  while [ "$tries" -lt 3 ]; do
    c1=$(ps -eo comm= | grep -cx rosbag); c1=${c1:-0}
    c2=$(ps -eo comm= | grep -cx gzserver); c2=${c2:-0}
    g=$(dfg)
    if [ "$c1" = "0" ] && [ "$c2" = "0" ] && [ "$g" -ge 25 ]; then
      say "GATE_OK $label try=$tries rosbag=$c1 gzserver=$c2 df=${g}G"
      return 0
    fi
    say "GATE_WAIT $label try=$tries rosbag=$c1 gzserver=$c2 df=${g}G -> sleep 600"
    sleep 600
    tries=$((tries+1))
  done
  say "GATE_FAIL $label 3x -> SUSPEND leg (no force)"
  return 1
}

# phase 0: bag md5s (manifest face, all 13)
if gate md5_all; then
  : > $WS/bag_md5.txt
  for b in "$VS"/run_T2MACH*/flight.bag "$BAGS"/t2v3_hover_134845.bag; do
    say "MD5_BEGIN $b"
    if md5sum "$b" >> $WS/bag_md5.txt 2>>"$LOG"; then say "MD5_OK $b"; else say "MD5_FAIL $b"; fi
  done
fi

run_img(){
  local id="$1" src="$2" budget="$3" outer="$4"
  local stage="$BAGS/run_t4w1_$id"
  local link="$stage/$(basename "$src")"
  mkdir -p "$stage"
  if [ -e "$link" ] || [ -L "$link" ]; then
    say "STAGE_EXISTS $id -> $link"
  else
    ln -s "$src" "$link" && say "STAGE_OK $id -> $link" || { say "STAGE_FAIL $id"; return 1; }
  fi
  if gate "${id}_extract"; then
    say "EXTRACT_BEGIN $id"
    nice -n 10 timeout 1800 python3 "$A/j3_extract_frames.py" --bag "$link" \
      --topic /iris_stereo_vins/vins_cam_left/image_raw \
      --topic /iris_stereo_vins/vins_cam_right/image_raw \
      --out "$WS/frames_$id" --segments 3 --per-seg 24 --pairs > "$WS/extract_$id.log" 2>&1
    say "EXTRACT_RC=$? $id"
  fi
  if gate "${id}_offset"; then
    say "OFFSET_BEGIN $id"
    nice -n 10 timeout 1800 python3 "$A/j3_feature_density.py" --mode offset --bag "$link" > "$WS/offset_$id.log" 2>&1
    say "OFFSET_RC=$? $id"
  fi
  if gate "${id}_metrics"; then
    say "METRICS_BEGIN $id"
    nice -n 10 timeout 900 python3 "$A/j3_image_metrics.py" --frames-dir "$WS/frames_$id" --out "$WS/metrics_$id.json" > "$WS/metrics_$id.log" 2>&1
    say "METRICS_RC=$? $id"
    say "FBRES_BEGIN $id"
    nice -n 10 timeout 900 python3 "$A/j3_fb_residual.py" --frames-dir "$WS/frames_$id" --out "$WS/fbres_$id.json" > "$WS/fbres_$id.log" 2>&1
    say "FBRES_RC=$? $id"
  fi
  if gate "${id}_replay"; then
    md5sum /home/ghj/catkin_ws/devel/lib/vins/vins_node > "$WS/replay_md5_${id}_pre.txt" 2>&1
    md5sum /home/ghj/catkin_ws/devel/.private/vins/lib/libvins_lib.so >> "$WS/replay_md5_${id}_pre.txt" 2>&1
    say "REPLAY_BEGIN $id budget=$budget outer_timeout=$outer"
    nice -n 10 timeout "$outer" bash "$A/j3_replay_features.sh" "$link" "$WS/replay_$id" "$budget" > "$WS/replay_$id.log" 2>&1
    say "REPLAY_RC=$? $id"
    md5sum /home/ghj/catkin_ws/devel/lib/vins/vins_node > "$WS/replay_md5_${id}_post.txt" 2>&1
    md5sum /home/ghj/catkin_ws/devel/.private/vins/lib/libvins_lib.so >> "$WS/replay_md5_${id}_post.txt" 2>&1
  fi
}

run_img mach3     "$VS/run_T2MACH3_011804/flight.bag" 600 900
run_img mach8     "$VS/run_T2MACH8_015411/flight.bag" 600 900
run_img hov134845 "$BAGS/t2v3_hover_134845.bag"       300 600

say "=== T4-W1 driver done ==="
