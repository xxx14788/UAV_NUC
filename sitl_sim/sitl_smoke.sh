#!/usr/bin/env bash
# SITL 一键冒烟(T1-W5,本目录最重要的基础设施)。
# 自动完成:持锁 → 起 SITL → mavros → px4ctrl → 冷 planner → bag → 起飞 → 确认 armed
#   → 发 goal(7,-4,1) → 等到位(<0.5m 或超时) → kill planner → 降落 → 停 bag
#   → analyze_flight.py → 六指标 PASS/FAIL → 全清理 → 放锁。
# 任何一步失败即 FAIL 并保留现场日志路径(不中途清进程,便于事后 rostopic 取证;
#   取证完毕手动 cleanup)。
# 用法: bash sitl_smoke.sh [--world NAME] [--goal x y z] [--keep] [--skip-sitl]
#   --world     默认 sitl_world_obstacles(A6 基准场景)
#   --keep      结束后不清理进程(留现场)
#   --skip-sitl 复用已在跑的 SITL/mavros/px4ctrl(增量调试用;仍要求持锁)
# 依赖: 本目录 start_sitl_depth.sh / kill_planner_all.sh / 04_takeoff.sh / 06_land.sh /
#   sitl_lock.sh / status_append.py / analysis/analyze_flight.py(仓库版 sitl_sim/)
source /opt/ros/noetic/setup.bash
set -u
SIM="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
source "$WS/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

WORLD="sitl_world_obstacles"
GOAL_X=7.0; GOAL_Y=-4.0; GOAL_Z=1.0
KEEP=0; SKIP_SITL=0
while [ $# -gt 0 ]; do
    case "$1" in
    --world) WORLD="$2"; shift 2 ;;
    --goal)  GOAL_X="$2"; GOAL_Y="$3"; GOAL_Z="$4"; shift 4 ;;
    --keep)  KEEP=1; shift ;;
    --skip-sitl) SKIP_SITL=1; shift ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
    esac
done

RUN="$SIM/smoke_runs/run_$(date +%F_%H%M%S)"
mkdir -p "$RUN"
LOG="$RUN/smoke.log"
BAG="$RUN/flight.bag"
PID_BAG=""; PID_HZ=""
WORLD_OVERRIDE=0   # --skip-sitl 时不动 world

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; echo "RESULT=FAIL" > "$RUN/RESULT"; log "现场保留: $RUN (进程未清,取证后手动: pkill -f 'bin/px4|gzserver|px4ctrl_node|roslaunch.*px4.launch'; $SIM/sitl_lock.sh release)"; exit 1; }

# T3 2026-09-28: owner 参数化——多会话并行时调用方传 SMOKE_OWNER=T3 等标识,
# 缺省 T1 向后兼容(09-28 凌晨 T3 会话跑的轮被误记 T1 的教训)
bash "$SIM/sitl_lock.sh" get "${SMOKE_OWNER:-T1}-smoke-$$" >/dev/null 2>&1 || fail "SITL 锁被占用($($SIM/sitl_lock.sh status))"
trap 'rc=$?; if [ $rc -ne 0 ]; then $SIM/sitl_lock.sh release >/dev/null 2>&1 || true; fi' EXIT
log "lock acquired; run dir=$RUN"

# 清残留(上一任务/上轮未收尾的 SITL;括号防 pkill 自匹配)
if [ "$SKIP_SITL" -eq 0 ]; then
    pkill -9 -f "bin/px[4]" 2>/dev/null; pkill -9 -f "gzserve[r]" 2>/dev/null
    pkill -f "px4ctrl_nod[e]" 2>/dev/null; pkill -f "roslaunch.*px4launc[h]" 2>/dev/null; pkill -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null
    pkill -f "devel/lib/ego_planne[r]" 2>/dev/null
    pkill -f "depth_caminfo_rela[y]" 2>/dev/null
    # 连 ROS master 一起清:跨 boot 复用的 master 上悬挂的注册/参数状态会诱发
    # mavros timesync 循环复位(Time jump 刷屏)与分钟级慢连(2026-09-27 夜实证:
    # 重启后首 boot 8s 连上且零刷屏;同 master 第二个 boot 复发)。每轮全新 ROS 图
    pkill -f "roslaunc[h]" 2>/dev/null; pkill -f "rosmaste[r]" 2>/dev/null
    pkill -f "roscore" 2>/dev/null; pkill -f "rosout" 2>/dev/null
    sleep 3
