#!/usr/bin/env bash
# W1 深挖:杀 PX4 重启后,px4ctrl 响应恢复的精确边界 + 时钟行为。
# 前置:SITL+mavros+px4ctrl 在线,机体 landed+disarmed(FSM MANUAL_CTRL)。自持锁。
# 输出:t1_evidence/probe_<ts>/ 下 clock.txt / fsm.txt / bus.txt / probe.log
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
SIM="$HOME/sitl_sim"
EV="$SIM/t1_evidence/probe_$(date +%F_%H%M%S)"
mkdir -p "$EV"
log() { echo "[$(date +%H:%M:%S.%N | cut -c1-12)] $*"; }

bash "$SIM/sitl_lock.sh" get "T1-probe-$$" >/dev/null 2>&1 || { echo "锁被占用"; exit 1; }
trap 'bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true' EXIT

# 三路记录(带墙钟对齐:每行前缀 wall 时间)
nohup timeout 180 python3 -u -c "
import rospy, time, sys
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from quadrotor_msgs.msg import TakeoffLand
def cb_c(m): print(f'{time.time():.3f} CLOCK {m.clock.to_sec():.3f}', file=sys.stderr)
def cb_f(m): print(f'{time.time():.3f} FSM {m.data}', file=sys.stderr)
def cb_t(m): print(f'{time.time():.3f} TAKEOFF_LAND_BUS cmd={m.takeoff_land_cmd}', file=sys.stderr)
rospy.init_node('t1_probe', anonymous=True, disable_signals=True)
rospy.Subscriber('/clock', Clock, cb_c, queue_size=10)
rospy.Subscriber('/debugPx4ctrl/fsm_state', String, cb_f, queue_size=10)
rospy.Subscriber('/px4ctrl/takeoff_land', TakeoffLand, cb_t, queue_size=10)
rospy.spin()
" > "$EV/probe_streams.log" 2>&1 &
PROBE_PID=$!
sleep 2
log "三路记录已开(clock/fsm/bus) → $EV/probe_streams.log"

log "杀 PX4+gzserver"
pkill -9 -f "bin/px4"; pkill -9 -f gzserver; sleep 5
SITL_WORLD="${SITL_WORLD:-}" nohup bash "$SIM/start_sitl_depth.sh" > "$EV/sitl_restart.log" 2>&1 &
C=0
for i in $(seq 1 60); do timeout 4 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && { C=1; break; }; sleep 2; done
[ "$C" -eq 1 ] || { log "重启失败"; exit 1; }
log "mavros 重连 ✓ —— 开始定时重试 takeoff(T+0/10/20/30/45/60s)"

for T in 0 30 60 90 120 180 240 300; do
    if [ "$T" -gt 0 ]; then sleep_step=$((T - PREV_T)); sleep "$sleep_step"; fi
    PREV_T=$T
    echo "===== T+${T}s publish =====" >> "$EV/probe.log"
    timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1
    ok=0
    for i in $(seq 1 15); do
        timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && { ok=1; break; }
        sleep 1
    done
    log "T+${T}s: armed=$ok"
    echo "T+${T}s armed=$ok" >> "$EV/probe.log"
    if [ "$ok" -eq 1 ]; then
        # 起飞成功 → 降落回干净态,继续下一档
        timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1
        for i in $(seq 1 90); do timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && break; sleep 1; done
        log "T+${T}s 档完成(已降落)"
        break
    fi
done

sleep 3
kill $PROBE_PID 2>/dev/null
log "完成,分析: grep CLOCK/FSM $EV/probe_streams.log"
echo "EVDIR=$EV"
