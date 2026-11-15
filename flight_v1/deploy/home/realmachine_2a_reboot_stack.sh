#!/bin/bash
# =============================================================================
# realmachine_2a_reboot_stack.sh — 五件套（v5，2026-11-15 代码质量重构）
# ⚠ 内部件：唯一正式起栈入口 = ~/realflight_stack.sh（清场/五件套/规划器/转接/RViz/健康门/preflight）。
#    直调会绕过健康门与 preflight；除调试外不要单独使用。
#
# 顺序（这几条顺序是有原因的，别随意调）:
#   0) roscore
#   1) mavros 连飞控  → 1a) 511@105 HIGHRES_IMU 200Hz + 511@65 RC_CHANNELS 50Hz
#                        然后用**一次** measure_rate 同时复核两路（header 时基，不是到达率）
#   2) 相机在 mavros 连上后**立刻**后台起（不依赖飞控，与 1a/1b 并行）——VINS 要它才能 init
#   1b) 飞控快检：连接/解锁态/陀螺三轴 |v|≤0.008 硬门（坏 IMU 会毒化 VINS init），
#       参数表 pull 后 6 个 param/get 并发取；不过 → 退栈并收掉相机
#   3) VINS（实机 config v0）→ 等 imu_propagate 出流
#   4) vins_to_mavros + 5) px4ctrl 与 imu_propagate 测频并行
#
# 硬门（不达标 exit 1，整栈失败）: IMU≥IMU_MIN_HZ、陀螺 |v|≤0.008、mavros connected、armed=False
# 软告警（打印但不拦，后续健康门/任务门再判）: RC 无流、相机无流、VINS 未出流、px4ctrl 未注册
# 证据留档（与旧版同名同形，供判读）: boot_$TS.log / mavros_connected_$TS.txt / imu_rate_$TS.txt /
#   rs_hz_$TS.txt / vins_hz_$TS.txt
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
# shellcheck disable=SC2034  # lib/common.sh 的 mark() 读这个变量（跨文件，shellcheck 看不到）
MARK_INDENT="  "

OUT=$HOME/sitl_realmachine/09_reboot_stack_2026-10-09
mkdir -p "$OUT" || die "无法创建 $OUT（磁盘满/权限？）"
cd "$OUT" || die "无法进入 $OUT（磁盘满/权限？）"

# 本脚本只能由 realflight_stack.sh 调用：直调且已有 master 时，会在别人的栈上再起一套五件套
if [ "${STACK_FROM_ORCHESTRATOR:-0}" != "1" ] && rostopic list >/dev/null 2>&1; then
  die "检测到已有 ROS master：请走 ~/realflight_stack.sh（本脚本仅允许其调用）"
fi

TS=$(date +%H%M%S)
LOG=boot_$TS.log
echo "=== 2a reboot stack start $(date -Is) ===" | tee "$LOG"

CAMERA_OWNED=0     # 1 = 相机已起但还没"交给栈"（提前退栈要收掉，避免留孤儿）
cleanup() {
  if [ "$CAMERA_OWNED" = 1 ]; then
    pkill -f '[r]ealsense2_camera' 2>/dev/null || true
  fi
  return 0
}
trap cleanup EXIT

# ---------------------------------------------------------------- 谓词
rosmaster_up()  { rostopic list >/dev/null 2>&1; }
mavros_conn() {
  local s
  s=$(timeout 2 rostopic echo -n1 --noarr /mavros/state 2>/dev/null) || s=""
  case $s in *"connected: True"*) return 0 ;; esac
  return 1
}
mavros_armed() {
  local s
  s=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null) || s=""
  case $s in *"armed: True"*) return 0 ;; esac
  return 1
}
vins_streaming() { timeout 5 rostopic echo -n1 --noarr /vins_estimator/imu_propagate >/dev/null 2>&1; }
v2m_running()    { pgrep -f '[v]ins_to_mavros_node' >/dev/null 2>&1; }
px4ctrl_registered() { nodes_snapshot; has_node /px4ctrl; }

# ---------------------------------------------------------------- 0) roscore
phase_roscore() {
  roscore >/dev/null 2>&1 &
  wait_until 8 0.5 "roscore 就绪" rosmaster_up || die "roscore 8s 未起来"
  echo "✓ [0/6] roscore 就绪"
  mark "roscore 就绪"
}

