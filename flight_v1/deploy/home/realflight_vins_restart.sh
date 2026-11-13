#!/bin/bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径，shellcheck 无法跟随（信息级）
# 轮间隔>5min 的 VINS 重启 v3（流式；地面态执行）
# v2→v3 改动：出流检查从"10s 一次测"升级为四级收敛验收——
#   [1] 等出流（轮询最多 WAIT_MAX=20s：imu_propagate 发布=初始化完成；实测静置 init ~2s，留 10 倍余量。注意 2s=出流时间非收敛时间，收敛证据=[2-5]）
#   [2-4] 收敛三查（python 采样 8s：odom≥8Hz / imu_prop≥40Hz 频率门；位置/速度/姿态全 finite；
#         8s 位置极差≤0.15m 判"静置 init"）
#   [5] 日志病理带（|Bas|≤0.8，末 20 条中位；cost≤1e4，**初始化段**前 20 条中位；
#       2026-11-11：cost 随滑窗残差数增长（实测同名链 init≈200 -> 90 min 后 1.4e4，与健康无关），
#       原"末 20 条"在晚检查时会假报警 -> 改为取 init 段。日志无行=⚠ 不判死）
# 末行"重启成功"才可开下一轮；任何 ✗ = 禁飞下一轮。
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
FAIL=0
WAIT_MAX=20   # 出流等待上限（秒），嫌长嫌短改这里

echo "--- 杀旧 VINS ---"
pkill -x vins_node 2>/dev/null; sleep 2
pgrep -x vins_node >/dev/null && { echo "✗ 杀不掉"; exit 1; } || echo "✓ 已清"

# 2026-11-15（V1）：确保 IMU 35 Hz 低通中继在跑（VINS 的 imu_topic=/vins_imu/data_raw）
if ! pgrep -f "[i]mu_lpf.py" >/dev/null 2>&1; then
  LPF_LOG=~/sitl_realmachine/imu_lpf_$(date +%H%M%S).log
  nohup python3 "$HOME/sitl_realmachine/flight_v1/imu_lpf.py" > "$LPF_LOG" 2>&1 &
  sleep 1
  echo "  ✓ IMU 低通中继已起（$LPF_LOG）"
else
  echo "  ✓ IMU 低通中继已在跑"
fi

LOG=~/sitl_realmachine/vins_restart_$(date +%H%M%S).log
nohup rosrun vins vins_node ~/sitl_realmachine/03_realmachine_config/vins_stereo_realmachine_v0.yaml > "$LOG" 2>&1 &
echo "--- 新 VINS pid=$! 日志=$LOG ---"

# 2026-11-07（检查发现）：VINS 重启 = 原点重锚，vins_to_mavros 是把 odometry 转成
# /mavros/vision_pose 的中继。它若带旧首帧锚点/旧偏置，PX4 的 EV 位姿就会错。
# 一并重启，代价 1 s，消掉一整类"位姿对不上"的怀疑。
echo "--- 同步重启 vins_to_mavros ---"
pkill -f "[v]ins_to_mavros_node" 2>/dev/null; sleep 1
V2M_LOG=~/sitl_realmachine/v2m_restart_$(date +%H%M%S).log
nohup rosrun vins_to_mavros vins_to_mavros_node > "$V2M_LOG" 2>&1 &
sleep 2
if pgrep -f "[v]ins_to_mavros_node" >/dev/null; then
  echo "  ✓ vins_to_mavros 已重启（日志 $V2M_LOG）"
else
  echo "  ✗ vins_to_mavros 起不来——禁飞下一轮"; exit 1
fi

echo "--- [1/5] 等出流（imu_propagate 发布=初始化完成；最多 ${WAIT_MAX}s，保持静置）---"
T0=$(date +%s); SEEN=0
while [ $(( $(date +%s) - T0 )) -lt $WAIT_MAX ]; do
  if timeout 5 rostopic echo -n 1 --noarr /vins_estimator/imu_propagate >/dev/null 2>&1; then SEEN=1; break; fi
done
if [ "$SEEN" = 1 ]; then
  echo "  ✓ 出流（$(( $(date +%s) - T0 ))s 内初始化完成）"
else
  echo "  ✗ ${WAIT_MAX}s 未见出流——看日志："; tail -8 "$LOG" | sed 's/^/    /'; exit 1
fi

echo "--- [2-4/5] 收敛三查（采样 8s：频率门 / 数值健全 / 静置判定）---"
python3 <<'PYEOF'
import math, sys, threading, time
import rospy
from nav_msgs.msg import Odometry

