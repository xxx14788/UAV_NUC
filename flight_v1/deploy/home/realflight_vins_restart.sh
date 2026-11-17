#!/bin/bash
# =============================================================================
# realflight_vins_restart.sh — 轮间隔 >5min 的 VINS 重启（地面态执行）
# （v6，2026-11-15 代码质量重构；判据与 v5 完全等价）
#
# 四级收敛验收（任何一项 ✗ = 禁飞下一轮）:
#   [1] 出流：/vins_estimator/imu_propagate 发布（= 初始化完成），最多 WAIT_MAX 秒
#   [2-4] 收敛三查（CONVERGE_WINDOW_S=8s 采样）：
#         频率 odom≥ODOM_MIN_HZ、imu_prop≥IMU_PROP_MIN_HZ；位置/速度/姿态全 finite；
#         8s 位置极差≤0.15m（判"静置 init"）
#   [5] 日志病理带：|Bas| 末 20 条中位 ≤0.8；cost **init 段**前 20 条中位 ≤1e4
#       （cost 随滑窗残差数增长，末段取会假报警；日志无行 = ⚠ 不判死）
# 组件同步重启（VINS 原点重锚后坐标系失效）：vins_to_mavros → 相机位姿转接 → EGO → px4ctrl
#   后三件在 8s 收敛采样期间**并行**完成；px4ctrl 只在未解锁时动。
#   2026-11-17 用户令：**规划器 30s 内未上线 = 禁飞下一轮**（原来只告警）。
#
# 出口: 末行 `===== 重启成功…=====` + 退出码 0，或 `===== ✗ 收敛检查未过…=====` + 1
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

WAIT_MAX=${WAIT_MAX:-20}
CONVERGE_WINDOW_S=${CONVERGE_WINDOW_S:-8}
POSE_RANGE_MAX_M=${POSE_RANGE_MAX_M:-0.15}
CFG=${CFG:-$HOME/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml}
VINS_LOG=""
TAIL_OUT=""
FAIL=0

cleanup() {
  [ -n "$TAIL_OUT" ] && rm -f "$TAIL_OUT" "$TAIL_OUT.fail"
  return 0
}
trap cleanup EXIT

# ---------------------------------------------------------------- 谓词
vins_dead()      { ! pgrep -x vins_node >/dev/null 2>&1; }
v2m_dead()       { ! pgrep -f '[v]ins_to_mavros_node' >/dev/null 2>&1; }
v2m_up()         { pgrep -f '[v]ins_to_mavros_node' >/dev/null 2>&1; }
imu_prop_live()  { timeout 5 rostopic echo -n 1 --noarr /vins_estimator/imu_propagate >/dev/null 2>&1; }
relay_up()       { nodes_snapshot; has_node /planner_camera_pose_relay; }
planner_up()     { nodes_snapshot; has_node_glob '*ego_planner*' || has_node_glob '*traj_server*'; }
px4ctrl_up()     { nodes_snapshot; has_node /px4ctrl; }
fc_armed() {
  local s
  s=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null) || s=""
  case $s in *"armed: True"*) return 0 ;; esac
  return 1
}

# ---------------------------------------------------------------- 收敛三查（门本体）
convergence_check() {
  python3 - "$CONVERGE_WINDOW_S" "$ODOM_MIN_HZ" "$IMU_PROP_MIN_HZ" "$POSE_RANGE_MAX_M" <<'PYEOF'
import math, sys, threading, time
import rospy
from nav_msgs.msg import Odometry

dur = float(sys.argv[1]); odom_min = float(sys.argv[2])
prop_min = float(sys.argv[3]); range_max = float(sys.argv[4])

lock = threading.Lock(); msgs = []; nprop = [0]; tprop0 = [None]

def cb(m):
    with lock: msgs.append(m)

def cbp(m):
    with lock:
        nprop[0] += 1
        if tprop0[0] is None: tprop0[0] = time.monotonic()

rospy.init_node("vins_restart_verify_v1", anonymous=True, disable_signals=True)
rospy.Subscriber("/vins_estimator/odometry", Odometry, cb, queue_size=20)
rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, cbp, queue_size=100)
time.sleep(dur)
with lock:
    ms = list(msgs); n_p = nprop[0]; tp0 = tprop0[0]

fails = []
hz_o = len(ms) / dur
span_p = (time.monotonic() - tp0) if tp0 is not None else dur
hz_p = n_p / span_p if span_p > 0 else 0.0
print("  [2] 频率门: odom %.1fHz（门≥%g）  imu_prop %.1fHz（门≥%g）" % (hz_o, odom_min, hz_p, prop_min))
if hz_o < odom_min: fails.append("odom 频率 %.1f<%gHz" % (hz_o, odom_min))
if hz_p < prop_min: fails.append("imu_prop 频率 %.1f<%gHz" % (hz_p, prop_min))

bad = 0
for m in ms:
    p, q, w = m.pose.pose.position, m.pose.pose.orientation, m.twist.twist.linear
    vals = (p.x, p.y, p.z, q.x, q.y, q.z, q.w, w.x, w.y, w.z)
    if not all(math.isfinite(v) for v in vals): bad += 1
