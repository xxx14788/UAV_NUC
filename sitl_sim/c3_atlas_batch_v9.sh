#!/bin/bash
# c3_atlas_batch_v9.sh — v8.6 §三.4 图集 v9 包：试录 12+pilot 6 全轮出图（复用 13m 层 c3_traj_plot.py 像素级口径）
source /opt/ros/noetic/setup.bash 2>/dev/null
CAMP="$HOME/sitl_sim/c3_corridor_20261013"
RUNS="$HOME/sitl_sim/vins_smoke_runs"
ATLAS="$CAMP/atlas_v9_v86"
mkdir -p "$ATLAS"
plot() { local r="$1" l="$2"
  local d="$(ls -d $RUNS/run_${r}_* 2>/dev/null | tail -1)"
  if [ -n "$d" ] && [ -f "$d/flight.bag" ]; then
    python3 "$CAMP/c3_traj_plot.py" "$d" v9 LAB "$l" "$ATLAS/${r}.png" 2>&1 | tail -1
    echo "PLOT $r"
  else echo "SKIP $r"; fi
}
plot V82F1 'trial-A S-F TIMEOUT1.5'
plot V82F2 'trial-A clean TIMEOUT6.9'
plot V82F3 'trial-A RUNAWAY(z122)'
plot V82F4 'trial-A clean arr0.45'
plot V82F5 'trial-A clean arr0.17'
plot V82F6 'trial-A RUNAWAY-mid(z49)'
plot V82G1 'trial-B RUNAWAY arr0.17'
plot V82G2 'trial-B RUNAWAY arr0.16'
plot V82G3 'trial-B RUNAWAY arr0.21'
plot V82G4 'trial-B RUNAWAY arr0.16'
plot V82G5 'trial-B clean arr0.18'
plot V82G6 'trial-B NEVER-FLEW(invalid)'
plot V86P1 'pilot clean TIMEOUT1.5'
plot V86P2 'pilot clean arr0.17'
plot V86P3 'pilot RUNAWAY arr0.17'
plot V86P4 'pilot clean TIMEOUT4.4'
plot V86P5 'pilot clean arr0.17 oscil'
plot V86P6 'pilot RUNAWAY arr0.17'
echo ATLAS_DONE