fi

roscore_up() { timeout 3 rostopic list >/dev/null 2>&1; }
if [ "$SKIP_SITL" -eq 0 ]; then
    # ---- 0. roscore / Xvfb ----
    roscore_up || { nohup roscore > "$RUN/roscore.log" 2>&1 & sleep 3; }
    roscore_up || fail "roscore 起不来"
    pgrep -f "Xvfb :99" >/dev/null || { nohup Xvfb :99 -screen 0 1600x1200x24 > "$RUN/xvfb.log" 2>&1 & sleep 2; }
    pgrep -f "Xvfb :99" >/dev/null || fail "Xvfb :99 起不来(相机渲染依赖)"

    # ---- 1. SITL(depth 模型 + world) ----
    log "starting SITL (world=$WORLD)"
    SITL_WORLD="$WORLD" nohup bash "$SIM/start_sitl_depth.sh" > "$RUN/sitl.log" 2>&1 &
    for i in $(seq 1 60); do pgrep -f "bin/px4" >/dev/null && break; sleep 2; done
    pgrep -f "bin/px4" >/dev/null || fail "px4 进程 120s 未出现,见 $RUN/sitl.log"
    log "px4 up"
else
    log "skip-sitl: 复用现有运行时(自担环境偏差)"
fi

# ---- 2. mavros ----
if [ "$SKIP_SITL" -eq 0 ]; then
    nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$RUN/mavros.log" 2>&1 &
fi
# 300s 窗:清洁环境 ~30s 连上;退化环境(当日多次重启后)实测 3-8 分钟才连上
for i in $(seq 1 150); do
    timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && break
    sleep 2
done
timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' || fail "mavros 300s 未连上 PX4,见 $RUN/mavros.log"
log "mavros connected"

# ---- 3. px4ctrl ----
if [ "$SKIP_SITL" -eq 0 ]; then
    nohup roslaunch px4ctrl run_ctrl_sitl.launch > "$RUN/px4ctrl.log" 2>&1 &
    for i in $(seq 1 30); do rosnode info px4ctrl >/dev/null 2>&1 && break; sleep 1; done
fi
rosnode info px4ctrl >/dev/null 2>&1 || fail "px4ctrl 未起来,见 $RUN/px4ctrl.log"
sleep 3
FSM_NOW=""
for i in 1 2 3; do   # fsm 1Hz,3s 探窗有竞态,重试 3 次(U6.4)
    FSM_NOW=$(timeout 3 rostopic echo -n1 /debugPx4ctrl/fsm_state 2>/dev/null | head -1)
    [ -n "$FSM_NOW" ] && break
    sleep 1
done
log "px4ctrl up (fsm: ${FSM_NOW:-<无 fsm_state 话题,旧版二进制?>})"

# ---- 4. 冷 planner ----
nohup roslaunch ego_planner run_planner_sitl.launch relay_on:=${RELAY_ON:-false} > "$RUN/planner.log" 2>&1 &
for i in $(seq 1 30); do rosnode list 2>/dev/null | grep -q traj_server && break; sleep 1; done
rosnode list 2>/dev/null | grep -q traj_server || fail "planner/traj_server 未起来,见 $RUN/planner.log"
log "planner up (cold)"

# ---- 5. bag ----
nohup rosbag record -O "$BAG" \
     /debugPx4ctrl /debugPx4ctrl/fsm_state /position_cmd /move_base_simple/goal \
     /px4ctrl/takeoff_land /mavros/state /mavros/extended_state \
     /mavros/local_position/odom /mavros/local_position/velocity_local \
     /mavros/imu/data /mavros/setpoint_raw/attitude /mavros/setpoint_raw/local \
          /drone_0_ego_planner_node/grid_map/occupancy \
     /drone_0_ego_planner_node/grid_map/occupancy_inflate \
     /drone_0_planning/bspline \
     /iris_depth_camera/camera/depth/image_raw \
     /iris_depth_camera/camera/depth/camera_info \
     /mavros/battery /gazebo/model_states /rosout > "$RUN/bag.log" 2>&1 &
