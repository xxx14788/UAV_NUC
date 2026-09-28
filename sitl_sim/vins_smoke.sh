#!/usr/bin/env bash
# vins_smoke.sh — T3-X1 VINS 同构链路一键冒烟（2026-09-28 v5 任务书）。
# 五件套起栈 + VINS init 门(裸话题 echo,180s) + T2 preflight + takeoff +
# goal + 真值/VINS 双口径到位 + 四指标 RESULT + 清场。
# 用法: vins_smoke.sh [--world W] [--goal x y z] [--tag NAME] [--budget 秒]
# 坑位吸收: 空world无特征(init必败)/echo字段路径假阴性/511默认50Hz/
# ROSTimeMovedBackwards杀watcher/goal竞态重发/降落投递随机/t3_clean自匹配ssh。
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
source /opt/ros/noetic/setup.bash 2>/dev/null || true   # set -u 前先 source(V3 教训)
set -u
WORLD=sitl_world_obstacles; GX=7.0; GY=-4.0; GZ=1.0; TAG=smoke; BUDGET=100
while [ $# -gt 0 ]; do case "$1" in
  --world) WORLD="$2"; shift 2;;
  --goal)  GX="$2"; GY="$3"; GZ="$4"; shift 4;;
  --tag)   TAG="$2"; shift 2;;
  --budget) BUDGET="$2"; shift 2;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
LOG() { echo "[$(date +%H:%M:%S)] $*"; }
L="$HOME/sitl_sim"
EV="$L/vins_smoke_runs/run_${TAG}_$(date +%H%M%S)"
mkdir -p "$EV"
exec > >(tee "$EV/round.log") 2>&1

# ---------- 锁(T3 前缀) ----------
LOCK="$L/SITL.lock"
ln -s "T3-vsmoke-$$-$(date +%H%M)" "$LOCK" 2>/dev/null || { LOG "FATAL 锁被占($(readlink "$LOCK" 2>/dev/null))"; exit 1; }
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
trap 'cleanup; rm -f "$LOCK"' EXIT

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
rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0 2>/dev/null; sleep 2
LOG "mavros up + 511@5000us"
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
sleep 3
LOG "sim_vins up, 等 VINS init(裸话题门,180s)"
ok=0; for i in $(seq 1 90); do sleep 2
  timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -q 'frame_id: world' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 180s 内 VINS 未 init"; exit 1; }
LOG "VINS init 完成 (+$((i*2))s)"
if ! python3 "$HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py" 10 > "$EV/preflight.txt" 2>&1; then
  LOG "preflight 红项"; cat "$EV/preflight.txt" | tail -8; exit 1
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
BAG="$EV/flight.bag"
nohup rosbag record -O "$BAG" \
  /vins_estimator/imu_propagate /vins_estimator/odometry /vins_estimator/feature_pts \
  /mavros/imu/data_raw /mavros/local_position/odom /mavros/state \
  /mavros/setpoint_raw/attitude /debugPx4ctrl/fsm_state /debugPx4ctrl \
  /gazebo/model_states /px4ctrl/takeoff_land /position_cmd /move_base_simple/goal /clock \
  > "$EV/record.log" 2>&1 &
REC=$!
sleep 3

# ---------- 起飞 ----------
LOG "起飞触发 (04_takeoff 60s 预算)"
if ! bash "$L/04_takeoff.sh" 60 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; tail -5 "$EV/takeoff.log"; kill -INT $REC 2>/dev/null; exit 1
fi
ok=0; for i in $(seq 1 20); do sleep 1
  # 裸话题 echo(字段路径假阴性教训),从 position 块取 z
  timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null \
    | sed -n '/^    position:/,/^    orientation:/p' | awk '/z:/{exit !($2+0>0.5)}' && { ok=1; break; }
done
[ $ok = 1 ] && LOG "离地(z>0.5)" || LOG "WARN 20s 未见 z>0.5(VINS口径)"
sleep 3

# ---------- goal(重发两轮吸收竞态) ----------
echo "goal: $GX $GY $GZ" > "$EV/goal.txt"
for k in 1 2; do
  timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
    "{header: {frame_id: 'world'}, pose: {position: {x: $GX, y: $GY, z: $GZ}}}" >/dev/null 2>&1
  sleep 2
done
LOG "goal 已发(2×8s)"

