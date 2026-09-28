#!/usr/bin/env bash
# two_leg_flight.sh — 两段式返程腿（T3 W7/W8 分离实验工具，2026-09-28）。
# 与 t3_verify_flight.sh 的差异：不用 gazebo 传送——机体从原点自主飞到
# 障碍区侧（leg1 goal），悬停后再发返程 goal（leg2）。
# 用途：分离"传送/EKF2 重锚"与"返程场景几何"两个因子：
#   两段式 PASS + 传送式 FAIL  → 传送重锚根因（W8-4 配方治理）
#   两段式也 FAIL              → 场景几何/建图根因（W8 M1/M2 路线）
# 用法: two_leg_flight.sh [--leg1 x y z] [--leg2 x y z] [--tag 名]
#   默认 leg1=(7,-4,1) leg2=(1,0,1)
SIM="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
source /opt/ros/noetic/setup.bash  # 先 source 再 set -u（ROS 环境脚本依赖未定义变量）
source "$WS/devel/setup.bash"
set -u

LEG1=(7.0 -4.0 1.0); LEG2=(1.0 0.0 1.0); TAG=2leg
while [ $# -gt 0 ]; do
  case "$1" in
    --leg1) LEG1=("$2" "$3" "$4"); shift 4;;
    --leg2) LEG2=("$2" "$3" "$4"); shift 4;;
    --tag) TAG="$2"; shift 2;;
    *) shift;;
  esac
done

