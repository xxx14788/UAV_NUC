#!/bin/bash
# =============================================================================
# realflight_stack.sh — 实飞起栈唯一入口（v7，2026-11-15 代码质量重构）
#
# 用法:
#   bash ~/realflight_stack.sh                    # 默认带 RViz（无可用 DISPLAY 时软跳过）
#   RVIZ_CMD="" bash ~/realflight_stack.sh        # 不起 RViz
#   PLANNER_LAUNCH="ego_planner xxx.launch" bash ~/realflight_stack.sh
#
# 出口契约（教程/任务脚本依赖，勿改文案）:
#   成功: 末行 `===== STACK READY HH:MM:SS（v7 总耗时 Xs），可开录起飞 =====`，退出码 0
#   失败:      `===== STACK FAIL——禁飞 =====`，退出码 1
#
# 阶段 → 门（门限全部在 ~/sitl_realmachine/lib/common.sh 单源定义）:
#   1/5 清场      已解锁 / 正在录包 → 拒绝起栈；清掉全部残留并确认 rosmaster 归零
#   2/5 五件套    realmachine_2a_reboot_stack.sh（内含 IMU≥IMU_MIN_HZ / RC≥RC_MIN_HZ /
#                 陀螺带 |v|≤0.008 / 相机流 / VINS 出流）
#   3/5 三件同起 + 门区并行:
#       规划器 / 相机位姿转接 / 轨迹回传 —— wait_until 注册齐，且至少 STACK_STABLE_MIN_S 秒
#       健康门   depth / 左目 / odom 三路一次测频（HEALTH_WINDOW_S 窗口）
#       px4ctrl 活性门  /debugPx4ctrl/fsm_state 有输出（PX4CTRL_ACTIVE_TIMEOUT_S 上限）
#       5/5 预检  t1_preflight_check_v1.py（内部 5s 采样 + 6 次 mavparam；首跑 NO-GO 重试一次）
#       占用地图  软告警（场地开阔时可能本来就空）
#   4/5 打印健康门结果   5/5 打印预检结果   最后 RViz + 判定
#
# 设计约定（改前先读 lib/common.sh 头部）:
#   * 所有等待用 wait_until / sleep_until_elapsed（秒数显式，不再手写计数器）
#   * 条件判定不用 `cmd | grep -q`（pipefail 下假失败），用 case/命令替换
#   * 2>/dev/null 只用在"没有输出是合法状态"的地方（rostopic echo 超时等）
#   * 并行段的输出各落 $GATE_DIR 下的文件，最后按 4/5、5/5 顺序打印（屏幕顺序与旧版一致）
# =============================================================================
set +u
# shellcheck source=/dev/null
source /opt/ros/noetic/setup.bash
# shellcheck source=/dev/null
source "$HOME/catkin_ws/devel/setup.bash"
# shellcheck source=/dev/null
source "$HOME/sitl_realmachine/lib/common.sh"
set -u
set -o pipefail

# ---------------------------------------------------------------- 路径常量
PLANNER_LAUNCH=${PLANNER_LAUNCH:-$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch}
CONTRACT=${CONTRACT:-$HOME/sitl_realmachine/flight_v1/contract/flight_contract.yaml}
RELAY_PY=$HOME/sitl_realmachine/flight_v1/camera_pose_relay.py
PATHPUB_PY=$HOME/sitl_realmachine/flight_v1/planned_path_pub.py
HEALTH_PY=$HOME/sitl_realmachine/flight_v1/vins_health_bridge.py   # 2026-11-15：VINS 健康量桥
PREFLIGHT_PY=$HOME/sitl_realmachine/tools/t1_preflight_check_v1.py
STACK_2A=$HOME/sitl_realmachine/realmachine_2a_reboot_stack.sh
LOCK=$HOME/sitl_realmachine/flight_v1/runtime/stack.lock
DEPTH_TOPIC=""
DEPTH_MIN=""
PASS=1
GATE_DIR=""

# ---------------------------------------------------------------- 基础设施
acquire_lock() {
  mkdir -p "$(dirname "$LOCK")"
  if [ -f "$LOCK" ]; then
    local old
    old=$(cat "$LOCK" 2>/dev/null) || old=""
    if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
      die "另一个起栈进程正在运行（PID $old）"
    fi
  fi
  printf '%s\n' "$$" > "$LOCK"
}

