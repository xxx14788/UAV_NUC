#!/usr/bin/env bash
# v5.2 min2 标准判定干净跑（无 strace，20 秒判定复测用）
# 用法: min2_clean_run.sh depth|camera
MODE=${1:-depth}
CDIR=/home/ghj/sitl_sim/c3_corridor_20261013
OUT=/tmp/v52_clean_${MODE}
mkdir -p "$OUT"
if [ "$MODE" = depth ]; then
  WORLD=$CDIR/min2_depth_repro.world
else
  WORLD=$CDIR/min2_cam.world
fi
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://localhost:11396
export DISPLAY=:99
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/usr/lib/x86_64-linux-gnu/gazebo-11:${LD_LIBRARY_PATH:-}

MASTER_STARTED=0
if ! timeout 5 rosnode list >/dev/null 2>&1; then
  nohup roscore -p 11396 >"$OUT/roscore.log" 2>&1 &
  MASTER_STARTED=1
  for i in $(seq 1 40); do
    timeout 5 rosnode list >/dev/null 2>&1 && break
    sleep 1
  done
fi
timeout 5 rosnode list >/dev/null 2>&1 || { echo "MASTER-UP-FAIL"; exit 1; }

date '+CLEAN-START %F %T' | tee -a "$OUT/run.log"
/home/ghj/sitl_sim/gzserver --verbose "$WORLD" >"$OUT/gz_${MODE}.log" 2>&1 &
GZPID=$!
echo "GZPID=$GZPID" | tee -a "$OUT/run.log"
cd "$CDIR" && timeout -k 5 60 python3 min2_probe_v52.py "$MODE" 40 2>&1 | tee "$OUT/probe_${MODE}.txt"
kill -TERM "$GZPID" 2>/dev/null; sleep 2; kill -KILL "$GZPID" 2>/dev/null
if [ "$MASTER_STARTED" = 1 ]; then
  pkill -f 'rosmaster --core -p 11396' 2>/dev/null
  pkill -f 'roscore -p 11396' 2>/dev/null
fi
date '+CLEAN-END %F %T' | tee -a "$OUT/run.log"
echo "DONE mode=$MODE"
