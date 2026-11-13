#!/bin/bash
# ⚠ 内部件：唯一正式起栈入口 = ~/realflight_stack.sh（清场/五件套/规划器/转接/RViz/健康门/preflight）。
#    直调本脚本会绕过健康门与 preflight；除调试外不要单独使用。
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径，shellcheck 无法跟随（信息级）
# T1 v11.34 2a v2（2026-10-21 加速版）— 旧机重上电复苏: 按台账正源命令重起五件全栈 (栈保留, 供 2b/2d)
# v3（2026-10-21 二改，用户指令"先查飞控再起 VINS"）：mavros 连上后立即做飞控快检
#   （连接/解锁态/模式/陀螺三轴标定硬门 |v|≤0.008、加计注记），坏了直接拦下不起相机/VINS
#   ——坏 IMU 会毒化 VINS 初始化。电池项硬件损坏禁读（用户 10-18 裁定），仍手动计时管理。
# v1→v2 加速：固定 sleep → 事件轮询（上限保底不变性）——
#   roscore 5s→≤8s 轮询；mavros 15s→connected 轮询≤20s；相机 14s→infra1 出流轮询≤20s；
#   VINS 12s→imu_propagate 出流轮询≤30s；v2m 3s→2s；px4ctrl 6s→节点轮询≤8s；
#   规划器占位死等 8s 删除（launch 本就注释勘误在案）。
#   证据 tee / 软检查语义不变（硬门仍在 realflight_stack.sh 4/5、5/5）。
# 正源: realmachine_2a_bench_p1.sh 的起栈序 + 02a_mavros_boot.log 的 fcu_url + 1b 的 rs640 显式版
set -o pipefail
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
OUT=~/sitl_realmachine/09_reboot_stack_2026-10-09
mkdir -p "$OUT" && cd "$OUT" || { echo "无法进入 $OUT（磁盘满/权限？）"; exit 1; }
# 2026-11-10（用户批准）：本脚本只能由 realflight_stack.sh 调用。
# 直调时若已有 master，会在别人的栈上再起一套五件套（同名节点互覆）。
if [ "${STACK_FROM_ORCHESTRATOR:-0}" != "1" ] && rostopic list >/dev/null 2>&1; then
  echo "✗ 检测到已有 ROS master：请走 ~/realflight_stack.sh（本脚本仅允许其调用）"
  exit 1
fi
TS=$(date +%H%M%S)
LOG=boot_$TS.log
echo "=== 2a reboot stack start $(date -Is) ===" | tee "$LOG"

# 等话题出现一条消息（$1=话题 $2=上限秒）；0=等到
wait_msg() {
  local t=0
  while [ $t -lt "$2" ]; do
    timeout 3 rostopic echo -n1 --noarr "$1" >/dev/null 2>&1 && return 0
    sleep 1; t=$((t+4))
  done
  return 1
}

# 0) roscore
roscore >/dev/null 2>&1 &
W=0; until rostopic list >/dev/null 2>&1; do sleep 0.5; W=$((W+1)); [ $W -ge 16 ] && break; done
echo "✓ [0/6] roscore 就绪（${W}x0.5s）"

# 1) mavros (FCU=/dev/pixhawk:921600 正源)
roslaunch mavros px4.launch fcu_url:=/dev/pixhawk:921600 > mavros_$TS.log 2>&1 &
W=0; until timeout 2 rostopic echo -n1 --noarr /mavros/state 2>/dev/null | grep -q "connected: True"; do
  sleep 1; W=$((W+3)); [ $W -ge 20 ] && { echo "WARN mavros 20s 未连接"; break; }
done
timeout 5 rostopic echo -n1 --noarr /mavros/state/connected 2>/dev/null | tail -1 | tee mavros_connected_$TS.txt
CONN=0
for i in 1 2 3; do
  timeout 4 rostopic echo -n1 --noarr /mavros/state 2>/dev/null | grep -q "connected: True" && { CONN=1; break; }
  sleep 1
done
[ "$CONN" = 1 ] && echo "✓ [1/6] mavros 已连接飞控（/dev/pixhawk:921600）" || echo "✗ [1/6] mavros 未连接——后续 IMU 提频/快检将拦截"

# 1a) IMU 提频 200Hz（2026-10-22 用户令；历史：10-09 实测 203Hz 后回退 50Hz=主线纪律裁定非技术否决，现重启）
# 511=SET_MESSAGE_INTERVAL, 105=HIGHRES_IMU(=/mavros/imu/data_raw 源), 4000us（实测选档：5000us→170Hz 成批欠发/4000us→200.6Hz 稳态/2000us→222Hz 超需，2026-10-22 三档亲测）
# 坑（09-28 记录在案）：mavcmd 无 ACK、链路建立前发即丢——故放在 connected 确认后+发完实测复核
for i in 1 2 3; do
  rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 >/dev/null 2>&1
  sleep 2
  IMU_HZ=$(timeout 6 rostopic hz /mavros/imu/data_raw 2>/dev/null | awk '/average rate/{v=$3} END{printf "%.0f", v}')
  [ "${IMU_HZ:-0}" -ge 190 ] && break
  echo "  [1a] IMU 提频第${i}次未达（/mavros/imu/data_raw 实测 ${IMU_HZ:-无}Hz），重发 511"
