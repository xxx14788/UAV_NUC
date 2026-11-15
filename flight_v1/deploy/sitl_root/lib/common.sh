#!/bin/bash
# ============================================================================
# 实飞脚本公共库  common.sh
# 被 realflight_stack.sh / realflight_vins_restart.sh /
#    realmachine_2a_reboot_stack.sh  source
#
# 设计约定（改这个文件前先读）：
#   1. 阈值只在这里定义一次，用同名环境变量可覆盖（现场临时调参不修改脚本）。
#   2. 所有"等一会儿直到某条件"的地方用 wait_until / sleep_until_elapsed，
#      不许再手写 while+sleep+计数器（步长与上限必须显式写秒，不再让人心算 迭代×步长）。
#   3. 测频统一走 measure_rate（header.stamp 为时基；rostopic hz 的"到达率"会随
#      调度抖动系统性偏低 —— 实测同一条 200Hz 流能读出 189.9Hz）。
#   4. 本库不 set -e；函数用返回值表达结果，调用方决定 die 还是降级。
#   5. 所有条件判断避免 `cmd | grep -q`（pipefail 下 grep 提前退出会造成假失败），
#      统一用 case/awk 或命令替换。
# ============================================================================
# shellcheck shell=bash

# ---------------------------- 阈值（单源） ----------------------------
export IMU_MIN_HZ=${IMU_MIN_HZ:-185}              # /mavros/imu/data_raw 目标 200；11-15 由 190 放宽（190 贴线误杀）
export IMU_MAX_GAP_MS=${IMU_MAX_GAP_MS:-25}       # 提频后单条最大间隔；成段丢包会先在这一项暴露
export RC_MIN_HZ=${RC_MIN_HZ:-20}                 # /mavros/rc/in（511@65@20000us → 实测 45~50Hz）
export ODOM_MIN_HZ=${ODOM_MIN_HZ:-8}              # 健康门 /vins_estimator/odometry
export CAM_MIN_HZ=${CAM_MIN_HZ:-20}               # 健康门 /camera/infra1/image_rect_raw
export IMU_PROP_MIN_HZ=${IMU_PROP_MIN_HZ:-40}     # 轮间重启 /vins_estimator/imu_propagate
export HEALTH_WINDOW_S=${HEALTH_WINDOW_S:-8}      # 健康门测频窗口
export DEPTH_MIN_FALLBACK_HZ=${DEPTH_MIN_FALLBACK_HZ:-15}  # 契约读不到时的回退门槛
export STACK_STABLE_MIN_S=${STACK_STABLE_MIN_S:-6}         # 3/5 段最小稳定窗（原 20s 死等）
export GATE_SETTLE_S=${GATE_SETTLE_S:-2}                   # 门区开测前的稳定余量
export PX4CTRL_ACTIVE_TIMEOUT_S=${PX4CTRL_ACTIVE_TIMEOUT_S:-12}
export PREFLIGHT_RETRY_S=${PREFLIGHT_RETRY_S:-10}
export SETTLE_COST_MAX=${SETTLE_COST_MAX:-1e4}             # 病理带就绪：尾部 cost 中位
export BAS_MAX=${BAS_MAX:-0.8}                             # 病理带 |Bas| 门（预检工具内，此处仅注释用）
LIB_DIR=${LIB_DIR:-$HOME/sitl_realmachine/lib}
export LIB_DIR

# ---------------------------- 时间 ----------------------------
if [ -n "${EPOCHREALTIME:-}" ]; then
  _now_ms() { local t=${EPOCHREALTIME//[!0-9]/}; printf '%s' $(( t / 1000 )); }
else
  _now_ms() { date +%s%3N; }
fi

_T0_MS=""
timer_start() { _T0_MS=$(_now_ms); }
elapsed_s() {
  local d
  d=$(( $(_now_ms) - ${_T0_MS:-0} ))
  printf '%d.%d' $(( d / 1000 )) $(( (d % 1000) / 100 ))
}
MARK_INDENT=${MARK_INDENT:-}
mark() { printf '%s[+%ss] %s\n' "$MARK_INDENT" "$(elapsed_s)" "$*"; }

# ---------------------------- 输出 / 错误 ----------------------------
# 约定：ok/bad/warn 缩进两格（门类输出），die 打到 stderr 并退出
ok()   { printf '  ✓ %s\n' "$*"; }
bad()  { printf '  ✗ %s\n' "$*"; }
warn() { printf '  ⚠ %s\n' "$*"; }
die()  { printf '✗ %s\n' "$*" >&2; exit 1; }

need_cmd() {
  local c
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || die "缺少命令：$c"
  done
}

# 数值比较（浮点）：num_ge A B → A>=B；num_lt A B → A<B
num_ge() { awk -v a="$1" -v b="$2" 'BEGIN{exit !((a+0)>=(b+0))}'; }
num_gt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !((a+0)>(b+0))}'; }
num_lt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !((a+0)<(b+0))}'; }

# 秒（可带小数）→ 毫秒整数。bash 的 $(( )) 只能算整数，别直接乘 1000。
_sec_to_ms() { awk -v s="$1" 'BEGIN{printf "%d", (s+0)*1000}'; }