# ---------- 到位监视(真值口径,锚点自推导;外部wall超时+异常吞噬) ----------
timeout -s INT $BUDGET python3 - "$GX" "$GY" "$GZ" "$BUDGET" > "$EV/arrive_watch.txt" 2>&1 <<'PYEOF'
import sys, math, time
import rospy
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
gx, gy, gz, budget = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
gx, gy, gz = float(gx), float(gy), float(gz)
rospy.init_node('vsmoke_arrive', disable_signals=True)
st = {'anchor': None, 'p0': None, 'g0': None, 'min_t': 1e9, 'min_v': 1e9,
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
    if st['g0'] is None and st['p0'] is not None:
        st['g0'] = (p.x, p.y, p.z)
        st['anchor'] = (p.x - st['p0'][0], p.y - st['p0'][1], p.z - st['p0'][2])
        print('anchor: g-p = (%.3f, %.3f, %.3f)' % st['anchor'], flush=True)
    if st['anchor'] is None: return
    tx, ty, tz = gx + st['anchor'][0], gy + st['anchor'][1], gz + st['anchor'][2]
    d = math.sqrt((p.x-tx)**2 + (p.y-ty)**2 + (p.z-tz)**2)
    st['last'] = d
    st['min_t'] = min(st['min_t'], d)
    now = time.monotonic()
    if d < 0.5:
        if st['ok_since'] is None: st['ok_since'] = now
        if now - st['ok_since'] >= 2.0: st['arrived'] = True
    else:
        st['ok_since'] = None
rospy.Subscriber('/vins_estimator/imu_propagate', Odometry, odom_cb, queue_size=2)
rospy.Subscriber('/gazebo/model_states', ModelStates, truth_cb, queue_size=2)
t_end = time.monotonic() + budget - 10
r = rospy.Rate(10)
while time.monotonic() < t_end and not st['arrived'] and not rospy.is_shutdown():
    try: r.sleep()
    except Exception: time.sleep(0.1)
if st['arrived']:
    print('ARRIVED_TRUTH min_d=%.3f' % st['min_t'])
else:
    print('TIMEOUT min_truth=%.3f last=%.3f min_vins=%.3f' % (st['min_t'], st['last'] or -1, st['min_v']))
PYEOF
ARR=$(tail -1 "$EV/arrive_watch.txt")
LOG "到位: $ARR"

# poscmd 频率(巡航中抽样)
timeout 8 rostopic hz /position_cmd 2>/dev/null | grep 'average rate' | tail -1 > "$EV/poscmd_hz.txt"

# ---------- 降落(重掷制) ----------
LOG "降落指令"
disarmed=0
for k in 1 2 3; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  for j in $(seq 1 12); do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { disarmed=1; break 2; }
    sleep 1
  done
done
[ $disarmed = 1 ] && LOG "已 disarm" || LOG "WARN 降落未确认 disarmed"
sleep 3
kill -INT $REC 2>/dev/null; sleep 3

# ---------- 四指标 RESULT(真值口径为主,VINS 自报同录) ----------
python3 - "$BAG" "$GX" "$GY" "$GZ" "$WORLD" "$EV" "$ARR" <<'PYEOF' > "$EV/RESULT.txt" 2>&1
import sys, math, re
import rosbag
bag, gx, gy, gz, world, ev, arr = sys.argv[1:8]
gx, gy, gz = float(gx), float(gy), float(gz)
BOX = {"box_A": (3.5,-1.5,0.0,1.0,1.0,1.8), "box_B": (5.0,-2.5,0.0,1.5,1.0,1.2),
       "box_C": (4.5,-3.5,0.0,1.0,1.0,2.2)}
if world.endswith('_v2'):
    BOX["box_D"] = (6.4,-2.0,0.0,1.0,1.0,2.8); BOX["box_E"] = (6.4,0.5,0.0,1.0,1.0,2.8)
def dbox(p, b):
    cx,cy,z0,sx,sy,sz = b
    dx = max(abs(p[0]-cx)-sx/2, 0.0); dy = max(abs(p[1]-cy)-sy/2, 0.0)
    dz = max(max(z0-p[2], p[2]-(z0+sz)), 0.0)
    return math.sqrt(dx*dx+dy*dy+dz*dz)
prop, truth, cmd, armed = [], [], [], []
with rosbag.Bag(bag,'r') as b:
    for topic, msg, t in b.read_messages():
        ts = t.to_sec()
        if topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position; prop.append((ts,p.x,p.y,p.z))
        elif topic == '/gazebo/model_states':
            try: i = msg.name.index('iris_stereo_vins')
            except ValueError: continue
            p = msg.pose[i].position; truth.append((ts,p.x,p.y,p.z))
        elif topic == '/position_cmd':
            p = msg.position; cmd.append((ts,p.x,p.y,p.z))
        elif topic == '/mavros/state':
            armed.append(msg.armed)
if not prop: print('RESULT=FAIL 无 imu_propagate'); sys.exit()
# 锚点+真值到位
p0 = prop[0]; a = None
for t in truth:
    if t[0] >= p0[0]: a = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3]); break
if a is None and truth: t = truth[0]; a = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3])
tgt = (gx+a[0], gy+a[1], gz+a[2]) if a else None
dt_min = min(math.sqrt((p[1]-tgt[0])**2+(p[2]-tgt[1])**2+(p[3]-tgt[2])**2) for p in truth) if tgt else -1
dv_min = min(math.sqrt((p[1]-gx)**2+(p[2]-gy)**2+(p[3]-gz)**2) for p in prop)
mind = min(dbox(p, bx) for p in truth for bx in BOX.values()) if truth else -1
hz = len(cmd)/(cmd[-1][0]-cmd[0][0]) if len(cmd)>10 else 0
# 跟踪 p95(|cmd - odom| 最近邻)
import bisect
dev = []
ts_prop = [p[0] for p in prop]
for c in cmd:
    j = bisect.bisect_left(ts_prop, c[0])
    if 0 < j < len(prop):
        p = prop[j]; dev.append(math.sqrt((c[1]-p[1])**2+(c[2]-p[2])**2+(c[3]-p[3])**2))
dev.sort(); p95 = dev[int(0.95*len(dev))] if dev else -1
disarm_ok = (not armed[-1]) if armed else False
m = [dt_min < 0.5, mind > 0.349, hz >= 50, disarm_ok]
print('到位(真值) min=%.3f m (<0.5)->%d | 到位(VINS自报) min=%.3f m' % (dt_min, m[0], dv_min))
print('避障 min_dist=%.3f m (>0.349)->%d' % (mind, m[1]))
print('poscmd %.1f Hz (>=50)->%d' % (hz, m[2]))
print('auto_disarm->%d' % m[3])
print('跟踪 p95=%.3f m (cmd-odom, 信息项)' % p95)
print('ARRIVE_WATCH: %s' % arr)
print('RESULT=%s  (证据: %s)' % ('PASS' if all(m) else 'FAIL', ev))
PYEOF
tail -8 "$EV/RESULT.txt"

# ---------- 清场(函数已前置定义+EXIT trap;正常路径显式调一遍) ----------
cleanup
LOG "轮完成 bag=$BAG"
