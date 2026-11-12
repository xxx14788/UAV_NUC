#!/bin/bash
# set_imu_rate.sh -- 重新申请 IMU 高速率（2026-11-06）
#
# **这不是新机制。** 它是 `~/sitl_realmachine/realmachine_2a_reboot_stack.sh` 里
# [1a] 步的复刻，供"mavros 被单独重启过"或"飞行轮开始前想再确认一次"时补发。
#
# 为什么需要补发
# --------------
# `set_message_interval` 是**运行时**状态，飞控重启就回到 50 Hz；
# 而且（09-28 记录在案）`mavcmd` **无 ACK、链路建立前发即丢**。
# 所以正确做法是：链路确认后发 + 发完实测复核 + 不达标重发。
#
# 取值（2026-10-22 用户令，三档亲测）
# -----------------------------------
#   511=SET_MESSAGE_INTERVAL, 105=HIGHRES_IMU(=/mavros/imu/data_raw 源)
#   5000us -> 170 Hz（成批欠发）
#   4000us -> 200.6 Hz（**选定**）
#   2000us -> 222 Hz（超需，白吃链路与 CPU）
# 实测上限约 222 Hz（mavlink 主循环节拍 ≈4.5ms，见 t1_evidence/w2_conclusion.md）。
#
# 用法：~/set_imu_rate.sh           # 补发并自检
#       ~/set_imu_rate.sh --check   # 只检查不发送（preflight 用）

set +u
source /opt/ros/noetic/setup.bash >/dev/null 2>&1
source "$HOME/catkin_ws/devel/setup.bash" >/dev/null 2>&1
set -u

INTERVAL_US=4000          # 与 realmachine_2a_reboot_stack.sh 保持一致
MSG_ID=105                # HIGHRES_IMU
MIN_HZ=190                # 与栈脚本的门限一致

rate_of() {
    timeout 6 rostopic hz /mavros/imu/data_raw 2>/dev/null \
        | awk '/average rate/{v=$3} END{printf "%.0f", v}'
}

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

if ! rostopic list >/dev/null 2>&1; then
    echo "  [FAIL] ROS master 不在线"
    exit 1
fi
if ! timeout 5 rostopic echo -n1 --noarr /mavros/state 2>/dev/null | grep -q "connected: True"; then
    echo "  [FAIL] /mavros/state 未连 FCU（mavcmd 会在链路未建立时静默丢弃）"
    exit 1
fi

BEFORE=$(rate_of)
HZ=$BEFORE

if [ $CHECK_ONLY = 0 ]; then
    for i in 1 2 3; do
        rosrun mavros mavcmd long 511 "$MSG_ID" "$INTERVAL_US" 0 0 0 0 0 >/dev/null 2>&1
        sleep 2
        HZ=$(rate_of)
        [ "${HZ:-0}" -ge "$MIN_HZ" ] && break
        echo "  第${i}次未达（${HZ:-无} Hz < ${MIN_HZ}），重发 511@${INTERVAL_US}us"
    done
fi

echo "  IMU 速率: 之前 ${BEFORE:-?} Hz -> 现在 ${HZ:-?} Hz（511/${MSG_ID}/${INTERVAL_US}us，门限 ${MIN_HZ}）"
if [ -z "$HZ" ]; then
    echo "  [FAIL] /mavros/imu/data_raw 无数据"
    exit 1
fi
if [ "${HZ:-0}" -ge "$MIN_HZ" ]; then
    echo "  [ OK ] data_raw ${HZ} Hz >= ${MIN_HZ} Hz（RLS 35-45ms 窗口够用；VINS 同一路输入）"
    exit 0
fi
echo "  [FAIL] data_raw ${HZ} Hz < ${MIN_HZ} Hz"
echo "         排查顺序：①链路是否 connected ②飞控是否刚重启 ③mavlink 节拍是否被负载拖慢"
echo "         （见 ~/sitl_sim/t1_evidence/w2_conclusion.md）"
exit 1
