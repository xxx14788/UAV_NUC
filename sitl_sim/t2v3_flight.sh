#!/usr/bin/env bash
# T2-v3 W1/W2 在线飞行编排(VINS 同构链路)。用法: t2v3_flight.sh <mode>
#   ground 地面轮(W1.1): 栈+静置40s,不起飞
#   hover  悬停轮(W1.2): px4ctrl(VINS odom 直供) 起飞0.75m 悬停30s 降落
#   route  航线轮(W1.3): 全五件套,goal(3,-2,1)→原点(0,0,1),双口径到位
#   w2a..w2e 鲁棒场景(W2): sim_vins 链路(EKF2 EV 融合闭环) + A-E 激励 flyer
# 域配方: use_sim_time=true 在 mavros 前(U6);preflight 五项门;bag 双口径全录。
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
MODE="${1:?ground|hover|route|w2a..w2e}"
LOG() { echo "[$(date +%H:%M:%S)] $*"; }

# ---------- 锁与清场 ----------
[ "$(readlink $HOME/sitl_sim/SITL.lock 2>/dev/null)" = "T2" ] || { LOG "FATAL 未持锁"; exit 1; }
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清($A/$B)"; exit 1; }
rosparam set /use_sim_time true 2>/dev/null || true
yes | rosnode cleanup >/dev/null 2>&1
pgrep -x roscore >/dev/null || { nohup roscore >/dev/null 2>&1 & sleep 3; }
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

# ---------- SITL + mavros + 提频 ----------
SITL_WORLD=sitl_world_obstacles nohup bash $HOME/sitl_sim/start_sitl_vins.sh \
  > $HOME/sitl_sim/t2v3_sitl_${MODE}.log 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; exit 1; }
LOG "SITL up"
nohup bash $HOME/catkin_ws/sitl_sim/02_start_mavros.sh > $HOME/sitl_sim/t2v3_mavros_${MODE}.log 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; exit 1; }
rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0 2>/dev/null
sleep 2
LOG "mavros up, IMU 提频"

# ---------- 装配 ----------
nohup roslaunch $HOME/catkin_ws/src/launch/sim_vins.launch > $HOME/sitl_sim/t2v3_simvins_${MODE}.log 2>&1 &
sleep 3
case "$MODE" in
  hover|route)
    nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > $HOME/sitl_sim/t2v3_px4ctrl_${MODE}.log 2>&1 &
    sleep 3
    if ! rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers; then
      LOG "px4ctrl 无响应,重启"; pkill -f run_ctrl_sitl_vins; sleep 2
      nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch >> $HOME/sitl_sim/t2v3_px4ctrl_${MODE}.log 2>&1 &
      sleep 3
    fi ;;
esac
[ "$MODE" = "route" ] && {
  nohup roslaunch ego_planner run_planner_sitl_vins.launch relay_on:=false > $HOME/sitl_sim/t2v3_planner_${MODE}.log 2>&1 &
  sleep 3; }
LOG "装配完成 ($MODE)"

# ---------- 录制 ----------
BAG=$HOME/sitl_sim/bags/t2v3_${MODE}_$(date +%H%M%S).bag
LOG "bag: $BAG"
FEATURE_TOPICS=""
rostopic list 2>/dev/null | grep -q "/vins_estimator/feature_pts" && FEATURE_TOPICS="/vins_estimator/feature_pts"
nohup rosbag record -O "$BAG" \
  /iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw \
  /mavros/imu/data_raw /mavros/local_position/odom /mavros/local_position/pose \
  /mavros/state /mavros/vision_pose/pose /vins_estimator/odometry \
  /vins_estimator/imu_propagate $FEATURE_TOPICS /position_cmd /move_base_simple/goal \
  /gazebo/model_states /px4ctrl/takeoff_land \
  > $HOME/sitl_sim/t2v3_record_${MODE}.log 2>&1 &
REC_PID=$!
sleep 3

LOG "静置 20s (VINS init 窗口)"
sleep 20
LOG "preflight 自检"
if ! python3 $HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py 10; then
  LOG "preflight 红项, 中止"; kill -INT $REC_PID; exit 1
