#!/bin/bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径（信息级）
# 首飞轮脚本 v1.7（2026-11-06，+悬停 30s 单一来源）——收敛检查 → 倒计时 → 解锁起飞 → 0.8m 悬停监测
# v1→v1.1：悬停目标 0.5→0.8m（2026-10-22 用户指令）；目标高度参数化单源（HOVER_Z + 传给监测器）
# v1.1→v1.2（2026-10-22 深夜）：治"失败/Ctrl+C 后模式乱跳"（判读件 §四-1）——
#   ① 退出自动清 px4ctrl（trap INT/TERM/EXIT；armed=True 时不动=空中不解它）
#   ② 前置自愈：px4ctrl 未运行自动拉起（~/realflight_ctrl.sh start，多轮夜不破流程）
# v1.2→v1.3（2026-10-22）：病理带门加陀螺零偏 |Bgs|≤0.02 rad/s（真实静态≈0.0001，放宽200倍；
#   拦"带毒初始化"型——两晚毒 VINS 中该型可拦；激励爆发型的主拦截面仍是 px4ctrl 输入门）
# v1.3→v1.4（2026-10-22 用户令）：悬停到位判据 2s→30s 稳定窗；总监测上限 30s→75s（容纳稳定窗+爬升+余量）
# v1.4→v1.5（2026-10-22 用户令）：①总监测上限 75→120s ②悬停到位后自动发 LAND 自动降落（含落地闭锁
#   确认监测；取代教程"首日不自动 LAND"条款——用户明示；失败路径仍走 CH5 手动）
# 前提：栈已起（STACK READY）、飞机在地面静置、遥控器在手（CH5 拨低=立刻接管；CH6=kill 保险丝）
# 悬停高度来源：px4ctrl 参数 auto_takeoff_land/takeoff_height（ctrl_param_fpv.yaml，节点启动时读一次，当前 0.7）
# 用法：bash ~/realflight_round.sh        （真飞：带 10s 倒计时，Ctrl+C 取消）
#       bash ~/realflight_round.sh --dry  （演练：只跑检查并打印将执行的动作，不解锁不起飞）
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
DRY=0; [ "${1:-}" = "--dry" ] && DRY=1
HOVER_Z=0.7
HOVER_S=30        # 2026-11-06 用户令：悬停稳定窗 30s（单一来源，传给监测器）

# v1.2 退出清场：未解锁时带走 px4ctrl（防残留抢模式）；解锁中（空中）不动它
ctrl_stop_safe() {
  # 2026-11-07 审查修正：--dry 承诺"只检查不动作"，但原来退出时照样停 px4ctrl。
  # 后果：先跑 dry 做飞前检查、再跑任务 B -> px4ctrl 已经被停了，任务 B 直接崩。
  # （今晚实测三次 px4ctrl 死亡全部对上是跑 dry 的时刻：04:23 / 05:45 / 05:51）
  if [ "${DRY:-0}" = "1" ]; then
    echo "[演练] 退出不停 px4ctrl（dry 模式只检查不动作）"
    return 0
  fi
  timeout 5 rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "armed: True" && return 0
  bash ~/realflight_ctrl.sh stop >/dev/null 2>&1
}
trap ctrl_stop_safe INT TERM EXIT

echo "===== 首飞轮 v1.7（悬停目标 ${HOVER_Z}m，稳定 ${HOVER_S}s 后自动降落）====="
[ $DRY = 1 ] && echo "[演练模式] 只检查不动作"

# ---------- [1/5] 前置断言 ----------
rostopic list >/dev/null 2>&1 || { echo "✗ ROS master 不在线——先起栈 bash ~/realflight_stack.sh"; exit 1; }
rosnode list 2>/dev/null | grep -qx "/vins_estimator" || { echo "✗ vins_node 未运行——先起栈或跑重启脚本"; exit 1; }
if ! rosnode list 2>/dev/null | grep -qx "/px4ctrl"; then
  echo "  px4ctrl 未运行——自动拉起"
  bash ~/realflight_ctrl.sh start || { echo "✗ px4ctrl 拉起失败——先起栈"; exit 1; }
fi

