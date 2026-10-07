#!/usr/bin/env bash
# t1_drill_run.sh — 注入演练编排器 v1.0 (T1 v11.25 阶段 4a;预注册=drill_prereg_v1)
# 用法: t1_drill_run.sh <D1|D2|D3|D4|D5> [goal_x goal_y goal_z] [world]
# 流程: 起 vins_smoke(后台,N8P 格默认)→等 pursuit(goal 后 25s)→注入→等收束(budget 上限)
#       →取证(RESULT/stoploss/alarm/inject/轨迹)→teardown 兜底。
# 注: 判据=drill_prereg_v1 冻结表;本脚本只编排不判读。
set -u
export ROS_DISTRO=noetic ROS_VERSION=1
source /opt/ros/noetic/setup.bash 2>/dev/null
source "$HOME/catkin_ws/devel/setup.bash" 2>/dev/null
L="$HOME/sitl_sim"

CASE="${1:?D1..D5}"
GX="${2:-1.010}"; GY="${3:-8.980}"; GZ="${4:-1.0}"
WORLD="${5:-sitl_world_obstacles}"
BUDGET=300
STAMP=$(date +%H%M%S)
TAG="DRILL${CASE}_N8P"
EV="$L/vins_smoke_runs/run_${TAG}_${STAMP}"
LOG="/tmp/drill_${CASE}_${STAMP}.log"

echo "[drill] case=$CASE goal=($GX,$GY,$GZ) world=$WORLD ev=$EV" | tee -a "$LOG"

# 案5 监控告警器随轮启动
if [ "$CASE" = "D5" ]; then
  mkdir -p "$EV"
  setsid nohup python3 "$L/t1_odom_monitor.py" "$EV" > "$EV/monitor_stdout.log" 2>&1 &
fi

mkdir -p /tmp/drill_logs; setsid nohup bash "$L/vins_smoke.sh" --world "$WORLD" --goal "$GX" "$GY" "$GZ" \
    --tag "$TAG" --budget "$BUDGET" --stoploss > "/tmp/smoke_${TAG}_${STAMP}.log" 2>&1 &
SMOKE_PID=$!
echo "[drill] vins_smoke pid=$SMOKE_PID" | tee -a "$LOG"

# 等 run 目录出现 + goal 投递(轮内 goal_trace 或 arrive_watch 出现)
EV=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1)
WAIT=0
while [ -z "$EV" ] && [ $WAIT -lt 120 ]; do sleep 3; WAIT=$((WAIT+3));
  EV=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1); done
[ -n "$EV" ] || { echo "[drill] FATAL run dir 未出现" | tee -a "$LOG"; exit 1; }
echo "[drill] EV=$EV" | tee -a "$LOG"

# 等 pursuit: arrive_watch 出现(goal 已投递且进入到达监视)
WAIT=0
while [ ! -s "$EV/arrive_watch.txt" ] && [ $WAIT -lt 180 ]; do sleep 3; WAIT=$((WAIT+3)); done
[ -s "$EV/arrive_watch.txt" ] && echo "[drill] pursuit 进入(${WAIT}s)" | tee -a "$LOG" || \
  echo "[drill] WARN arrive_watch 未出现,按时序注入(${WAIT}s)" | tee -a "$LOG"
sleep 25  # pursuit 稳定段

INJ_T=$(date +%H:%M:%S)
echo "[drill] 注入@$INJ_T case=$CASE" | tee -a "$LOG"
case "$CASE" in
D1)  # 杀 VINS 进程
  VP=$(pgrep -x vins_node | head -1)
  [ -n "$VP" ] && kill -9 "$VP" && echo "[drill] kill -9 vins_node($VP)" | tee -a "$LOG" \
    || echo "[drill] WARN vins_node 不在" | tee -a "$LOG"
  ;;
D2)  # 毒 odom 跳变(+5m 单帧)
  python3 "$L/t1_inject_odom.py" --jump 5 --out "$EV" >> "$LOG" 2>&1
  ;;
D3)  # 毒 odom 断流(STOP 30s→CONT)
  VP=$(pgrep -x vins_node | head -1)
  if [ -n "$VP" ]; then kill -STOP "$VP"; echo "[drill] STOP vins($VP) 30s" | tee -a "$LOG";
    sleep 30; kill -CONT "$VP"; echo "[drill] CONT vins" | tee -a "$LOG"; fi
  ;;
D4)  # planner 饿死(STOP 60s→CONT)
  EP=$(pgrep -f ego_planner_node | head -1)
  if [ -n "$EP" ]; then kill -STOP "$EP"; echo "[drill] STOP planner($EP) 60s" | tee -a "$LOG";
    sleep 60; kill -CONT "$EP"; echo "[drill] CONT planner" | tee -a "$LOG"; fi
  ;;
D5)  # 慢漂接管(0.15m/s 30s)
  python3 "$L/t1_inject_odom.py" --drift 0.15 --dur 30 --out "$EV" >> "$LOG" 2>&1
  ;;
*) echo "unknown case" ; exit 1;;
esac

# 等收束: RESULT.txt 或 budget+120s
WAIT=0
while [ ! -f "$EV/RESULT.txt" ] && [ $WAIT -lt $((BUDGET + 150)) ]; do
  sleep 5; WAIT=$((WAIT+5)); done
sleep 5
echo "[drill] 收束态:" | tee -a "$LOG"
for f in RESULT.txt stoploss.flag stoploss_*.json odom_alarm.flag odom_alarm.json inject_*.json; do
  [ -f "$EV"/$f ] && { echo "--- $f:"; head -c 400 "$EV"/$f; echo; } >> "$LOG" 2>&1
done
# teardown 兜底(vins_smoke 自清失败时)
kill -0 "$SMOKE_PID" 2>/dev/null && { bash "$L/kill_planner_all.sh" >/dev/null 2>&1 || true; }
sleep 3
pkill -9 -x vins_node 2>/dev/null || true
echo "[drill] 完毕 log=$LOG ev=$EV" | tee -a "$LOG"
