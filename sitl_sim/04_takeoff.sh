#!/usr/bin/env bash
# 触发 px4ctrl 自动起飞(等价于 Fast-Drone-250/shfiles/takeoff.sh)。
# T1 修复史:
#  - v1(09-26 前): rostopic pub -1 单发 → TCP 建连竞态丢命令(两次实测)
#  - v2(09-27): -r 1×4s 重试制 → 吸收 SITL 重启后 15-40s 投递停滞窗口
#  - v3(09-27 夜): 每轮 20s 长窗×-r 2 + 并行 armed 监视。退化环境下新建
#    pub→px4ctrl 的 TCPROS 建连可长达数十秒,4s 短窗会零投递(实测);
#    20s 窗让单轮建连全覆盖,90s 总预算。U3(09-28)实测:新 pub 的 TCPROS 建连在
#    px4ctrl(roscpp)侧随机失败(~50%,稳态也有),单次协商失败后 roscpp 不重试,
#    需下一次 publisherUpdate(=新 pub 进程)才重连——轮长缩到 12s 提高重掷密度。
#    机制详见 t1_evidence/u3_conclusion.md。
# px4ctrl 对重复 TAKEOFF 幂容(triggered 每 cycle 清零;离开 MANUAL_CTRL 后静默忽略)。
# 用法: 04_takeoff.sh [总超时秒数,默认 90]
source /opt/ros/noetic/setup.bash
set -u
# ★ 必须 source catkin_ws:quadrotor_msgs/TakeoffLand 是本工作空间的消息类型
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

DEADLINE=$(( $(date +%s) + ${1:-90} ))
n=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    n=$((n + 1))
    timeout 12 rostopic pub -r 2 /px4ctrl/takeoff_land \
         quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
    PUB=$!
    ok=0
    for i in $(seq 1 12); do
        if timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True'; then ok=1; break; fi
        sleep 1
    done
    kill "$PUB" 2>/dev/null
    if [ "$ok" = 1 ]; then
        echo "TAKEOFF 成功(第 $n 轮,armed ✓)"
        exit 0
    fi
    echo "  第 $n 轮未 armed,重试(剩余 $(( DEADLINE - $(date +%s) ))s)..."
done
echo "TAKEOFF 失败:${1:-90}s 内未 armed。排查:" >&2
echo "  timeout 4 rostopic echo -n2 /debugPx4ctrl/fsm_state   # 状态名+五布尔" >&2
echo "  tail -30 ~/sitl_sim/logs/px4ctrl.log(或 roslaunch 终端)" >&2
exit 1
