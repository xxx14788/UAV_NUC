#!/usr/bin/env bash
# T3-W2 失败场景修复验证飞行（2026-09-27）。
# 场景 = 2026-09-26 两次坠机的精确复现：机体传送至障碍区侧 (odom 6.9,-4) 起飞，
#   悬停后发返程 goal。修复前该场景必坠（H5 姿态合成缺陷，见 t3_experiments.md W1）。
# 流程: 持锁 → SITL(v1 obstacles) → mavros → px4ctrl → 传送+EKF2收敛等待 → 冷 planner
#   → bag → 起飞 → armed → 悬停 → goal → 到位/发散看门狗 → kill planner → 降落
#   → 停 bag → 双工具分析 → 清理 → 放锁。
# 看门狗(任一触发即中止): |odom_xy|>13(将出图) / 姿态|pitch|>150deg(倒扣) / 150s 超时。
# 用法: bash t3_verify_flight.sh --goal x y z [--tag NAME] [--keep]
#   默认传送位姿 odom (6.9,-4,0.08) yaw -40deg（FAIL1 悬停姿态）。
# 依赖: sitl_smoke.sh 同款基础设施(01/03/04/06 脚本 + sitl_lock.sh + kill_planner_all.sh)。
source /opt/ros/noetic/setup.bash
set -u

SIM="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
source "$WS/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

GOAL_X=1.0; GOAL_Y=0.0; GOAL_Z=1.0; TAG="V"
KEEP=0
while [ $# -gt 0 ]; do
    case "$1" in
    --goal) GOAL_X="$2"; GOAL_Y="$3"; GOAL_Z="$4"; shift 4 ;;
    --tag)  TAG="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    *) echo "未知参数 $1" >&2; exit 2 ;;
    esac
done

# 传送目标(odom) → gazebo 真值 = odom + (1.01, 0.98)
SPAWN_OX=6.9; SPAWN_OY=-4.0; SPAWN_YAW_DEG=${SPAWN_YAW:-145.0}  # T3 末轮:面向goal方位(原-40背对障碍致盲图穿箱,V2f/V2i实证)
GX=$(python3 -c "print(f'{$SPAWN_OX+1.01:.3f}')")
GY=$(python3 -c "print(f'{$SPAWN_OY+0.98:.3f}')")
GZ=0.08
QZ=$(python3 -c "import math;print(f'{math.sin(math.radians($SPAWN_YAW_DEG)/2):.4f}')")
QW=$(python3 -c "import math;print(f'{math.cos(math.radians($SPAWN_YAW_DEG)/2):.4f}')")

RUN="$SIM/t3_runs/${TAG}_$(date +%H%M%S)"
mkdir -p "$RUN"
LOG="$RUN/flight.log"
BAG="$RUN/flight.bag"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
fail() {
    log "ABORT: $*"
    bash "$WS/sitl_sim/kill_planner_all.sh" >>"$LOG" 2>&1 || true
    sleep 1
    bash "$SIM/06_land.sh" </dev/null >>"$LOG" 2>&1 || true
    echo "RESULT=ABORT" > "$RUN/RESULT"
    log "现场保留: $RUN (手动清理: pkill -f 'bin/px[4]|gzserve[r]|px4ctrl_nod[e]|roslaunch.*px4launc[h]|roslaunch.*run_ctrl_sit[l]'; $SIM/sitl_lock.sh release T3)"
    exit 1
}

bash "$SIM/sitl_lock.sh" get "T3-verify-$$" >/dev/null 2>&1 || fail "SITL 锁被占用($($SIM/sitl_lock.sh status))"
trap 'rc=$?; if [ $rc -ne 0 ]; then $SIM/sitl_lock.sh release T3 >/dev/null 2>&1 || true; fi' EXIT
log "lock ok; run=$RUN goal=($GOAL_X,$GOAL_Y,$GOAL_Z) spawn_odom=($SPAWN_OX,$SPAWN_OY,yaw$SPAWN_YAW_DEG)"

pkill -9 -f "bin/px[4]" 2>/dev/null; pkill -9 -f "gzserve[r]" 2>/dev/null
pkill -f "px4ctrl_nod[e]" 2>/dev/null; pkill -f "roslaunch.*px4launc[h]" 2>/dev/null
pkill -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null; pkill -f "devel/lib/ego_planne[r]" 2>/dev/null
sleep 3

