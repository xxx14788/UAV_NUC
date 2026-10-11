#!/usr/bin/env bash
# t1_c1_verify_v1.sh — C-1 SITL 验证轮（2026-10-11 软件收官合并册 单元1 头号件）
# 设计=unit4_c1_killpath_source_v1140.md §4：起飞→悬停→单发 cmd179(0,21196)→五元组观测。
# 分支预写（判据预注册，执行前冻结）：
#   复现 = ACK result=0 ∧ armed 恒 True（在线）∧ ulog arming_state 零翻转（离线）
#          → 断链机理动态实锤 → 运行时候选三选收窄（events/log_message 补采已在 logger_topics.txt）
#   不复现 = disarm 生效（armed→False / arming_state 2→1 / 电机停+落地）
#          → 间歇性证据 + SITL 与实机构建差异注记 + C-1 关闭（静态穷举定案+动态未复现）
# 五元组：①ACK result（/mavros/cmd/ack 在线 + ulog vehicle_command_ack）
#         ②arming_state（ulog vehicle_status）③actuator_armed（ulog）
#         ④mode/nav_state（/mavros/state 在线 + ulog nav_state）⑤悬停维持（local_position z 序列）
# 增强段（复现嫌疑时）：3 连发 179 一致性补验（与 08_24_40 的 412 连发形态对齐）；单发为主判。
source /opt/ros/noetic/setup.bash          # 先 source 再 set -u
source "$HOME/catkin_ws/devel/setup.bash"  # LAST: 基座覆盖坑
set -u
LOG() { echo "[$(date +%H:%M:%S)] $*"; }

# dual-copy deploy guard（repo 正源；分叉拒跑）
_REPO_SH="$HOME/catkin_ws/sitl_sim/t1_c1_verify_v1.sh"
if [ -f "$_REPO_SH" ] && [ "$(md5sum "$_REPO_SH" | cut -d' ' -f1)" != "$(md5sum "$0" | cut -d' ' -f1)" ]; then
  LOG "FATAL dual-copy fork: runtime($0) != repo($_REPO_SH); REFUSING. fix: cp repo -> runtime then retry"
  exit 3
fi
L="$HOME/sitl_sim"
EVROOT="$L/t1_evidence/v112_2026-10-11/c1_verify"
EV="$EVROOT/run_C1_$(date +%H%M%S)"
mkdir -p "$EV"
md5sum "$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml" > "$EV/vins_config.md5" 2>/dev/null || true
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

# ---------- 锁 + 清场断言前置（v11.40 D-1010-T2-01 修复序） ----------
LOCK="$L/SITL.lock"
SL="$L/sitl_lock.sh"
MYSTREAM="${SMOKE_OWNER:-T1-C1VERIFY}"
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清(px4=$A gz=$B),先清场再跑(断言在取锁前)"; exit 1; }
"$SL" get "$MYSTREAM" || { LOG "FATAL 锁获取失败(活主持有或盘门拒绝,原因见上)"; exit 1; }
MYOWNER=$(readlink "$LOCK" 2>/dev/null || true)
"$SL" hbloop "$MYSTREAM" & HBPID=$!
ACKPID=""; SEQPIDs=""
cleanup() {
  [ -n "$ACKPID" ] && kill "$ACKPID" 2>/dev/null
  [ -n "$ZPID" ] && kill "$ZPID" 2>/dev/null
  pkill -f "rostopic ech[o] -p /mavros/cmd/ack" 2>/dev/null
  pkill -f "rostopic ech[o] -p /mavros/local_position" 2>/dev/null
  kill "$HBPID" 2>/dev/null
  pkill -f "tee $EV/round.lo[g]" 2>/dev/null
  pkill -f 'vins_to_mavro[s]' 2>/dev/null; kill_vins_my_domain
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
  pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
  pkill -x gzclient 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
  pkill -f 'run_ctrl_sitl_vin[s]' 2>/dev/null
  pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  sleep 3
}
trap 'if [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$MYOWNER" ]; then cleanup; "$SL" release "$MYSTREAM" >/dev/null 2>&1; fi' EXIT

# ---------- 栈起（照抄 vins_smoke 五件套，无 planner——本轮无 goal） ----------
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
LOG "mavros up + 511@4000us(仓库标准)"
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
sleep 3
LOG "sim_vins up, 等 VINS init(wall-clock 300s)"
ok=0; T0G=$(date +%s)
while [ $(( $(date +%s) - T0G )) -lt 300 ]; do
  sleep 2
  if timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -qE 'frame_id: "?world"?'; then ok=1; break; fi
done
[ $ok = 1 ] || { LOG "FATAL VINS init 超窗"; exit 1; }
LOG "VINS init ✓"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 8
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; exit 1; }
LOG "px4ctrl up（五件套减 planner 就绪）"

# ---------- ack 在线录（全程,超时 900s 兜底）+ z 持久流（mavros 订阅触发型流,瞬时 echo 首帧延迟>timeout=空采——v1 轮 60/60 z 全空根因） ----------
setsid nohup timeout 1200 rostopic echo -p /mavros/local_position/odom/pose/position/z > "$EV/z_stream.csv" 2>/dev/null < /dev/null &
ZPID=$!
setsid nohup timeout 900 rostopic echo -p /mavros/cmd/ack > "$EV/ack_online.csv" 2>/dev/null < /dev/null &
ACKPID=$!