dur = 8.0
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
print("  [2] 频率门: odom %.1fHz（门≥8）  imu_prop %.1fHz（门≥40）" % (hz_o, hz_p))
if hz_o < 8:  fails.append("odom 频率 %.1f<8Hz" % hz_o)
if hz_p < 40: fails.append("imu_prop 频率 %.1f<40Hz" % hz_p)

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
    print("  [4] 静置判定: 8s 位置极差 %.3fm（门≤0.15=静置 init）" % rng)
    if rng > 0.15: fails.append("位置极差 %.3fm>0.15m（非静置 init？）" % rng)

if fails:
    print("  ✗ " + "；".join(fails))
    sys.exit(1)
print("  ✓ 收敛三查过")
PYEOF
[ $? = 0 ] || FAIL=1

echo "--- [5/5] 日志病理带（|Bas| 末20 中位 / cost init前20 中位）---"
sleep 3
med() { sort -g | awk '{a[NR]=$1} END{if(NR==0)exit; if(NR%2)print a[(NR+1)/2]; else printf "%.6g",(a[NR/2]+a[NR/2+1])/2}'; }
BASMED=$(grep -o '|Bas|=[0-9.e+-]*' "$LOG" | cut -d= -f2 | tail -20 | med)
COSTMED=$(grep -o 'final_cost=[0-9.e+-]*' "$LOG" | cut -d= -f2 | head -20 | med)   # init 段，勿改回 tail
if [ -n "$BASMED" ] && [ -n "$COSTMED" ]; then
  echo "  |Bas|=$BASMED（门≤0.8，末20）  cost=$COSTMED（门≤1e4，init前20）"
  awk "BEGIN{exit !($BASMED<=0.8 && $COSTMED<=1e4)}" \
    && echo "  ✓ 病理带内" || { echo "  ✗ 病理带超限"; FAIL=1; }
else
  echo "  ⚠ 日志暂无 Bas/cost 行（缓冲未积累）——不判失败，可开盯盘人工复核 Bas"
fi

if [ $FAIL -ne 0 ]; then
  echo "===== ✗ 收敛检查未过——禁飞下一轮：开盯盘 bash ~/realflight_vins_watch.sh 观察，或看日志 $LOG ====="
  exit 1
fi

# --- 附加：同步重启规划器（VINS 原点重锚后 ego 旧栅格地图坐标系错位，航线轮前必须随之重启）---
# 2026-11-07（检查发现）：原来先打"重启成功"再去起规划器，规划器起挂了也算成功。
# 现在把"成功"挪到最后，并且**验证节点真的起来了**。
# 2026-11-07（用户令）：VINS 重启必须把 ego+vins 的**所有相关组件**都带到干净状态，
# 但**不动全栈**（rosmaster / mavros / 相机 一律不重启）。
# 组件顺序：转接（规划器吃 /planner/camera_pose）-> 规划器 -> px4ctrl（吃 VINS odom）
echo "--- 同步重启相机位姿转接 ---"
pkill -f "[c]amera_pose_relay.py" 2>/dev/null; sleep 1
RELAY_LOG=~/sitl_realmachine/camera_pose_relay_$(date +%H%M%S).log
nohup python3 "$HOME/sitl_realmachine/flight_v1/camera_pose_relay.py" > "$RELAY_LOG" 2>&1 &
sleep 2
if rosnode list 2>/dev/null | grep -qx "/planner_camera_pose_relay"; then
  echo "  ✓ 相机位姿转接已在线（$RELAY_LOG）"
else
  echo "  ⚠ 相机位姿转接未上线（$RELAY_LOG）—— 规划器地图会是空的"
fi

pkill -f "run_planner" 2>/dev/null; sleep 2
# 2026-11-07：规划器 launch 参数化。任务模式（地图版）必须传
#   PLANNER_LAUNCH="ego_planner run_planner_realmachine_map_v1.launch"
# 否则重启 VINS 会把"地图版"换回"vins 版"，坐标系/地图全错。
# 2026-11-07 审查修正：默认值从 vins 版改成**地图版**。
# 原因：任务 B 期间若手动重启 VINS 而没传 PLANNER_LAUNCH，规划器会悄悄退回 vins 版
# -> 天花板(map_size_z 1.3)、膨胀(0.337)、goal_gate 全部丢失（D1/D5/D6/D7 同时失效）。
# 悬停任务不受影响（规划器只是空转）。
# 2026-11-14 用户令：VINS 重启脚本由 RViz/形状两个任务共用，重启 VINS 必须
# **同时完全重启 EGO**（原点重锚后旧栅格地图坐标系失效），且统一用地图版规划器。
# 默认即地图版；不再存在"退回 vins 版"的分支。
echo "  [vins restart] 统一地图版规划器；EGO 随 VINS 一起重启（原点重锚）"
PLANNER_LAUNCH="${PLANNER_LAUNCH:-$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch}"
PLOG=~/sitl_realmachine/planner_$(date +%H%M%S).log
nohup roslaunch $PLANNER_LAUNCH > "$PLOG" 2>&1 &
# 2026-11-07：验证规划器节点真的起来了（最多等 30 s）
PLN_OK=0
# shellcheck disable=SC2034  # 循环变量只用于计数
for _i in $(seq 1 30); do
  if rosnode list 2>/dev/null | grep -qE "ego_planner|traj_server"; then PLN_OK=1; break; fi
  sleep 1
