#!/usr/bin/env bash
# P2-A 臂参数观察器(T1 v11.7 单元5 ②): master 起来后立刻置 p2_cmdresp/enabled=true,
# 早于 vins_smoke 五件套里 px4ctrl 启动(px4ctrl 启动时从 param server 读)。
# 用法: nohup bash p2a_param_watcher.sh </dev/null > /tmp/p2a_watcher.log 2>&1 &
# 坑位: 勿加 set -u——ROS profile 链在未绑变量上爆(3090 十坑,set -u 须在 source 之后)
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
export ROS_MASTER_URI=http://localhost:11311
DEADLINE=$(( $(date +%s) + 400 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  if rosparam list >/dev/null 2>&1; then
    # px4ctrl 私有 nh 读参(PX4CtrlParam nh=~px4ctrl;gain/Kp2 同源在 /px4ctrl/)——双路径都设
    rosparam set /px4ctrl/p2_cmdresp/enabled true
    rosparam set /p2_cmdresp/enabled true
    echo "[$(date +%T)] set p2_cmdresp/enabled=true (server up)"
    # 等确认 px4ctrl 起来并读走(启动 banner enabled=1 自证)
    for i in $(seq 1 120); do
      if pgrep -x px4ctrl_node >/dev/null 2>&1; then
        sleep 3
        echo "[$(date +%T)] px4ctrl_node up; param state: $(rosparam get /p2_cmdresp/enabled 2>/dev/null)"
        exit 0
      fi
      sleep 2
    done
    echo "[$(date +%T)] WARN px4ctrl_node not seen in 240s"; exit 1
  fi
  sleep 1
done
echo "no master in 400s"; exit 1
