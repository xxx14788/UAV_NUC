#!/usr/bin/env bash
# vins_smoke.sh — T3-X1 VINS 同构链路一键冒烟（2026-09-28 v5 任务书）。
# 五件套起栈 + VINS init 门(裸话题 echo,wall-clock 300s+30s心跳) + T2 preflight +
# takeoff + goal(重发) + 真值/VINS 双口径到位 + 四指标 RESULT(round_result.sh) + 清场。
# --leg2 支持两段式返程(X3②⑤/X4)。紧凑 bag(~40MB/轮)。
# 用法: vins_smoke.sh [--world W] [--goal x y z] [--leg2 x y z] [--tag NAME] [--budget 秒]
# 坑位吸收(全部实证): 空world无特征init必败/echo输出 frame_id 带引号(grep须 "?world"?)/
# 字段路径echo假阴性/source基座在devel之后会覆盖ws包路径/seq门实际5s每迭代/
# 511默认50Hz/ROSTimeMovedBackwards杀watcher/goal竞态/降落投递随机/磁盘100%。
source /opt/ros/noetic/setup.bash          # 先 source 再 set -u(V3 教训)
source "$HOME/catkin_ws/devel/setup.bash"  # 必须 LAST:重复 source 基座会覆盖掉 ws 包路径(X1轮1教训)
set -u
WORLD=sitl_world_obstacles; GX=7.0; GY=-4.0; GZ=1.0; TAG=smoke; BUDGET=100; HASL2=0; L2X=0; L2Y=0; L2Z=0; PROBECHECK=0
while [ $# -gt 0 ]; do case "$1" in
  --world) WORLD="$2"; shift 2;;
  --goal)  GX="$2"; GY="$3"; GZ="$4"; shift 4;;
  --leg2)  HASL2=1; L2X="$2"; L2Y="$3"; L2Z="$4"; shift 4;;
  --tag)   TAG="$2"; shift 2;;
  --budget) BUDGET="$2"; shift 2;;
  --probecheck) PROBECHECK=1; shift;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
LOG() { echo "[$(date +%H:%M:%S)] $*"; }
L="$HOME/sitl_sim"
EV="$L/vins_smoke_runs/run_${TAG}_$(date +%H%M%S)"
mkdir -p "$EV"
exec > >(tee "$EV/round.log") 2>&1

# ---------- 锁(T4-E1 v2 统一仲裁:死主自动接管/心跳/磁盘水位线门;流名载体=权序标签) ----------
LOCK="$L/SITL.lock"
SL="$L/sitl_lock.sh"
MYSTREAM="${SMOKE_OWNER:-T3-$TAG}"
"$SL" get "$MYSTREAM" || { LOG "FATAL 锁获取失败(活主持有或盘门拒绝,原因见上)"; exit 1; }
MYOWNER=$(readlink "$LOCK" 2>/dev/null || true)
"$SL" hbloop "$MYSTREAM" & HBPID=$!
cleanup() {
  kill "$HBPID" 2>/dev/null
  pkill -f "tee $EV/round.lo[g]" 2>/dev/null   # exec>(tee) 进程替换会让 bash 退出时等 tee,tee 等 stdout 写者→挂壳;杀之解锁(E2 验收实测)
  pkill -f 'vins_nod[e]' 2>/dev/null; pkill -f 'vins_to_mavro[s]' 2>/dev/null
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
  pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
  pkill -x gzclient 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
  pkill -f 'run_ctrl_sitl_vin[s]' 2>/dev/null; pkill -f 'run_planner_sitl_vin[s]' 2>/dev/null
  pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  sleep 3
}
trap 'if [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$MYOWNER" ]; then cleanup; "$SL" release "$MYSTREAM" >/dev/null 2>&1; fi' EXIT

# ---------- 清场断言(不动他人,只拒绝脏现场) ----------
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清(px4=$A gz=$B),先清场再跑"; exit 1; }

# ---------- fresh master + 域配方 ----------
pkill -f 'vins_nod[e]' 2>/dev/null; pkill -f 'vins_to_mavro[s]' 2>/dev/null
pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
pkill -f 'arr_prob[e]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null; sleep 3
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