cleanup() {
  [ -n "$GATE_DIR" ] && rm -rf "$GATE_DIR"
  rm -f "$LOCK"
  return 0
}

# ---------------------------------------------------------------- 谓词
rosmaster_gone() { ! pgrep -x rosmaster >/dev/null 2>&1; }

planner_registered() { has_node_pat '*ego_planner*|*traj_server*'; }
relay_registered()   { has_node /planner_camera_pose_relay; }
pathpub_registered() { has_node /planned_path_pub; }
health_registered() { has_node /vins_health_bridge; }   # 2026-11-15

three_registered() {
  nodes_snapshot
  planner_registered && relay_registered && pathpub_registered
}

# ---------------------------------------------------------------- 清场
phase_cleanup() {
  echo "===== 1/5 清场 $(date '+%T') ====="

  # 安全门（2026-11-07 用户令）：清场会全杀；已解锁或正在录包时绝不允许
  if pgrep -x rosmaster >/dev/null 2>&1 || pgrep -x roscore >/dev/null 2>&1; then
    local state
    state=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null) || state=""
    case $state in
      *"armed: True"*) die "飞控已解锁——拒绝起栈（先落地、上锁）" ;;
    esac
  fi
  if rosbag_recording; then
    die "正在录包——先正常结束录制（flight.sh record stop）再起栈"
  fi
  # 本机可能同时跑别人的私有 master 台架（实测有 :11312）：清场按进程名杀，可能波及对方。
  # 只提示不拦——但要让人知道"我的起栈可能会打断另一条会话"。
  local foreign
  foreign=$(foreign_master_hint)
  if [ -n "$foreign" ]; then
    warn "本机另有 ROS master：$(printf '%s' "$foreign" | tr '\n' ' ')"
    echo "    清场按进程名杀，可能影响对方台架——建议先停台架再起栈（本次继续）"
  fi

  # 先把残留打出来（真出问题时好定位），再杀
  local stale
  stale=$( { pgrep -a -x rosmaster; pgrep -a -x vins_node
             pgrep -af '[m]avros_node|[r]ealsense2_camera|[r]un_planner|[r]oslaunch'; } 2>/dev/null \
           | grep -v realflight ) || stale=""
  if [ -n "$stale" ]; then
    echo "发现残留："
    printf '%s\n' "$stale" | sed 's/^/  杀 /'
  else
    echo "无残留（干净）"
  fi

  # 括号式模式：普通词会连调用者自己的 shell 行一起命中（实测踩过两次）
  pkill -x vins_node 2>/dev/null || true
  pkill -x rosmaster 2>/dev/null || true
  pkill -x roscore 2>/dev/null || true
  pkill -f '[m]avros_node' 2>/dev/null || true
  pkill -f '[r]ealsense2_camera' 2>/dev/null || true
  pkill -f '[r]un_planner' 2>/dev/null || true
  pkill -f '[r]oslaunch' 2>/dev/null || true
  pkill -f '[c]amera_pose_relay.py' 2>/dev/null || true
  pkill -f '[p]lanned_path_pub.py' 2>/dev/null || true
  pkill -f '[v]ins_to_mavros_node' 2>/dev/null || true
  # 以下三项是 roslaunch 的子进程；launch 被杀后偶尔会剩孤儿（2026-11-08 P0-6 同形状）
  pkill -f '[e]go_planner' 2>/dev/null || true
  pkill -f '[t]raj_server' 2>/dev/null || true
  pkill -f '[p]x4ctrl' 2>/dev/null || true
  pkill -x rviz 2>/dev/null || true
  # 地图工具节点不在五件套里，但会抢 /grid_map 与 CPU（2026-11-10 用户批准）
  nodes_snapshot
  if has_node /mapping_view; then rosnode kill /mapping_view >/dev/null 2>&1 || true; fi

  wait_until 3 0.1 "rosmaster 自行退出" rosmaster_gone || true
  pkill -9 -x rosmaster 2>/dev/null || true
  wait_until 3 0.1 "rosmaster 强制退出" rosmaster_gone \
    || die "rosmaster 杀不掉——手动 ps 检查后重跑"
  ok "清场毕（rosmaster 0 残留）"
}

