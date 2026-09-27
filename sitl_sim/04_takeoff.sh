#!/usr/bin/env bash
# 触发 px4ctrl 自动起飞(等价于 Fast-Drone-250/shfiles/takeoff.sh)。
# T1-W5 修复 1:原 `rostopic pub -1` 单发模式存在 TCP 建连竞态(2026-09-26 两次实测丢命令)。
# T1-W1 修复 2:SITL 重启后 ~30s 内,新建 pub→px4ctrl 连接投递停滞(T1 实测:T+0 失败、
#   T+30 成功,窗口自愈;机制在 roscpp 连接层,证据见 t1_evidence/)。故本脚本改为
#   "发布重试直到 armed"(最多 60s),窗口内自动重试,窗口过后必达。
#   px4ctrl 对重复 TAKEOFF 幂等(triggered 每 cycle 清零;离开 MANUAL_CTRL 后静默忽略)。
# 用法: 04_takeoff.sh [超时秒数,默认 60]
set -u
source /opt/ros/noetic/setup.bash
# ★ 必须 source catkin_ws:quadrotor_msgs/TakeoffLand 是本工作空间的消息类型,
#   只 source /opt/ros/noetic 会报 "Cannot load message class for [quadrotor_msgs/TakeoffLand]"
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

DEADLINE=$(( $(date +%s) + ${1:-60} ))
n=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    n=$((n + 1))
    timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land \
         quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1
    if timeout 4 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True'; then
        echo "TAKEOFF 成功(第 $n 轮,armed ✓)"
        exit 0
    fi
    echo "  第 $n 轮未 armed,2s 后重试(剩余 $(( DEADLINE - $(date +%s) ))s)..."
    sleep 2
done
echo "TAKEOFF 失败:${1:-60}s 内未 armed。排查:" >&2
echo "  timeout 4 rostopic echo -n2 /debugPx4ctrl/fsm_state   # 状态名+五布尔" >&2
echo "  tail -30 ~/sitl_sim/logs/px4ctrl.log(或 roslaunch 终端)" >&2
exit 1
