#!/usr/bin/env bash
# n6fix_rehearsal.sh v1.0 — N6 修正操作序列端到端彩排（全域收尾册单元 1.1，2026-10-14）
# 背景：N6 真发现（rehearsal_final_verdict）：CH6 高/planner 在流时发 LAND 被 fsm_decision
# decide_hover/decide_cmd 消费不评估（rc_cmd∧cmd_ok tick 吞 LAND；traj_server 到点后 100Hz
# cmd=cmd_ok 恒真）→ direct-LAND 90s 静默无效。
# 本件=修正路径直接彩排实证（代码级根源已核：decide_cmd 中 !rc_cmd→AUTO_HOVER 与 !cmd_ok→
# AUTO_HOVER 两支即修正机理；LAND 在 AUTO_HOVER 可评估）：
#   ctrl = 对照：CMD_CTRL 态 direct-LAND（预期=N6 同构复现无效）
#   fix1 = 修正①：CH6 拨低等价（/mavros/rc/in 注入 CH5=2000[hover 位]+CH6=1000[gear 低]，
#          is_command_mode→false→rc_cmd 断）→等 2s→发 LAND。SITL 栈内 /mavros/rc/in 无竞争
#          发布者（RC-Free 默认态在案，若有 mavros 竞争发布则本路 ABORT 注记）。
#   fix2 = 修正②：kill_planner_all.sh（停 cmd 流→cmd_ok 断）→等 2s→发 LAND。
# 起栈复用 vins_smoke 五件套+坑防线（obstacles world 防 init 负深；fsm echo 引号）。
# 判据预注册=轮目录 prereg.txt（本脚本起栈前最先落盘，禁放宽）。
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u

CASE="${1:-}"
case "$CASE" in ctrl|fix1|fix2) ;; *) echo "usage: $0 <ctrl|fix1|fix2>"; exit 2;; esac

L="$HOME/sitl_sim"
TS=$(date +%H%M%S)
EV="$L/t1_evidence/preflight_boost_20261011/rehearsal_n6fix_${CASE}_${TS}"
mkdir -p "$EV"
LOG="$EV/n6fix.log"
TL="$EV/timeline.tsv"
WORLD="sitl_world_obstacles"