# ---------------------------------------------------------------- 1) mavros
phase_mavros() {
  roslaunch mavros px4.launch fcu_url:=/dev/pixhawk:921600 > "mavros_$TS.log" 2>&1 &
  local connected=0
  if wait_until 20 1 "mavros 连上飞控" mavros_conn; then connected=1; fi
  timeout 5 rostopic echo -n1 --noarr /mavros/state/connected 2>/dev/null | tail -1 | tee "mavros_connected_$TS.txt" || true
  if [ "$connected" = 1 ]; then
    echo "✓ [1/6] mavros 已连接飞控（/dev/pixhawk:921600）"
  else
    warn "[1/6] mavros 未连接——后续 IMU 提频/快检将拦截"
  fi
  mark "mavros 连接（$([ "$connected" = 1 ] && echo 完成 || echo 失败)）"
}

# ---------------------------------------------------------------- 1a) 511 提频
set_msg_interval() {   # $1=MAVLink msg id  $2=interval us
  rosrun mavros mavcmd long 511 "$1" "$2" 0 0 0 0 0 >/dev/null 2>&1 || true
}

# 用一次 measure_rate 同时复核 IMU 与 RC（header 时基），没达标的只重发那一条
phase_imu_rc_rate() {
  local attempt=1 resend_imu=1 resend_rc=1 blob li lr
  local imu_rate=0 imu_gap=0 rc_rate=0 imu_ok=0 rc_ok=0
  while [ "$attempt" -le 3 ]; do
    [ "$resend_imu" = 1 ] && set_msg_interval 105 4000
    [ "$resend_rc" = 1 ] && set_msg_interval 65 20000
    sleep 1     # mavcmd 无 ACK：命令生效到流率稳定有时间差（用户令：不稳的步骤留 1~3s）
    blob=$(measure_rate 3 /mavros/imu/data_raw /mavros/rc/in)
    li=$(topic_line "$blob" /mavros/imu/data_raw)
    lr=$(topic_line "$blob" /mavros/rc/in)
    imu_rate=$(rate_of "$li")
    imu_gap=$(gap_of "$li")
    rc_rate=$(rate_of "$lr")
    imu_ok=0; num_ge "$imu_rate" "$IMU_MIN_HZ" && imu_ok=1
    rc_ok=0;  num_ge "$rc_rate" "$RC_MIN_HZ" && rc_ok=1
    [ "$imu_ok" = 1 ] && [ "$rc_ok" = 1 ] && break
    resend_imu=$(( 1 - imu_ok ))
    resend_rc=$(( 1 - rc_ok ))
    echo "  [1a/1a2] 第${attempt}次未达标（IMU ${imu_rate}Hz / RC ${rc_rate}Hz），只重发没达标的"
    attempt=$((attempt + 1))
    [ "$attempt" -le 3 ] && sleep 1
  done
  mark "IMU/RC 提频+并行测频（$((attempt > 3 ? 3 : attempt)) 次尝试）"

  if [ "$imu_ok" = 1 ]; then
    echo "✓ [1a/6] IMU 提频：/mavros/imu/data_raw 实测 ${imu_rate}Hz——目标 200/门限 ${IMU_MIN_HZ}，每栈自动发 511@4000µs"
    if ! num_ge "$IMU_MAX_GAP_MS" "$imu_gap"; then
      warn "IMU 最大间隔 ${imu_gap}ms > ${IMU_MAX_GAP_MS}ms —— 疑似成段丢包（会污染预积分 Δv/Δθ，飞行中看 |Bas|/cost 趋势）"
    fi
  else
    bad "[1a/6] IMU 提频失败：/mavros/imu/data_raw 实测 ${imu_rate}Hz <${IMU_MIN_HZ}——STACK FAIL（流率未生效，禁飞）"
    exit 1
  fi
  if [ "$rc_ok" = 1 ]; then
    echo "✓ [1a2/6] RC 流：/mavros/rc/in 实测 ${rc_rate}Hz（511@65@20000us）"
  else
    bad "[1a2/6] RC 流仍无数据（${rc_rate}Hz）——遥控器是否上电/对频？px4ctrl 会卡在 Waiting for RC"
  fi

  # 留档（保持旧格式的 average rate: 记号，追加新字段）
  echo -n "  [留档] IMU 流率(/mavros/imu/data_raw): " | tee "imu_rate_$TS.txt"
  echo "average rate: ${imu_rate} （门 ${IMU_MIN_HZ}Hz；最大间隔 ${imu_gap}ms；header 时基）" \
    | tee -a "imu_rate_$TS.txt"
}

