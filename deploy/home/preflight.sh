#!/bin/bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径（信息级）
# preflight.sh -- px4ctrl 飞行前闸门（2026-11-06 顾问）
#
# 为什么要有它：代码改了但没在 NUC 上编译过，就飞 = 拿飞机试编译。
# 本脚本把"能不能飞"变成机器判据，任何一项不过就 NO-GO。
#
# 用法:  ~/preflight.sh
# 退出码: 0=GO  1=NO-GO

set -uo pipefail
FAIL=0
ok()   { printf "  \033[32m[ OK ]\033[0m %s\n" "$*"; }
bad()  { printf "  \033[31m[FAIL]\033[0m %s\n" "$*"; FAIL=$((FAIL+1)); }
warn() { printf "  \033[33m[WARN]\033[0m %s\n" "$*"; }
sec()  { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

# 注意：ROS 的 setup.bash 内部引用了未定义变量，在 set -u 下会直接把脚本打死
# （症状：一行输出都没有、exit 1）。所以 source 期间必须临时关掉 -u。
set +u
source /opt/ros/noetic/setup.bash >/dev/null 2>&1
source "$HOME/catkin_ws/devel/setup.bash" >/dev/null 2>&1
set -u

# ---------------------------------------------------------------- 1 编译
sec "1 编译（源码 vs 二进制一致性）"
NODE="$HOME/catkin_ws/devel/.private/px4ctrl/lib/px4ctrl/px4ctrl_node"
TBIN="$HOME/catkin_ws/devel/.private/px4ctrl/lib/px4ctrl/test_ctrl_core"
SRC_NEW=$(find "$HOME/catkin_ws/src/px4ctrl/src" -newer "$NODE" -name '*.cpp' -o -newer "$NODE" -name '*.h' 2>/dev/null | head -5)
if [ -n "$SRC_NEW" ]; then
  bad "src/ 有文件比 px4ctrl_node 新，必须先编译："
  echo "$SRC_NEW" | sed 's/^/         /'
else
  ok "src/ 不比节点二进制新"
fi
# 测试文件只影响测试二进制，不影响飞行节点 —— 分开比，否则永远误报
if [ -x "$TBIN" ]; then
  TST_NEW=$(find "$HOME/catkin_ws/src/px4ctrl/test" -newer "$TBIN" -name '*.cpp' 2>/dev/null | head -5)
  if [ -n "$TST_NEW" ]; then
    bad "test/ 有文件比测试二进制新（单测结果不可信）："
    echo "$TST_NEW" | sed 's/^/         /'
  else
    ok "test/ 不比测试二进制新"
  fi
fi
if [ -x "$HOME/catkin_ws/devel/.private/px4ctrl/lib/px4ctrl/px4ctrl_node" ]; then
  ok "px4ctrl_node 存在"
else
  bad "px4ctrl_node 缺失"
fi

# ---------------------------------------------------------------- 2 单测
sec "2 单测（必须全绿）"
TDIR="$HOME/catkin_ws/devel/.private/px4ctrl/lib/px4ctrl"
TOT=0; FAILED=0
for t in "$TDIR"/test_*; do
  [ -x "$t" ] || continue
  n=$(timeout 60 "$t" 2>&1 | grep -oP '(?<=PASSED  \] )\d+' | head -1)
  if [ -z "$n" ]; then
    bad "$(basename "$t") 未通过"; FAILED=$((FAILED+1)); n=0
  else
    TOT=$((TOT+n))
  fi
done
if [ "$FAILED" -eq 0 ]; then ok "全部通过，共 $TOT 例"; else bad "$FAILED 个测试程序失败"; fi
# 2026-11-06：期望用例数从源码数出来，不再写死（写死 = 下次加测试就漏检）
EXPECT=$(cat "$HOME"/catkin_ws/src/px4ctrl/test/test_*.cpp 2>/dev/null | grep -c '^TEST(')
if [ -n "$EXPECT" ] && [ "$TOT" -lt "$EXPECT" ]; then
  bad "用例数 $TOT < 源码里的 $EXPECT（有测试没编进来，或二进制是旧的）"
else
  ok "用例数 $TOT >= 源码 $EXPECT"
fi

# ---------------------------------------------------------------- 3 模式与参数
sec "3 控制模式与参数"
MODEOUT=$(~/"ctrl_mode.sh" 2>/dev/null)
echo "$MODEOUT" | sed 's/^/       /'
EN=$(echo "$MODEOUT" | grep -oP '(?<=ctrl_v2.enabled     = )\w+')
HP=$(echo "$MODEOUT" | grep -oP '(?<=hover_percentage    = )[0-9.]+')
if [ "$EN" = "True" ]; then
  ok "v2 已打开（增益/限幅锁在 ctrl_core.h）"
  # 0.46 以下：I_need 会超过 i_lim=2.943 -> 积分饱和、起飞拖到 7 s 以上甚至飞不起来
  # 0.62 以上：冷启偏高 -> 峰值会顶到 z_peak 门
  awk -v h="$HP" 'BEGIN{ if (h<0.46 || h>0.62) exit 1 }'     && ok "hover_percentage=$HP 在设计带 [0.46,0.62]"     || bad "hover_percentage=$HP 出带 [0.46,0.62]（<0.46 积分饱和；>0.62 冲高）"
else
  bad "v2 未打开（legacy 是 P-only，已知无法稳定悬停）"
fi

# ---------------------------------------------------------------- 4 消息/节点
sec "4 消息定义与节点"
if rosmsg show quadrotor_msgs/Px4ctrlDebug 2>/dev/null | grep -q "i_z"; then
  ok "Px4ctrlDebug 含 i_z（积分可观测）"
else
  bad "Px4ctrlDebug 缺 i_z —— 判读会缺关键量"
fi
if rosnode list 2>/dev/null | grep -qx "/px4ctrl"; then ok "/px4ctrl 在线"; else bad "/px4ctrl 不在线"; fi

# ---------------------------------------------------------------- 5 传感器
sec "5 传感器链路"
rate() { timeout 6 rostopic hz "$1" 2>&1 | grep -m1 "average rate" | grep -oP '[0-9.]+' | head -1; }
ST=$(timeout 6 rostopic echo -n1 --noarr /mavros/state 2>/dev/null)
V=$(echo "$ST" | grep -m1 connected | grep -oP '(True|False)')
A=$(echo "$ST" | grep -m1 armed | grep -oP '(True|False)')
[ "$V" = "True" ] && ok "mavros 已连 FCU" || bad "mavros 未连 FCU"
# 三态：读不到 != 已解锁。原来读不到会被误报成"已解锁"，是脚本自己的假阳性。
if [ -z "$A" ]; then
  bad "读不到 /mavros/state.armed（栈没起或 mavros 没连 FCU）"
elif [ "$A" = "False" ]; then
  ok "未解锁（安全）"
else
  bad "**已解锁**！不要在这个状态下跑 preflight"
fi
R=$(rate /mavros/rc/in);        [ -n "$R" ] && ok "RC 在线 ${R} Hz" || bad "RC 无数据（px4ctrl 会停在等 RC 的门上）"
IQ=$(rate /mavros/imu/data);     [ -n "$IQ" ] && ok "imu/data(姿态) ${IQ} Hz" || bad "imu/data 无数据（姿态来源）"
IR=$(rate /mavros/imu/data_raw); [ -n "$IR" ] && { [ "${IR%%.*}" -ge 190 ] && ok "imu/data_raw(加速度) ${IR} Hz" || bad "data_raw ${IR} Hz < 190 —— 补发：~/set_imu_rate.sh （511/105/4000us；飞控重启即回 50，栈脚本 [1a] 会自动发，单独重启 mavros 时要补）"; } || bad "data_raw 无数据（加速度来源）"
O=$(rate /vins_estimator/imu_propagate); [ -n "$O" ] && ok "VINS odom ${O} Hz" || bad "VINS odom 无数据（VINS 未初始化）"
C=$(rate /camera/infra1/image_rect_raw);  [ -n "$C" ] && ok "相机 infra1 ${C} Hz" || bad "相机无图像"

# ---------------------------------------------------------------- 6 判据
sec "6 判据锁"
cd "$HOME/sitl_sim" 2>/dev/null || { bad "缺 ~/sitl_sim"; }
if [ -f tools/judge_acceptance.py ] && [ -f tools/acceptance_v1.json ]; then
  H=$(python3 -c "import hashlib;print(hashlib.sha256(open('tools/acceptance_v1.json','rb').read()).hexdigest())")
  E=$(grep -oP '(?<=ACCEPTANCE_SHA256 = ")[0-9a-f]{64}' tools/judge_acceptance.py)
  [ "$H" = "$E" ] && ok "判据 sha256 与执行器一致 ${H:0:8}…" || bad "判据被改过（json $H vs 脚本 $E）"
else
  bad "判据文件缺失"
fi

sec "7 工具链"
[ -x "$HOME/make_meta.py" ] && ok "make_meta.py 可用（每轮生成 meta.json）" || warn "缺 ~/make_meta.py（G2/G7 要手写 meta）"
[ -x "$HOME/ctrl_mode.sh" ] && ok "ctrl_mode.sh 可用" || bad "缺 ~/ctrl_mode.sh"

# ---------------------------------------------------------------- 8 px4ctrl 视角的 IMU 速率
sec "8 px4ctrl 实际吃到的 IMU 速率（不是 rostopic 视角）"
if rosnode list 2>/dev/null | grep -qx "/px4ctrl"; then
  # px4ctrl 在 feed_accel 里每 5 s 自报一次（ROS_INFO -> /rosout）。
  # 终端看不到是因为 INFO 走 stdout 被块缓冲，但 /rosout 一定有，且会被录进 bag。
  ACR=$(timeout 8 rostopic echo -n40 /rosout 2>/dev/null | grep -a "imu accel rate" | tail -1 | grep -oP "rate = \K[0-9.]+")
  if [ -z "$ACR" ]; then
    warn "还没看到 px4ctrl 的自报（节点刚起 <5s，或还没订上 data_raw）"
  elif awk -v a="$ACR" 'BEGIN{exit !(a+0 >= 100)}'; then
    ok "px4ctrl 自报 ${ACR} Hz（RLS 40ms 窗口约 $(awk -v a="$ACR" 'BEGIN{printf "%.1f", a*0.04}') 个样本）"
  else
    bad "px4ctrl 自报只有 ${ACR} Hz —— 补发 ~/set_imu_rate.sh"
  fi
else
  warn "/px4ctrl 不在线，跳过（先起栈）"
fi

# ---------------------------------------------------------------- 9 RC 通道硬校验
# 借鉴 flight_v1/flight_mission.py 的 validate_rc_channels()：
# "遥控器开着"不等于"开关在正确档位"。这一条能在起飞前拦住一次废飞。
sec "9 RC 通道硬校验（借鉴 flight_v1）"
# 2026-11-07 用户裁定：起栈阶段（RC_CHECK=0）不卡摇杆/开关位置——
#   起栈只关心"栈是否健康"；任务脚本（takeoff/auto）才要求四杆居中 + CH5/CH6 档位，
#   由 flight_mission.py 的 validate_rc_channels() 在起飞前硬卡。
if [ "${RC_CHECK:-1}" = "0" ]; then
  echo "  [SKIP] RC 通道硬校验（RC_CHECK=0：起栈放行，起飞时仍硬卡）"
else
# 2026-11-08（用户令④）：RC 判据只留一份 —— 调 flight_v1/rc_gate.py（读契约 runtime.rc）
RC_RC=0
python3 "$HOME/sitl_realmachine/flight_v1/rc_gate.py" || RC_RC=$?
[ "$RC_RC" -eq 0 ] && ok "RC 通道校验过" || bad "RC 通道校验不过 —— 摆好摇杆/开关再飞"
fi

# ---------------------------------------------------------------- 10 接线审计
# 借鉴 flight_v1/check_interfaces.py：不只"话题有数据"，还要"谁订了谁"对。
# px4ctrl 必须同时订 imu/data(姿态 50Hz) 与 imu/data_raw(加速度 200Hz) ——
# 这是 2026-11-06 双订阅改动的运行时证据。
sec "10 接线审计（借鉴 check_interfaces.py）"
RC_IF=0
python3 - <<'PYEOF' || RC_IF=$?
import subprocess, sys
def subs(t):
    try:
        out = subprocess.run(["rostopic", "info", t], capture_output=True,
                             text=True, timeout=6).stdout
    except Exception:
        return False
    tail = out.split("Subscribers:")[-1]
    return "/px4ctrl" in tail
a, b = subs("/mavros/imu/data"), subs("/mavros/imu/data_raw")
if a and b:
    print("  [ OK ] px4ctrl 同时订阅 imu/data(姿态) 与 imu/data_raw(加速度)")
    sys.exit(0)
print("  [FAIL] px4ctrl 未同时订阅两个 IMU 话题: data=%s data_raw=%s" % (a, b))
sys.exit(1)
PYEOF
[ "$RC_IF" -eq 0 ] && ok "IMU 双订阅接线在" || bad "IMU 双订阅接线缺失（v2 会退化成 50Hz 加速度）"

# ---------------------------------------------------------------- §11 电池
# 2026-11-07（独立审计指出）：preflight 原来不查电池，而 /mavros/battery 实测 0.0V/-1%。
# 这里**只告警不拦**：0.0V 可能是"没装电池"也可能是"PM 遥测没配"，两者都要人判断，
# 硬门会把正常状态误判成 NO-GO（D 类误杀）。有电压时按 4S 带做提示。
sec "§11 电池"
BATT=$(timeout 6 rostopic echo -n1 /mavros/battery/voltage 2>/dev/null | head -1)
if [ -z "$BATT" ]; then
  printf "  [33m[WARN][0m /mavros/battery 无数据 —— 必须用外部电压表确认 >=14.0V 再飞
"
elif awk -v v="$BATT" "BEGIN{exit !(v+0 <= 0.1)}"; then
  printf "  [33m[WARN][0m 电池电压读数 %.2fV（≈0）—— 多半是 PM 遥测未配；必须用外部电压表确认 >=14.0V 再飞
" "$BATT"
elif awk -v v="$BATT" "BEGIN{exit !(v+0 < 14.0)}"; then
  printf "  [33m[WARN][0m 电池电压 %.2fV < 14.0V —— 偏低，建议换电池
" "$BATT"
else
  printf "  [ OK ] 电池电压 %.2fV >= 14.0V
" "$BATT"
fi

# ---------------------------------------------------------------- 结论
sec "结论"
if [ "$FAIL" -eq 0 ]; then
  printf "  \033[32m*** GO ***\033[0m  可以飞。当前飞行程序悬停 30s -> G3(60s窗) 会判 NOT_EVALUABLE，G1/G2/G6 正常。\n"
  exit 0
else
  printf "  \033[31m*** NO-GO ***\033[0m  %d 项不过，先修。\n" "$FAIL"
  exit 1
fi
