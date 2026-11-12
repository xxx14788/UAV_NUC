#!/bin/bash
# rehearsal.sh —— 按实飞流程彩排一遍（**不解锁、不起飞**）
#
# 用户要求（2026-11-07）：设计模拟测试，按实飞流程走一遍，确认所有脚本没问题。
#
# 流程与实飞完全一致，只在"发布 TAKEOFF"这一行之前拦截：
#   1) 栈在位（master + 节点 + 规划器地图非空）
#   2) preflight.sh                -> 期望 *** GO ***
#   3) VINS 盯盘（只读，取 8s）
#   4) 录包 start -> 4s -> stop    -> 期望 bag 生成
#   5) 任务A 彩排：realflight_round.sh --dry      -> 到 10s 倒计时为止
#   6) 任务B 彩排：realflight_mission.sh auto --dry -> 栈检查+开录+[DRY]拦截+停录
#
# 用法：bash ~/rehearsal.sh 2>&1 | tee /tmp/rehearsal_$(date +%H%M%S).log
set -u
# ROS 的 setup.bash 在 set -u 下会因未定义变量直接退出（1.ros_distro.sh: ROS_DISTRO），
# source 期间必须临时关掉 -u。
set +u
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash 2>/dev/null || true
set -u

PASS=0; FAIL=0; SKIP=0
declare -a RESULT
ok()   { PASS=$((PASS+1)); RESULT+=("  [PASS] $*"); echo "  [PASS] $*"; }
bad()  { FAIL=$((FAIL+1)); RESULT+=("  [FAIL] $*"); echo "  [FAIL] $*"; }
skip() { SKIP=$((SKIP+1)); RESULT+=("  [SKIP] $*"); echo "  [SKIP] $*"; }
hr()   { echo; echo "======== $* ========"; }

hr "0. 前置：不得已解锁"
ARMED=$(timeout 6 rostopic echo -n1 /mavros/state 2>/dev/null | awk '/armed:/{print $2; exit}')
case "${ARMED:-unknown}" in
  False) ok "未解锁（armed=False）" ;;
  True)  bad "已解锁！彩排立即中止（真实飞行中）"; exit 1 ;;
  *)     bad "读不到 /mavros/state（armed=${ARMED:-unknown}）—— 栈没起？"; exit 1 ;;
esac

hr "1. 栈在位"
rostopic list >/dev/null 2>&1 && ok "ROS master 可达" || bad "ROS master 不可达"
for n in /px4ctrl /vins_estimator /mavros /drone_0_ego_planner_node /drone_0_traj_server /planner_camera_pose_relay; do
  rosnode list 2>/dev/null | grep -qx "$n" && ok "节点 $n" || bad "节点缺 $n"
done
OCC=$(timeout 14 python3 - <<'PYOCC' 2>/dev/null
import rospy
from sensor_msgs.msg import PointCloud2
rospy.init_node("reh_occ", anonymous=True)
w = []
rospy.Subscriber("/drone_0_ego_planner_node/grid_map/occupancy_inflate",
                 PointCloud2, lambda m: w.append(m.width))
rospy.sleep(6)
print(w[-1] if w else 0)
PYOCC
)
if [ "${OCC:-0}" -gt 0 ] 2>/dev/null; then ok "规划器地图已填充（膨胀点 ${OCC}）"
else bad "规划器地图为空（膨胀点 0）—— 避障/天花板不会生效"; fi

hr "2. preflight.sh"
OUT=$(timeout 120 bash ~/preflight.sh 2>&1 | sed 's/\x1b\[[0-9;]*m//g'); RC=${PIPESTATUS[0]}
echo "$OUT" | grep -E "GO \*\*\*|NO-GO|\[FAIL\]" | tail -6
[ "$RC" = 0 ] && ok "preflight GO（exit 0）" || bad "preflight NO-GO（exit $RC）"

hr "3. VINS 盯盘（只读 8s）"
VOUT=$(timeout 8 bash ~/realflight_vins_watch.sh 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | head -20)
if [ -n "$VOUT" ]; then
  echo "$VOUT" | head -8 | sed 's/^/    /'
  ok "VINS 盯盘有输出"
else
  skip "VINS 盯盘无输出（可能日志未就绪）"
fi

hr "4. 录包 start -> 4s -> stop"
bash ~/sitl_realmachine/flight_v1/flight.sh record start >/tmp/reh_rec.log 2>&1 && ok "record start" || bad "record start 失败"
sleep 4
bash ~/sitl_realmachine/flight_v1/flight.sh record stop >/tmp/reh_rec_stop.log 2>&1 && ok "record stop" || bad "record stop 失败"
BAG=$(find ~/flight_data -name "*.bag" -newermt "-3 minutes" 2>/dev/null | head -1)
if [ -n "$BAG" ] && [ -s "$BAG" ]; then
  SZ=$(du -m "$BAG" | cut -f1); ok "bag 生成 ${SZ}MB  $BAG"
else bad "没找到 bag"; fi

hr "5. 任务A 彩排（realflight_round.sh --dry）"
AOUT=$(timeout 200 bash ~/realflight_round.sh --dry 2>&1 | sed 's/\x1b\[[0-9;]*m//g'); ARC=${PIPESTATUS[0]}
echo "$AOUT" | grep -E "演练|ATT_GATE: (PASS|FAIL)|病理带|✓ \[|✗" | tail -8 | sed 's/^/    /'
[ "$ARC" = 0 ] && ok "任务A 彩排 exit 0（到倒计时为止）" || bad "任务A 彩排 exit $ARC"

hr "6. 任务B 彩排（realflight_mission.sh auto --dry）"
BOUT=$(timeout 260 bash ~/realflight_mission.sh auto --dry 2>&1 | sed 's/\x1b\[[0-9;]*m//g'); BRC=${PIPESTATUS[0]}
echo "$BOUT" | grep -E "栈件在位|\[DRY\]|任务完成|✗|录包" | tail -10 | sed 's/^/    /'
if [ "$BRC" = 0 ] && echo "$BOUT" | grep -q "\[DRY\] 本次"; then
  ok "任务B 彩排 exit 0，且在发布 TAKEOFF 前拦截"
else
  bad "任务B 彩排异常（exit $BRC，未见 [DRY] 拦截）"
fi

hr "汇总"
printf "%s\n" "${RESULT[@]}"
echo
echo "  PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
if [ "$FAIL" -eq 0 ]; then
  echo "  *** 彩排全过：按实飞流程走通，且全程未解锁 ***"
  exit 0
else
  echo "  *** 彩排有 $FAIL 项失败 —— 先修再飞 ***"
  exit 1
fi
