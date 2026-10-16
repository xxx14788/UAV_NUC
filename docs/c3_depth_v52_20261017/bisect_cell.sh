#!/usr/bin/env bash
# v5.2 环境二分矩阵复测器（每格自动清场+起跑前残留断言+跑后确认死）
# 用法: bash bisect_cell.sh <name> <envsetup-file> [cwd]
# envsetup-file 内容=若干 export 行（bash source）
NAME="$1"; ENVF="$2"; CWD="${3:-/tmp}"
CDIR=/home/ghj/sitl_sim/c3_corridor_20261013
OUT=/tmp/v52_bisect/$NAME
mkdir -p "$OUT"
source /opt/ros/noetic/setup.bash
export DISPLAY=:99
export ROS_MASTER_URI=http://localhost:11396
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/usr/lib/x86_64-linux-gnu/gazebo-11:${LD_LIBRARY_PATH:-}
# 起跑前残留断言
if pgrep -x gzserver >/dev/null; then echo "[$NAME] ABORT-STALE-GZSERVER"; exit 9; fi
if ! timeout 5 rosnode list >/dev/null 2>&1; then
  nohup roscore -p 11396 >/dev/null 2>&1 &
  for i in $(seq 1 30); do timeout 5 rosnode list >/dev/null 2>&1 && break; sleep 1; done
fi
[ -f "$ENVF" ] && source "$ENVF"
cd "$CWD" || exit 9
/home/ghj/sitl_sim/gzserver --verbose "$CDIR/min2_depth_repro.world" >"$OUT/gz.log" 2>&1 &
GZPID=$!
cd "$CDIR"
sleep 12
timeout -k 5 40 python3 min2_probe_v52.py depth 30 2>&1 | tee "$OUT/probe.txt" | grep VERDICT | sed "s/^/[$NAME] /"
kill -TERM "$GZPID" 2>/dev/null; sleep 3; kill -KILL "$GZPID" 2>/dev/null; sleep 1
if pgrep -x gzserver >/dev/null; then pkill -9 -x gzserver; sleep 1; echo "[$NAME] post-kill applied"; fi
grep -c 'Address already in use' "$OUT/gz.log" 2>/dev/null | sed 's/^/[$NAME] addr-conflict-lines: /'