# v1.5->v1.6（2026-11-06）：固化 IMU 高速率请求。
# /mavros/imu/data_raw 由 PX4 的 HIGHRES_IMU(105) 驱动，默认只有 50 Hz；
# 而 set_message_interval 是**运行时**状态，飞控一重启就回到 50 —— 前几天"能跑 200Hz"
# 是之前某次请求留下的，从未被脚本固化（NUC 重启后就掉了，实测 49.9Hz）。
# 50Hz 下 RLS 的 35-45ms 推力配对量化误差 ±10ms，推力快变时会变成 ~3% 模型误差。
bash ~/set_imu_rate.sh || { echo "✗ IMU 速率设置失败（见上方提示）——先解决再飞"; exit 1; }
H=$(rosparam get /px4ctrl/auto_takeoff_land/takeoff_height 2>/dev/null)
[ "$H" = "$HOVER_Z" ] || { echo "✗ px4ctrl takeoff_height=$H（需 $HOVER_Z）——改 ctrl_param_fpv.yaml 后重启栈"; exit 1; }
timeout 5 rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "armed: False" \
  || { echo "✗ 已解锁或状态未知——异常，人工检查"; exit 1; }
echo "  ✓ [1/5] 前置过：栈件在位（VINS/px4ctrl/高度参数 ${HOVER_Z}m）、未解锁"
# F-3-prime (2026-10-22 判读v5): FSM 卡死守卫——022120/024542/004708 三轮 TK 发令
# 未解锁事故根因=px4ctrl FSM 卡 AUTO_HOVER（解锁态）静默忽略 TAKEOFF（只在 MANUAL_CTRL
# 处理）。非 MANUAL_CTRL 且未解锁 → 自动重启 px4ctrl（注意：RC 模式开关在悬停位时重启
# 会再入 AUTO_HOVER——复位失败时提示拨到手动位）。
FSM_NOW=$(timeout 4 rostopic echo -n 1 /debugPx4ctrl/fsm_state 2>/dev/null | sed -n 's/^data: *//p' | tr -d '"' | head -1)
if ! echo "$FSM_NOW" | grep -q "^MANUAL_CTRL"; then
  echo "  ✗ px4ctrl FSM 卡在 [${FSM_NOW%% *}]——TAKEOFF 会被静默忽略，自动重启 px4ctrl"
  bash ~/realflight_ctrl.sh stop >/dev/null 2>&1; sleep 2
  bash ~/realflight_ctrl.sh start >/dev/null 2>&1; sleep 3
  FSM_NOW=$(timeout 4 rostopic echo -n 1 /debugPx4ctrl/fsm_state 2>/dev/null | sed -n 's/^data: *//p' | tr -d '"' | head -1)
  echo "$FSM_NOW" | grep -q "^MANUAL_CTRL" \
    && echo "  ✓ [F-3'] FSM 已复位 MANUAL_CTRL" \
    || { echo "  ✗ [F-3'] 仍非 MANUAL_CTRL——请把遥控器模式开关拨到手动位后重跑（px4ctrl 启动时按 RC 定初态）"; exit 1; }
fi
if timeout 4 rosnode list 2>/dev/null | grep -qE "ego_planner|traj_server"; then
  echo "    （ego 在位，地图已随 VINS 同源[重启脚本联动]——悬停轮不用它，航线轮直接可用）"
else
  echo "    （ego 未在位——悬停轮可继续；航线轮前须起规划器）"
fi

# ---------- [2/5] VINS 收敛检查（与重启脚本同款四级，只验证不重启） ----------
echo "--- [2/5] VINS 收敛检查 ---"
timeout 6 rostopic echo -n 1 --noarr /vins_estimator/imu_propagate >/dev/null 2>&1 \
  || { echo "  ✗ 无出流（未初始化？）——先跑重启脚本"; exit 1; }
echo "  ✓ 出流（初始化完成）"
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
rospy.init_node("round_conv_check", anonymous=True, disable_signals=True)
rospy.Subscriber("/vins_estimator/odometry", Odometry, cb, queue_size=20)
rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, cbp, queue_size=100)
time.sleep(dur)
with lock:
    ms = list(msgs); n_p = nprop[0]; tp0 = tprop0[0]
fails = []
hz_o = len(ms) / dur
span_p = (time.monotonic() - tp0) if tp0 is not None else dur
hz_p = n_p / span_p if span_p > 0 else 0.0
print("  频率门: odom %.1fHz(≥8)  imu_prop %.1fHz(≥40)" % (hz_o, hz_p))
if hz_o < 8: fails.append("odom %.1f<8Hz" % hz_o)
if hz_p < 40: fails.append("prop %.1f<40Hz" % hz_p)
bad = 0
for m in ms:
    p, q, w = m.pose.pose.position, m.pose.pose.orientation, m.twist.twist.linear
    if not all(math.isfinite(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w,w.x,w.y,w.z)): bad += 1