# ---------- 起飞 + 悬停稳定 ----------
if ! bash "$L/04_takeoff.sh" 150 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; tail -5 "$EV/takeoff.log"; exit 1
fi
LOG "起飞 ✓，悬停稳定窗 25s（基线 z 序列采样——读 z 持久流尾帧）"
: > "$EV/hover_base.tsv"
for i in $(seq 1 25); do
  z=$(tail -1 "$EV/z_stream.csv" 2>/dev/null | cut -d, -f2)
  echo "$(date +%H:%M:%S) $z" >> "$EV/hover_base.tsv"
  sleep 1
done
LOG "基线窗毕: $(awk '{print $2}' "$EV/hover_base.tsv" | grep -v '^$' | sort -n | sed -n '1p;$p' | tr '\n' ' ')"

# ---------- 单发 179(0,21196) ----------
echo "inject_wallclock=$(date -Is)" >> "$EV/inject.txt"
echo "cmd=179 param1=0 param2=21196 via: rosrun mavros mavcmd long（COMMAND_LONG→from_external=1 source=1/240,与 08_24_40 同路径）" >> "$EV/inject.txt"
rosrun mavros mavcmd long 179 0 21196 0 0 0 0 0 >> "$EV/inject.txt" 2>&1
LOG "★ 单发 cmd179(0,21196) 已发 — 观测窗 60s（五元组在线面）"

state_sample() {  # $1=输出文件 $2=次数 $3=段标签
  local f="$1" n="$2" lbl="$3" i ts st z
  for i in $(seq 1 "$n"); do
    ts=$(date +%H:%M:%S)
    st=$(timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -E '^(armed|mode):' | tr '\n' ' ' | tr -d '"')
    z=$(tail -1 "$EV/z_stream.csv" 2>/dev/null | cut -d, -f2)
    echo "$ts [$lbl] $st z=$z" >> "$f"
    sleep 1
  done
}
state_sample "$EV/state_seq.tsv" 60 observe

armed_false_n=$(grep -c 'armed: False' "$EV/state_seq.tsv" || true)
armed_true_n=$(grep -c 'armed: True' "$EV/state_seq.tsv" || true)
LOG "观测窗毕: armed True=$armed_true_n False=$armed_false_n"

REPRO_SUS=0
if [ "${armed_false_n:-0}" = "0" ] && [ "${armed_true_n:-0}" -gt 0 ]; then
  REPRO_SUS=1
  LOG "armed 全程 True → 复现嫌疑：3 连发一致性补验（08_24_40 形态对齐）"
  echo "burst3_wallclock=$(date -Is)" >> "$EV/inject.txt"
  for k in 1 2 3; do rosrun mavros mavcmd long 179 0 21196 0 0 0 0 0 >> "$EV/inject.txt" 2>&1; sleep 2; done
  state_sample "$EV/state_seq.tsv" 30 burst3
  armed_false_n2=$(grep -c 'armed: False' "$EV/state_seq.tsv" || true)
  LOG "3 连发后累计 armed False=$armed_false_n2"
else
  LOG "disarm 在线生效（或不一致态）——不复现分支初判"
fi

# ---------- 收卷（仍 armed → land 重发制；已 disarm → 等落地） ----------
LAST_ARMED=$(tail -20 "$EV/state_seq.tsv" | grep -o 'armed: \(True\|False\)' | tail -1)
if echo "$LAST_ARMED" | grep -q True; then
  LOG "仍 armed → land 收卷（takeoff_land cmd=2 重发制 60s）"
  for k in 1 2 3 4 5; do
    timeout 12 rostopic pub -r 2 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
    sleep 12
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && break
  done
else
  LOG "已 disarm → 落地确认（z 序列 20s）"
fi
state_sample "$EV/state_seq.tsv" 20 settle

# ---------- ulog 收卷 + 离线五元组 ----------
sleep 5
ULG=$(ls -t "$HOME/PX4-Autopilot/build/px4_sitl_default/rootfs/log"/*/*.ulg 2>/dev/null | head -1)
if [ -n "$ULG" ]; then
  cp "$ULG" "$EV/round.ulg" && LOG "ulog 收卷: $(basename "$ULG") ($(stat -c%s "$EV/round.ulg") bytes)"
  python3 "$HOME/sitl_sim/t1_c1_extract_ulog.py" "$EV/round.ulg" > "$EV/ulog_five_tuple.txt" 2>&1 \
    && LOG "五元组离线提取毕" || LOG "WARN ulog 提取失败（离线面缺,在线面仍可初判）"
else
  LOG "WARN ulg 未找到（SITL logger 未落盘?）"
fi

# ---------- RESULT（在线面初判;终判=判决文书,离线面合并后由主会话落） ----------
{
  echo "=== C-1 SITL 验证轮 RESULT（在线面）==="
  echo "run=$EV"
  echo "inject=$(grep inject_wallclock "$EV/inject.txt" 2>/dev/null)"
  echo "observe: armed True=$armed_true_n False=$armed_false_n"
  echo "repro_suspect_online=$REPRO_SUS"
  echo "hover_base: $(awk 'NF==2{print $2}' "$EV/hover_base.tsv" | grep -v '^$' | wc -l) samples, min/max: $(awk 'NF==2{print $2}' "$EV/hover_base.tsv" | grep -v '^$' | sort -n | sed -n '1p;$p' | tr '\n' ' ')"
  echo "ack_online lines: $(grep -vc '^%' "$EV/ack_online.csv" 2>/dev/null || echo 0)"
  echo "settle tail: $(tail -3 "$EV/state_seq.tsv" | tr '\n' ' | ')"
  echo "（终判以 ulog_five_tuple.txt 离线面 + 本在线面合并 → 判决文书 c1_verdict_v1.md）"
} > "$EV/RESULT.txt"
cat "$EV/RESULT.txt"
LOG "轮毕（清场+锁释放在 EXIT trap）"