print("  [3] 数值健全: finite %d/%d（位置/速度/姿态）" % (len(ms) - bad, len(ms)))
if bad: fails.append("非有限值 %d 条" % bad)
if not ms: fails.append("odom 零消息")

if ms:
    xs = [m.pose.pose.position.x for m in ms]
    ys = [m.pose.pose.position.y for m in ms]
    zs = [m.pose.pose.position.z for m in ms]
    rng = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    print("  [4] 静置判定: %gs 位置极差 %.3fm（门≤%gm=静置 init）" % (dur, rng, range_max))
    if rng > range_max: fails.append("位置极差 %.3fm>%gm（非静置 init？）" % (rng, range_max))

if fails:
    print("  ✗ " + "；".join(fails))
    sys.exit(1)
print("  ✓ 收敛三查过")
PYEOF
}

median_of() { sort -g | awk '{a[NR]=$1} END{if(NR==0)exit; if(NR%2)print a[(NR+1)/2]; else printf "%.6g",(a[NR/2]+a[NR/2+1])/2}'; }

check_pathology() {
  local bas cost need_lines=20 w=0
  # 等日志积累（原来 sleep 3；改成轮询出现 ≥20 条 cost，上限 3s）
  while [ "$w" -lt 30 ]; do
    need_lines=$(grep -c 'final_cost=' "$VINS_LOG" 2>/dev/null) || need_lines=0
    [ "${need_lines:-0}" -ge 20 ] && break
    sleep 0.1
    w=$((w + 1))
  done
  bas=$(grep -o '|Bas|=[0-9.e+-]*' "$VINS_LOG" 2>/dev/null | cut -d= -f2 | tail -20 | median_of) || bas=""
  cost=$(grep -o 'final_cost=[0-9.e+-]*' "$VINS_LOG" 2>/dev/null | cut -d= -f2 | head -20 | median_of) || cost=""
  if [ -n "$bas" ] && [ -n "$cost" ]; then
    echo "  |Bas|=$bas（门≤0.8，末20）  cost=$cost（门≤1e4，init前20）"
    if num_ge "$BAS_MAX" "$bas" && num_ge "$SETTLE_COST_MAX" "$cost"; then
      ok "病理带内"
    else
      bad "病理带超限"
      FAIL=1
    fi
  else
    warn "日志暂无 Bas/cost 行（缓冲未积累）——不判失败，可开盯盘人工复核 Bas"
  fi
}

# ---------------------------------------------------------------- 组件重启（并行尾巴）
restart_components() {
  local armed=0 shared_grace=1
  if fc_armed; then armed=1; fi

  # 一次杀齐（旧实例必须死透），再统一留 1s 让 socket / 栅格 / setpoint 释放
  pkill -f '[c]amera_pose_relay.py' 2>/dev/null || true
  pkill -f '[r]un_planner' 2>/dev/null || true
  [ "$armed" = 0 ] && { pkill -f '[r]un_ctrl' 2>/dev/null || true; }
  local w=0 alive
  while [ "$w" -lt 30 ]; do
    alive=0
    pgrep -f '[c]amera_pose_relay.py' >/dev/null 2>&1 && alive=1
    pgrep -f '[r]un_planner' >/dev/null 2>&1 && alive=1
    [ "$armed" = 0 ] && pgrep -f '[r]un_ctrl' >/dev/null 2>&1 && alive=1
    [ "$alive" = 0 ] && break
    sleep 0.1
    w=$((w + 1))
  done
  sleep "$shared_grace"

  echo "--- 同步重启相机位姿转接 ---"
  local relay_log
  relay_log=$HOME/sitl_realmachine/camera_pose_relay_$(date +%H%M%S).log
  nohup python3 "$HOME/sitl_realmachine/flight_v1/camera_pose_relay.py" > "$relay_log" 2>&1 &

  # 规划器 launch 参数化：任务模式（地图版）必须传，否则会退回 vins 版丢天花板/膨胀/goal_gate
  echo "  [vins restart] 统一地图版规划器；EGO 随 VINS 一起重启（原点重锚）"
  local plan_log
  read -r -a _plan_argv <<< "${PLANNER_LAUNCH:-$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch}"
  plan_log=$HOME/sitl_realmachine/planner_$(date +%H%M%S).log
  nohup roslaunch "${_plan_argv[@]}" > "$plan_log" 2>&1 &

  local ctrl_log=""
  echo "--- 同步重启 px4ctrl（仅未解锁时）---"
  if [ "$armed" = 1 ]; then
    warn "当前已解锁：跳过 px4ctrl 重启（空中不动控制器）"
  else
    ctrl_log=$HOME/sitl_realmachine/px4ctrl_$(date +%H%M%S).log
    nohup roslaunch px4ctrl run_ctrl.launch > "$ctrl_log" 2>&1 &
  fi

  # 并行轮询在线（规划器上限 30s；px4ctrl 20s；转接随规划器一起判）
  local t0 el rd=0 pl=0 px=0
  [ "$armed" = 1 ] && px=1
  t0=$(_now_ms)
  while :; do
    if relay_up; then rd=1; fi
    if planner_up; then pl=1; fi
    if [ "$armed" = 0 ] && px4ctrl_up; then px=1; fi
    [ "$rd" = 1 ] && [ "$pl" = 1 ] && [ "$px" = 1 ] && break
    el=$(( ($(_now_ms) - t0) / 1000 ))
    [ "$el" -ge 30 ] && break
    sleep 0.5
  done
  el=$(( ($(_now_ms) - t0) / 1000 ))

  if [ "$rd" = 1 ]; then
    ok "相机位姿转接已在线（$relay_log，${el}s）"
  else
    warn "相机位姿转接未上线（$relay_log）—— 规划器地图会是空的"
  fi
  if [ "$pl" = 1 ]; then
    echo "--- ✓ 规划器已随 VINS 重启并在线（$plan_log，${el}s）---"
  else
    # 2026-11-17 用户令：规划器缺失=禁飞下一轮（原来是 ⚠ 软告警）。
    # 尾巴跑在子 shell 里，用标记文件把判定带回主流程。
    printf '0\n' > "$TAIL_OUT.fail"
    echo "--- ✗ 规划器 30s 内未上线（$plan_log）——禁飞下一轮，先看日志 ---"
  fi
  if [ "$armed" = 0 ]; then
    if [ "$px" = 1 ]; then
      ok "px4ctrl 已重启并在线（$ctrl_log，${el}s）"
    else
      warn "px4ctrl 20s 内未上线（$ctrl_log）"
    fi
  fi
}

