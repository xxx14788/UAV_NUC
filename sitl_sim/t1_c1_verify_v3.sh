#!/usr/bin/env bash
# t1_c1_verify_v3.sh — C-1 修复正控验证轮（工程合并 v1.6 单元1 处置条款执行件）
# 背景 = C-1 终局判决: 旧 kill 双命令[400+p1=1=ARM 空转]+[179=SET_HOME]均非停电机(固件行为正确);
#        修复 = fsm_decision.h 号勘定 185/400(gtest 51/51 绿)。
# 本轮 = 修复命令语义的固件侧正控: 悬停单发**正确命令**, 验证该构建 MAVLink kill 真可用。
# 用法: C1_SPEC=disarm(默认: 400 0 21196 → 期望空中解锁+电机停+下坠)
#       C1_SPEC=term   (185 1.0 0 → 期望 termination 态+输出归零, 不一定解锁)
# 判据预注册(执行前冻结):
#   disarm 轮 PASS = 注入后 15s 内 armed False(在线) ∧ ulog arming_state 翻转 2→1 ∧ actuator_outputs 归零带
#   disarm 轮 FAIL = ACK≠0 或 armed 恒 True(=真固件级阻断, 升级呈报)
#   term 轮 PASS = ACK=0 ∧ nav_state 进入 TERMINATION(ulog) ∧ armed 允许保持(termination 语义不停 arming)
#   term 轮 FAIL = ACK≠0 或 nav_state 恒 OFFBOARD
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
LOG() { echo "[$(date +%H:%M:%S)] $*"; }
SPEC="${C1_SPEC:-disarm}"
_REPO_SH="$HOME/catkin_ws/sitl_sim/t1_c1_verify_v3.sh"
if [ -f "$_REPO_SH" ] && [ "$(md5sum "$_REPO_SH" | cut -d' ' -f1)" != "$(md5sum "$0" | cut -d' ' -f1)" ]; then
  LOG "FATAL dual-copy fork"; exit 3
fi
L="$HOME/sitl_sim"
EVROOT="$L/t1_evidence/v113_2026-10-11/c1_separation"
EV="$EVROOT/run_C1v3_${SPEC}_$(date +%H%M%S)"
mkdir -p "$EV"
exec > >(tee "$EV/round.log") 2>&1

kill_vins_my_domain() {
  local my_m="${ROS_MASTER_URI:-http://localhost:11311}" p m
  for p in $(pgrep -f "lib/vins/vins_nod[e]" 2>/dev/null); do
    m=$(tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    m="${m:-http://localhost:11311}"
    [ "$m" = "$my_m" ] && kill -9 "$p" 2>/dev/null
  done
  return 0
}
LOCK="$L/SITL.lock"; SL="$L/sitl_lock.sh"
MYSTREAM="${SMOKE_OWNER:-T1-C1V3}"
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清(px4=$A gz=$B)"; exit 1; }
"$SL" get "$MYSTREAM" || { LOG "FATAL 锁获取失败"; exit 1; }
MYOWNER=$(readlink "$LOCK" 2>/dev/null || true)
"$SL" hbloop "$MYSTREAM" & HBPID=$!
ZPID=""; ACKPID=""
cleanup() {
  [ -n "$ACKPID" ] && kill "$ACKPID" 2>/dev/null; [ -n "$ZPID" ] && kill "$ZPID" 2>/dev/null
  pkill -f "rostopic ech[o] -p /mavros/cmd/ack" 2>/dev/null
  pkill -f "rostopic ech[o] -p /mavros/local_position" 2>/dev/null
  kill "$HBPID" 2>/dev/null; pkill -f "tee $EV/round.lo[g]" 2>/dev/null
  pkill -f 'vins_to_mavro[s]' 2>/dev/null; kill_vins_my_domain
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
  pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null; pkill -x gzclient 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
  pkill -f 'run_ctrl_sitl_vin[s]' 2>/dev/null; pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  sleep 3
}
trap 'if [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$MYOWNER" ]; then cleanup; "$SL" release "$MYSTREAM" >/dev/null 2>&1; fi' EXIT

# ---------- 栈起(同 v2 五件套减 planner) ----------
bash "$L/kill_planner_all.sh" >/dev/null 2>&1
kill_vins_my_domain
pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null; sleep 3
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99
WORLD=sitl_world_obstacles
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
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
sleep 3
ok=0; T0G=$(date +%s)
while [ $(( $(date +%s) - T0G )) -lt 300 ]; do
  sleep 2
  timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -qE 'frame_id: "?world"?' && { ok=1; break; }
done
[ $ok = 1 ] || { LOG "FATAL VINS init 超窗"; exit 1; }
LOG "VINS init ✓"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 8
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; exit 1; }
LOG "px4ctrl up（含 kill 号勘定修复版）"