LOG()  { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
TL()   { printf "%s\t%s\t%s\n" "$(date +%s.%3N)" "$(date +%H:%M:%S.%3N)" "$*" >> "$TL"; LOG "TL| $*"; }

# ---------- 判据预注册（起栈前最先落盘，本节之后任何改动无效） ----------
cat > "$EV/prereg.txt" << 'PRE'
N6 修正彩排判据预注册（v1.0，2026-10-14，跑前锁定）
判定源：fsm=/debugPx4ctrl/fsm_state；真值 z=/gazebo/model_states(iris)；armed=/mavros/state。

[修正轮 fix1/fix2 预期=LAND 生效]
  P1: LAND 发出后 120s 观察窗内 fsm 出现 AUTO_LAND（下降态证据）
  P2: 真值 z 出现下降沿（相对悬停参考高差>0.5m）且终值 z<0.15（触地，与 N6 判据同门）
  P3: 终态 armed=False
  三条全真=修正路径 PASS；任一假=FAIL（如实记录形态，异常加轮判读）。

[对照轮 ctrl 预期=N6 同构复现无效]
  C1: 90s 观察窗内 fsm 不出现 AUTO_LAND
  C2: 真值 z 无下降沿（min|maxz-z| 保持<0.5m）
  C3: armed 恒 True
  三条全真=REPRODUCED（N6 判决同构复现=对照成立）；
  若 C1-C3 任一假（LAND 意外生效）=对照组失效（判 NOT-REPRODUCED，查因加轮）。

[fix1 注记 v2] 首版 RC 注入路在 19:43 实测被预注册防线正确拦截（/mavros/rc/in 有
mavros 发布者）；深挖定案=px4ctrl 栈参数 no_RC=true 时根本不订阅 /mavros/rc/in
（px4ctrl_node.cpp L65 上游注释明示"mavros will still publish wrong rc messages
although no RC is connected"）——真 RC 路（CH6 物理拨低）在本栈结构性不可达，
归首飞窗现场件（与 CH5 手动终极面同类域边界）；rc_cmd 断分支与 cmd_ok 断分支
fsm 同构（decide_cmd 两支同退 AUTO_HOVER，代码级证据）。fix1-v2 按任务书等价定义
（"CH6 拨低等价=停 position_cmd 流"）改走**单点停流**：rosnode kill traj_server
（position_cmd 唯一发布者；与 fix2 的 kill_planner_all.sh 全家杀形成粒度对照）。
PRE
TL "prereg 落盘（判据锁定）"

# ---------- 状态查询助手（rehearsal v7 同款） ----------
fsm_now()   { timeout 3 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state/data 2>/dev/null | head -1 | tr -d '\r\n"' | awk '{print $1}'; }
armed_now() { timeout 3 rostopic echo -n1 /mavros/state/armed 2>/dev/null | head -1 | tr -d '\r\n '; }
z_odom()    { timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/z 2>/dev/null | head -1 | tr -d '\r\n '; }
gz_pos() {
  timeout 5 python3 - "$@" << 'PYEOF' 2>/dev/null
import sys, rospy
from gazebo_msgs.msg import ModelStates
rospy.init_node('gz_probe', anonymous=True)
r = rospy.Rate(20); deadline = rospy.Time.now() + rospy.Duration(4)
while not rospy.is_shutdown() and rospy.Time.now() < deadline:
    try:
        m = rospy.wait_for_message('/gazebo/model_states', ModelStates, timeout=2)
        for i, n in enumerate(m.name):
            if 'iris' in n:
                p = m.pose[i].position
                print("%.3f %.3f %.3f" % (p.x, p.y, p.z)); sys.exit(0)
    except rospy.ROSException:
        break
    r.sleep()
print("NA"); sys.exit(1)
PYEOF
}
gz_z() { local P; P=$(gz_pos); [ "$P" = NA ] && echo NA || echo "$P" | awk '{print $3}'; }
odom_pos() {
  timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position 2>/dev/null \
    | grep -E '^\s*[xyz]:' | awk '{printf "%.3f ", $2}' | sed 's/ $//'
}
wait_dist_odom() {
  local D0=$(date +%s) P D
  while [ $(( $(date +%s) - D0 )) -lt "${5:-60}" ]; do
    P=$(odom_pos)
    if [ -n "$P" ]; then
      D=$(python3 -c "import math;px,py,pz=map(float,'$P'.split());print(math.dist((px,py,pz),($1,$2,$3)))" 2>/dev/null)
      python3 -c "exit(0 if float('${D:-999}')<${4} else 1)" 2>/dev/null && return 0
    fi
    sleep 3
  done
  return 1
}

# ---------- 清场核验（全名单=x4_batch force_cleanup ∪ rehearsal cleanup；③C 教训） ----------
STACKLOCK="$L/.n6fix_stack.lock"
full_cleanup() {
  pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -x px4 2>/dev/null; pkill -x gzserver 2>/dev/null; pkill -x gzclient 2>/dev/null
  bash "$L/kill_planner_all.sh" >/dev/null 2>&1
  pkill -f 'sim_vins.launc[h]' 2>/dev/null
  pkill -x vins_node 2>/dev/null
  pkill -f 'vins_to_mavro[s]' 2>/dev/null
  pkill -x px4ctrl_node 2>/dev/null; pkill -f 'px4ctrl_nod[e]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null; pkill -f 'mavros_nod[e]' 2>/dev/null
  pkill -x traj_server 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null; pkill -x rosmaster 2>/dev/null
  sleep 3
}
sampler_stop() { [ -f "$EV/sampler.pid" ] && kill -- -"$(cat "$EV/sampler.pid")" 2>/dev/null; :; }
cleanup() {
  TL "清场开始"
  sampler_stop
  pkill -f 'rostopic p[u]b' 2>/dev/null
  pkill -f 'rehearsal_sampl[e]r' 2>/dev/null
  full_cleanup
  rm -f "$STACKLOCK"
  TL "清场毕"
}
trap 'cleanup' INT TERM

LOG "=== N6 修正彩排 case=$CASE EV=$EV world=$WORLD ==="
TL "N6fix 启动 case=$CASE"

# 锁核验：栈窗锁+残场全名单
if [ -f "$STACKLOCK" ]; then
  LP=$(cat "$STACKLOCK" 2>/dev/null)
  if [ -n "$LP" ] && kill -0 "$LP" 2>/dev/null; then
    LOG "FATAL 栈窗锁被活进程持有 pid=$LP（他册栈窗？）——ABORT"; TL "FATAL lock_held pid=$LP"; exit 1
  fi
  LOG "栈窗锁残留但持锁进程已死（pid=$LP）——回收后继续"; rm -f "$STACKLOCK"
fi
full_cleanup
RES=0
for p in roscore gzserver px4 vins_node px4ctrl_node traj_server mavros_node; do
  pgrep -x "$p" >/dev/null 2>&1 && { LOG "FATAL 清场后残活 $p"; RES=1; }
done
[ "$RES" = 0 ] || { TL "FATAL residue"; exit 1; }
echo $$ > "$STACKLOCK"
TL "清场核验毕 全名单零残活 锁=pid $$"

# ---------- 段A 起栈（vins_smoke 五件套同款） ----------
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

TL "起栈.SITL"
SITL_WORLD="$WORLD" nohup bash "$L/start_sitl_vins.sh" > "$EV/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; TL "FATAL SITL"; cleanup; exit 1; }
PX4V=$(grep -m1 -oE 'PX4 .*[0-9a-f]{7,}' "$EV/sitl.log" | head -c 60)
TL "起栈.SITL_ok 版本指纹注记=${PX4V:-见sitl.log}（在役栈沿用，本册不重编不换栈）"

TL "起栈.mavros"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$EV/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; TL "FATAL mavros"; cleanup; exit 1; }
rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 2>/dev/null; sleep 2

