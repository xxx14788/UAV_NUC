#!/usr/bin/env bash
# W3:spawn 后 EKF2 odom yaw 检查(磁场修正验收)。
# 用法: bash w3_yaw_check.sh [重启轮数,默认 2]
# 每轮:杀 SITL → 以 SITL_WORLD 环境重启 → 等 EKF2 收敛 → 读 odom 四元数算 yaw。
# PASS 判据:每轮 |yaw| < 5°。
# 注意:必须配 sitl_sim/worlds/ 里的北向磁场 world(SITL_WORLD=sitl_north 等)。
source /opt/ros/noetic/setup.bash
set -u
N="${1:-2}"
SIM="$HOME/sitl_sim"
EV="$SIM/t1_evidence/w3_yaw_$(date +%F_%H%M%S).txt"
source "$HOME/catkin_ws/devel/setup.bash" || exit 1

bash "$SIM/sitl_lock.sh" get "T1-w3-$$" >/dev/null 2>&1 || { echo "锁被占用"; exit 1; }
trap 'bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true' EXIT

echo "# W3 yaw check $(date) SITL_WORLD=${SITL_WORLD:-<默认,无磁场修正>}" > "$EV"
ALL_OK=1
for round in $(seq 1 "$N"); do
    pkill -9 -f "bin/px4" 2>/dev/null; pkill -9 -f gzserver 2>/dev/null; sleep 5
    roscore_up() { timeout 3 rostopic list >/dev/null 2>&1; }
    roscore_up || { nohup roscore >/dev/null 2>&1 & sleep 3; }
    pgrep -f "Xvfb :99" >/dev/null || nohup Xvfb :99 -screen 0 1600x1200x24 >/dev/null 2>&1 &
    nohup bash "$SIM/start_sitl_depth.sh" > "$SIM/t1_evidence/w3_sitl_r${round}.log" 2>&1 &
    nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557 > "$SIM/t1_evidence/w3_mavros_r${round}.log" 2>&1 &
    ok=0
    for i in $(seq 1 60); do
        timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'connected: True' && { ok=1; break; }; sleep 2
    done
    [ "$ok" -eq 1 ] || { echo "round $round: mavros 未连" >> "$EV"; ALL_OK=0; continue; }
    sleep 15   # EKF2 收敛
    q=$(timeout 5 rostopic echo -n1 /mavros/local_position/odom/pose/pose/orientation 2>/dev/null)
    yaw=$(printf '%s' "$q" | python3 -c "
import sys, math
v = {}
for ln in sys.stdin:
    ln = ln.strip()
    for k in ('x','y','z','w'):
        if ln.startswith(k+':'):
            v[k] = float(ln.split(':')[1])
try:
    y = math.degrees(2*math.atan2(v['z'], v['w']))
    y = (y + 180) % 360 - 180   # 归一化到 [-180,180](如 -0.8° 会算出 359.2°)
    print(y)
except KeyError:
    print('nan')
")
    if [ "$yaw" = "nan" ]; then
        echo "round $round: odom 无数据" >> "$EV"; ALL_OK=0
    else
        okyaw=$(python3 -c "print(1 if abs(float('$yaw'))<5 else 0)")
        echo "round $round: yaw=${yaw}deg -> $([ "$okyaw" = 1 ] && echo PASS || echo FAIL)" | tee -a "$EV"
        [ "$okyaw" = 1 ] || ALL_OK=0
    fi
done
pkill -9 -f "bin/px4" 2>/dev/null; pkill -9 -f gzserver 2>/dev/null
[ "$ALL_OK" = 1 ] && { echo "RESULT=PASS" >> "$EV"; echo "PASS -> $EV"; exit 0; } || { echo "RESULT=FAIL" >> "$EV"; echo "FAIL -> $EV"; exit 1; }