# ---------------------------------------------------------------- 2/5
phase_five_piece() {
  echo "===== 2/5 起五件套主栈 $(date '+%T') ====="
  if ! bash "$STACK_2A"; then
    die "主栈脚本失败——停（看上方自检输出哪条流没起来）"
  fi
  ok "五件套自检过（mavros/IMU/infra/VINS 四流，pid 行见上）"
}

# ---------------------------------------------------------------- 3/5 起件
start_planner() {
  PLOG=$HOME/sitl_realmachine/planner_$(date +%H%M%S).log
  # PLANNER_LAUNCH 允许是 "包 launch文件" 两段（历史约定），故显式拆分而不是靠分词
  read -r -a _plan_argv <<< "$PLANNER_LAUNCH"
  nohup roslaunch "${_plan_argv[@]}" > "$PLOG" 2>&1 &
  echo "规划器 pid=$! 日志=$PLOG（悬停不依赖它）"
}

start_relay() {
  # pose_type=1(POSE_STAMPED) 必须吃 /planner/camera_pose；缺失 → 地图永远空
  # 判活必须问当前 master（pgrep 会把连旧 master 的孤儿当"已在运行"，2026-11-09 P0-6）
  if nodes_snapshot && relay_registered; then
    echo "  相机位姿转接已在运行（当前 master 上，跳过）"
    return 0
  fi
  pkill -f '[c]amera_pose_relay.py' 2>/dev/null || true
  sleep_until_elapsed "$(_now_ms)" 0.5   # 让旧实例把 socket 放掉
  RELAY_LOG=$HOME/sitl_realmachine/camera_pose_relay_$(date +%H%M%S).log
  nohup python3 "$RELAY_PY" > "$RELAY_LOG" 2>&1 &
  echo "  相机位姿转接 pid=$! 日志=$RELAY_LOG（/vins_estimator/camera_pose -> /planner/camera_pose）"
}

start_pathpub() {
  if nodes_snapshot && pathpub_registered; then
    echo "  轨迹回传已在运行（当前 master 上，跳过）"
    return 0
  fi
  pkill -f '[p]lanned_path_pub.py' 2>/dev/null || true
  sleep_until_elapsed "$(_now_ms)" 0.5
  PPLOG=$HOME/sitl_realmachine/planned_path_$(date +%H%M%S).log
  nohup python3 "$PATHPUB_PY" > "$PPLOG" 2>&1 &
  echo "  轨迹回传 pid=$! 日志=$PPLOG（/flight_v1/planned_path|executed_trail|goal_marker）"
}

start_health_bridge() {
  # 2026-11-15（用户令）：VINS 健康量进录包。只读 tail vins 日志，转发
  # track/|Bas|/|Bgs|/cost 到 /vins_estimator/health；不动 VINS 本体。
  if nodes_snapshot && health_registered; then
    echo "  VINS 健康桥已在运行（当前 master 上，跳过）"
    return 0
  fi
  pkill -f '[v]ins_health_bridge.py' 2>/dev/null || true
  sleep_until_elapsed "$(_now_ms)" 0.3
  HLOG=$HOME/sitl_realmachine/vins_health_$(date +%H%M%S).log
  nohup python3 "$HEALTH_PY" > "$HLOG" 2>&1 &
  echo "  VINS 健康桥 pid=$! 日志=$HLOG（/vins_estimator/health 进录包）"
}

read_contract() {
  local pair
  pair=$(python3 - "$CONTRACT" <<'PYEOF'
import sys
topic, hz = '/camera/depth/image_rect_raw', 15.0
try:
    import yaml
    with open(sys.argv[1], encoding='utf-8') as fh:
        d = yaml.safe_load(fh)
    topic = d['seams']['depth']['topic'] or topic
    hz = d.get('seams', {}).get('depth', {}).get('min_hz', hz)
except Exception:
    pass
print(topic, hz)
PYEOF
)
  read -r DEPTH_TOPIC DEPTH_MIN <<< "$pair"
  [ -n "$DEPTH_TOPIC" ] || DEPTH_TOPIC=/camera/depth/image_rect_raw
  [ -n "$DEPTH_MIN" ] || DEPTH_MIN=$DEPTH_MIN_FALLBACK_HZ
  echo "  深度门话题（读契约）= $DEPTH_TOPIC（门 ${DEPTH_MIN}Hz）"
}

