#!/usr/bin/env bash
# A7 仿真 VINS 传感器模型启动（iris_stereo_vins：深度+双目+IMU）。
# v2(T4-E2,2026-09-29): setsid 进程组+px4 存活监督——挂壳孤儿根除。
#   旧版病灶: `sleep infinity | exec make` 在 make/px4 死后仍被 sleep infinity
#   吊住,脚本+管道永不退出 → PPID=1 孤儿(09-29 晨 4 实例 11-28min 实证)。
#   v2: 栈进独立会话(PGID=STACK_PID);监督循环发现 px4 连续缺席即整组
#   TERM→KILL 清场;INT/TERM 信号同路径;任何退出路径不留壳。
#   (sleep infinity 保留=pxh stdin 防刷屏五坑之一,现居进程组内可整组杀)
# 前置与排障结论同 start_sitl_depth.sh（roscore、Xvfb:99、gazebo 库路径、
# gzserver wrapper、pxh stdin 五个坑）。
# 用法: nohup bash start_sitl_vins.sh > log 2>&1 &
#       SITL_WORLD=sitl_world_obstacles 可选避障 world
#       SITL_VINS_GRACE=秒 覆盖起栈宽限(默认 60;仅测试用)
source /opt/ros/noetic/setup.bash   # 先 source 再 set -u（ROS 环境脚本依赖未定义变量）
source /usr/share/gazebo/setup.sh
set -u
export DISPLAY=:99
export VERBOSE_SIM=1
export PATH="$HOME/sitl_sim:$PATH"  # 前置 gzserver wrapper
export PX4_SITL_WORLD="${SITL_WORLD:-}"
cd "$HOME/PX4-Autopilot" || exit 1

setsid bash -c 'sleep infinity | HEADLESS=1 exec make px4_sitl gazebo-classic_iris_stereo_vins' &
STACK_PID=$!

reap() {
  kill -- "-$STACK_PID" 2>/dev/null
  sleep 5
  kill -9 -- "-$STACK_PID" 2>/dev/null
}
trap 'reap; exit 0' INT TERM

GRACE="${SITL_VINS_GRACE:-60}"
sleep "$GRACE"
MISS=0
while :; do
  if pgrep -x px4 >/dev/null 2>&1; then MISS=0; else MISS=$((MISS+1)); fi
  if [ "$MISS" -ge 3 ]; then
    echo "[start_sitl_vins 监督] px4 亡,进程组整组清场 $(date +%T)" >&2
    reap
    exit 0
  fi
  sleep 2
done