fi

# ---------- 飞行 ----------
ARRIVE=0
case "$MODE" in
  ground)
    LOG "地面轮: 追加静置 20s"
    sleep 20 ;;
  hover)
    LOG "起飞(0.75m)"
    timeout 30 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1
    sleep 10
    LOG "悬停 30s"
    sleep 30
    LOG "降落"
    timeout 30 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
    sleep 12 ;;
  route)
    LOG "起飞"
    timeout 30 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1
    sleep 12
    for G in "3 -2 1" "0 0 1"; do
      set -- $G
      # RTF 低载时 rostopic pub 的 python 启动可超 6s 一条未发(实测 goal 零到
      # 达 FSM)——加长窗口 + FSM "Triggered" 回执重试
      for TRY in 1 2 3; do
        LOG "发 goal ($1,$2,$3) try$TRY"
        timeout 25 rostopic pub -r 2 /move_base_simple/goal geometry_msgs/PoseStamped \
          "{header: {frame_id: 'world'}, pose: {position: {x: $1, y: $2, z: $3}}}" >/dev/null 2>&1
        sleep 2
        if grep -q Triggered $HOME/sitl_sim/t2v3_planner_route.log 2>/dev/null; then
          LOG "goal 已达 FSM(Triggered)"
          break
        fi
        LOG "goal 未达 FSM, 重试"
      done
      python3 - "$1" "$2" "$3" <<'EOF'
import sys, rospy
from nav_msgs.msg import Odometry
gx, gy, gz = map(float, sys.argv[1:4])
rospy.init_node('t2v3_arrive_watch', disable_signals=True)
st = {'t_ok': 0, 'd': 1e9, 'min': 1e9, 'vmin': 1e9}
def cb(m):
    p = m.pose.pose.position
    d = ((p.x-gx)**2 + (p.y-gy)**2 + (p.z-gz)**2) ** 0.5
    st['d'] = d; st['min'] = min(st['min'], d)
    st['t_ok'] = st['t_ok'] + 0.5 if d < 0.5 else 0
rospy.Subscriber('/mavros/local_position/odom', Odometry, cb, queue_size=2)
import time as _time
t0 = _time.time()
while _time.time() - t0 < 240 and not rospy.is_shutdown():
    _time.sleep(0.5)   # 墙钟计时(sim 时钟倒流/停滞免疫), 240s 墙钟裕量(RTF 低载)
    if st['t_ok'] >= 3.0:
        print('ARRIVED min_d=%.3f' % st['min']); sys.exit(0)
print('TIMEOUT min_d=%.3f last_d=%.3f' % (st['min'], st['d'])); sys.exit(1)
EOF
      RC=$?
      LOG "到位 rc=$RC"
      sleep 5
    done
    LOG "降落"
    timeout 30 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
    sleep 12 ;;
  w2*)
    PROF=${MODE#w2}
    LOG "W2 场景 $PROF: 静置补 10s 后启动 flyer"
    sleep 10
    timeout 200 python3 $HOME/sitl_sim/t2_offboard_fly.py "$PROF" > $HOME/sitl_sim/t2v3_flyer_${PROF}.log 2>&1
    LOG "flyer rc=$?"
    sleep 5 ;;
esac

kill -INT $REC_PID 2>/dev/null; sleep 3

# ---------- 清场 ----------
pkill -f 'simulator_mavlink' 2>/dev/null; pkill -f 'sitl_run.sh' 2>/dev/null
pkill -f 'bin/px4' 2>/dev/null; pkill -x gzserver 2>/dev/null; pkill -x gzclient 2>/dev/null
pkill -f '02_start_mavros' 2>/dev/null; pkill -x mavros_node 2>/dev/null
pkill -f 'run_ctrl_sitl' 2>/dev/null; pkill -f 'run_planner_sitl' 2>/dev/null
pkill -f 'src/launch/sim_vins.launch' 2>/dev/null; pkill -f 'vins_node' 2>/dev/null
sleep 3
bash "$HOME/sitl_sim/sitl_lock.sh" release T2 >/dev/null 2>&1 || true
LOG "$MODE 完成 bag=$BAG"