timeout 3 rostopic list >/dev/null 2>&1 || { nohup roscore > "$RUN/roscore.log" 2>&1 & sleep 3; }
timeout 3 rostopic list >/dev/null 2>&1 || fail "roscore 起不来"
pgrep -f "Xvfb :99" >/dev/null || { nohup Xvfb :99 -screen 0 1600x1200x24 > "$RUN/xvfb.log" 2>&1 & sleep 2; }
pgrep -f "Xvfb :99" >/dev/null || fail "Xvfb :99 起不来"

log "starting SITL (world=sitl_world_obstacles)"
SITL_WORLD=sitl_world_obstacles nohup bash "$SIM/start_sitl_depth.sh" > "$RUN/sitl.log" 2>&1 &
for i in $(seq 1 60); do pgrep -f "bin/px4" >/dev/null && break; sleep 2; done
pgrep -f "bin/px4" >/dev/null || fail "px4 120s 未出现"

nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$RUN/mavros.log" 2>&1 &
for i in $(seq 1 60); do
    timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && break
    sleep 2
done
timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' || fail "mavros 未连上"
log "mavros connected"

nohup roslaunch px4ctrl run_ctrl_sitl.launch > "$RUN/px4ctrl.log" 2>&1 &
for i in $(seq 1 30); do rosnode info px4ctrl >/dev/null 2>&1 && break; sleep 1; done
rosnode info px4ctrl >/dev/null 2>&1 || fail "px4ctrl 未起来"
sleep 3
log "px4ctrl up"

# ---- 传送前环境自检(W7v1 事故加固:多实例/加载竞态防线) ----
# 2026-09-28 W7v1 轮事故:残留 gazebo 与本轮 world 混流,model_states 出现
# 无箱数组与重名机体 iris_depth_camera_0,传送错机体+150s 未到位。
MODELS=$(timeout 8 rostopic echo -n1 /gazebo/model_states/name 2>/dev/null)
for i in $(seq 1 30); do
    echo "$MODELS" | grep -q box_A && break
    sleep 2; MODELS=$(timeout 8 rostopic echo -n1 /gazebo/model_states/name 2>/dev/null)
done
echo "$MODELS" | grep -q box_A || fail "world 未就绪(30s 无 box_A,疑加载竞态/残留实例),拒飞"
NIRIS=$(echo "$MODELS" | grep -c 'iris')
[ "$NIRIS" -eq 1 ] || fail "iris* 模型 $NIRIS 个(应恰 1,多实例污染),拒飞——现场保留,排查:pgrep -a gzserver"

