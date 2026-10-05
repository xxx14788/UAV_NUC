#!/usr/bin/env bash
# 触发 px4ctrl 自动降落,并等它自己 disarm。
# 前置:px4ctrl 必须在 AUTO_HOVER —— LAND 在其他状态会被拒绝,且不会排队。
# T1-W5 修复:pub 与 04 相同的建连竞态处理(-r 1 持续 4s 替代单发)。
source /opt/ros/noetic/setup.bash
set -u
source "$HOME/catkin_ws/devel/setup.bash" || { echo "catkin_ws 未编译"; exit 1; }

state=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null || true)
if ! printf '%s' "$state" | grep -q 'armed: True'; then
    echo "⚠️  飞机当前不在 armed 状态 —— 若还没起飞，LAND 会被 px4ctrl 拒绝。"
    echo "    仍要发送请按回车，否则 Ctrl-C 退出。"
    read -r _
fi

# F2 (T1 v11.7 单元1,disarm_fix_prereg_v1 §2): /position_cmd 静默门——
# 若 planner/traj_server 未清场干净,LAND 会被 px4ctrl 在 CMD_CTRL 态按设计拒绝
# (disarm 五连败根因族,X2g1/g3/g4/X3l2a/l2b 取证在册)。快失败,不空耗 90s 等待窗。
# 窗口=3s:rostopic echo 进程启动(python 导入)≈1-1.5s,1Hz 僵尸发布者在剩余窗内必达;
# J3 实测 timeout 1 时订阅未及建立=门失效(启动延迟吃满窗口),勿改回。
if timeout 3 rostopic echo -n1 /position_cmd >/dev/null 2>&1; then
    echo "✗ /position_cmd 3s 内仍有消息 — planner/traj_server 清场失败,LAND 必被 CMD_CTRL 拒;先跑 kill_planner_all.sh 再降落" >&2
    exit 2
fi

timeout 4 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null
rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ]; then
    echo "LAND 发布失败 rc=$rc" >&2
    exit 1
fi
echo "已发送 LAND，等待落地 disarm（最多 90 秒）..."

if timeout 90 rostopic echo /mavros/state 2>/dev/null | grep -m1 -q '^armed: False$'; then
    echo "✅ 已落地并自动 disarm。"
else
    echo "⚠️  90 秒内未 disarm。先查这个："
    echo "      rostopic echo -n1 /mavros/extended_state    # landed_state 必须是 1 (ON_GROUND)"
    echo "    手动兜底："
    echo "      rosservice call /mavros/cmd/arming \"value: false\""
    echo "      rosservice call /mavros/set_mode \"base_mode: 0, custom_mode: 'AUTO.LOITER'\""
    exit 1
fi
