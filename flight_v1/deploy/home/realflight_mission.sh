#!/bin/bash
# realflight_mission.sh -- 任务飞行入口（2026-11-07）
#
# 用户令：脚本收敛回**实飞教程脚本族**，只有"不同任务"才另写。
#   共用（教程原有）：realflight_check / stack / vins_restart / record_v1 / vins_watch / ctrl
#   任务（各一个）：  realflight_round.sh（单轮悬停验证）
#                     realflight_mission.sh（本文件，任务飞行）
#
# 本文件只是教程族命名的入口，真正逻辑在 ~/sitl_realmachine/flight_v1/flight.sh
# （任务专属：地图检查/目标校验与 FSM/起飞降落）。
# **起栈唯一入口 = ~/realflight_stack.sh**：五件套+规划器+相机位姿转接+RViz+健康门全在那里。
#
# 用法:
#   bash ~/realflight_mission.sh start        # 起栈（唯一入口 realflight_stack.sh，含 RViz/健康门/preflight）
#   bash ~/realflight_mission.sh status
#   bash ~/realflight_mission.sh rviz         # 需要桌面/NoMachine
#   bash ~/realflight_mission.sh record start
#   bash ~/realflight_mission.sh takeoff      # 到 0.70m 稳定 5s，之后 RViz 点目标(<=3.5m)
#   bash ~/realflight_mission.sh land         # 到点会自动降；这条是手动兜底
#   bash ~/realflight_mission.sh vins restart # 重启 VINS（**含 ego**，用地图版规划器）
#   bash ~/realflight_mission.sh record stop
#   bash ~/realflight_mission.sh stop
set -uo pipefail

FLOW="$HOME/sitl_realmachine/flight_v1"

# 任务模式默认的 RViz 命令（起栈时由 realflight_stack.sh 拉起）
export RVIZ_CMD="${RVIZ_CMD:-bash $HOME/sitl_realmachine/rviz_mapping_v1/map_rviz.sh}"

case "${1:-help}" in
  auto)
    # ========================================================================
    # 任务 B（任务模式）：**栈由你自己先起好**（bash ~/realflight_stack.sh，两个任务共用）。
    # 本脚本只做任务：检查栈件在位 -> 开录 -> 起飞 -> 你在 RViz 点目标
    #             -> 导航 -> 到点稳定 5s -> 等下一目标 20s -> 无新目标自动降落 -> 停录
    # 本脚本**不启动、不重启、不清场**任何栈进程（起栈是你的动作，避免抢 rosmaster）。
    # **唯一手动步骤：在 RViz 里点一个 3.5 m 内的目标点。**
    # ========================================================================
    # 2026-11-07：彩排支持 —— `realflight_mission.sh auto --dry` 只跑到"发布 TAKEOFF"前一步。
    DRYARG=""
    [ "${2:-}" = "--dry" ] && DRYARG="--dry"
    echo "===== 全流程自动开始 $(date '+%T') ${DRYARG:+（彩排模式，不解锁）} ====="
    # 用户要求：栈由你自己起一次，任务脚本不得启动/重启栈（否则抢 rosmaster）。
    if ! rostopic list >/dev/null 2>&1; then
      echo "✗ 没有 ROS master —— 请先自己起栈：bash ~/realflight_stack.sh" >&2; exit 1
    fi
    _miss=""
    for _n in /px4ctrl /vins_estimator /mavros /drone_0_ego_planner_node /drone_0_traj_server; do
      rosnode list 2>/dev/null | grep -qx "$_n" || _miss="$_miss $_n"
    done
    [ -z "$_miss" ] || { echo "✗ 栈件缺:$_miss —— 请先自己起栈" >&2; exit 1; }
    echo "✓ 栈件在位（复用你已起的栈；本脚本不重启任何进程）"
    bash "$FLOW/flight.sh" record start || { echo "✗ 开录失败，停止"; exit 1; }
    echo "--- 起飞；到位后请在 RViz 点目标（<=3.5 m）。之后全自动。 ---"
    RC=0
    _LOG="/tmp/flight_mission_$(date +%Y%m%d_%H%M%S).log"
    # 2026-11-13 用户令：去掉通用"遥控器接管"横幅 —— 失败时打印 mission 给出的具体原因。
    # flight_mission.py 异常退出前打印 `FLIGHT FAIL: <原因>`（多行时后续行以 "- " 开头）；
    # PYTHONUNBUFFERED=1 保证经 tee 后仍逐行实时显示。
    PYTHONUNBUFFERED=1 bash "$FLOW/flight.sh" takeoff $DRYARG 2>&1 | tee "$_LOG"
    _MISSION_RC=${PIPESTATUS[0]}
    if [ "$_MISSION_RC" -eq 0 ]; then
      echo "===== 任务完成：已到点并自动降落 ====="
    else
      _fail=$(sed -n '/^FLIGHT FAIL: /,$p' "$_LOG")
      if [ -n "$_fail" ]; then
        _reason=$(printf '%s\n' "$_fail" | head -n 1 | sed 's/^FLIGHT FAIL: //; s/：$//')
        echo "===== ✗ 任务异常中止：${_reason} ====="
        printf '%s\n' "$_fail" | tail -n +2 | sed 's/^/  /'
      else
        # flight.sh 在 exec mission 之前失败（规划器未就绪/录包起不来等）：取最后一条错误行
        _reason=$(grep -aE '✗|未就绪|失败|拒绝|ERROR|错误' "$_LOG" | tail -n 1 | sed 's/^[[:space:]]*//')
        [ -n "$_reason" ] || _reason=$(grep -av '^[[:space:]]*$' "$_LOG" | tail -n 1 | sed 's/^[[:space:]]*//')
        [ -n "$_reason" ] || _reason="无输出"
        echo "===== ✗ 任务异常中止：${_reason} ====="
      fi
      echo "  （完整输出：$_LOG）"
      RC=1   # 2026-11-07 审查修正：原来异常也 exit 0，上层/人会以为成功
    fi
    bash "$FLOW/flight.sh" record stop || true
    exit $RC
    ;;
  vins)
    # VINS 重启必须连带重启 ego（原点重锚 -> 旧栅格地图坐标系错位），
    # 且任务模式要用**地图版**规划器，否则会换回 vins 版。
    # 2026-11-07 审查修正：这个 launch 在 ~/sitl_realmachine/flight_v1/ 里，不属于 ego_planner 包。
    # 原来写成 "ego_planner xxx.launch" -> roslaunch 报 RLException，规划器根本起不来。
    export PLANNER_LAUNCH="$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch"
    exec bash "$HOME/realflight_vins_restart.sh" "${@:2}"
    ;;
  help|--help)
    sed -n "3,20p" "$0" | sed "s/^# \{0,1\}//"
    echo
    echo "任务子命令（转调 flight_v1/flight.sh）："
    bash "$FLOW/flight.sh" help 2>&1 | tail -1
    ;;
  *)
    exec bash "$FLOW/flight.sh" "$@"
    ;;
esac