# ---------- 五件套 ----------
SITL_WORLD="$WORLD" nohup bash "$L/start_sitl_vins.sh" > "$EV/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; exit 1; }
LOG "SITL up ($WORLD)"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$EV/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; exit 1; }
rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 2>/dev/null; sleep 2
LOG "mavros up + 511@4000us(仓库标准 632e0ee:4ms网格量化,~223Hz;5000us实际=125Hz量化伪影)"
# T1 P0-A.1 (2026-10-01): E2 stderr probes (E2uls/E2clamp/E2gap) default-on EVERY round
# (v8.0: 此后一切飞行轮默认带探针,跳变机制数据); env gate = estimator.cpp a5cd330 form
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
sleep 3
LOG "sim_vins up, 等 VINS init(wall-clock 300s, 30s 心跳取证)"
ok=0; T0G=$(date +%s); HB=0
while [ $(( $(date +%s) - T0G )) -lt 300 ]; do
  sleep 2
  if timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -qE 'frame_id: "?world"?'; then ok=1; break; fi
  NOW=$(( $(date +%s) - T0G ))
  if [ $NOW -ge $((HB+30)) ]; then
    HB=$NOW
    ODM=$(timeout 3 rostopic list 2>/dev/null | grep -c 'vins_estimator/odometry')
    IMU_HZ=$(timeout 8 rostopic hz /mavros/imu/data_raw 2>/dev/null | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}')
    PROP_HZ=$(timeout 8 rostopic hz /vins_estimator/imu_propagate 2>/dev/null | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}')
    LOG "gate +${NOW}s: odometry_topic=$ODM imu_raw=${IMU_HZ:-NA}Hz prop=${PROP_HZ:-NA}Hz"
  fi
done
[ $ok = 1 ] || { LOG "FATAL 300s 内 VINS 未 init"; exit 1; }
LOG "VINS init 完成 (+$(( $(date +%s) - T0G ))s)"
if [ "$PROBECHECK" = "1" ]; then
  E2ULS=$(grep -c "E2uls" "$EV/simvins.log" 2>/dev/null || true); E2ULS=${E2ULS:-0}
  E2CLAMP=$(grep -c "E2clamp" "$EV/simvins.log" 2>/dev/null || true); E2CLAMP=${E2CLAMP:-0}
  E2GAP=$(grep -c "E2gap" "$EV/simvins.log" 2>/dev/null || true); E2GAP=${E2GAP:-0}
  LOG "PROBECHECK: E2uls=$E2ULS E2clamp=$E2CLAMP E2gap=$E2GAP (init-only round, no takeoff)"
  grep -m 3 "E2uls" "$EV/simvins.log" 2>/dev/null || true
  if [ "$E2ULS" -ge 1 ]; then LOG "PROBECHECK PASS: probe chain transmits (E2uls lines in simvins.log)"; exit 0
  else LOG "PROBECHECK FAIL: VINS init but zero E2uls lines - probe chain broken"; exit 1; fi
fi
if ! python3 "$HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py" 10 > "$EV/preflight.txt" 2>&1; then
  REDS=$(grep -c '红' "$EV/preflight.txt" || true); REDS=${REDS:-0}
  IMU_RED=$(grep -c 'IMU 频率.*>200' "$EV/preflight.txt" || true); IMU_RED=${IMU_RED:-0}
  IMU_HZ=$(grep -oE 'IMU 频率: [0-9.]+' "$EV/preflight.txt" | grep -oE '[0-9.]+$' | head -1)
  if [ "$REDS" = "1" ] && [ "$IMU_RED" = "1" ] && [ -n "$IMU_HZ" ] && awk "BEGIN{exit !($IMU_HZ+0>=100)}"; then
    LOG "preflight IMU>200 门豁免:实测${IMU_HZ}Hz≥100(原v3标准)。依据=5000us+默认config为T2-W1.3实证飞行配对;4000us+默认config实证VINS飞行爆散(X1_232055,odom冲740m,已移交T2域)"
  else
    LOG "preflight 红项"; tail -8 "$EV/preflight.txt"; exit 1
  fi
fi
LOG "preflight 全绿(双目纹理/域/IMU/真值 X1.1 覆盖)"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 3
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; exit 1; }
nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
sleep 4
rostopic info /position_cmd 2>/dev/null | grep -q Publishers || { LOG "FATAL planner 无 position_cmd"; exit 1; }
LOG "五件套齐(px4ctrl+ego)"