# ---------------------------------------------------------------- 2) 相机（提前起）
phase_camera_launch() {
  roslaunch realsense2_camera rs_camera.launch \
    infra_width:=848 infra_height:=480 infra_fps:=30 \
    depth_width:=848 depth_height:=480 depth_fps:=30 \
    enable_infra1:=true enable_infra2:=true enable_depth:=true \
    align_depth:=false enable_color:=false > "rs_$TS.log" 2>&1 &
  CAMERA_OWNED=1
  mark "相机 launch 已发（后台，与飞控块并行）"
}

phase_camera_ready() {
  local blob l rate gap
  # 等 publisher 出现（冷启动/USB 重枚举时 4s 窗口可能一帧都收不到）
  wait_until 12 0.3 "infra1 出流" topic_published /camera/infra1/image_rect_raw || true
  blob=$(measure_rate 4 /camera/infra1/image_rect_raw)
  l=$(topic_line "$blob" /camera/infra1/image_rect_raw)
  rate=$(rate_of "$l")
  gap=$(gap_of "$l")
  case $(src_of "$l") in
    absent) rate=0 ;;
  esac
  echo "camera_rate=$rate" | tee "rs_hz_$TS.txt"
  if num_gt "$rate" 0; then
    echo "✓ [2/6] 相机就绪：infra1 左目图像流(/camera/infra1/image_rect_raw) ${rate}Hz（最大间隔 ${gap}ms；双目 848×480 + 深度 848×480 @30）"
  else
    bad "[2/6] 相机无流——健康门将拦截"
  fi
  mark "相机就绪（提前起 + 测频，实测 ${rate}Hz）"
}

# ---------------------------------------------------------------- 1b) 飞控快检
fetch_param() { rosservice call /mavros/param/get "param_id: '$1'" 2>/dev/null | awk '/real:/{print $2}'; }

wait_param_table() {   # pull 一次，然后 0.3s 步长轮询到可读（上限 10s）
  local v="" t0
  rosservice call /mavros/param/pull "{}" >/dev/null 2>&1 || true
  t0=$(_now_ms)
  while [ $(( ($(_now_ms) - t0) / 1000 )) -lt 10 ]; do
    v=$(fetch_param CAL_GYRO0_XOFF)
    if [ -n "$v" ] && [ "$v" != "0.0" ] && [ "$v" != "0" ]; then printf '%s' "$v"; return 0; fi
    sleep 0.3
  done
  printf '%s' "$v"
  return 1
}

phase_fcu_quickcheck() {
  if ! mavros_conn; then die "FCU_QUICK_FAIL: mavros 未连接——检查飞控供电/串口"; fi
  if mavros_armed; then die "FCU_QUICK_FAIL: 飞控处于解锁态——禁止起栈"; fi
  timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep "mode:" | head -1 | sed 's/^/  [FCU 快检] /' || true

  if ! wait_param_table >/dev/null; then
    warn "[FCU 快检] 参数表 10s 未同步（快检读值可疑，以末尾预检为准）"
  fi

  # 6 个 param/get 并发（串行 = 6 次 rosservice 进程启动）
  local p ids="" gfail=0 v
  for p in CAL_GYRO0_XOFF CAL_GYRO0_YOFF CAL_GYRO0_ZOFF CAL_ACC0_XOFF CAL_ACC0_YOFF CAL_ACC0_ZOFF; do
    ( fetch_param "$p" > "p_$p.txt" ) &
    ids="$ids $!"
  done
  # shellcheck disable=SC2086  # ids 是一串 PID，必须分词
  wait $ids

  for p in CAL_GYRO0_XOFF CAL_GYRO0_YOFF CAL_GYRO0_ZOFF; do
    v=$(cat "p_$p.txt" 2>/dev/null) || v=""
    if [ -z "$v" ]; then
      bad "[FCU 快检] $p 取值失败（参数服务未就绪）"
      gfail=1
      continue
    fi
    if awk -v x="$v" 'BEGIN{d = x < 0 ? -x : x; exit !(d > 0.008)}'; then
      bad "[FCU 快检] $p=$v 超带 |v|≤0.008——QGC 重校陀螺后再起栈"
      gfail=1
    else
      echo "  [FCU 快检] ✓ $p=$v（带 |v|≤0.008）"
    fi
  done
  for p in CAL_ACC0_XOFF CAL_ACC0_YOFF CAL_ACC0_ZOFF; do
    v=$(cat "p_$p.txt" 2>/dev/null) || v=""
    [ -n "$v" ] && echo "  [FCU 快检] ○ $p=$v（注记项，不拦）"
  done
  rm -f p_CAL_*.txt
  if [ "$gfail" != 0 ]; then
    bad "[FCU 快检] ✗ 未过——不起相机/VINS（先 QGC 重校）"
    exit 1
  fi
  echo "  [FCU 快检] ✓ 过——继续起相机/VINS"
  mark "飞控快检（6 参数并发）"
}