done

# 1a2) RC_CHANNELS 提频（2026-11-06 新增，用户 RC 已开但 /mavros/rc/in 无数据）
# 实测：PX4 默认**不转发** RC_CHANNELS(65)，/mavros/rc/in 恒空 ->
#       px4ctrl 的 rc_is_received() 永远 false -> 卡在 "Waiting for RC"，
#       起栈脚本因此判 STACK FAIL（这不是 RC 没开，是没让它转发）。
# 511=SET_MESSAGE_INTERVAL, 65=RC_CHANNELS, 20000us=50Hz。设完实测 45.6Hz。
for i in 1 2 3; do
  rosrun mavros mavcmd long 511 65 20000 0 0 0 0 0 >/dev/null 2>&1
  sleep 2
  RC_HZ=$(timeout 6 rostopic hz /mavros/rc/in 2>/dev/null | awk '/average rate/{v=$3} END{printf "%.0f", v}')
  [ "${RC_HZ:-0}" -ge 20 ] && break
  echo "  [1a2] RC 提频第${i}次未达（/mavros/rc/in 实测 ${RC_HZ:-无}Hz），重发 511@65"
done
if [ "${RC_HZ:-0}" -ge 20 ]; then
  echo "✓ [1a2/6] RC 流：/mavros/rc/in 实测 ${RC_HZ}Hz（511@65@20000us）"
else
  echo "✗ [1a2/6] RC 流仍无数据（${RC_HZ:-无}Hz）——遥控器是否上电/对频？px4ctrl 会卡在 Waiting for RC"
fi
if [ "${IMU_HZ:-0}" -ge 190 ]; then
  echo "✓ [1a/6] IMU 提频：/mavros/imu/data_raw（VINS 的 IMU 输入流）实测 ${IMU_HZ}Hz——目标 200/门限 190，每栈自动发 511@4000µs"
else
  echo "✗ [1a/6] IMU 提频失败：/mavros/imu/data_raw 实测 ${IMU_HZ:-无}Hz <190——STACK FAIL（流率未生效，禁飞）"
  exit 1
fi

# 1b) 飞控快检（起相机/VINS 前——2026-10-21 用户指令：先查飞控再起 VINS）
ST=$(timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null)
echo "$ST" | grep -q "connected: True" || { echo "FCU_QUICK_FAIL: mavros 未连接——检查飞控供电/串口"; exit 1; }
echo "$ST" | grep -q "armed: False"   || { echo "FCU_QUICK_FAIL: 飞控处于解锁态——禁止起栈"; exit 1; }
echo "$ST" | grep "mode:" | head -1 | sed 's/^/  [FCU 快检] /'
# 参数表显式同步（mavros 连接后异步拉取，秒读会拿到全 0 假值——最多重试 10s）
PV=""
for i in $(seq 1 10); do
  PV=$(rosservice call /mavros/param/get "param_id: 'CAL_GYRO0_XOFF'" 2>/dev/null | awk '/real:/{print $2}')
  [ -n "$PV" ] && [ "$PV" != "0.0" ] && [ "$PV" != "0" ] && break
  rosservice call /mavros/param/pull "{}" >/dev/null 2>&1; sleep 1
done
[ -n "$PV" ] && [ "$PV" != "0.0" ] && [ "$PV" != "0" ] || echo "  [FCU 快检] ⚠ 参数表 10s 未同步（快检读值可疑，以末尾预检为准）"
GFAIL=0
for p in CAL_GYRO0_XOFF CAL_GYRO0_YOFF CAL_GYRO0_ZOFF; do
  V=$(rosservice call /mavros/param/get "param_id: '$p'" 2>/dev/null | awk '/real:/{print $2}')
  if [ -z "$V" ]; then echo "  [FCU 快检] ✗ $p 取值失败（参数服务未就绪）"; GFAIL=1; continue; fi
  if awk -v x="$V" 'BEGIN{d=x<0?-x:x; exit !(d>0.008)}'; then
    echo "  [FCU 快检] ✗ $p=$V 超带 |v|≤0.008——QGC 重校陀螺后再起栈"; GFAIL=1
  else
    echo "  [FCU 快检] ✓ $p=$V（带 |v|≤0.008）"
  fi
done
for p in CAL_ACC0_XOFF CAL_ACC0_YOFF CAL_ACC0_ZOFF; do
  V=$(rosservice call /mavros/param/get "param_id: '$p'" 2>/dev/null | awk '/real:/{print $2}')
  [ -n "$V" ] && echo "  [FCU 快检] ○ $p=$V（注记项，不拦）"