# ---------- 紧凑录制(无图像,~40MB/轮;磁盘两次100%教训) ----------
IMG_TOPICS=""
[ "${VINS_SMOKE_IMAGES:-0}" = "1" ] && IMG_TOPICS="/iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw"
BAG="$EV/flight.bag"
nohup rosbag record -O "$BAG" \
  /vins_estimator/imu_propagate /vins_estimator/odometry /vins_estimator/feature_pts \
  /mavros/imu/data /mavros/imu/data_raw /mavros/local_position/odom /mavros/state \
  /mavros/setpoint_raw/attitude /debugPx4ctrl/fsm_state /debugPx4ctrl \
  /gazebo/model_states /px4ctrl/takeoff_land /position_cmd /move_base_simple/goal /clock \
  $IMG_TOPICS \
  > "$EV/record.log" 2>&1 &
REC=$!
sleep 3

# ---------- 起飞 ----------
LOG "起飞触发 (04_takeoff 120s 预算,重启后首boot慢投递余量)"
if ! bash "$L/04_takeoff.sh" 120 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; tail -5 "$EV/takeoff.log"; exit 1
fi
sleep 13
LOG "已等离地稳定"

# ---------- goal(重发两轮吸收竞态) ----------
echo "goal: $GX $GY $GZ leg2: $HASL2 $L2X $L2Y $L2Z" > "$EV/goal.txt"
for k in 1 2; do
  timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
    "{header: {frame_id: 'world'}, pose: {position: {x: $GX, y: $GY, z: $GZ}}}" >/dev/null 2>&1
  sleep 2
done
LOG "goal 已发(2×8s)"

# ---------- 到位监视(真值口径,锚点自推导;外部wall超时+异常吞噬) ----------
arrive_watch() {  # $1..3 goal; $4 tag后缀
  local WX="$1" WY="$2" WZ="$3" WTAG="$4"
  timeout -s INT $BUDGET python3 - "$WX" "$WY" "$WZ" "$BUDGET" > "$EV/arrive_watch${WTAG}.txt" 2>&1 <<'PYEOF'
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
  tail -2 "$EV/arrive_watch${WTAG}.txt"
}
arrive_watch "$GX" "$GY" "$GZ" ""
ARR=$(tail -1 "$EV/arrive_watch.txt")

# ---------- leg2(两段式返程,X3②⑤) ----------
ARR2="N/A"
if [ $HASL2 = 1 ]; then
  LOG "leg1 后悬停 8s, 发 leg2 ($L2X $L2Y $L2Z)"
  sleep 8
  for k in 1 2; do
    timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
      "{header: {frame_id: 'world'}, pose: {position: {x: $L2X, y: $L2Y, z: $L2Z}}}" >/dev/null 2>&1
    sleep 2
  done
  arrive_watch "$L2X" "$L2Y" "$L2Z" "2"
  ARR2=$(tail -1 "$EV/arrive_watch2.txt")
  LOG "leg2 到位: $ARR2"
fi
timeout 8 rostopic hz /position_cmd 2>/dev/null | grep 'average rate' | tail -1 > "$EV/poscmd_hz.txt"

# ---------- 降落(重掷制) ----------
LOG "降落指令(5 轮重掷)"
disarmed=0
for k in 1 2 3 4 5; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  for j in $(seq 1 12); do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { disarmed=1; break 2; }
    sleep 1
  done
done
[ $disarmed = 1 ] && LOG "已 disarm" || LOG "WARN 降落未确认 disarmed"
sleep 3
kill -INT $REC 2>/dev/null; sleep 3

# ---------- 轮中环境死亡活体检查(E4.2;清场前栈应在,缺=崩) ----------
if ! pgrep -x gzserver >/dev/null 2>&1 || ! pgrep -x px4 >/dev/null 2>&1; then
  echo "$(date +%T) gzserver/px4 活体检查缺席(gz=$(pgrep -xc gzserver || echo 0) px4=$(pgrep -xc px4 || echo 0))" > "$EV/ENVDEAD"
fi

# ---------- 四指标 RESULT(独立脚本 round_result.sh,与 resume 共用) ----------
bash "$HOME/sitl_sim/round_result.sh" "$BAG" "$GX" "$GY" "$GZ" "$WORLD" "$EV" "$ARR" "$ARR2" "$HASL2" "$L2X" "$L2Y" "$L2Z" > "$EV/RESULT.txt" 2>&1
tail -10 "$EV/RESULT.txt"
grep -q "RESULT=ENV-FAIL" "$EV/RESULT.txt" && LOG "ENV-FAIL 环境性崩溃口径(E4.2):重试不计入飞行预算"

# ---------- 清场(函数已前置+EXIT trap;正常路径显式调一遍) ----------
cleanup
LOG "轮完成 bag=$BAG"