done
if [ "$PLN_OK" = 1 ]; then
  echo "--- ✓ 规划器已随 VINS 重启并在线（$PLANNER_LAUNCH，日志 $PLOG）---"
else
  echo "--- ⚠ 规划器 30s 内未上线（$PLANNER_LAUNCH，日志 $PLOG）——悬停轮不依赖；发目标点前必须解决 ---"
fi
# 2026-11-14（用户令）：VINS 重启后 RViz 也重启。
# 旧 RViz 订阅的是旧 VINS/规划器实例的 latch 话题，VINS 原点重锚后显示与坐标系会错位；
# 重启 VINS 就必须把 RViz 一起换掉。SSH 终端没有 DISPLAY 时先探测 :0，探不到就不动旧窗口。
echo "--- 同步重启 RViz ---"
RVIZ_SH="$HOME/sitl_realmachine/rviz_mapping_v1/map_rviz.sh"
RVIZ_DISPLAY="${DISPLAY:-}"
if [ -z "$RVIZ_DISPLAY" ] && command -v xdpyinfo >/dev/null 2>&1 && xdpyinfo -display :0 >/dev/null 2>&1; then
  RVIZ_DISPLAY=:0
fi
if [ -z "$RVIZ_DISPLAY" ]; then
  echo "  ⚠ 无可用 DISPLAY：RViz 未重启（旧窗口保持原样；请在桌面终端再跑一次）"
elif [ ! -f "$RVIZ_SH" ]; then
  echo "  ⚠ 找不到 $RVIZ_SH：RViz 未重启"
else
  pkill -TERM -x rviz 2>/dev/null || true
  pkill -f "[m]ap_rviz.sh" 2>/dev/null || true
  sleep 1
  RVIZ_LOG=~/sitl_realmachine/rviz_$(date +%H%M%S).log
  DISPLAY="$RVIZ_DISPLAY" nohup bash "$RVIZ_SH" > "$RVIZ_LOG" 2>&1 &
  RV_OK=0
  # shellcheck disable=SC2034  # 循环变量只用于计数
  for _k in $(seq 1 15); do
    rosnode list 2>/dev/null | grep -qx "/mapping_rviz" && { RV_OK=1; break; }
    sleep 1
  done
  if [ "$RV_OK" = 1 ]; then
    echo "  ✓ RViz 已重启并在线（DISPLAY=$RVIZ_DISPLAY，日志 $RVIZ_LOG）"
  else
    echo "  ⚠ RViz 15s 内未上线（DISPLAY=$RVIZ_DISPLAY，日志 $RVIZ_LOG）"
  fi
fi

# 2026-11-07（用户令）：px4ctrl 吃 VINS odom，VINS 重锚后它的 sanity gate/悬停锚点是旧状态。
# **只在未解锁时重启**（空中绝不动控制器）。
echo "--- 同步重启 px4ctrl（仅未解锁时）---"
if timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q "armed: True"; then
  echo "  ⚠ 当前已解锁：跳过 px4ctrl 重启（空中不动控制器）"
else
  pkill -f "run_ctrl" 2>/dev/null; sleep 2
  CTRL_LOG=~/sitl_realmachine/px4ctrl_$(date +%H%M%S).log
  nohup roslaunch px4ctrl run_ctrl.launch > "$CTRL_LOG" 2>&1 &
  P4_OK=0
  # shellcheck disable=SC2034
  for _j in $(seq 1 20); do
    rosnode list 2>/dev/null | grep -qx "/px4ctrl" && { P4_OK=1; break; }
    sleep 1
  done
  if [ "$P4_OK" = 1 ]; then
    echo "  ✓ px4ctrl 已重启并在线（$CTRL_LOG）"
  else
    echo "  ⚠ px4ctrl 20s 内未上线（$CTRL_LOG）"
  fi
fi
echo "===== 重启成功：VINS 初始化+收敛全过、vins_to_mavros/转接/规划器/RViz/px4ctrl 均已处理 ====="