# fix1 前置探测：/mavros/rc/in 竞争发布者核验（v2 已定案=no_RC=true 栈不订阅 RC，此探测保留为注记性证据采集）
RC_PUBS=$(rostopic info /mavros/rc/in 2>/dev/null | grep -c 'http://')
TL "rc_in 探测 publishers=$RC_PUBS（注记：no_RC=true 栈不消费 RC——px4ctrl_node.cpp L65）"

TL "起栈.VINS"
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
ok=0; for i in $(seq 1 150); do sleep 2
  timeout 3 rostopic echo -n1 --noarr /vins_estimator/imu_propagate/pose/pose/position/x 2>/dev/null | grep -qE '[-0-9]' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL VINS odom 未出流(300s)"; TL "FATAL VINS"; cleanup; exit 1; }
TL "VINS.init_done"

TL "起栈.px4ctrl"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 4
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; TL "FATAL px4ctrl"; cleanup; exit 1; }

TL "起栈.planner"
nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
ok=0; for i in $(seq 1 20); do sleep 2
  rostopic info /position_cmd 2>/dev/null | grep -q Publishers && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL planner 无 position_cmd"; TL "FATAL planner"; cleanup; exit 1; }
TL "起栈.五件套齐"

# ---------- 监控：采样器（v7 外置版）+复盘袋 ----------
setsid nohup python3 -u "$L/rehearsal_sampler.py" "$EV/sampler.tsv" > "$EV/sampler.out" 2>&1 < /dev/null &
echo $! > "$EV/sampler.pid"
nohup rosbag record -O "$EV/n6fix.bag" \
  /vins_estimator/imu_propagate /mavros/state /debugPx4ctrl/fsm_state /position_cmd \
  /move_base_simple/goal /px4ctrl/takeoff_land /mavros/rc/in /gazebo/model_states /clock \
  > "$EV/record.log" 2>&1 &
sleep 2

# ---------- 段B 起飞+悬停+goal 进 CMD_CTRL ----------
LOG "=== B1 起飞 ==="
TL "起飞.命令发出"
T0=$(date +%s); ok=0
while [ $(( $(date +%s) - T0 )) -lt 60 ]; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
  PUB=$!
  for i in $(seq 1 12); do [ "$(armed_now)" = "True" ] && { ok=1; break; }; sleep 1; done
  kill "$PUB" 2>/dev/null; [ "$ok" = 1 ] && break
done
[ "$ok" = 1 ] || { LOG "FATAL 60s 未 armed"; TL "FATAL arm"; cleanup; exit 1; }
for i in $(seq 1 30); do
  Z=$(z_odom); [ "${Z:-0}" != NA ] && python3 -c "exit(0 if float('${Z:-0}')>=0.5 else 1)" 2>/dev/null && break
  sleep 2
done
sleep 8   # 悬停稳态
TL "B1.悬停稳态 z_odom=$(z_odom)"

LOG "=== B2 goal(2,0,1) 进 CMD_CTRL ==="
timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
  "{header: {frame_id: 'world'}, pose: {position: {x: 2.0, y: 0.0, z: 1.0}}}" >/dev/null 2>&1
CMDOK=0
for i in $(seq 1 20); do
  F=$(fsm_now); [ "$F" = "CMD_CTRL" ] && { CMDOK=1; break; }; sleep 1
done
[ "$CMDOK" = 1 ] || { LOG "FATAL goal 后未进 CMD_CTRL（fsm=$(fsm_now)）——前置态不成立，试验无效"; TL "FATAL no_CMD_CTRL"; cleanup; exit 1; }
TL "B2.CMD_CTRL 确认"
wait_dist_odom 2.0 0.0 1.0 0.75 75 && TL "B2.到位 odom 域" || TL "B2.到位超时（继续试验——cmd 流存在性不受影响）"
sleep 5   # 到点后 planner 悬停 cmd 流持续（N6 现象条件）

# ---------- 段C 试验序列 ----------
OBS="$EV/obs.tsv"; echo "t_rel	fsm	z_gt	armed" > "$OBS"
ZREF=$(gz_z); TL "C.试验开始 case=$CASE 参考真值z=$ZREF"