# ---------------------------------------------------------------- 门区（后台）
probe_display() {
  local d
  for d in :0 :1 :1001; do
    if DISPLAY=$d timeout 2 xdpyinfo >/dev/null 2>&1; then
      printf '%s\n' "$d" > "$GATE_DIR/display"
      return 0
    fi
  done
  return 1
}

run_health_gate() {
  measure_rate "$HEALTH_WINDOW_S" \
    "$DEPTH_TOPIC" /camera/infra1/image_rect_raw /vins_estimator/odometry
}

run_px4ctrl_gate() {
  if timeout "$PX4CTRL_ACTIVE_TIMEOUT_S" rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state >/dev/null 2>&1; then
    printf '1\n' > "$GATE_DIR/px4act"
  else
    printf '0\n' > "$GATE_DIR/px4act"
  fi
}

run_occ_probe() {
  # 软告警：轮询到首次非空（cap 12s），场地开阔时可能一直空
  timeout 14 python3 - <<'PYOCC' 2>/dev/null
import rospy
from sensor_msgs.msg import PointCloud2
rospy.init_node("occchk", anonymous=True)
w = [0]
rospy.Subscriber("/drone_0_ego_planner_node/grid_map/occupancy_inflate",
                 PointCloud2, lambda m: w.__setitem__(0, max(w[0], m.width)))
t0 = rospy.get_time()
while not rospy.is_shutdown() and rospy.get_time() - t0 < 12:
    if w[0] > 0:
        break
    rospy.sleep(0.5)
print(w[0])
PYOCC
}