done
[ $GFAIL = 0 ] && echo "  [FCU 快检] ✓ 过——继续起相机/VINS" || exit 1
# 注：陀螺/加计读值依赖 mavros 参数表拉取完成——实测秒读会拿到全 0 假值，
#     上面的取值带 pull 重试（见下）；快检为早期预警，末尾预检为权威门。
# [IMU 率史料三行] ①10-09 用户令 511→203Hz 实测通（r2 批 202-222Hz 全优）；②10-10 晨停用（当时记因"压垮全家桶/链饿死 202→129→0Hz"——
#   同日凌晨翻案定案：真根因=FC USB(cdc_acm) 断链重枚举+统计假象（断流时间入分母），与频率无关，SITL 走 UDP 无此病互证）；
#   ③2026-10-22 用户重启裁定 200Hz（三档实测选 4000µs），实现于上方 §1a。备考旧命令：rosservice call /mavros/cmd/command "{broadcast: false, command: 511, confirmation: 0, param1: 105.0, param2: 4000.0, ...}"
echo -n "  [留档] IMU 流率复测(/mavros/imu/data_raw): " | tee imu_rate_$TS.txt
timeout 10 rostopic hz /mavros/imu/data_raw -w 30 2>/dev/null | grep -m1 average | tee -a imu_rate_$TS.txt

# 2) realsense：infra/depth 848x480@30（2026-11-11 用户令；与 1280 同水平视场 89.5°，
#    双目跟踪 22ms < 33ms 帧预算；depth 必须与 IR 同档，跨档 depth 不出帧）
#    RGB 关、align 关：均无消费方（align 产物自 11-08 健康门改造后无人用）
roslaunch realsense2_camera rs_camera.launch infra_width:=848 infra_height:=480 infra_fps:=30 depth_width:=848 depth_height:=480 depth_fps:=30 enable_infra1:=true enable_infra2:=true enable_depth:=true align_depth:=false enable_color:=false > rs_$TS.log 2>&1 &
wait_msg /camera/infra1/image_rect_raw 20 || echo "WARN 相机 20s 未见 infra1"
CAM_HZ=$(timeout 6 rostopic hz /camera/infra1/image_rect_raw -w 5 2>/dev/null | awk '/average rate/{v=$3} END{print v}')
echo "camera_rate=$CAM_HZ" | tee rs_hz_$TS.txt
[ -n "$CAM_HZ" ] && echo "✓ [2/6] 相机就绪：infra1 左目图像流(/camera/infra1/image_rect_raw) ${CAM_HZ}Hz（双目 848×480 + 深度 848×480 @30）" || echo "✗ [2/6] 相机无流——健康门将拦截"

# 3) VINS (实机 config v0)
rosrun vins vins_node ~/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml > vins_$TS.log 2>&1 &
wait_msg /vins_estimator/imu_propagate 30 || echo "WARN VINS 30s 未出流" | tee -a vins_hz_$TS.txt
OUT=$(timeout 10 rostopic hz /vins_estimator/imu_propagate -w 20 2>/dev/null | grep average | head -1)
echo "$OUT" | tee vins_hz_$TS.txt
VINS_HZ=$(echo "$OUT" | awk '/average rate/{print $3}')
[ -n "$VINS_HZ" ] && echo "✓ [3/6] VINS 就绪：里程计传播流(/vins_estimator/imu_propagate) ${VINS_HZ}Hz" || echo VINS_ODOM_STALL | tee -a vins_hz_$TS.txt

# 4) vins_to_mavros
rosrun vins_to_mavros vins_to_mavros_node > v2m_$TS.log 2>&1 &
sleep 2
pgrep -f vins_to_mavros >/dev/null && echo "✓ [4/6] vins_to_mavros 桥就绪（VINS 里程计→/mavros/vision_pose/pose）" || echo "✗ [4/6] vins_to_mavros 未起"

# 5) px4ctrl
if rosnode list 2>/dev/null | grep -qx "/px4ctrl"; then
  echo "✓ [5/6] px4ctrl 已在运行（跳过重复启动）"
else
  roslaunch px4ctrl run_ctrl.launch > px4ctrl_$TS.log 2>&1 &
fi
W=0; until rosnode list 2>/dev/null | grep -qx "/px4ctrl"; do sleep 1; W=$((W+1)); [ $W -ge 8 ] && { echo "WARN px4ctrl 8s 未注册"; break; }; done
rosnode list 2>/dev/null | grep -qx "/px4ctrl" && echo "✓ [5/6] px4ctrl 就绪（控制器，MANUAL 态待命）" || echo "✗ [5/6] px4ctrl 未注册——健康门将拦截"

# 6) planner
# [2026-10-09 勘误] launch 旧机不存在(T1 v11.36 C-5) 永久注释: roslaunch planner single_run_in_exp.launch > planner_$TS.log 2>&1 &
# [v2] 原此处死等 8s 删除（realflight_stack.sh 3/5 另起 ego_planner 并事件等待）

echo "✓ [6/6] 五件套进程清单: rs=$(pgrep -f rs_camera | head -1) vins=$(pgrep -x vins_node | head -1) v2m=$(pgrep -f vins_to_mavros | head -1) mavros=$(pgrep -f 'mavros px4.launch' | head -1) px4c=$(pgrep -f run_ctrl | head -1) pln=$(pgrep -f ego_planner_node | head -1)" | tee -a "$LOG"
echo "=== 2a reboot stack up $(date -Is) ===" | tee -a "$LOG"
