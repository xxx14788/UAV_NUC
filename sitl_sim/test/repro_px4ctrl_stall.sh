#!/usr/bin/env bash
# W1 复现脚本:px4ctrl 在 PX4 SITL 重启后静默卡死。
# 流程:SITL 起 → px4ctrl → 正常起飞降落一轮 → 杀 PX4 → 重启 PX4 → 发 takeoff →
#       断言 20s 内 armed。
# 期望:未修复构建 → FAIL(输出卡死现场全套);已修复构建 → PASS。
# 产出:~/sitl_sim/t1_evidence/repro_<ts>/ 下 state/param/nodeinfo/fsm_state/日志尾部。
source /opt/ros/noetic/setup.bash
set -u
SIM="$HOME/sitl_sim"
EV="$SIM/t1_evidence/repro_$(date +%F_%H%M%S)"
mkdir -p "$EV"
source "$HOME/catkin_ws/devel/setup.bash" || exit 1

log() { echo "[$(date +%H:%M:%S)] $*"; }
bash "$SIM/sitl_lock.sh" get "T1-repro-$$" >/dev/null 2>&1 || { echo "锁被占用"; exit 1; }
trap 'bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true' EXIT
log "lock ok, evidence -> $EV"

# 清残留(上轮未收尾的 SITL;括号技巧防 pkill 自匹配 ssh 命令行)
pkill -9 -f "bin/px[4]" 2>/dev/null; pkill -9 -f "gzserve[r]" 2>/dev/null
pkill -f "px4ctrl_nod[e]" 2>/dev/null; pkill -f "roslaunch.*px4launc[h]" 2>/dev/null; pkill -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null
sleep 3

# ---- 起 SITL + mavros + px4ctrl ----
roscore_up() { timeout 3 rostopic list >/dev/null 2>&1; }
roscore_up || { nohup roscore > "$EV/roscore.log" 2>&1 & sleep 3; }
pgrep -f "Xvfb :99" >/dev/null || nohup Xvfb :99 -screen 0 1600x1200x24 > "$EV/xvfb.log" 2>&1 &
SITL_WORLD="${SITL_WORLD:-}" nohup bash "$SIM/start_sitl_depth.sh" > "$EV/sitl.log" 2>&1 &
for i in $(seq 1 60); do pgrep -f "bin/px4" >/dev/null && break; sleep 2; done
pgrep -f "bin/px4" >/dev/null || { log "px4 未起来"; exit 1; }
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$EV/mavros.log" 2>&1 &
for i in $(seq 1 60); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && break; sleep 2; done
nohup roslaunch px4ctrl run_ctrl_sitl.launch > "$EV/px4ctrl.log" 2>&1 &
for i in $(seq 1 30); do rosnode info px4ctrl >/dev/null 2>&1 && break; sleep 1; done
sleep 3
log "全链路起: SITL+mavros+px4ctrl"

# ---- 正常起飞降落一轮 ----
bash "$SIM/04_takeoff.sh" || { log "第一轮起飞发布失败"; exit 1; }
A=0
for i in $(seq 1 40); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && { A=1; break; }; sleep 1; done
[ "$A" -eq 1 ] || { log "第一轮起飞失败(前置条件不满足,证据: $EV)"; exit 1; }
log "第一轮 armed ✓,10s 后降落"
sleep 10
timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
D=0
for i in $(seq 1 90); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { D=1; break; }; sleep 1; done
[ "$D" -eq 1 ] || { log "第一轮降落未 disarm"; exit 1; }
log "第一轮降落 disarm ✓ —— 开始杀 PX4"

# ---- 杀 PX4 → 重启 ----
pkill -9 -f "bin/px4"; pkill -9 -f gzserver; sleep 5
SITL_WORLD="${SITL_WORLD:-}" nohup bash "$SIM/start_sitl_depth.sh" > "$EV/sitl_restart.log" 2>&1 &
C=0
for i in $(seq 1 60); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && { C=1; break; }; sleep 2; done
[ "$C" -eq 1 ] || { log "PX4 重启后 mavros 未重连"; exit 1; }
log "PX4 重启完成,mavros 重连 ✓ —— 直接发 takeoff(不重启 px4ctrl)"

# ---- 发 takeoff,断言 20s 内 armed(全程记录 state/fsm 供事后判定) ----
nohup timeout 70 rostopic echo /mavros/state > "$EV/state_watch.txt" 2>&1 &
nohup timeout 70 rostopic echo /debugPx4ctrl/fsm_state > "$EV/fsm_watch.txt" 2>&1 &
bash "$SIM/04_takeoff.sh"
A2=0
for i in $(seq 1 20); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && { A2=1; break; }; sleep 1; done

if [ "$A2" -eq 1 ]; then
    log "PASS: PX4 重启后 px4ctrl 无需重启即可起飞(修复生效或未复现)"
    timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 || true
    for i in $(seq 1 90); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && break; sleep 1; done
    echo "RESULT=PASS" > "$EV/RESULT"
    exit 0
fi

# ---- FAIL: 卡死现场全套 ----
log "FAIL: 20s 未 armed —— 采集卡死现场"
timeout 10 rostopic echo /mavros/state 2>/dev/null | head -60 > "$EV/mavros_state.txt"
rosparam dump /px4ctrl "$EV/px4ctrl_params.yaml" 2>/dev/null || true
rosnode info px4ctrl > "$EV/px4ctrl_nodeinfo.txt" 2>&1 || true
timeout 8 rostopic echo -n3 /debugPx4ctrl/fsm_state > "$EV/fsm_state.txt" 2>/dev/null || \
    echo "(无 /debugPx4ctrl/fsm_state —— 旧版二进制,建议 --f4-only 构建)" > "$EV/fsm_state.txt"
timeout 8 rostopic echo -n3 /debugPx4ctrl > "$EV/debug.txt" 2>/dev/null || true
tail -50 "$EV/px4ctrl.log" > "$EV/px4ctrl_tail.txt" 2>/dev/null || true
pgrep -af "px4ctrl|bin/px4|gzserver" > "$EV/processes.txt" || true
log "现场已存 $EV;手动降落兜底: rosservice call /mavros/cmd/arming \"value: false\""
echo "RESULT=FAIL" > "$EV/RESULT"
exit 1