# ---------------------------------------------------------------- 5/5 预检
newest_vins_log() {
  local f
  # 2026-11-15：只认 15 分钟内还在写的日志（活日志每帧都写，mtime 必新）；
  # 否则会拿上一轮/上次开机的旧日志判收敛。
  f=$(find "$HOME/sitl_realmachine" -maxdepth 2 -name 'vins_*.log' -mmin -15 \
        -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
  if [ -z "$f" ]; then
    # 回退路径：按 mtime 取最新（日志文件名由本工程产生，无空格/特殊字符）
    # shellcheck disable=SC2012
    f=$(ls -t "$HOME"/sitl_realmachine/*/vins_*.log "$HOME"/sitl_realmachine/vins_*.log 2>/dev/null | head -1) || f=""
  fi
  printf '%s' "$f"
}

tail_median_cost() {
  grep -o 'final_cost=[0-9.e+-]*' "$1" 2>/dev/null | cut -d= -f2 | tail -400 | sort -g |
    awk '{a[NR]=$1} END{if(NR)print a[int(NR/2)+1]}'
}

settle_ready() {
  local c
  c=$(tail_median_cost "$1")
  [ -n "$c" ] && num_lt "$c" "$SETTLE_COST_MAX"
}

preflight_go() {
  case $1 in *"PREFLIGHT GO"*) return 0 ;; esac
  return 1
}

run_preflight() {
  local vlog c pf slice="" rc=1
  vlog=$(newest_vins_log)
  if [ -z "$vlog" ]; then
    bad "未找到 VINS 日志"
    printf '0\n' > "$GATE_DIR/preflight.rc"
    return 0
  fi
  echo "  [vins-log] $vlog"

  # 病理带就绪：冷启动初始化段 cost 是天文数字，收敛后才有意义（本机实测 <1s 就达标）
  wait_until 120 5 "病理带就绪（尾部 cost 中位 <${SETTLE_COST_MAX}）" settle_ready "$vlog" || true
  c=$(tail_median_cost "$vlog")
  if [ -n "$c" ] && num_lt "$c" "$SETTLE_COST_MAX"; then
    ok "病理带就绪（尾部 cost 中位 $c）"
    slice=/tmp/pf_slice_$$.log
    tail -n 800 "$vlog" > "$slice"
  else
    bad "120s 病理带未就绪（cost 尾部中位 ${c:-无数据}）——VINS 未收敛，禁飞"
    rc=0
  fi
  local logf=${slice:-$vlog}

  pf=$(python3 "$PREFLIGHT_PY" --vins-log "$logf" 2>&1) || true
  printf '%s\n' "$pf" | sed 's/^/  /'
  if preflight_go "$pf"; then
    ok "预检 GO"
  else
    warn "首跑 NO-GO（冷启动常见瞬态）——${PREFLIGHT_RETRY_S}s 后重试一次"
    sleep "$PREFLIGHT_RETRY_S"
    [ -n "$slice" ] && [ -f "$slice" ] && tail -n 800 "$vlog" > "$slice"
    pf=$(python3 "$PREFLIGHT_PY" --vins-log "$logf" 2>&1) || true
    printf '%s\n' "$pf" | sed 's/^/  /'
    if preflight_go "$pf"; then
      ok "预检 GO（重试后）"
    else
      bad "预检 NO-GO——按上面打印项处理"
      rc=0
    fi
  fi
  [ -n "$slice" ] && rm -f "$slice"
  printf '%s\n' "$rc" > "$GATE_DIR/preflight.rc"
}

# ---------------------------------------------------------------- 结果打印
check_rate() {   # $1=名称 $2=话题 $3=门槛 $4=measure_rate 多行输出
  local name=$1 topic=$2 min=$3 blob=$4 line rate gap src
  line=$(topic_line "$blob" "$topic")
  if [ -z "$line" ]; then
    bad "$name 无数据（测频未返回）[$topic]"
    return 1
  fi
  rate=$(rate_of "$line")
  gap=$(gap_of "$line")
  src=$(src_of "$line")
  case $src in
    absent) bad "$name 无流（话题没有发布者）[$topic]"; return 1 ;;
    error)  bad "$name 测频失败（python/rospy 异常）[$topic]"; return 1 ;;
  esac
  if num_ge "$rate" "$min"; then
    ok "$name = ${rate}Hz（门 ${min}；最大间隔 ${gap}ms；时基 ${src}）[$topic]"
    return 0
  fi
  bad "$name = ${rate}Hz < ${min}（最大间隔 ${gap}ms；时基 ${src}）[$topic]"
  return 1
}

print_health() {
  echo "===== 4/5 健康门 + px4ctrl 活性门（三路已在 3/5 段并行跑完）$(date '+%T') ====="
  local blob
  blob=$(cat "$GATE_DIR/health" 2>/dev/null) || blob=""
  check_rate "深度流"     "$DEPTH_TOPIC"                  "$DEPTH_MIN"   "$blob" || PASS=0
  check_rate "左目流"     /camera/infra1/image_rect_raw   "$CAM_MIN_HZ"  "$blob" || PASS=0
  check_rate "VINS里程计" /vins_estimator/odometry        "$ODOM_MIN_HZ" "$blob" || PASS=0

  nodes_snapshot
  if planner_registered; then
    ok "规划器节点在"
  else
    warn "规划器节点未见（悬停可继续；任务飞行会在 flight.sh start 的任务门硬判）——查 $PLOG"
  fi
  if relay_registered; then
    ok "相机位姿转接在（/planner/camera_pose）"
  else
    bad "相机位姿转接缺失 —— 规划器地图会是空的（避障/天花板都不生效）"
    if [ -n "${RELAY_LOG:-}" ] && [ -f "$RELAY_LOG" ]; then
      echo "    转接日志尾（$RELAY_LOG）："
      tail -5 "$RELAY_LOG" | sed 's/^/      /'
    fi
    PASS=0
  fi
  if topic_has_publisher /flight_v1/planned_path /planned_path_pub; then
    ok "轨迹回传发布者在（/flight_v1/planned_path <- /planned_path_pub）"
  else
    bad "轨迹回传发布者缺失 —— RViz 没有预期轨迹、录包也会缺该话题"
    PASS=0
  fi
  if [ "$(cat "$GATE_DIR/px4act" 2>/dev/null)" = 1 ]; then
    ok "px4ctrl 控制循环在（/debugPx4ctrl/fsm_state 有输出）"
  else
    bad "px4ctrl 未进控制循环（多半 RC 未连接/未开）——STACK FAIL"
    PASS=0
  fi
}

print_occ() {
  local occ
  occ=$(cat "$GATE_DIR/occ" 2>/dev/null) || occ=0
  occ=${occ:-0}
  if num_gt "$occ" 0; then
    ok "规划器地图已填充（膨胀点 ${occ}）"
  else
    warn "规划器地图为空（膨胀点 0）—— 场地开阔时可能正常；但箱子必须能被看到，否则避障/天花板不生效"
  fi
}

print_preflight() {
  echo "===== 5/5 预检脚本（电池/陀螺/VINS 病理带，完整输出）====="
  cat "$GATE_DIR/preflight.log" 2>/dev/null || true
  [ "$(cat "$GATE_DIR/preflight.rc" 2>/dev/null)" = 1 ] || PASS=0
}

start_rviz() {
  RVIZ_CMD=${RVIZ_CMD-bash "$HOME/sitl_realmachine/rviz_mapping_v1/map_rviz.sh"}
  [ -n "$RVIZ_CMD" ] || return 0
  if [ -z "${DISPLAY:-}" ] && [ -s "$GATE_DIR/display" ]; then
    DISPLAY=$(cat "$GATE_DIR/display")
    export DISPLAY
    echo "  [rviz] 自动探测到可用 DISPLAY=$DISPLAY"
  fi
  if [ -z "${DISPLAY:-}" ]; then
    echo "  [rviz] 跳过：当前无 DISPLAY（SSH 会话）——需要 RViz 请在 NoMachine 桌面起栈，或另跑 flight.sh rviz"
    return 0
  fi
  local log
  log=$HOME/sitl_realmachine/rviz_$(date +%H%M%S).log
  nohup bash -c "$RVIZ_CMD" > "$log" 2>&1 &
  echo "  [rviz] 已启动（$RVIZ_CMD），日志 $log"
}

# ---------------------------------------------------------------- 主流程
timer_start
acquire_lock
GATE_DIR=$(mktemp -d)
trap cleanup EXIT

phase_cleanup
mark "1/5 清场"
phase_five_piece
mark "2/5 五件套"

echo "===== 3/5 起规划器 + 相机位姿转接 + 轨迹回传（三件同时起）====="
T3=$(_now_ms)
start_planner
start_relay
read_contract
start_pathpub
start_health_bridge

# 门区在这里就后台启动：预检最慢（~13s）先起；健康门要算 ${HEALTH_WINDOW_S}s 平均率，
# 留 GATE_SETTLE_S 秒余量避开三件 launch 的 exec 抖动后再测（这段余量同时计入 6s 下限）。
( run_preflight ) > "$GATE_DIR/preflight.log" 2>&1 &
PF_PID=$!
( probe_display ) &
DISP_PID=$!
sleep_until_elapsed "$T3" "$GATE_SETTLE_S"
echo "  [并行] 预检 + 健康门 + px4ctrl 活性门 已在后台启动（与规划器就绪等待并行）"
( run_health_gate ) > "$GATE_DIR/health" 2>&1 &
HEALTH_PID=$!
( run_px4ctrl_gate ) &
PX4_PID=$!

if ! wait_until 20 0.5 "规划器/转接/回传注册齐" three_registered; then
  # 明细：哪一件没齐（旧版就打印这个，别丢——排障时是第一信息）
  st_pl=0; st_rd=0; st_pp=0
  nodes_snapshot
  planner_registered && st_pl=1
  relay_registered && st_rd=1
  pathpub_registered && st_pp=1
  warn "未齐明细：规划器=${st_pl} 转接=${st_rd} 回传=${st_pp}（4/5 逐项判）"
fi
sleep_until_elapsed "$T3" "$STACK_STABLE_MIN_S"
mark "3/5 三件就绪（$(( ($(_now_ms) - T3) / 1000 ))s）"

( run_occ_probe ) > "$GATE_DIR/occ" 2>&1 &
OCC_PID=$!

# 占用采样也要等（超时上限 14s 在 run_occ_probe 内部）；不等就是读文件的竞态
wait "$PF_PID" "$DISP_PID" "$HEALTH_PID" "$PX4_PID" "$OCC_PID"
mark "门区并行过（健康门/px4ctrl/预检/占用）"

print_health
print_occ
print_preflight

if [ "$PASS" -eq 1 ]; then
  start_rviz
  echo "===== STACK READY $(date '+%T')（v7 总耗时 $(elapsed_s)s），可开录起飞 ====="
else
  echo "===== STACK FAIL——禁飞 ====="
  exit 1
fi