PID_BAG=$!
sleep 2
log "bag recording -> $BAG"

# ---- 6. 起飞 ----
# 六指标-5: 起飞前 est-vs-truth 偏航探针(磁参数健康的一等公民指标)
YAW_OUT=$(timeout 15 python3 "$SIM/smoke_probe.py" --yaw 2>/dev/null | grep YAWDIFF)
YAWDIFF=$(echo "$YAW_OUT" | grep -o "[-0-9.]*" | head -1)
if [ -n "$YAWDIFF" ] && [ "$YAWDIFF" != "nan" ]; then
    PASS_YAW=$(python3 -c "print(1 if abs(float('$YAWDIFF'))<5 else 0)")
    log "est-vs-truth 偏航差 ${YAWDIFF}deg(<5)->$PASS_YAW (metric: yaw-align)"
else
    YAWDIFF=n/a; PASS_YAW=0
    log "WARN: yaw 探针无数据(odom/gazebo truth 缺)"
fi
bash "$SIM/04_takeoff.sh" >> "$LOG" 2>&1 || fail "takeoff 发布失败"
ARMED=0
for i in $(seq 1 30); do
    timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && { ARMED=1; break; }
    sleep 1
done
[ "$ARMED" -eq 1 ] || fail "起飞后 30s 未 armed(px4ctrl 卡死或 PX4 拒绝;fsm=$(timeout 3 rostopic echo -n1 /debugPx4ctrl/fsm_state 2>/dev/null | head -1);px4ctrl.log 尾部:$(tail -3 "$RUN/px4ctrl.log" 2>/dev/null | tr '\n' ' '))"
log "armed ✓ (metric: armed-ok)"
sleep 8   # 爬升+悬停稳定

# ---- 7. goal ----
log "sending goal ($GOAL_X,$GOAL_Y,$GOAL_Z)"
timeout 4 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
     "{header: {frame_id: 'world'}, pose: {position: {x: $GOAL_X, y: $GOAL_Y, z: $GOAL_Z}}}" >/dev/null 2>&1
# /position_cmd 频率(飞行段采样)
nohup timeout 30 rostopic hz -w 100 /position_cmd > "$RUN/poscmd_hz.txt" 2>&1 &
PID_HZ=$!
# 六指标-6: 飞行中深度流探针(渲染饱和致盲的一等公民指标)
nohup timeout 32 python3 "$SIM/smoke_probe.py" --depthhz > "$RUN/depth_hz.txt" 2>&1 &
PID_DH=$!