# ---------------------------------------------------------------- 主流程
timer_start

echo "--- 杀旧 VINS ---"
pkill -x vins_node 2>/dev/null || true
wait_until 3 0.1 "旧 vins_node 退出" vins_dead || die "✗ 杀不掉"
ok "已清"
mark "杀旧 VINS"

VINS_LOG=$HOME/sitl_realmachine/vins_restart_$(date +%H%M%S).log
nohup rosrun vins vins_node "$CFG" > "$VINS_LOG" 2>&1 &
echo "--- 新 VINS pid=$! 日志=$VINS_LOG ---"

# VINS 重启 = 原点重锚：vins_to_mavros 若带旧首帧锚点/旧偏置，PX4 的 EV 位姿会错，一并重启
echo "--- 同步重启 vins_to_mavros ---"
pkill -f '[v]ins_to_mavros_node' 2>/dev/null || true
wait_until 2 0.1 "旧 vins_to_mavros 退出" v2m_dead || true
V2M_LOG=$HOME/sitl_realmachine/v2m_restart_$(date +%H%M%S).log
nohup rosrun vins_to_mavros vins_to_mavros_node > "$V2M_LOG" 2>&1 &
if wait_until 5 0.1 "vins_to_mavros 起来" v2m_up; then
  ok "vins_to_mavros 已重启（日志 $V2M_LOG）"
else
  die "vins_to_mavros 起不来——禁飞下一轮"
fi

echo "--- [1/5] 等出流（imu_propagate 发布=初始化完成；最多 ${WAIT_MAX}s，保持静置）---"
if ! wait_until "$WAIT_MAX" 0.6 "VINS 出流（imu_propagate）" imu_prop_live; then
  bad "${WAIT_MAX}s 未见出流——看日志："
  tail -8 "$VINS_LOG" | sed 's/^/    /'
  exit 1
fi
mark "VINS 出流"

# 组件重启整块丢后台，与 8s 收敛采样并行（输出落文件，最后按原顺序打印）
TAIL_OUT=$(mktemp)
( restart_components ) > "$TAIL_OUT" 2>&1 &
TAIL_PID=$!

echo "--- [2-4/5] 收敛三查（采样 ${CONVERGE_WINDOW_S}s：频率门 / 数值健全 / 静置判定）---"
if ! convergence_check; then
  FAIL=1
fi
mark "收敛三查(${CONVERGE_WINDOW_S}s，与转接/EGO/px4ctrl 重启并行)"

echo "--- [5/5] 日志病理带（|Bas| 末20 中位 / cost init前20 中位）---"
check_pathology
wait "$TAIL_PID" 2>/dev/null || true
cat "$TAIL_OUT"
# 组件重启阶段的硬失败（规划器未上线）由标记文件带回
[ -f "$TAIL_OUT.fail" ] && FAIL=1
mark "病理带 + 组件重启"

if [ "$FAIL" -ne 0 ]; then
  echo "===== ✗ 收敛检查未过——禁飞下一轮：开盯盘 bash ~/realflight_vins_watch.sh 观察，或看日志 $VINS_LOG ====="
  exit 1
fi
echo "===== 重启成功：VINS 初始化+收敛全过、vins_to_mavros/转接/规划器/px4ctrl 均已处理（v6 总耗时 $(elapsed_s)s）====="