# ---------------------------- 轮询 ----------------------------
# wait_until <上限秒> <步长秒> <描述> <谓词函数> [谓词参数...]
#   谓词返回 0 = 满足。成功打印 ✓（含耗时），超时打印 ⚠ 并返回 1（不退出）。
wait_until() {
  local limit_s=$1 step_s=$2 desc=$3
  shift 3
  local t0 d limit_ms
  t0=$(_now_ms)
  limit_ms=$(_sec_to_ms "$limit_s")
  while :; do
    if "$@"; then
      d=$(( $(_now_ms) - t0 ))
      printf '  ✓ %s（%d.%ds）\n' "$desc" $(( d / 1000 )) $(( (d % 1000) / 100 ))
      return 0
    fi
    d=$(( $(_now_ms) - t0 ))
    if [ "$d" -ge "$limit_ms" ]; then
      printf '  ⚠ %s：%ss 未满足\n' "$desc" "$limit_s"
      return 1
    fi
    sleep "$step_s"
  done
}

# sleep_until_elapsed <起点ms> <至少秒(可小数)>  —— "最小稳定窗"：条件已满足也要等够
# 永远返回 0（这个函数只负责等待，不该让调用方因算术问题中断）
sleep_until_elapsed() {
  local from_ms=$1 need_ms d left
  need_ms=$(_sec_to_ms "$2")
  d=$(( $(_now_ms) - from_ms ))
  [ "$d" -ge "$need_ms" ] && return 0
  left=$(( need_ms - d ))
  printf -v _sleep_s '%d.%03d' $(( left / 1000 )) $(( left % 1000 ))
  sleep "$_sleep_s"
  return 0
}

# ---------------------------- 测频 ----------------------------
# measure_rate <窗口秒> <话题...>  → 每话题一行：
#   topic=<t> rate=<hz> n=<条数> span_s=<秒> max_gap_ms=<最大间隔> arrival_max_gap_ms=<到达间隔> src=<stamp|arrival|absent|error>
measure_rate() {
  local w=$1
  shift
  local hard=$(( ${w%.*} + 8 ))
  timeout "$hard" python3 "$LIB_DIR/measure_rate.py" --window "$w" "$@" 2>/dev/null
}

# topic_line <measure_rate 的多行输出> <话题> → 该话题那一行（无则空）
# 注意：awk 里不写 exit —— pipefail 下提前退出可能给上游 printf 发 SIGPIPE 造成假失败
topic_line() {
  printf '%s\n' "$1" | awk -v k="topic=$2" '$1==k {print}'
}

# field_of <一行> <字段名> → 字段值（无则空）
field_of() {
  printf '%s\n' "$1" | tr ' ' '\n' | awk -v k="$2=" 'index($0,k)==1 {sub(k,""); print}'
}

# rate_of / gap_of：从一行里取 rate / max_gap_ms（空则 0）
rate_of() { local v; v=$(field_of "$1" rate); printf '%s' "${v:-0}"; }
gap_of()  { local v; v=$(field_of "$1" max_gap_ms); printf '%s' "${v:-0}"; }
src_of()  { local v; v=$(field_of "$1" src); printf '%s' "${v:-absent}"; }

# ---------------------------- 话题/节点判定（避免 | grep -q） ----------------------------
# 说明：全部基于命令替换 + case，pipefail 安全，且只起一次进程。
nodes_snapshot() { _NODES=$(rosnode list 2>/dev/null) || _NODES=""; }
has_node() { case $'\n'$_NODES$'\n' in *$'\n'"$1"$'\n'*) return 0 ;; esac; return 1; }
has_node_pat() { case $_NODES in $1) return 0 ;; esac; return 1; }   # $1 = case 模式（如 *ego_planner*|*traj_server*）

topic_published() {
  local t=$1 out
  out=$(rostopic list 2>/dev/null) || out=""
  case $'\n'$out$'\n' in *$'\n'"$t"$'\n'*) return 0 ;; esac
  return 1
}

topic_has_publisher() {   # $1=话题 $2=发布者节点名
  local info
  info=$(rostopic info "$1" 2>/dev/null) || info=""
  case $info in *"$2"*) return 0 ;; esac
  return 1
}

# 录包守卫：只认"连我这个 master"的 rosbag record
#   为什么不用 ps | grep：本机可能同时跑别的私有 master 台架（实测有 :11312），
#   人家在录包不该拦住我的起栈；反之我的录包必须拦。判据 = 进程环境里的 ROS_MASTER_URI。
#   * 不用 grep -q（pipefail 下早退会给上游 SIGPIPE 造成假放行），走 awk / case
rosbag_recording() {
  local my=${ROS_MASTER_URI:-http://localhost:11311}
  local p uri cmd
  for p in $(pgrep -f 'rosbag record' 2>/dev/null); do
    [ -r "/proc/$p/environ" ] || continue
    uri=$(tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | awk -F= '/^ROS_MASTER_URI=/{print $2; exit}')
    uri=${uri:-http://localhost:11311}
    [ "$uri" = "$my" ] || continue
    cmd=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null) || cmd=""
    case $cmd in
      *python*rosbag\ record*) return 0 ;;
    esac
  done
  return 1
}

# 本机是否还有别的 ROS master（私有台架）。只做提示，不拦。
foreign_master_hint() {
  local p my=${ROS_MASTER_URI:-http://localhost:11311} myport uri
  myport=${my##*:}
  for p in $(pgrep -f 'rosmaster --core' 2>/dev/null); do
    uri=$(tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | awk -F= '/^ROS_MASTER_URI=/{print $2; exit}') || uri=""
    case $uri in
      *":$myport"*) continue ;;
      "") continue ;;
    esac
    printf '%s\n' "${uri:-未知}"
  done
}