case "$CASE" in
  ctrl)
    TL "C.ctrl direct-LAND 发出（N6 同构形态）"
    timeout 95 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" > "$EV/land_pub.log" 2>&1 &
    WSEC=90 ;;
  fix1)
    TL "C.fix1 单点停流：rosnode kill traj_server（CH6 拨低等价=停 position_cmd 流；no_RC 栈 RC 路不可达见 prereg）"
    rosnode kill /traj_server > "$EV/traj_kill.log" 2>&1 || pkill -f 'traj_serve[r]' 2>/dev/null
    sleep 2
    TL "C.fix1 等待2s毕 发 LAND"
    timeout 95 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" > "$EV/land_pub.log" 2>&1 &
    WSEC=120 ;;
  fix2)
    TL "C.fix2 kill_planner_all.sh 执行"
    bash "$L/kill_planner_all.sh" > "$EV/kill_planner.log" 2>&1
    sleep 2
    TL "C.fix2 等待2s毕 发 LAND"
    timeout 95 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" > "$EV/land_pub.log" 2>&1 &
    WSEC=120 ;;
esac

T1=$(date +%s); SEEN_AUTO_LAND=0; MINZ=999; ZMIN_AT=0; ARMED_END="NA"
while [ $(( $(date +%s) - T1 )) -lt "$WSEC" ]; do
  F=$(fsm_now); A=$(armed_now); ZG=$(gz_z)
  [ "$ZG" != NA ] && python3 -c "exit(0 if float('$ZG')<$MINZ else 1)" 2>/dev/null && { MINZ=$ZG; ZMIN_AT=$(( $(date +%s) - T1 )); }
  printf "%d\t%s\t%s\t%s\n" "$(( $(date +%s) - T1 ))" "${F:-NA}" "${ZG:-NA}" "${A:-NA}" >> "$OBS"
  [ "$F" = "AUTO_LAND" ] && [ $SEEN_AUTO_LAND = 0 ] && { SEEN_AUTO_LAND=1; TL "C.AUTO_LAND 出现 t=$(( $(date +%s) - T1 ))s"; }
  if [ "${A:-NA}" = "False" ]; then ARMED_END=False
    [ "$ZG" != NA ] && python3 -c "exit(0 if float('$ZG')<0.15 else 1)" 2>/dev/null && { TL "C.触地+disarm t=$(( $(date +%s) - T1 ))s z=$ZG"; break; }
  fi
  sleep 3
done
ARMED_END=$(armed_now)
ZEND=$(gz_z)
TL "C.观察窗毕 seen_AUTO_LAND=$SEEN_AUTO_LAND min_z=$MINZ@${ZMIN_AT}s z_end=$ZEND armed_end=$ARMED_END"

# ---------- 段D 判定（按 prereg） ----------
DROP=$(python3 -c "
try: print('%.3f' % (float('${ZREF:-0}') - float('$MINZ')))
except Exception: print('NA')")
if [ "$CASE" = ctrl ]; then
  C1=$([ $SEEN_AUTO_LAND = 0 ] && echo 1 || echo 0)
  C2=$(python3 -c "
try: print(1 if float('$DROP')<0.5 else 0)
except Exception: print(0)")
  C3=$([ "$ARMED_END" = "True" ] && echo 1 || echo 0)
  if [ "$C1" = 1 ] && [ "$C2" = 1 ] && [ "$C3" = 1 ]; then VERDICT=REPRODUCED; else VERDICT=NOT-REPRODUCED; fi
  echo "case=ctrl C1(no_AUTO_LAND)=$C1 C2(no_drop,drop=${DROP}m)=$C2 C3(armed_True)=$C3 VERDICT=$VERDICT" > "$EV/round_verdict.txt"
else
  P1=$([ $SEEN_AUTO_LAND = 1 ] && echo 1 || echo 0)
  P2=$(python3 -c "
try: print(1 if float('$DROP')>0.5 and float('$ZEND')<0.15 else 0)
except Exception: print(0)")
  P3=$([ "$ARMED_END" = "False" ] && echo 1 || echo 0)
  if [ "$P1" = 1 ] && [ "$P2" = 1 ] && [ "$P3" = 1 ]; then VERDICT=PASS; else VERDICT=FAIL; fi
  echo "case=$CASE P1(AUTO_LAND)=$P1 P2(drop=${DROP}m,z_end=$ZEND<0.15)=$P2 P3(disarm)=$P3 VERDICT=$VERDICT" > "$EV/round_verdict.txt"
fi
LOG "=== 判定：$(cat "$EV/round_verdict.txt") ==="
TL "N6fix 毕 case=$CASE verdict=$VERDICT"

# ---------- 段E 清场 ----------
pkill -f 'rosbag recor[d]' 2>/dev/null; sleep 3
cleanup
TL "N6fix 全毕"
exit 0