# ---------------------------------------------------------------- 3) VINS
phase_vins() {
  rosrun vins vins_node "$HOME/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml" \
    > "vins_$TS.log" 2>&1 &
  if wait_until 30 0.6 "VINS 出流（imu_propagate）" vins_streaming; then
    mark "VINS 出流（imu_propagate 已发布）"
  else
    warn "VINS 30s 未出流"
    echo "VINS_ODOM_STALL" >> "vins_hz_$TS.txt"
  fi
}

# ---------------------------------------------------------------- 4)+5) 桥与控制器
phase_bridge_and_ctrl() {
  rosrun vins_to_mavros vins_to_mavros_node > "v2m_$TS.log" 2>&1 &
  if wait_until 5 0.25 "vins_to_mavros 起来" v2m_running; then
    echo "✓ [4/6] vins_to_mavros 桥就绪（VINS 里程计→/mavros/vision_pose/pose）"
  else
    bad "[4/6] vins_to_mavros 未起"
  fi

  if px4ctrl_registered; then
    echo "✓ [5/6] px4ctrl 已在运行（跳过重复启动）"
  else
    roslaunch px4ctrl run_ctrl.launch > "px4ctrl_$TS.log" 2>&1 &
  fi

  local blob l rate
  blob=$(measure_rate 3 /vins_estimator/imu_propagate)
  l=$(topic_line "$blob" /vins_estimator/imu_propagate)
  rate=$(rate_of "$l")
  if num_gt "$rate" 0; then
    echo "✓ [3/6] VINS 就绪：里程计传播流(/vins_estimator/imu_propagate) ${rate}Hz"
    echo "average rate: $rate  (imu_propagate)" > "vins_hz_$TS.txt"
  else
    echo "VINS_ODOM_STALL" >> "vins_hz_$TS.txt"
  fi

  if wait_until 8 0.25 "px4ctrl 注册" px4ctrl_registered; then
    echo "✓ [5/6] px4ctrl 就绪（控制器，MANUAL 态待命）"
  else
    bad "[5/6] px4ctrl 未注册——健康门将拦截"
  fi
  mark "v2m + px4ctrl + imu_prop 测频"
}

# ---------------------------------------------------------------- 主流程
timer_start
phase_roscore
phase_mavros
phase_camera_launch      # 越早越好：与下面飞控块并行，VINS 起点就能吃到图
phase_imu_rc_rate
phase_fcu_quickcheck
CAMERA_OWNED=0           # 过了快检，相机归栈所有（cleanup 不再收）
phase_camera_ready
phase_vins
phase_bridge_and_ctrl

echo "✓ [6/6] 五件套进程清单: rs=$(pgrep -f rs_camera | awk 'NR==1') vins=$(pgrep -x vins_node | awk 'NR==1') v2m=$(pgrep -f vins_to_mavros | awk 'NR==1') mavros=$(pgrep -f 'mavros px4.launch' | awk 'NR==1') px4c=$(pgrep -f run_ctrl | awk 'NR==1') pln=$(pgrep -f ego_planner_node | awk 'NR==1')" | tee -a "$LOG"
echo "=== 2a reboot stack up $(date -Is)（v5 总耗时 $(elapsed_s)s）===" | tee -a "$LOG"
