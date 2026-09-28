#!/usr/bin/env bash
# resume_X1.sh — 从 init 门之后接手活栈(preflight→px4ctrl→planner→录制→起飞→goal→到位→降落→RESULT→清场)
# 用法: bash resume_X1.sh <run目录> [gx gy gz]
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
EV="${1:?run dir}"; shift || true
GX="${1:-7.0}"; GY="${2:--4.0}"; GZ="${3:-1.0}"
WORLD=sitl_world_obstacles
LOG() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$EV/round.log"; }
LOCK="$HOME/sitl_sim/SITL.lock"
OWNER0=$(readlink "$LOCK" 2>/dev/null || true)
echo "$OWNER0" | grep -q '^T3' || { LOG "FATAL 锁非T3(cur=$OWNER0)"; exit 1; }
cleanup() {
  pkill -f 'vins_nod[e]' 2>/dev/null; pkill -f 'vins_to_mavro[s]' 2>/dev/null
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
  pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
  pkill -x gzclient 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
  pkill -f 'run_ctrl_sitl_vin[s]' 2>/dev/null; pkill -f 'run_planner_sitl_vin[s]' 2>/dev/null
  pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  sleep 3
}
trap 'if [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$OWNER0" ]; then cleanup; rm -f "$LOCK"; fi' EXIT

if ! python3 "$HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py" 10 > "$EV/preflight.txt" 2>&1; then
  LOG "preflight 红项"; tail -8 "$EV/preflight.txt"; exit 1
fi
LOG "preflight 全绿(接手栈)"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 3
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; exit 1; }
nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
sleep 4
rostopic info /position_cmd 2>/dev/null | grep -q Publishers || { LOG "FATAL planner 无 position_cmd"; exit 1; }
LOG "五件套齐(px4ctrl+ego)"

BAG="$EV/flight.bag"
nohup rosbag record -O "$BAG" \
  /vins_estimator/imu_propagate /vins_estimator/odometry /vins_estimator/feature_pts \
  /mavros/imu/data_raw /mavros/local_position/odom /mavros/state \
  /mavros/setpoint_raw/attitude /debugPx4ctrl/fsm_state /debugPx4ctrl \
  /gazebo/model_states /px4ctrl/takeoff_land /position_cmd /move_base_simple/goal /clock \
  > "$EV/record.log" 2>&1 &
REC=$!
sleep 3

LOG "起飞触发"
if ! bash "$HOME/sitl_sim/04_takeoff.sh" 60 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; tail -5 "$EV/takeoff.log"; exit 1
fi
sleep 13
LOG "已等离地稳定"

for k in 1 2; do
  timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
    "{header: {frame_id: 'world'}, pose: {position: {x: $GX, y: $GY, z: $GZ}}}" >/dev/null 2>&1
  sleep 2
done
LOG "goal 已发 ($GX $GY $GZ)"

timeout -s INT 100 python3 - "$GX" "$GY" "$GZ" "100" > "$EV/arrive_watch.txt" 2>&1 <<'PYEOF'
import sys, math, time
import rospy
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
gx, gy, gz, budget = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
gx, gy, gz = float(gx), float(gy), float(gz)
rospy.init_node('vsmoke_arrive', disable_signals=True)
st = {'anchor': None, 'p0': None, 'min_t': 1e9, 'min_v': 1e9,
      'last': None, 'ok_since': None, 'arrived': False}
def odom_cb(m):
    p = m.pose.pose.position
    if st['p0'] is None: st['p0'] = (p.x, p.y, p.z)
    d = math.sqrt((p.x-gx)**2 + (p.y-gy)**2 + (p.z-gz)**2)
    st['min_v'] = min(st['min_v'], d)
def truth_cb(m):
    try: i = m.name.index('iris_stereo_vins')
    except ValueError: return
    p = m.pose[i].position
    if st['anchor'] is None and st['p0'] is not None:
        st['anchor'] = (p.x - st['p0'][0], p.y - st['p0'][1], p.z - st['p0'][2])
        print('anchor: (%.3f, %.3f, %.3f)' % st['anchor'], flush=True)
    if st['anchor'] is None: return
    tx, ty, tz = gx + st['anchor'][0], gy + st['anchor'][1], gz + st['anchor'][2]
    d = math.sqrt((p.x-tx)**2 + (p.y-ty)**2 + (p.z-tz)**2)
    st['last'] = d; st['min_t'] = min(st['min_t'], d)
    now = time.monotonic()
    if d < 0.5:
        if st['ok_since'] is None: st['ok_since'] = now
        if now - st['ok_since'] >= 2.0: st['arrived'] = True
    else: st['ok_since'] = None
rospy.Subscriber('/vins_estimator/imu_propagate', Odometry, odom_cb, queue_size=2)
rospy.Subscriber('/gazebo/model_states', ModelStates, truth_cb, queue_size=2)
t_end = time.monotonic() + budget - 10
r = rospy.Rate(10)
while time.monotonic() < t_end and not st['arrived'] and not rospy.is_shutdown():
    try: r.sleep()
    except Exception: time.sleep(0.1)
print(('ARRIVED_TRUTH min_d=%.3f' % st['min_t']) if st['arrived']
      else ('TIMEOUT min_truth=%.3f last=%.3f min_vins=%.3f' % (st['min_t'], st['last'] or -1, st['min_v'])))
PYEOF
ARR=$(tail -1 "$EV/arrive_watch.txt")
LOG "到位: $ARR"
timeout 8 rostopic hz /position_cmd 2>/dev/null | grep 'average rate' | tail -1 > "$EV/poscmd_hz.txt"

LOG "降落指令"
disarmed=0
for k in 1 2 3; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  for j in $(seq 1 12); do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { disarmed=1; break 2; }
    sleep 1
  done
done
[ $disarmed = 1 ] && LOG "已 disarm" || LOG "WARN 降落未确认"
sleep 3
kill -INT $REC 2>/dev/null; sleep 3
bash "$HOME/sitl_sim/round_result.sh" "$BAG" "$GX" "$GY" "$GZ" "$WORLD" "$EV" "$ARR" "N/A" "0" "0" "0" "0" > "$EV/RESULT.txt" 2>&1
tail -8 "$EV/RESULT.txt"
LOG "接手轮完成 bag=$BAG"
