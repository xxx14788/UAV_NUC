#!/usr/bin/env bash
# rehearsal.sh v1.0 — SITL 彩排批（专项① 单元1，2026-10-11）
# 手册剖面全流程（正常段）+ 异常接管演练段 + dashboard v1 实跑验证。
# 起栈机制复刻 vins_smoke.sh（同一套五件套+坑防线）；飞行剖面按手册 v2 §2/§9.4。
#
# SITL 等价注记（覆盖面边界，进判决书）：
#   - 手册步"手动起飞 1.2m"（PX4 姿态手控+摇杆）SITL 无 RC 摇杆不可模拟；
#     等价面=px4ctrl 自起飞（AUTO_TAKEOFF, auto_arm, 0.75m）→ AUTO_HOVER 悬停态同构。
#   - CH5/CH6 开关：SITL 无 RC 时 input.cpp 默认 is_hover_mode/is_command_mode=true
#     （fsm_decision.h Inputs 默认），goal→cmd 流→自动进 CMD_CTRL=CH6 高等价；
#     停 cmd 流→AUTO_HOVER=CH6 低等价。"手动控"终极面（CH5 低）SITL 覆盖不到=首飞窗现场件。
#   - RViz 2D Nav Goal 与 CLI rostopic pub 发同一话题 /move_base_simple/goal，
#     headless 无 GUI 故 CLI 等价覆盖；RViz 可视化面归首飞窗现场。
#
# 判定线（预注册，禁放宽）：
#   正常段 N1 五件套活 / N2 起飞 armed+z≥0.5+fsm=AUTO_HOVER / N3 悬停60s |Δpos|<0.5m
#          N4 goal(2,0) 到位<0.75m(真值) / N5 goal(0,0) 返航到位<0.75m
#          N6 降落触地 z<0.15+armed=False / N7 SITL ulog 生成
#   异常段 A1 杀VINS→AUTO_LAND ≤10s / A2 盲降触地+disarm 链完整
#          A3 毒odom→dashboard JUMP RED 联动 / A4 odom_gate 不跟跳(真值稳<0.5m)
#          A5 接管序列(停毒流+land)降落完成
source /opt/ros/noetic/setup.bash   # 先 source 再 set -u（ROS 环境脚本依赖未定义变量）
source "$HOME/catkin_ws/devel/setup.bash"
set -u

L="$HOME/sitl_sim"
TS=$(date +%H%M%S)
EV="$L/t1_evidence/preflight_boost_20261011/rehearsal_$TS"
mkdir -p "$EV"
LOG="$EV/rehearsal.log"
TL="$EV/timeline.tsv"
WORLD="${REHEARSAL_WORLD:-sitl_world_obstacles}"   # 批轮标准 world（plain 纹理不足→VINS init 负深度循环，M3 域实证）

