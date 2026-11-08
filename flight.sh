#!/usr/bin/env bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径（信息级）
set -eo pipefail
BASE="$HOME/sitl_realmachine"
FLOW="$BASE/flight_v1"
MAP="$BASE/rviz_mapping_v1"
STATE="$FLOW/runtime"
CMD="${1:-help}"
mkdir -p "$STATE"

source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u

state_once() { timeout 4 rostopic echo -n 1 /mavros/state 2>/dev/null; }
connected() { state_once | grep -q 'connected: True'; }
running() { rosnode list 2>/dev/null | grep -qx "$1"; }
ros_processes() {
  ps -eo comm=,args= | awk '$1 !~ /^(bash|sh|ps|awk|grep|ssh)$/ && $0 ~ /rosmaster|roscore|roslaunch|vins_node|vins_to_mavros|px4ctrl_node|mavros_node|realsense2_camera|ego_planner_node|traj_server|rviz|rosbag record|planned_path_pub|camera_pose_relay|map_only_node/ {print}'
}

case "$CMD" in
  start)
    # 2026-11-07（用户令）：起栈唯一入口 = ~/realflight_stack.sh。
    # 本脚本不再启动任何栈进程（五件套/规划器/相机位姿转接/RViz 全在 stack.sh），只做事后任务门。
    if [ "${2:-}" = "--dry" ]; then
      echo "[dry] 将执行：bash ~/realflight_stack.sh → 地图检查 → 规划器在线 → 接口检查"
      exit 0
    fi
    # 已解锁拒起栈：stack.sh 第 1 步会全杀，空中/已解锁时绝不允许。
    if rostopic list >/dev/null 2>&1; then
      if timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True'; then
        echo "✗ 飞控已解锁——拒绝起栈（先落地、上锁）" >&2; exit 1
      fi
    fi
    RVIZ_CMD="${RVIZ_CMD:-bash $MAP/map_rviz.sh}" bash "$HOME/realflight_stack.sh" || {
      echo "起栈失败（见上方健康门输出）；不要起飞。" >&2; exit 1; }
    # 2026-11-07 测试补回：stack.sh 只跑 VINS/病理带预检；preflight.sh 是编译/单测/RC/接线/电池的全量闸门。
    # 起栈阶段放行 RC 摇杆位置（用户裁定：起栈放行，起飞才要求居中）——takeoff 仍硬卡。
    RC_CHECK=0 bash "$HOME/preflight.sh" >/dev/null 2>&1 || {
      echo "preflight 未过 —— 先单独跑 ~/preflight.sh 看哪一条不过。" >&2; exit 1; }
    connected || { echo "MAVROS 未连接；不要起飞。" >&2; exit 1; }
    python3 "$MAP/map_check.py" --watch 6 --config "$STATE/map.yaml" || {
      echo "地图检查未过；不要起飞。" >&2; exit 1; }
    # 接口检查会读规划器的订阅（/planner/camera_pose、/flight_v1/goal_gate），必须先等节点在线。
    for _ in $(seq 1 10); do
      running /drone_0_ego_planner_node && running /drone_0_traj_server && break
      sleep 1
    done
    running /drone_0_ego_planner_node && running /drone_0_traj_server || {
      echo "规划器未在线；不要起飞（看 ~/sitl_realmachine/planner_*.log）。" >&2; exit 1; }
    python3 "$FLOW/check_interfaces.py" || {
      echo "接口检查未过；不要起飞。" >&2; exit 1; }
    echo "启动完成（唯一栈入口 realflight_stack.sh）。起飞前先 flight.sh status。"
    ;;
  status)
    python3 "$MAP/map_check.py" --status --allow-armed --watch 4
    python3 "$FLOW/check_interfaces.py"
    echo "--- flight nodes ---"
    rosnode list | grep -E 'mavros|camera|vins|px4ctrl|planner|traj_server|rviz' || true
    ;;
  monitor)
    exec bash "$HOME/realflight_vins_watch.sh" "${@:2}"
    ;;
  record)
    ACTION="${2:-start}"
    PIDFILE="$STATE/record.pid"
    case "$ACTION" in
      start)
        if [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
          echo "录包已运行，PID $(cat "$PIDFILE")"; exit 1
        fi
        LOG="$STATE/record_$(date +%Y%m%d_%H%M%S).log"
        nohup bash "$HOME/realflight_record_v1.sh" > "$LOG" 2>&1 &
        echo "$!" > "$PIDFILE"
        sleep 2
        kill -0 "$(cat "$PIDFILE")" 2>/dev/null || { cat "$LOG"; exit 1; }
        echo "录包已启动；日志 $LOG；bag 目录见日志首行。"
        ;;
      stop)
        [ -s "$PIDFILE" ] || { echo "没有本入口启动的录包进程。"; exit 1; }
        RP="$(cat "$PIDFILE")"
        kill -TERM "$RP" 2>/dev/null || true
        for _ in $(seq 1 15); do kill -0 "$RP" 2>/dev/null || break; sleep 1; done
        if kill -0 "$RP" 2>/dev/null; then
          echo "录包未在 15 秒内完成优雅收尾；未强杀，请检查 $STATE/record_*.log。" >&2; exit 1
        fi
        rm -f "$PIDFILE"
        echo "录包已停止并执行 rosbag 收尾。"
        ;;
      *) echo "用法: flight.sh record {start|stop}" >&2; exit 2 ;;
    esac
    ;;
  rviz)
    exec bash "$MAP/map_rviz.sh"
    ;;
  takeoff)
    running /drone_0_ego_planner_node && running /drone_0_traj_server || {
      echo "规划器未就绪；先完成 start、地面验图和 RViz 检查。" >&2; exit 1;
    }
    # 2026-11-08（用户令）：**起飞即录包**。今晚 22:33-22:39 真正飞出去那次没有 bag，
    # 事件无法复盘。这里若发现没在录，先自动起录；起不来就拒绝起飞。
    if [ "${RECORD_AUTO:-1}" = "1" ]; then
      if ! { [ -s "$STATE/record.pid" ] && kill -0 "$(cat "$STATE/record.pid")" 2>/dev/null; }; then
        echo "!! 起飞前未在录包：自动启动（RECORD_AUTO=0 可关闭）"
        LOG="$STATE/record_$(date +%Y%m%d_%H%M%S).log"
        nohup bash "$HOME/realflight_record_v1.sh" > "$LOG" 2>&1 &
        echo $! > "$STATE/record.pid"
        sleep 2
        if ! kill -0 "$(cat "$STATE/record.pid")" 2>/dev/null; then
          echo "✗ 录包启动失败（$LOG），拒绝起飞" >&2
          exit 1
        fi
        echo "录包已启动（日志 $LOG）"
      fi
    fi
    # 用户要求：去掉起飞前的多余配置审计；飞前门在 flight_mission.py 自己的 preflight。
    exec python3 "$FLOW/flight_mission.py" takeoff "${@:2}"
    ;;
  land)
    exec python3 "$FLOW/flight_mission.py" land
    ;;
  stop)
    [ ! -e "$STATE/stopping" ] || { echo "停栈已经在进行。" >&2; exit 1; }
    touch "$STATE/stopping"
    trap 'rm -f "$STATE/stopping"' EXIT
    if rostopic list >/dev/null 2>&1; then
      python3 "$FLOW/flight_mission.py" assert-ground
    elif pgrep -x rosmaster >/dev/null || pgrep -x roscore >/dev/null; then
      echo "ROS 状态未知，拒绝停栈；检查 ROS master 与飞控状态。" >&2; exit 1
    else
      echo "ROS master 未运行；没有本入口可停止的 ROS 栈。"
      exit 0
    fi
    if [ -s "$STATE/record.pid" ] && kill -0 "$(cat "$STATE/record.pid")" 2>/dev/null; then
      "$FLOW/flight.sh" record stop
    fi
    if pgrep -f '[r]osbag record' >/dev/null; then
      echo "检测到未由本入口管理的 rosbag record；先正常结束录制再停栈。" >&2; exit 1;
    fi
    if rostopic list >/dev/null 2>&1; then
      NODES=$(rosnode list | grep -E '^/(mavros|camera|realsense|vins|px4ctrl|drone_0_|planner_camera_pose_relay|planned_path_pub|mapping_view)' || true)
      [ -z "$NODES" ] || rosnode kill $NODES >/dev/null 2>&1 || true
      sleep 2
      pkill -INT -f '[r]oslaunch' 2>/dev/null || true
      pkill -INT -f '[c]amera_pose_relay.py' 2>/dev/null || true
      pkill -INT -f '[p]lanned_path_pub.py' 2>/dev/null || true
      pkill -INT -x vins_node 2>/dev/null || true
      pkill -INT -f '[v]ins_to_mavros_node' 2>/dev/null || true
      pkill -INT -x px4ctrl_node 2>/dev/null || true
      pkill -INT -f '[m]avros_node' 2>/dev/null || true
      pkill -INT -f '[r]ealsense2_camera' 2>/dev/null || true
      pkill -INT -f '[e]go_planner_node' 2>/dev/null || true
      pkill -INT -x traj_server 2>/dev/null || true
      # 2026-11-07 实测：RViz(Qt) 不响应 SIGINT，必须 TERM，否则停栈留残留。
      pkill -TERM -x rviz 2>/dev/null || true
      sleep 2
      pkill -INT -x rosmaster 2>/dev/null || true
      pkill -INT -x roscore 2>/dev/null || true
    fi
    for _ in $(seq 1 10); do
      [ -z "$(ros_processes)" ] && break
      sleep 1
    done
    ROS_LEFT="$(ros_processes)"
    if [ -n "$ROS_LEFT" ]; then
      printf '%s\n' "$ROS_LEFT" >&2
      echo "仍有 ROS master/launch 残留，请检查 ps -ef | grep -E 'ros|vins|mavros'。" >&2; exit 1;
    fi
    rm -f "$STATE/record.pid"
    rm -f "$STATE/landing.requested"
    rm -f "$STATE/stopping"
    trap - EXIT
    echo "本轮 ROS 全栈已停止。"
    ;;
  preflight)
    exec bash "$HOME/preflight.sh"
    ;;
  vins)
    # 2026-11-07：VINS 的重启/检查统一委派给共享脚本，任务脚本不再自己实现。
    ACTION="${2:-check}"
    case "$ACTION" in
      restart) exec bash "$HOME/realflight_vins_restart.sh" ;;
      check)   exec bash "$HOME/realflight_vins_watch.sh" "${@:3}" ;;
      *) echo "用法: flight.sh vins {restart|check}" >&2; exit 2 ;;
    esac
    ;;
  help|*)
    cat <<'EOF'
用法: flight.sh {start [--dry]|preflight|status|monitor|vins restart|vins check|record start|record stop|rviz|takeoff|land|stop}
EOF
    ;;
esac