print("  数值健全: finite %d/%d" % (len(ms)-bad, len(ms)))
if bad: fails.append("非有限值 %d 条" % bad)
if ms:
    xs=[m.pose.pose.position.x for m in ms]; ys=[m.pose.pose.position.y for m in ms]; zs=[m.pose.pose.position.z for m in ms]
    rng = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    print("  静置判定: 8s 位置极差 %.3fm(≤0.15)" % rng)
    if rng > 0.15: fails.append("位置极差 %.3fm>0.15（非静置？）" % rng)
else:
    fails.append("odom 零消息")
if fails:
    print("  ✗ " + "；".join(fails)); sys.exit(1)
print("  ✓ 收敛三查过"); sys.exit(0)
PYEOF
[ $? = 0 ] || { echo "✗ 收敛未过——禁飞"; exit 1; }

# ---------- [2.5/5] 姿态一致性门（2026-11-05）：VINS vs PX4 不一致 -> 自动重启 VINS 重新初始化 ----------
# 根因（20261105_003830 实测）：VINS 初始化后 pitch 偏 +2.0deg（加速度计真值 0.08deg、PX4 -0.2deg），
# px4ctrl 按 VINS 的"竖直"生成推力方向 -> 整机斜 2deg 起飞 -> 9.8*sin(2)=0.34m/s^2 -> 1.1m 漂移。
# 该偏差每次初始化不同（前后三次实测 -0.54/-0.75/+1.90deg），只能起飞前把关。
echo "--- [2.5/5] 姿态一致性（VINS vs PX4；不合格自动重启 VINS，最多 3 次）---"
ATT_OK=0
for ATT_TRY in 1 2 3; do
  ATT_OUT=$(python3 ~/sitl_realmachine/att_gate.py 2>&1)
  echo "$ATT_OUT" | sed 's/^/  /'
  # PASS(<0.5deg) 与 WARN(0.5-1.0deg) 都放行（WARN 打印漂移预期）；只有 FAIL(>=1.0deg) 重启 VINS
  if echo "$ATT_OUT" | grep -q "ATT_GATE: PASS"; then ATT_OK=1; break; fi
  if echo "$ATT_OUT" | grep -q "ATT_GATE: WARN"; then ATT_OK=1; break; fi
  if [ $ATT_TRY -lt 3 ]; then
    echo "  ✗ 姿态不合格（第 $ATT_TRY 次）——自动重启 VINS 重新初始化"
    bash ~/realflight_vins_restart.sh >/dev/null 2>&1 || { echo "  ✗ VINS 重启失败——禁飞"; exit 1; }
    sleep 3
  fi