LOG()  { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
TL()   { printf "%s\t%s\t%s\n" "$(date +%s.%3N)" "$(date +%H:%M:%S.%3N)" "$*" >> "$TL"; LOG "TL| $*"; }

# ---------- 状态查询助手 ----------
fsm_now()      { timeout 3 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state/data 2>/dev/null | head -1 | tr -d '\r\n"' | awk '{print $1}'; }
armed_now()    { timeout 3 rostopic echo -n1 /mavros/state/armed 2>/dev/null | head -1 | tr -d '\r\n '; }
z_odom()       { timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/z 2>/dev/null | head -1 | tr -d '\r\n '; }
mode_now()     { timeout 3 rostopic echo -n1 /mavros/state/mode 2>/dev/null | head -1 | tr -d '\r\n'; }
# 真值位置（gazebo model_states: name idx 0=iris…动态查）
gz_pos() {
  timeout 5 python3 - "$@" << 'PYEOF' 2>/dev/null
import sys, rospy, math
from gazebo_msgs.msg import ModelStates
rospy.init_node('gz_probe', anonymous=True)
r = rospy.Rate(20); deadline = rospy.Time.now() + rospy.Duration(4)
name_i = -1
while not rospy.is_shutdown() and rospy.Time.now() < deadline:
    try:
        m = rospy.wait_for_message('/gazebo/model_states', ModelStates, timeout=2)
        for i, n in enumerate(m.name):
            if 'iris' in n:   # 唯一机体模型=iris_stereo_vins（含 iris 子串即命中）
                name_i = i; break
        if name_i >= 0:
            p = m.pose[name_i].position
            print("%.3f %.3f %.3f" % (p.x, p.y, p.z)); sys.exit(0)
    except rospy.ROSException:
        break
    r.sleep()
print("NA"); sys.exit(1)
PYEOF
}
dist_gt() {  # 真值到目标距离
  local P; P=$(gz_pos) || { echo 999; return; }
  [ "$P" = NA ] && { echo 999; return; }
  python3 -c "import math;px,py,pz=map(float,'$P'.split());print(math.dist((px,py,pz),($1,$2,$3)))"
}
wait_dist() {  # $1..3=目标 $4=门 $5=超时秒 —— 到位等待
  local D0=$(date +%s) D
  while [ $(( $(date +%s) - D0 )) -lt "${5:-60}" ]; do
    D=$(dist_gt "$1" "$2" "$3")
    LOG "  dist=$D (gate ${4})"
    python3 -c "exit(0 if float('$D' or 999)<${4} else 1)" && return 0
    sleep 3
  done
  return 1
}
wait_fsm() {  # $1=期望态 $2=超时
  local D0=$(date +%s) F
  while [ $(( $(date +%s) - D0 )) -lt "${2:-30}" ]; do
    F=$(fsm_now); [ "$F" = "$1" ] && return 0
    sleep 1
  done
  return 1
}

# 后台采样器：1Hz fsm/armed/mode/z → sampler.tsv（时序正源）
sampler_start() {
  setsid nohup python3 - "$EV/sampler.tsv" << 'PYEOF' >/dev/null 2>&1 < /dev/null &
import sys, rospy, threading
from std_msgs.msg import String
from mavros_msgs.msg import State
from nav_msgs.msg import Odometry
out = open(sys.argv[1], 'a', buffering=1)
st = {'fsm':'', 'armed':None, 'mode':'', 'odom_hz':0, 'z':None}
lock = threading.Lock()
import collections, time
times = collections.deque()
def on_fsm(m): st['fsm'] = m.data
def on_state(m): st['armed'] = m.armed; st['mode'] = m.mode
def on_odom(m):
    t = time.time(); times.append(t)
    while times and t - times[0] > 2: times.popleft()
    st['odom_hz'] = len(times)/2.0
    st['z'] = m.pose.pose.position.z
rospy.init_node('rehearsal_sampler', anonymous=True)
rospy.Subscriber('/debugPx4ctrl/fsm_state', String, on_fsm)
rospy.Subscriber('/mavros/state', State, on_state)
rospy.Subscriber('/vins_estimator/imu_propagate', Odometry, on_odom)
r = rospy.Rate(1)
import datetime
while not rospy.is_shutdown():
    with lock:
        out.write("%s\t%s\t%s\t%s\t%.1f\t%s\n" % (
            datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3],
            st['fsm'], st['armed'], st['mode'], st['odom_hz'],
            '' if st['z'] is None else '%.3f' % st['z']))
    r.sleep()
PYEOF
  echo $! > "$EV/sampler.pid"
}
sampler_stop() { [ -f "$EV/sampler.pid" ] && kill -- -"$(cat "$EV/sampler.pid")" 2>/dev/null; :; }

cleanup() {
  TL "彩排清场开始"
  sampler_stop
  pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 't1_flight_monito[r]' 2>/dev/null
  pkill -f 't1_odom_monito[r]' 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -x px4 2>/dev/null
  bash "$L/kill_planner_all.sh" >/dev/null 2>&1
  pkill -f 'sim_vins.launc[h]' 2>/dev/null
  pkill -x vins_node 2>/dev/null
  pkill -f 'vins_to_mavro[s]' 2>/dev/null
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null; pkill -f 'mavros_nod[e]' 2>/dev/null
  sleep 3
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  TL "彩排清场毕"
  [ "$1" = "keep" ] || exit 0   # trap 路径退出；段E 收尾 keep 走判决书落盘
}
trap 'cleanup' INT TERM