RUN="$SIM/t3_runs/${TAG}_$(date +%H%M%S)"
mkdir -p "$RUN"; LOG="$RUN/flight.log"
log(){ echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
fail(){ log "ABORT: $*"; echo "RESULT=FAIL" > "$RUN/RESULT"; log "现场保留: $RUN"; exit 1; }

bash "$SIM/sitl_lock.sh" get "T3-${TAG}-$$" >/dev/null 2>&1 || fail "锁被占用"
trap 'rc=$?; if [ $rc -ne 0 ]; then $SIM/sitl_lock.sh release T3 >/dev/null 2>&1 || true; fi' EXIT

# 清场（与 smoke 同款）
pkill -9 -f "bin/px[4]" 2>/dev/null; pkill -9 -f "gzserve[r]" 2>/dev/null
pkill -f "px4ctrl_nod[e]" 2>/dev/null; pkill -f "roslaunch.*px4launc[h]" 2>/dev/null
pkill -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null; pkill -f "devel/lib/ego_planne[r]" 2>/dev/null
pkill -f "roslaunc[h]" 2>/dev/null; pkill -f "rosmaste[r]" 2>/dev/null; pkill -f "roscore" 2>/dev/null; pkill -f "rosout" 2>/dev/null
sleep 3

log "leg1=(${LEG1[*]}) leg2=(${LEG2[*]})"
setsid nohup roscore > /tmp/roscore_2leg.log 2>&1 < /dev/null &
sleep 4
[ -d /tmp/.X11-unix ] || Xvfb :99 -screen 0 1280x1024x24 > "$RUN/xvfb.log" 2>&1 &

cd "$SIM" && SITL_WORLD=sitl_world_obstacles nohup bash start_sitl_depth.sh > "$RUN/sitl.log" 2>&1 < /dev/null &
for i in $(seq 1 60); do pgrep -f "bin/px4" >/dev/null && break; sleep 2; done
pgrep -f "bin/px4" >/dev/null || fail "px4 120s 未出现"
# world 就绪+单机体自检
MODELS=$(timeout 8 rostopic echo -n1 /gazebo/model_states/name 2>/dev/null)
for i in $(seq 1 30); do echo "$MODELS" | grep -q box_A && break; sleep 2; MODELS=$(timeout 8 rostopic echo -n1 /gazebo/model_states/name 2>/dev/null); done
echo "$MODELS" | grep -q box_A || fail "world 未就绪"
NIRIS=$(echo "$MODELS" | grep -c 'iris'); [ "$NIRIS" -eq 1 ] || fail "iris* 模型 $NIRIS 个"

nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$RUN/mavros.log" 2>&1 &
for i in $(seq 1 60); do
    timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && break; sleep 2
done
timeout 15 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' || fail "mavros 未连上"
log "mavros connected"

nohup roslaunch px4ctrl run_ctrl_sitl.launch > "$RUN/px4ctrl.log" 2>&1 &
for i in $(seq 1 30); do rosnode info px4ctrl >/dev/null 2>&1 && break; sleep 1; done
rosnode info px4ctrl >/dev/null 2>&1 || fail "px4ctrl 未起来"
sleep 3; log "px4ctrl up"

nohup roslaunch ego_planner run_planner_sitl.launch > "$RUN/planner.log" 2>&1 &
for i in $(seq 1 30); do rosnode list 2>/dev/null | grep -q traj_server && break; sleep 1; done
rosnode list 2>/dev/null | grep -q traj_server || fail "traj_server 未起来"
sleep 3; log "planner up"

nohup rosbag record -O "$RUN/flight.bag" \
     /debugPx4ctrl /position_cmd /move_base_simple/goal \
     /px4ctrl/takeoff_land /mavros/state /mavros/extended_state \
     /mavros/local_position/odom /mavros/local_position/velocity_local \
     /mavros/imu/data /mavros/setpoint_raw/attitude \
     /drone_0_ego_planner_node/grid_map/occupancy \
     /drone_0_ego_planner_node/grid_map/occupancy_inflate \
     /drone_0_planning/bspline /mavros/battery /gazebo/model_states      /mavros/global_position/raw_fix /mavros/imu/atm_pressure /diagnostics > "$RUN/bag.log" 2>&1 &
PID_BAG=$!
log "bag recording"

# T3-E2: 长驻到位探针（新 TCPROS 连接高负载饿死,2legE/F 实证）
cat > /tmp/arr_probe.py <<'PY'
import rospy, math
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64
rospy.init_node('arr_probe')
pub = rospy.Publisher('/arr_probe/d', Float64, queue_size=1)
g = [7.0, -4.0, 1.0]
def cb(m):
    p = m.pose.pose.position
    pub.publish(math.dist((p.x, p.y, p.z), tuple(g)))
rospy.Subscriber('/mavros/local_position/odom', Odometry, cb)
while not rospy.is_shutdown():
    gp = rospy.get_param('/arr_probe/goal', None)
    if gp:
        try: g = [float(x) for x in gp.split()]
        except Exception: pass
    rospy.sleep(1.0)
PY
nohup python3 /tmp/arr_probe.py > /dev/null 2>&1 &
PID_PROBE=$!
rosparam set /arr_probe/goal "${LEG1[*]}"


bash "$SIM/04_takeoff.sh" 90 >>"$LOG" 2>&1 || fail "takeoff 失败"
log "armed, hover settle 8s"; sleep 8

send_goal(){
  timeout 10 rostopic pub -1 /move_base_simple/goal geometry_msgs/PoseStamped \
    "{header: {frame_id: 'world'}, pose: {position: {x: $1, y: $2, z: $3}, orientation: {w: 1.0}}}" >/dev/null 2>&1
}
arrived(){  # $1..3 goal, $4 timeout_s -> 0=arrived
  # T3-E2: 读长驻探针话题（每次新建 TCPROS 连接在高负载下饿死,2legE/F 实证）
  local t0=$(date +%s) d
  rosparam set /arr_probe/goal "$1 $2 $3" 2>/dev/null
  while [ $(( $(date +%s) - t0 )) -lt "${4:-90}" ]; do
    d=$(timeout 12 rostopic echo -n1 /arr_probe/d 2>/dev/null | grep -oE 'data: [0-9.e-]+' | awk '{print $2}')
    [ -n "$d" ] && awk "BEGIN{exit !($d < 0.5)}" && return 0
    sleep 2
  done
  return 1
}

log "SEND leg1 goal (${LEG1[*]})"
for r in 1 2 3; do send_goal "${LEG1[@]}"; sleep 5; done
arrived "${LEG1[@]}" 100 && log "leg1 到位 ✓" || fail "leg1 100s 未到位"
log "leg1 悬停稳定 8s"; sleep 8

log "SEND leg2 (返程) goal (${LEG2[*]})"
for r in 1 2 3; do send_goal "${LEG2[@]}"; sleep 5; done
arrived "${LEG2[@]}" 100 && log "★ leg2 返程到位 ✓✓" || log "leg2 100s 未到位(继续降落收尾)"

timeout 20 rostopic pub -1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 4" >/dev/null 2>&1
sleep 12
kill $PID_BAG 2>/dev/null; sleep 3
log "---- analyze ----"
python3 "$WS/sitl_sim/analysis/analyze_flight.py" "$RUN/flight.bag" --goal "${LEG2[@]}" 2>&1 | tee -a "$LOG"
echo "RESULT=DONE" > "$RUN/RESULT"
bash "$SIM/sitl_lock.sh" release T3 >/dev/null 2>&1 || true
log "done: $RUN"