done
[ $ATT_OK = 1 ] || { echo "✗ 连续 3 次姿态不合格——禁飞（查相机是否被碰/外参是否被改）"; exit 1; }
echo "  ✓ [2.5/5] 姿态一致，允许继续"
VL=$(ls -t ~/sitl_realmachine/vins_*.log ~/sitl_realmachine/*/vins_*.log 2>/dev/null | head -1)
if [ -n "$VL" ]; then
  sleep 2
  med() { sort -g | awk '{a[NR]=$1} END{if(NR==0)exit; if(NR%2)print a[(NR+1)/2]; else printf "%.6g",(a[NR/2]+a[NR/2+1])/2}'; }
  BASMED=$(grep -o '|Bas|=[0-9.e+-]*' "$VL" | cut -d= -f2 | tail -20 | med)
  COSTMED=$(grep -o 'final_cost=[0-9.e+-]*' "$VL" | cut -d= -f2 | tail -20 | med)
  BGSMED=$(grep -o '|Bgs|=[0-9.e+-]*' "$VL" | cut -d= -f2 | tail -20 | med)
  if [ -n "$BASMED" ] && [ -n "$COSTMED" ] && [ -n "$BGSMED" ]; then
    echo "  病理带: |Bas|=$BASMED(≤0.8)  |Bgs|=$BGSMED(≤0.02)  cost=$COSTMED(≤1e4)"
    awk "BEGIN{exit !($BASMED<=0.8 && $BGSMED<=0.02 && $COSTMED<=1e4)}" && echo "  ✓ 病理带内" \
      || { echo "  ✗ 病理带超限——禁飞（若 cost 正常=初始化抽签：跑重启脚本换牌后再来）"; exit 1; }
  else echo "  ⚠ 日志暂无 Bas/Bgs/cost 行——不判失败，建议开盯盘人工复核"; fi
fi

# ---------- [3/5] 倒计时 ----------
echo "--- [3/5] 10 秒后解锁起飞（Ctrl+C 取消）---"
echo "    口诀：CH5 拨低=立刻接管；彻底失控才 CH6；<13.2V 立即手动降"
for i in 10 9 8 7 6 5 4 3 2 1; do echo "    $i ..."; sleep 1; done
if [ $DRY = 1 ]; then
  echo "[演练] 到此为止——真跑将执行：发布 TAKEOFF → px4ctrl 自动解锁 → 爬升至 ${HOVER_Z}m 悬停 → 脚本监测到位"
  exit 0
fi

# ---------- [4/5] 解锁+起飞 ----------
# px4ctrl 收到 TAKEOFF 后自行调解锁服务（PX4CtrlFSM:944）并爬升到 takeoff_height；发布保持 8s 足够触发
echo "--- [4/5] 发布 TAKEOFF ---"
nohup rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 1" >/dev/null 2>&1 &
PUB=$!
sleep 8; kill $PUB 2>/dev/null
A=0
for i in $(seq 1 10); do
  timeout 3 rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "armed: True" && { A=1; break; }
  sleep 1
done
[ $A = 1 ] && echo "  ✓ 已解锁" || { echo "  ✗ 10s 未见解锁——px4ctrl 未响应，人工检查（遥控器预备）"; exit 1; }

# ---------- [5/5] 爬升监测（VINS z 到目标±0.15 稳 30 秒） ----------
echo "--- [5/5] 爬升监测（z 目标 ${HOVER_Z}m，到位判据=稳定 ${HOVER_S}s，总上限 120s）---"
python3 - "$HOVER_Z" "$HOVER_S" <<'PYEOF'
import sys, time
import rospy
from nav_msgs.msg import Odometry
target = float(sys.argv[1]); lo, hi = target - 0.15, target + 0.15
STABLE_S = float(sys.argv[2])   # 单一来源：脚本顶部 HOVER_S（2026-11-06 用户令 30s）
CAP_S = 120.0     # v1.5: 总监测上限（用户令 75→120s）
rospy.init_node("round_z_monitor", anonymous=True, disable_signals=True)
st = {"z": None, "t_ok": 0.0, "t0": time.monotonic()}
def cb(m):
    st["z"] = m.pose.pose.position.z
rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, cb, queue_size=5)
while time.monotonic() - st["t0"] < CAP_S and not rospy.is_shutdown():
    z = st["z"]
    if z is not None:
        print("\r    z=%.3f m   " % z, end="", flush=True)
        if lo <= z <= hi:
            if st["t_ok"] == 0.0:
                st["t_ok"] = time.monotonic()
            elif time.monotonic() - st["t_ok"] >= STABLE_S:
                print("\n  ✓ 悬停到位 z=%.3fm（稳定 %.0fs，目标 %.2fm）" % (z, STABLE_S, target))
                sys.exit(0)
        else:
            st["t_ok"] = 0.0
    time.sleep(0.2)
print("\n  ✗ %.0fs 未到位（最后 z=%s）——CH5 预备接管，肉眼判断" % (CAP_S, st["z"]))
sys.exit(1)
PYEOF
if [ $? = 0 ]; then
  if [ "${HOLD_FOR_GOAL:-0}" = "1" ]; then
    # 2026-11-07（审查）：这个分支已废弃。它把"单轮验证"和"任务飞行"混在一个脚本里，
    # 且提示语是旧的（0.5m / 等 RViz 目标 / 手动 land）。任务飞行现在有独立入口。
    echo "✗ HOLD_FOR_GOAL 已废弃：任务飞行请用  bash ~/realflight_mission.sh auto" >&2
    echo "  本脚本只做「悬停 N 秒 → 自动降落」这一件事。" >&2
    exit 2
  fi
  echo "===== 悬停到位（稳定 30s）→ 自动降落（v1.5 用户令；CH5 随时可接管）====="
  nohup rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  PUB2=$!
  sleep 8; kill $PUB2 2>/dev/null
  D=0
  for i in $(seq 1 60); do
    timeout 3 rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "armed: False" && { D=1; break; }
    sleep 1
  done
  [ $D = 1 ] && echo "  ✓ 已落地闭锁——本轮完成（自动降落）" || { echo "  ⚠ 60s 未确认闭锁——CH5 拨低手动接管降落！"; exit 1; }
else
  echo "===== ⚠ 未确认到位——不要离人；降落：CH5 拨低手动缓降（失败路径不自动降）====="
  exit 1
fi