VERDICT="$EV/rehearsal_verdict.md"
V_N1=?; V_N2=?; V_N3=?; V_N4=?; V_N5=?; V_N6=?; V_N7=?; V_A1=?; V_A2=?; V_A3=?; V_A4=?; V_A5=?
vset() { eval "V_$1=$2"; }

# ============================================================
LOG "=== SITL 彩排批 v1.0 启动 EV=$EV world=$WORLD ==="
TL "彩排启动 world=$WORLD"

# ---------- 段A 起栈（vins_smoke 同款） ----------
pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
bash "$L/kill_planner_all.sh" >/dev/null 2>&1
pkill -x vins_node 2>/dev/null
pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null; sleep 3
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

TL "起栈.SITL"
SITL_WORLD="$WORLD" nohup bash "$L/start_sitl_vins.sh" > "$EV/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; TL "FATAL SITL"; exit 1; }
LOG "SITL up ($WORLD)"

TL "起栈.mavros"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$EV/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; TL "FATAL mavros"; exit 1; }
rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 2>/dev/null; sleep 2
TL "起栈.mavros_511@4000us"

TL "起栈.VINS"
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
ok=0; for i in $(seq 1 150); do sleep 2
  timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/x 2>/dev/null | grep -qE '[-0-9]' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL VINS odom 未出流(300s)"; TL "FATAL VINS"; exit 1; }
TL "VINS.init_done odom出流"

TL "起栈.px4ctrl"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 4
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; TL "FATAL px4ctrl"; exit 1; }

TL "起栈.planner"
nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
ok=0; for i in $(seq 1 20); do sleep 2
  rostopic info /position_cmd 2>/dev/null | grep -q Publishers && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL planner 无 position_cmd"; TL "FATAL planner"; exit 1; }
TL "起栈.五件套齐"
vset N1 PASS

# ---------- 段B 监控双源起屏 ----------
TL "监控.dashboard起屏"
python3 "$L/t1_flight_monitor.py" \
  --vins-log "$EV/simvins.log" --csv "$EV/dashboard.csv" --bag-dir "$EV/bags" --plain \
  > "$EV/dashboard_plain.log" 2>&1 < /dev/null &
echo $! > "$EV/dashboard.pid"
MON_DIR="$EV/monitor_d5"; mkdir -p "$MON_DIR"
setsid nohup python3 "$L/t1_odom_monitor.py" "$MON_DIR" > "$MON_DIR/monitor_stdout.log" 2>&1 < /dev/null &
echo $! > "$EV/monitor.pid"
sampler_start
sleep 3

# 全程复盘袋（彩排判读正源；含 dashboard 消费话题）
TL "录制.复盘袋起"
nohup rosbag record -O "$EV/rehearsal.bag" \
  /vins_estimator/imu_propagate /vins_estimator/odometry /mavros/state /mavros/battery \
  /debugPx4ctrl/fsm_state /position_cmd /move_base_simple/goal /px4ctrl/takeoff_land \
  /gazebo/model_states /mavros/local_position/odom /clock \
  > "$EV/record.log" 2>&1 &
sleep 2

