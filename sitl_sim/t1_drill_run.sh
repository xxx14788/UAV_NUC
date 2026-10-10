#!/usr/bin/env bash
# t1_drill_run.sh — 注入演练编排器 v1.0 (T1 v11.25 阶段 4a;预注册=drill_prereg_v1)
# 用法: t1_drill_run.sh <D1|D2|D3|D4|D5> [goal_x goal_y goal_z] [world]
# 流程: 起 vins_smoke(后台,N8P 格默认)→等 pursuit(goal 后 25s)→注入→等收束(budget 上限)
#       →取证(RESULT/stoploss/alarm/inject/轨迹)→teardown 兜底。
# 注: 判据=drill_prereg_v1 冻结表;本脚本只编排不判读。
export ROS_DISTRO=noetic ROS_VERSION=1        ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}        ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
L="$HOME/sitl_sim"

CASE="${1:?D1..D5}"
GX="${2:-1.010}"; GY="${3:-8.980}"; GZ="${4:-1.0}"
WORLD="${5:-sitl_world_obstacles}"
BUDGET=300
STAMP=$(date +%H%M%S)
MARKER=$(mktemp)
TAG="DRILL${CASE}_N8P"
EV="$L/vins_smoke_runs/run_${TAG}_${STAMP}"
LOG="/tmp/drill_${CASE}_${STAMP}.log"

echo "[drill] case=$CASE goal=($GX,$GY,$GZ) world=$WORLD ev=$EV" | tee -a "$LOG"

# 案5 监控告警器随轮启动
MON_DIR=""
if [ "$CASE" = "D5" ]; then
  MON_DIR=$(mktemp -d /tmp/drill_d5_monitor_XXXX)
  setsid nohup python3 "$L/t1_odom_monitor.py" "$MON_DIR" > "$MON_DIR/monitor_stdout.log" 2>&1 &
fi

mkdir -p /tmp/drill_logs; setsid nohup bash "$L/vins_smoke.sh" --world "$WORLD" --goal "$GX" "$GY" "$GZ" \
    --tag "$TAG" --budget "$BUDGET" --stoploss > "/tmp/smoke_${TAG}_${STAMP}.log" 2>&1 &
SMOKE_PID=$!
echo "[drill] vins_smoke pid=$SMOKE_PID" | tee -a "$LOG"

# 等 run 目录出现 + goal 投递(轮内 goal_trace 或 arrive_watch 出现)
# P-3(v11.39): find|head -1 按 inode 序非时间序,多目录并发时可能拿错(时间戳差一秒同前缀
# 目录在案);改 sort 字典序(H%M%S=时间序)取最新,同前缀多目录下确定性地取本轮目录。
EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" -newer "$MARKER" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
WAIT=0
while [ -z "$EV" ] && [ $WAIT -lt 120 ]; do sleep 3; WAIT=$((WAIT+3));
  EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" -newer "$MARKER" ! -name "*envfail*" 2>/dev/null | sort | tail -1); done
[ -n "$EV" ] || { echo "[drill] FATAL run dir 未出现" | tee -a "$LOG"; exit 1; }
echo "[drill] EV=$EV" | tee -a "$LOG"

# P-3(v11.39) 注入前 flying 门 v4(双门): ①round.log "poscmd 存活门通过"(planner 在令)
#   ②/mavros/state armed:True(FC 解锁=liftoff 边界)。双门齐开后 sleep DRILL_POSTGATE 注入。
# 勘误史: v1 extended_state 探针 NA;v2 z 探针 index 不定;v3 poscmd 单门+固定窗
#   → S1 近点场景 poscmd-live+25s 落在落地边界(到达+降落≈+30-70s)→落地态注入废轮实证。
#   v4 armed 门=起飞沿确定,postgate 从 armed 起算(S1-S3=15s 爬升段/S4=40s 降落段近似)。
GATE_WAIT=0; GATE_MAX=${DRILL_GATE_MAX:-300}
until grep -q 'poscmd 存活门通过' "$EV/round.log" 2>/dev/null; do
  sleep 2; GATE_WAIT=$((GATE_WAIT+2))
  [ $GATE_WAIT -ge $GATE_MAX ] && break
done
if grep -q 'poscmd 存活门通过' "$EV/round.log" 2>/dev/null; then
  echo "[drill] flying 门①开(poscmd 存活 @+${GATE_WAIT}s)" | tee -a "$LOG"
  ARM_WAIT=0
  while [ $ARM_WAIT -lt 90 ]; do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && break
    sleep 2; ARM_WAIT=$((ARM_WAIT+2))
  done
  if [ $ARM_WAIT -lt 90 ]; then
    echo "[drill] flying 门②开(armed:True @+${ARM_WAIT}s) -> postgate ${DRILL_POSTGATE:-15}s" | tee -a "$LOG"
    sleep ${DRILL_POSTGATE:-15}
  else
    echo "[drill] WARN armed 门超时(90s),门①后按时序注入" | tee -a "$LOG"
  fi
else
  echo "[drill] WARN flying 门超时(${GATE_MAX}s poscmd 未起),按时序注入" | tee -a "$LOG"
fi

if ! pgrep -x vins_node >/dev/null; then
  echo "[drill] ABORT vins_node 不在(pursuit 前提失效),取消注入" | tee -a "$LOG"
  exit 2
fi
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
if [ -n "$MON_DIR" ] && [ -d "$MON_DIR" ]; then
  cp "$MON_DIR"/* "$EV/" 2>/dev/null
  echo "[drill] monitor 产物回拷 $EV" | tee -a "$LOG"
fi
echo "[drill] 完毕 log=$LOG ev=$EV" | tee -a "$LOG"
