#!/usr/bin/env bash
# W1 恢复测试(修复验收):连续 3 循环 杀 PX4 → 重启 PX4 → 直接 takeoff,全过为 PASS。
# 前置:px4ctrl 已运行(修复版二进制);SITL+mavros+px4ctrl 全链路在线(可由
#       repro_px4ctrl_stall.sh 的前半段或手动 01/02/03 脚本拉起)。
# 本脚本自己持锁;每循环结束都回到 landed+disarmed 干净态。
source /opt/ros/noetic/setup.bash
set -u
SIM="$HOME/sitl_sim"
EV="$SIM/t1_evidence/recovery_$(date +%F_%H%M%S)"
mkdir -p "$EV"
source "$HOME/catkin_ws/devel/setup.bash" || exit 1

log() { echo "[$(date +%H:%M:%S)] $*"; }
bash "$SIM/sitl_lock.sh" get "T1-recovery-$$" >/dev/null 2>&1 || { echo "锁被占用"; exit 1; }
trap 'bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true' EXIT

wait_armed() {  # $1=timeout_s → 0/1
    local i
    for i in $(seq 1 "$1"); do
        timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True' && return 0
        sleep 1
    done
    return 1
}
wait_disarmed() {
    local i
    for i in $(seq 1 90); do
        timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && return 0
        sleep 1
    done
    return 1
}
land_now() {
    timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 || true
    wait_disarmed
}

rosnode info px4ctrl >/dev/null 2>&1 || { log "px4ctrl 不在线(先起 03_start_px4ctrl.sh)"; exit 1; }
timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' || { log "mavros 未连接"; exit 1; }
log "前置 OK,evidence -> $EV"

PASS_N=0
for cycle in 1 2 3; do
    log "===== cycle $cycle: 杀 PX4 ====="
    pkill -9 -f "bin/px4"; pkill -9 -f gzserver; sleep 5
    SITL_WORLD="${SITL_WORLD:-}" nohup bash "$SIM/start_sitl_depth.sh" > "$EV/sitl_c${cycle}.log" 2>&1 &
    C=0
    for i in $(seq 1 60); do timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && { C=1; break; }; sleep 2; done
    [ "$C" -eq 1 ] || { log "cycle $cycle: PX4 重启失败"; break; }
    log "cycle $cycle: PX4 重连 ✓ → 直接 takeoff"
    bash "$SIM/04_takeoff.sh" || break
    if wait_armed 20; then
        log "cycle $cycle: TAKEOFF ✓(fsm: $(timeout 3 rostopic echo -n1 /debugPx4ctrl/fsm_state 2>/dev/null | head -1))"
        PASS_N=$((PASS_N + 1))
        sleep 5
        land_now && log "cycle $cycle: 降落 ✓" || { log "cycle $cycle: 降落异常"; break; }
    else
        log "cycle $cycle: 20s 未 armed —— FAIL"
        timeout 8 rostopic echo -n3 /debugPx4ctrl/fsm_state > "$EV/fsm_c${cycle}.txt" 2>/dev/null || true
        tail -30 "$EV/sitl_c${cycle}.log" > "$EV/sitl_c${cycle}_tail.txt" 2>/dev/null || true
        break
    fi
done

if [ "$PASS_N" -eq 3 ]; then
    log "PASS: 3/3 杀 PX4 重启后不重启 px4ctrl 直接起飞成功"
    echo "RESULT=PASS (3/3)" > "$EV/RESULT"
    exit 0
else
    log "FAIL: $PASS_N/3"
    echo "RESULT=FAIL ($PASS_N/3)" > "$EV/RESULT"
    exit 1
fi
