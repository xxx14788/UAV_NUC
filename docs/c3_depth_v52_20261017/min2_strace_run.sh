#!/usr/bin/env bash
# v5.2 §一A.2.b 双 trace 采集（修复前强制铁律件）
# 用法: min2_strace_run.sh depth|camera
# 私有 master 11395；PID 精确追踪防 pkill 自匹配；trace+探针结果落 /tmp/v52_trace_<mode>/
# 注：不用 set -u——ROS setup.bash 链在 set -u 下爆 ROS_DISTRO 未绑定（在案旧坑）
MODE=${1:-}
if [ -z "$MODE" ]; then echo "usage: $0 depth|camera"; exit 2; fi
CDIR=/home/ghj/sitl_sim/c3_corridor_20261013
OUT=/tmp/v52_trace_${MODE}
mkdir -p "$OUT"
if [ "$MODE" = depth ]; then
  WORLD=$CDIR/min2_depth_repro.world
else
  WORLD=$CDIR/min2_cam.world
fi
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://localhost:11395
# X 显示：ghj 的 Xvfb :99（总设计师 10-16 21:20 软 GL 测试同款，复刻“有帧但空渲染”签名；
# 无 DISPLAY 时 DepthCameraSensor 创建直接失败=无话题，与生产故障签名不同）
export DISPLAY=:99
# gazebo 渲染插件目录（libDepthCameraPlugin.so 等；PX4 生产 env 含此路径，最小 env 须手动补）
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/gazebo-11/plugins:/usr/lib/x86_64-linux-gnu/gazebo-11:${LD_LIBRARY_PATH:-}

MASTER_STARTED=0
if ! timeout 5 rosnode list >/dev/null 2>&1; then
  nohup roscore -p 11395 >"$OUT/roscore.log" 2>&1 &
  MASTER_STARTED=1
  for i in $(seq 1 40); do
    timeout 5 rosnode list >/dev/null 2>&1 && break
    sleep 1
  done
fi
timeout 5 rosnode list >/dev/null 2>&1 || { echo "MASTER-UP-FAIL"; exit 1; }

date '+TRACE-START %F %T' | tee -a "$OUT/run.log"
strace -f -e trace=openat,mmap,brk,madvise -o "$OUT/${MODE}.trace" \
  /home/ghj/sitl_sim/gzserver --verbose "$WORLD" >"$OUT/gz_${MODE}.log" 2>&1 &
STRACE_PID=$!
echo "STRACE_PID=$STRACE_PID" | tee -a "$OUT/run.log"

cd "$CDIR" && timeout -k 5 150 python3 min2_probe_v52.py "$MODE" 120 2>&1 | tee "$OUT/probe_${MODE}.txt"
PROBE_RC=${PIPESTATUS[0]}
echo "PROBE_RC=$PROBE_RC" | tee -a "$OUT/run.log"

GZPID=$(pgrep -P "$STRACE_PID" 2>/dev/null | head -1)
[ -n "$GZPID" ] && kill -TERM "$GZPID" 2>/dev/null
sleep 3
[ -n "$GZPID" ] && kill -KILL "$GZPID" 2>/dev/null
kill -TERM "$STRACE_PID" 2>/dev/null
sleep 2
kill -KILL "$STRACE_PID" 2>/dev/null
if [ "$MASTER_STARTED" = 1 ]; then
  pkill -f 'rosmaster --core -p 11395' 2>/dev/null
  pkill -f 'roscore -p 11395' 2>/dev/null
fi
date '+TRACE-END %F %T' | tee -a "$OUT/run.log"
ls -la "$OUT" | tee -a "$OUT/run.log"
wc -l "$OUT/${MODE}.trace" | tee -a "$OUT/run.log"
echo "DONE mode=$MODE"