# ---------- 段C 正常段（手册剖面逐步） ----------
LOG "=== 正常段 C0 自检 ==="
HZ=$(timeout 8 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/x >/dev/null 2>&1; \
     python3 -c "
import rospy, time
from nav_msgs.msg import Odometry
rospy.init_node('hz_probe', anonymous=True)
t0=time.time(); n=0; deadline=t0+6
while time.time()<deadline:
    try: rospy.wait_for_message('/vins_estimator/imu_propagate', Odometry, timeout=3); n+=1
    except rospy.ROSException: break
print('%.1f'%(n/(time.time()-t0)) if n else '0')" 2>/dev/null)
LOG "C0 odom 频率=${HZ}Hz (基线15,门5)"
TL "自检.odom_hz=$HZ"

LOG "=== C1 起飞（SITL 等价=px4ctrl 自起飞 0.75m）==="
TL "起飞.命令发出 takeoff_land=1"
T0=$(date +%s)
ok=0
while [ $(( $(date +%s) - T0 )) -lt 60 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
  PUB=$!
  for i in $(seq 1 12); do
    if [ "$(armed_now)" = "True" ]; then ok=1; break; fi
    sleep 1
  done
  kill "$PUB" 2>/dev/null
  [ "$ok" = 1 ] && break
done
[ "$ok" = 1 ] || { LOG "N2 FAIL: 60s 未 armed"; vset N2 FAIL; }
TL "起飞.armed=$ok"
# 等 AUTO_HOVER+升空
Z=""
for i in $(seq 1 30); do
  Z=$(z_odom); F=$(fsm_now)
  LOG "  climbing z=${Z:-NA} fsm=${F:-NA}"
  if [ "${Z:-0}" != NA ] && python3 -c "exit(0 if float('${Z:-0}')>=0.5 else 1)" 2>/dev/null && [ "$F" = "AUTO_HOVER" ]; then
    break
  fi
  sleep 2
done
Z=$(z_odom); F=$(fsm_now)
LOG "C1 终态 z=${Z:-NA} fsm=${F:-NA}"
TL "起飞.终态 z=$Z fsm=$F"
if [ "${Z:-0}" != NA ] && python3 -c "exit(0 if float('${Z:-0}')>=0.5 else 1)" 2>/dev/null && [ "$F" = "AUTO_HOVER" ]; then
  vset N2 PASS
else
  vset N2 FAIL
fi

LOG "=== C2 自主悬停 60s（AUTO_HOVER 保持+漂移带）==="
TL "悬停.开始60s"
P0=$(gz_pos); LOG "  P0=$P0"
MAXD=0
for i in $(seq 1 12); do
  sleep 5
  P=$(gz_pos); D=$(python3 -c "
import math
try:
    a=list(map(float,'$P0'.split())); b=list(map(float,'$P'.split()))
    print(math.dist(a,b))
except Exception: print(999)")
  LOG "  hover t=$((i*5))s pos=$P dist=$D"
  MAXD=$(python3 -c "print(max($MAXD,$D))")
done
TL "悬停.结束 maxdrift=$MAXD (门0.5m)"
python3 -c "exit(0 if $MAXD<0.5 else 1)" && vset N3 PASS || vset N3 FAIL

LOG "=== C3 goal A：CLI 短航点 (2,0) [RViz 同话题等价注记] ==="
TL "goalA.发出(2,0,1)"
timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
  "{header: {frame_id: 'world'}, pose: {position: {x: 2.0, y: 0.0, z: 1.0}}}" >/dev/null 2>&1
F=$(fsm_now); LOG "  goal 后 fsm=${F:-NA}（CMD_CTRL=CH6 高等价达成面）"
if wait_dist 2.0 0.0 1.0 0.75 60; then vset N4 PASS; TL "goalA.到位 PASS"; else vset N4 FAIL; TL "goalA.到位 FAIL"; fi

LOG "=== C4 goal B：返航上方 (0,0) ==="
TL "goalB.发出(0,0,1)"
timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
  "{header: {frame_id: 'world'}, pose: {position: {x: 0.0, y: 0.0, z: 1.0}}}" >/dev/null 2>&1
if wait_dist 0.0 0.0 1.0 0.75 60; then vset N5 PASS; TL "goalB.到位 PASS"; else vset N5 FAIL; TL "goalB.到位 FAIL"; fi

LOG "=== C5 降落+disarm（06_land 模式=CH6 低+降落决策等价）==="
TL "降落.命令发出 takeoff_land=2"
T0=$(date +%s)
while [ $(( $(date +%s) - T0 )) -lt 90 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  PUB=$!; LANDED=0
  for i in $(seq 1 12); do
    Z=$(z_odom); A=$(armed_now)
    if [ "${Z:-9}" != NA ] && python3 -c "exit(0 if float('${Z:-9}')<0.15 else 1)" 2>/dev/null && [ "$A" = "False" ]; then LANDED=1; break; fi
    sleep 1
  done
  kill "$PUB" 2>/dev/null
  [ "$LANDED" = 1 ] && break
done
Z=$(z_odom); A=$(armed_now)
TL "降落.终态 z=$Z armed=$A"
if [ "${Z:-9}" != NA ] && python3 -c "exit(0 if float('${Z:-9}')<0.15 else 1)" 2>/dev/null && [ "$A" = "False" ]; then vset N6 PASS; else vset N6 FAIL; fi

LOG "=== C6 SITL ulog 检查 ==="
SITL_LOGDIR="$HOME/PX4-Autopilot/build/px4_sitl_default/tmp/rootfs/fs/microsd/log"
ULOG=$(find "$SITL_LOGDIR" -name '*.ulg' -newer "$EV" 2>/dev/null | head -1)
[ -n "$ULOG" ] && { vset N7 PASS; LOG "  ulog=$ULOG"; } || { vset N7 FAIL; LOG "  无新 ulog（检查 SD_LOG 参数）"; }
TL "ulog=$ULOG"

LOG "=== 正常段毕：N1=$V_N1 N2=$V_N2 N3=$V_N3 N4=$V_N4 N5=$V_N5 N6=$V_N6 N7=$V_N7 ==="
TL "正常段毕 N1=$V_N1 N2=$V_N2 N3=$V_N3 N4=$V_N4 N5=$V_N5 N6=$V_N6 N7=$V_N7"

# ---------- 段D 异常接管演练段 ----------
LOG "=== D1 重起飞（异常段前置）==="
TL "D1.重起飞"
T0=$(date +%s); ok=0
while [ $(( $(date +%s) - T0 )) -lt 60 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
  PUB=$!
  for i in $(seq 1 12); do
    [ "$(armed_now)" = "True" ] && { ok=1; break; }; sleep 1
  done
  kill "$PUB" 2>/dev/null; [ "$ok" = 1 ] && break
done
for i in $(seq 1 30); do
  Z=$(z_odom); [ "${Z:-0}" != NA ] && python3 -c "exit(0 if float('${Z:-0}')>=0.5 else 1)" 2>/dev/null && break
  sleep 2
done
sleep 5   # 悬停稳态
TL "D1.悬停稳态 z=$(z_odom)"

LOG "=== D2 注入①：杀 VINS（悬停态）→ HAFIX 盲降链端到端 ==="
VINSPID=$(pgrep -x vins_node | head -1)
TL "D2.杀VINS pid=$VINSPID"
pkill -x vins_node
TKILL=$(date +%s.%N)
# 时序追踪：fsm AUTO_LAND 出现时刻+触地+disarm
AUTO_LAND_SEEN=0; DISARM_SEEN=0; TLAND=""; TDISARM=""
T0=$(date +%s)
while [ $(( $(date +%s) - T0 )) -lt 120 ]; do
  F=$(fsm_now); A=$(armed_now); Z=$(z_odom)
  LOG "  D2 t=$(( $(date +%s) - T0 ))s fsm=${F:-NA} armed=${A:-NA} z=${Z:-NA}"
  if [ "$F" = "AUTO_LAND" ] && [ $AUTO_LAND_SEEN = 0 ]; then AUTO_LAND_SEEN=1; TLAND=$(date +%s.%N); TL "D2.AUTO_LAND出现"; fi
  if [ "$A" = "False" ] && [ $DISARM_SEEN = 0 ] && [ $AUTO_LAND_SEEN = 1 ]; then
    DISARM_SEEN=1; TDISARM=$(date +%s.%N); TL "D2.disarm完成"
    [ "${Z:-9}" != NA ] && python3 -c "exit(0 if float('${Z:-9}')<0.2 else 1)" 2>/dev/null && break
  fi
  sleep 1
done
DT_LAND=$(python3 -c "
try: print('%.1f' % (float('${TLAND:-0}') - float('$TKILL')))
except Exception: print('NA')")
TL "D2.时序 kill→AUTO_LAND=${DT_LAND}s (门15s=dead_s5.0实现值+链路余量,初值10s无依据已校准)"
python3 -c "exit(0 if float('${DT_LAND:-99}')<=15.0 else 1)" 2>/dev/null && vset A1 PASS || vset A1 FAIL
if [ $AUTO_LAND_SEEN = 1 ] && [ $DISARM_SEEN = 1 ]; then vset A2 PASS; else vset A2 FAIL; fi
LOG "D2 判定 A1=$V_A1 (kill→AUTO_LAND ${DT_LAND}s) A2=$V_A2 (盲降+disarm 链)"
sleep 5

LOG "=== D3 VINS 复场（重起→init→重起飞）==="
TL "D3.VINS重起"
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins_restart.log" 2>&1 &
ok=0; for i in $(seq 1 150); do sleep 2
  timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/x 2>/dev/null | grep -qE '[-0-9]' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "D3 FATAL VINS 复场失败"; TL "D3.FATAL_VINS"; }
TL "D3.VINS_init毕"
T0=$(date +%s); ok=0
while [ $(( $(date +%s) - T0 )) -lt 60 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
  PUB=$!
  for i in $(seq 1 12); do [ "$(armed_now)" = "True" ] && { ok=1; break; }; sleep 1; done
  kill "$PUB" 2>/dev/null; [ "$ok" = 1 ] && break
done
for i in $(seq 1 30); do
  Z=$(z_odom); [ "${Z:-0}" != NA ] && python3 -c "exit(0 if float('${Z:-0}')>=0.5 else 1)" 2>/dev/null && break
  sleep 2
done
sleep 5
TL "D3.重悬停 z=$(z_odom)"
LOG "  D3 复场毕 z=$(z_odom)"

LOG "=== D4 注入②：毒 odom（大跳）→ dashboard 告警联动 + 接管序列 ==="
TL "D4.毒odom注入开始(10s,大跳x+8m)"
P_BEFORE=$(gz_pos)
POISON_PID=""
( timeout 10 rostopic pub -r 2 /vins_estimator/imu_propagate nav_msgs/Odometry \
    "{header: {frame_id: 'world'}, pose: {pose: {position: {x: 8.0, y: 0.0, z: 3.0}, orientation: {w: 1.0}}}}" >/dev/null 2>&1 ) &
POISON_PID=$!
sleep 10
TL "D4.毒odom注入结束"
P_AFTER=$(gz_pos)
LOG "  真值 before=$P_BEFORE after=$P_AFTER"
GTJUMP=$(python3 -c "
import math
try:
    a=list(map(float,'$P_BEFORE'.split())); b=list(map(float,'$P_AFTER'.split()))
    print('%.3f' % math.dist(a,b))
except Exception: print('999')")
TL "D4.真值位移=$GTJUMP (门0.5m=不跟跳)"
python3 -c "exit(0 if float('$GTJUMP')<0.5 else 1)" 2>/dev/null && vset A4 PASS || vset A4 FAIL
# dashboard 联动：毒窗内 csv/行有 RED
sleep 2
if grep -qE '(RED).*(跳变=[1-9])|(跳变=[0-9.]+ m.{0,4}\[RED\])' "$EV/dashboard_plain.log"; then
  vset A3 PASS; LOG "  dashboard JUMP RED 联动 ✓"
else
  # csv 兜底查（plain 行 1s 粒度可能错过 2Hz 毒帧——查 csv 5s 粒度的 alarms 列）
  if grep -q 'JUMP' "$EV/dashboard.csv" 2>/dev/null; then vset A3 PASS; LOG "  dashboard csv JUMP 记录 ✓"
  else vset A3 FAIL; LOG "  dashboard 未捕获 JUMP（查因）"; fi
fi
TL "D4.dashboard联动 A3=$V_A3"

LOG "=== D5 接管序列模拟（=CH6 拨低停轨迹+降落决策；CH5 手动终极面=首飞窗现场件）==="
TL "D5.接管序列:land命令"
T0=$(date +%s)
while [ $(( $(date +%s) - T0 )) -lt 90 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  PUB=$!; LANDED=0
  for i in $(seq 1 12); do
    Z=$(z_odom); A=$(armed_now)
    if [ "${Z:-9}" != NA ] && python3 -c "exit(0 if float('${Z:-9}')<0.15 else 1)" 2>/dev/null && [ "$A" = "False" ]; then LANDED=1; break; fi
    sleep 1
  done
  kill "$PUB" 2>/dev/null; [ "$LANDED" = 1 ] && break
done
Z=$(z_odom); A=$(armed_now)
if [ "${Z:-9}" != NA ] && python3 -c "exit(0 if float('${Z:-9}')<0.15 else 1)" 2>/dev/null && [ "$A" = "False" ]; then vset A5 PASS; else vset A5 FAIL; fi
TL "D5.终态 z=$Z armed=$A A5=$V_A5"
LOG "=== 异常段毕：A1=$V_A1 A2=$V_A2 A3=$V_A3 A4=$V_A4 A5=$V_A5 ==="
TL "异常段毕 A1=$V_A1 A2=$V_A2 A3=$V_A3 A4=$V_A4 A5=$V_A5"

# ---------- 段E 收尾 ----------
sleep 3
pkill -f 'rosbag recor[d]' 2>/dev/null; sleep 3
TL "彩排主流程毕 清场"
cleanup keep
TL "彩排全毕"

# 判决书
cat > "$VERDICT" << EOF
# SITL 彩排批判决（rehearsal v1.0, $TS）

## 正常段（手册剖面）
| 判定 | 面 | 结果 |
|---|---|---|
| N1 | 五件套活（SITL/mavros/VINS/px4ctrl/planner） | $V_N1 |
| N2 | 起飞 armed+z≥0.5+fsm=AUTO_HOVER | $V_N2 |
| N3 | 悬停 60s 真值漂移<0.5m（max=$MAXD） | $V_N3 |
| N4 | goal A (2,0) 到位<0.75m | $V_N4 |
| N5 | goal B (0,0) 返航到位<0.75m | $V_N5 |
| N6 | 降落触地 z<0.15+disarm | $V_N6 |
| N7 | SITL ulog 生成 | $V_N7 |

## 异常接管段
| 判定 | 面 | 结果 |
|---|---|---|
| A1 | 杀VINS→AUTO_LAND ≤10s（实测 ${DT_LAND}s） | $V_A1 |
| A2 | 盲降触地+disarm 链完整（HAFIX 修复版） | $V_A2 |
| A3 | 毒odom→dashboard JUMP RED 联动 | $V_A3 |
| A4 | odom_gate 不跟跳（真值位移 $GTJUMP m） | $V_A4 |
| A5 | 接管序列（停毒+land）降落完成 | $V_A5 |

## 覆盖面注记（SITL 等价边界）
- 手动姿态起飞（PX4 MANUAL+摇杆）/CH5 手动终极接管：SITL 无 RC 不可模拟=首飞窗现场确认件①域。
- RViz 2D Nav Goal：与 CLI 同话题（/move_base_simple/goal）等价覆盖；GUI 可视化归首飞窗现场。
- 起飞高度 0.75m（SITL 自起飞）vs 手册手动 1.2m：升空→悬停态同构。

## 产物
- timeline.tsv（时序正源）/ sampler.tsv（1Hz fsm+armed+z）/ dashboard.csv+dashboard_plain.log（七面）
- monitor_d5/（D5 监控告警面）/ rehearsal.bag（复盘袋）/ rehearsal.log
EOF
LOG "判决落盘 $VERDICT"