# ---- 传送(disarmed 状态) + EKF2 收敛等待 ----
log "teleport -> gazebo ($GX,$GY,$GZ) yaw ${SPAWN_YAW_DEG}deg (= odom ($SPAWN_OX,$SPAWN_OY))"
timeout 10 rosservice call /gazebo/set_model_state "{model_state: {model_name: iris_depth_camera, pose: {position: {x: $GX, y: $GY, z: $GZ}, orientation: {x: 0.0, y: 0.0, z: $QZ, w: $QW}}, reference_frame: world}}" >>"$LOG" 2>&1 || fail "set_model_state 服务调用失败"
SETTLED=0
for i in $(seq 1 45); do
    p=$(timeout 5 rostopic echo -n1 /mavros/local_position/odom/pose/pose/position 2>/dev/null)
    d=$(printf '%s' "$p" | python3 -c "
import sys
v={}
for ln in sys.stdin:
    ln=ln.strip()
    for k in ('x','y'):
        if ln.startswith(k+':'): v[k]=float(ln.split(':')[1])
try:
    dx=v['x']-$SPAWN_OX; dy=v['y']-$SPAWN_OY
    print(f'{(dx*dx+dy*dy)**0.5:.3f}')
except KeyError: print('nan')" 2>/dev/null)
    [ "$d" != "nan" ] && [ -n "$d" ] && python3 -c "exit(0 if float('$d')<0.4 else 1)" && { SETTLED=$((SETTLED+1)); } || SETTLED=0
    [ $SETTLED -ge 3 ] && break
    sleep 1
done
[ $SETTLED -ge 3 ] && log "EKF2 已收敛到传送位姿(d=$d m)" || fail "传送后 45s EKF2 未收敛(最后 d=${d:-n/a}m)——估计断裂,不起飞"

# ---- 冷 planner + bag ----
nohup roslaunch ego_planner run_planner_sitl.launch > "$RUN/planner.log" 2>&1 &
for i in $(seq 1 30); do rosnode list 2>/dev/null | grep -q traj_server && break; sleep 1; done
rosnode list 2>/dev/null | grep -q traj_server || fail "planner/traj_server 未起来"
nohup rosbag record -O "$BAG" \
     /debugPx4ctrl /position_cmd /move_base_simple/goal \
     /px4ctrl/takeoff_land /mavros/state /mavros/extended_state \
     /mavros/local_position/odom /mavros/local_position/velocity_local \
     /mavros/imu/data /mavros/setpoint_raw/attitude \
          /drone_0_ego_planner_node/grid_map/occupancy \
     /drone_0_ego_planner_node/grid_map/occupancy_inflate \
     /drone_0_planning/bspline \
     /iris_depth_camera/camera/depth/image_raw \
     /iris_depth_camera/camera/depth/camera_info \
     /mavros/battery /gazebo/model_states /rosout > "$RUN/bag.log" 2>&1 &
PID_BAG=$!
sleep 2
log "planner up (cold), bag recording"

# ---- 起飞 ----
bash "$SIM/04_takeoff.sh" >> "$LOG" 2>&1 || fail "takeoff 发布失败"
ARMED=0
for i in $(seq 1 30); do
    timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && { ARMED=1; break; }
    sleep 1
done
[ "$ARMED" -eq 1 ] || fail "起飞后 30s 未 armed"
log "armed ok, hover settle 10s"
sleep 10

# ---- goal + 看门狗 ----
log "SEND GOAL ($GOAL_X,$GOAL_Y,$GOAL_Z) [带重发:planner 订阅建连有停滞窗口]"
GOAL_OK=0
for gi in 1 2 3 4 5 6; do
    timeout 4 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
         "{header: {frame_id: 'world'}, pose: {position: {x: $GOAL_X, y: $GOAL_Y, z: $GOAL_Z}}}" >/dev/null 2>&1
    # 送达判据:position_cmd 开始产出偏离起飞点>0.3m 的指令
    sleep 4
    cp=$(timeout 4 rostopic echo -n1 /position_cmd/position 2>/dev/null | head -3)
    far=$(printf '%s' "$cp" | python3 -c "
import sys
v={}
for ln in sys.stdin:
    ln=ln.strip()
    for k in ('x','y'):
        if ln.startswith(k+':'): v[k]=float(ln.split(':')[1])
try:
    print('%.3f'%((v['x']-$SPAWN_OX)**2+(v['y']-$SPAWN_OY)**2)**0.5)
except Exception: print('nan')" 2>/dev/null)
    if [ "$far" != "nan" ] && [ -n "$far" ]; then
        python3 -c "exit(0 if float('$far')>0.3 else 1)" && { GOAL_OK=1; log "goal 送达(第 $gi 轮,cmd 偏移 ${far}m)"; break; }
    fi
    log "  第 $gi 轮未确认,2s 后重发"
    sleep 2
done
[ "$GOAL_OK" -eq 1 ] || log "WARN: 6 轮重发仍未见 cmd 偏移(继续监控)"

ARRIVED=0; ABORTED=""
for i in $(seq 1 150); do
    p=$(timeout 5 rostopic echo -n1 /mavros/local_position/odom/pose/pose/position 2>/dev/null)
    m=$(printf '%s' "$p" | python3 -c "
import sys,math
v={}
for ln in sys.stdin:
    ln=ln.strip()
    for k in ('x','y','z'):
        if ln.startswith(k+':'): v[k]=float(ln.split(':')[1])
try:
    dx=v['x']-$GOAL_X; dy=v['y']-$GOAL_Y; dz=v['z']-$GOAL_Z
    dgoal=math.sqrt(dx*dx+dy*dy+dz*dz)
    dcen=math.sqrt(v['x']**2+v['y']**2)
    print('%.3f %.3f %.3f'%(dgoal,dcen,v['z']))
except Exception: print('nan nan nan')" 2>/dev/null)
    d=$(printf '%s' "$m" | cut -d' ' -f1)
    tocenter=$(printf '%s' "$m" | cut -d' ' -f2)
    zval=$(printf '%s' "$m" | cut -d' ' -f3)
    if [ "$d" != "nan" ] && [ -n "$d" ]; then
        python3 -c "exit(0 if float('$d')<0.3 else 1)" && { ARRIVED=1; log "到达 goal d=${d}m"; break; }
        python3 -c "exit(0 if float('$tocenter')>13 else 1)" && { ABORTED="出图风险(|xy|=$tocenter)"; break; }
        python3 -c "exit(0 if float('$zval')>2.6 else 1)" && { ABORTED="高度异常 z=$zval"; break; }
    fi
    # 倒扣看门狗(姿态)
    q=$(timeout 3 rostopic echo -n1 /mavros/imu/data/orientation 2>/dev/null | head -4)
    pit=$(printf '%s' "$q" | python3 -c "
import sys,math
v={}
for ln in sys.stdin:
    ln=ln.strip()
    for k in ('x','y','z','w'):
        if ln.startswith(k+':'): v[k]=float(ln.split(':')[1])
try:
    x,y,z,w=v['x'],v['y'],v['z'],v['w']
    print(f'{math.degrees(math.asin(max(-1,min(1,2*(w*y-z*x))))):.1f}')
except Exception: print('nan')" 2>/dev/null)
    [ "$pit" != "nan" ] && [ -n "$pit" ] && python3 -c "exit(0 if abs(float('$pit'))>150 else 1)" && { ABORTED="倒扣姿态 pitch=${pit}deg"; break; }
    sleep 1
done
[ -n "$ABORTED" ] && log "WATCHDOG ABORT: $ABORTED"
[ "$ARRIVED" -eq 1 ] || log "WARN: 150s 未到位(ABORTED=${ABORTED:-timeout})"

# ---- 停 planner → 降落 ----
bash "$WS/sitl_sim/kill_planner_all.sh" >> "$LOG" 2>&1 || bash "$SIM/kill_planner_all.sh" >> "$LOG" 2>&1
sleep 2
bash "$SIM/06_land.sh" </dev/null >> "$LOG" 2>&1
DISARM=$?

kill -INT "$PID_BAG" 2>/dev/null; sleep 3; kill -0 "$PID_BAG" 2>/dev/null && kill "$PID_BAG" 2>/dev/null
for i in $(seq 1 20); do [ -f "$BAG" ] && break; sleep 1; done

# ---- 分析 ----
log "---- analyze_takeoff_divergence ----"
python3 "$WS/sitl_sim/analysis/analyze_takeoff_divergence.py" "$BAG" 2>&1 | tee "$RUN/divergence.txt"
log "---- analyze_flight ----"
python3 "$WS/sitl_sim/analysis/analyze_flight.py" "$BAG" --goal "$GOAL_X" "$GOAL_Y" "$GOAL_Z" 2>&1 | tee "$RUN/flight_metrics.txt"

VERDICT=FAIL
FLIP=$(grep -c 'flip=True' "$RUN/divergence.txt" || true)
OSC=$(grep -c 'osc=True' "$RUN/divergence.txt" || true)
ARR=$(grep -o 'arrival_err(stable 10s mean)=[0-9.]*m' "$RUN/flight_metrics.txt" | sed 's/.*)=//; s/m$//' | head -1)
[ -n "$ABORTED" ] || { [ "$ARRIVED" -eq 1 ] && [ "$FLIP" -eq 0 ] && [ "$OSC" -eq 0 ] && VERDICT=PASS; }
echo "RESULT=$VERDICT" > "$RUN/RESULT"
log "RESULT=$VERDICT (arrived=$ARRIVED watchdog=${ABORTED:-none} flip=$FLIP osc=$OSC arrival=${ARR:-n/a})"

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
bash "$SIM/sitl_lock.sh" release T3 >/dev/null 2>&1 || true
trap - EXIT
python3 - <<PYEOF
line = "$(date +%H:%M) | T3 | W2 验证轮 $TAG | $VERDICT | goal=($GOAL_X,$GOAL_Y,$GOAL_Z) arrived=$ARRIVED watchdog=${ABORTED:-none} flip=$FLIP osc=$OSC $RUN\n"
open('/home/uav/sitl_sim/STATUS.md','a').write(line)
PYEOF
[ "$VERDICT" = PASS ] && exit 0 || exit 1