setsid nohup timeout 1200 rostopic echo -p /mavros/local_position/odom/pose/position/z > "$EV/z_stream.csv" 2>/dev/null < /dev/null & ZPID=$!
setsid nohup timeout 900 rostopic echo -p /mavros/cmd/ack > "$EV/ack_online.csv" 2>/dev/null < /dev/null & ACKPID=$!

if ! bash "$L/04_takeoff.sh" 150 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; exit 1
fi
LOG "起飞 ✓，悬停稳定窗 20s"
sleep 20

# ---------- 注入正确命令 ----------
case "$SPEC" in
  disarm) INJ="400 0 21196 0 0 0 0 0";;
  term)   INJ="185 1.0 0 0 0 0 0 0";;
  *) LOG "FATAL unknown spec $SPEC"; exit 2;;
esac
echo "inject_wallclock=$(date -Is) spec=$SPEC inj='$INJ'" >> "$EV/inject.txt"
rosrun mavros mavcmd long $INJ >> "$EV/inject.txt" 2>&1
LOG "★ 正控注入 [$INJ] 已发 — 观测窗 45s"

: > "$EV/state_seq.tsv"
for i in $(seq 1 45); do
  ts=$(date +%H:%M:%S)
  st=$(timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -E '^(armed|mode):' | tr '\n' ' ' | tr -d '"')
  z=$(tail -1 "$EV/z_stream.csv" 2>/dev/null | cut -d, -f2)
  echo "$ts [observe] $st z=$z" >> "$EV/state_seq.tsv"
  sleep 1
done
armed_false_n=$(grep -c 'armed: False' "$EV/state_seq.tsv" || true)
armed_true_n=$(grep -c 'armed: True' "$EV/state_seq.tsv" || true)
LOG "观测窗毕: armed True=$armed_true_n False=$armed_false_n"

# 收卷: disarm 轮通常已坠地; term 轮可能仍 armed → land 重发制
LAST_ARMED=$(tail -10 "$EV/state_seq.tsv" | grep -o 'armed: \(True\|False\)' | tail -1)
if echo "$LAST_ARMED" | grep -q True; then
  LOG "仍 armed → land 收卷"
  for k in 1 2 3 4 5; do
    timeout 12 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
    sleep 12
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && break
  done
fi
sleep 10
ULG=$(ls -t "$HOME/PX4-Autopilot/build/px4_sitl_default/rootfs/log"/*/*.ulg 2>/dev/null | head -1)
if [ -n "$ULG" ]; then
  cp "$ULG" "$EV/round.ulg" && LOG "ulog 收卷: $(basename "$ULG")"
  python3 "$HOME/sitl_sim/t1_c1_extract_ulog.py" "$EV/round.ulg" > "$EV/ulog_five_tuple.txt" 2>&1 || true
fi
grep -a "C1FR" "$EV/sitl.log" > "$EV/c1fr_console.txt" 2>/dev/null || true

{
  echo "=== C-1 v3 正控轮 RESULT（在线面; spec=$SPEC; inj='$INJ'）==="
  echo "run=$EV"
  echo "observe: armed True=$armed_true_n False=$armed_false_n"
  echo "ack_online lines: $(grep -vc '^%' "$EV/ack_online.csv" 2>/dev/null || echo 0)"
  echo "settle tail: $(tail -3 "$EV/state_seq.tsv" | tr '\n' ' | ')"
  echo "（终判 = ulog 面合并后正控判决: disarm 轮 PASS=armed翻转+输出零; term 轮 PASS=nav TERMINATION）"
} > "$EV/RESULT.txt"
cat "$EV/RESULT.txt"
LOG "轮毕"