ARRIVED=0
for i in $(seq 1 120); do
    p=$(timeout 5 rostopic echo -n1 /mavros/local_position/odom/pose/pose/position 2>/dev/null)
    # 用 python 解析距离,避免 shell 浮点不可用
    d=$(printf '%s' "$p" | python3 -c "
import sys
vals = {}
for ln in sys.stdin:
    ln = ln.strip()
    for k in ('x','y','z'):
        if ln.startswith(k+':'):
            vals[k] = float(ln.split(':')[1])
try:
    dx = vals['x']-$GOAL_X; dy = vals['y']-$GOAL_Y; dz = vals['z']-$GOAL_Z
    print(f'{(dx*dx+dy*dy+dz*dz)**0.5:.3f}')
except KeyError:
    print('nan')
" 2>/dev/null)
    [ "$d" != "nan" ] && [ -n "$d" ] && python3 -c "exit(0 if float('$d')<0.5 else 1)" && { ARRIVED=1; break; }
    sleep 1
done
[ "$ARRIVED" -eq 1 ] && log "到达 goal(<0.5m)✓" || log "WARN: 120s 未到位(记录为指标后继续降落)"
wait ${PID_HZ} 2>/dev/null || true

# ---- 8. 停 planner → 降落 ----
bash "$WS/sitl_sim/kill_planner_all.sh" >> "$LOG" 2>&1 || bash "$SIM/kill_planner_all.sh" >> "$LOG" 2>&1
sleep 2
bash "$SIM/06_land.sh" </dev/null >> "$LOG" 2>&1
DISARM=$?
[ "$DISARM" -eq 0 ] && log "降落自动 disarm ✓ (metric: auto-disarm-ok)" || log "WARN: 降落/disarm 异常(rc=$DISARM)"

# ---- 9. 停 bag + 分析 ----
kill -INT "$PID_BAG" 2>/dev/null; sleep 3; kill -0 "$PID_BAG" 2>/dev/null && kill "$PID_BAG" 2>/dev/null
for i in $(seq 1 20); do [ -f "$BAG" ] && break; sleep 1; done
ANALYSIS="$RUN/analysis.txt"
python3 "$WS/sitl_sim/analysis/analyze_flight.py" "$BAG" --goal "$GOAL_X" "$GOAL_Y" "$GOAL_Z" 2>&1 | tee "$ANALYSIS"

# ---- 10. 六指标判定 ----
ARR_ERR=$(grep -o 'arrival_err(stable 10s mean)=[0-9.]*m' "$ANALYSIS" | sed 's/.*)=//; s/m$//' | head -1)
MIN_DIST=$(grep -o 'overall=[0-9.]*m' "$ANALYSIS" | grep -o '[0-9.]*' | head -1)
HZ=$(grep -o 'average rate: [0-9.]*' "$RUN/poscmd_hz.txt" | grep -o '[0-9.]*' | tail -1)
[ -z "$HZ" ] && HZ=0
PASS_ARR=0; PASS_DIST=0; PASS_HZ=0; PASS_DISARM=0; PASS_DEPTH=0
DEPTHHZ=$(grep -o 'DEPTHHZ=[0-9.]*' "$RUN/depth_hz.txt" 2>/dev/null | grep -o '[0-9.]*' | head -1)
[ -z "$DEPTHHZ" ] && DEPTHHZ=0
python3 -c "exit(0 if float('$DEPTHHZ')>=9 else 1)" 2>/dev/null && PASS_DEPTH=1
python3 -c "exit(0 if float('${ARR_ERR:-99}')<0.5 else 1)" 2>/dev/null && PASS_ARR=1
python3 -c "exit(0 if float('${MIN_DIST:-0}')>0.349 else 1)" 2>/dev/null && PASS_DIST=1
python3 -c "exit(0 if float('$HZ')>=50 else 1)" 2>/dev/null && PASS_HZ=1
[ "$DISARM" -eq 0 ] && PASS_DISARM=1

log "六指标: arrival=${ARR_ERR:-n/a}m(<0.5)->$PASS_ARR  min_dist=${MIN_DIST:-n/a}m(>0.349)->$PASS_DIST  poscmd_hz=$HZ(>=50)->$PASS_HZ  auto_disarm->$PASS_DISARM  yaw_align=${YAWDIFF}deg(<5)->$PASS_YAW  depth_hz=${DEPTHHZ}Hz(>=9)->$PASS_DEPTH"
VERDICT=FAIL
[ $PASS_ARR -eq 1 ] && [ $PASS_DIST -eq 1 ] && [ $PASS_HZ -eq 1 ] && [ $PASS_DISARM -eq 1 ] && [ "$PASS_YAW" = 1 ] && [ $PASS_DEPTH -eq 1 ] && VERDICT=PASS
echo "RESULT=$VERDICT" > "$RUN/RESULT"
log "RESULT=$VERDICT  (全部证据: $RUN)"

# ---- 11. 清理 + 放锁 ----
if [ "$KEEP" -eq 0 ]; then
    pkill -f "devel/lib/ego_planner" 2>/dev/null
    pkill -f "px4ctrl_node" 2>/dev/null
    pkill -f "roslaunch.*run_ctrl_sitl" 2>/dev/null
    pkill -f "roslaunch.*px4.launch" 2>/dev/null
    pkill -9 -f "bin/px4" 2>/dev/null
    pkill -9 -f gzserver 2>/dev/null
    sleep 2
    log "processes cleaned"
fi
bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true
trap - EXIT
python3 "$SIM/status_append.py" "smoke | T1 | sitl_smoke | $VERDICT | goal=($GOAL_X,$GOAL_Y,$GOAL_Z) $RUN"
[ "$VERDICT" = PASS ] && exit 0 || exit 1
