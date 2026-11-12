#!/bin/bash
# px4ctrl 起停助手 v1（2026-10-22）——治"round 失败/Ctrl+C 后 px4ctrl 残留抢模式"
# 背景：首轮 20261022_002600 失败后 px4ctrl 残留、持续 100Hz setpoint 与遥控抢模式（判读件 §四-1）
# 用法：bash ~/realflight_ctrl.sh stop    # 安全停（armed=True 拒绝——先降落再停）
#       bash ~/realflight_ctrl.sh start   # 按栈同款拉起（roslaunch px4ctrl run_ctrl.launch）
#       bash ~/realflight_ctrl.sh status
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
CMD="${1:-status}"
up() { rosnode list 2>/dev/null | grep -qx "/px4ctrl"; }
is_armed() { timeout 5 rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "armed: True"; }
case $CMD in
  status)
    if up; then
      A=$(timeout 5 rostopic echo -n 1 /mavros/state 2>/dev/null | grep armed)
      echo "px4ctrl: 运行中  ${A:-状态未知}"
    else
      echo "px4ctrl: 未运行"
    fi ;;
  start)
    if up; then echo "✓ px4ctrl 已在运行"; exit 0; fi
    TS=$(date +%H%M%S)
    nohup roslaunch px4ctrl run_ctrl.launch > /tmp/px4ctrl_$TS.log 2>&1 &
    W=0; until up; do sleep 1; W=$((W+1)); [ $W -ge 8 ] && { echo "✗ 8s 未注册——看 /tmp/px4ctrl_$TS.log"; exit 1; }; done
    echo "✓ px4ctrl 已拉起（日志 /tmp/px4ctrl_$TS.log）" ;;
  stop)
    if ! up; then echo "✓ px4ctrl 本来就没在跑"; exit 0; fi
    if is_armed; then echo "✗ 拒绝：飞机处于解锁状态——先降落（CH5 拨低缓降）再来停"; exit 1; fi
    P1=$(pgrep -f 'roslaunch px4ctrl run_ctrl.launch' | head -1)
    [ -n "$P1" ] && kill -INT "$P1" 2>/dev/null
    sleep 2
    pkill -x px4ctrl_node 2>/dev/null
    sleep 1
    if up; then echo "✗ 停不干净——人工检查 pgrep -af px4ctrl"; exit 1; fi
    echo "✓ px4ctrl 已停（setpoint 流断、不再抢模式）" ;;
  *)
    echo "用法: bash ~/realflight_ctrl.sh {start|stop|status}"; exit 1 ;;
esac
