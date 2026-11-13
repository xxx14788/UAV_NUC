#!/bin/bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径（信息级）
# 起栈与测试 v3（流式）——先全杀再干净起；每步打印实况；末行 STACK READY 才可飞
# v3.1 变更（2026-11-03，用户批准）：健康门加 **px4ctrl 活性门**——查 /debugPx4ctrl/fsm_state 是否有输出；
#   RC 未开时 px4ctrl 停在 "Waiting for RC"（节点仍在 rosnode list，原逻辑会假绿 STACK READY）。
# v4 变更（2026-11-07 用户令）：**起栈唯一入口收口**——
#   五件套 / 规划器 / 相机位姿转接 / RViz / 健康门 / preflight 全部只在本脚本启动；
#    任务脚本（flight.sh start）不再自己起任何进程。原 SKIP_PLANNER 参数化留下了
#    第二条起栈路径，已删除。RViz 默认开，无 DISPLAY（SSH）时软跳过。
# v2→v3 加速（2026-10-21 用户指令）：
#   稳定窗 sleep 110 → 等规划器节点出现(≤40s 轮询)+20s 最小稳定窗（相机曝光/病理带日志积累）
#   健康门三连：串行 12s×3 → 并行 8s；预检 python 双调用 → 单调用；清场等待 3+2 → 1.5+1
#   门限与判定语义零改动：深度≥15 / 左目≥20 / odom≥8Hz、PREFLIGHT GO、STACK READY
# v5（2026-11-14 用户令"起栈太慢，尽量并行，不动任务脚本"）：**门限/文案/唯一入口零改动**——
#   ① 3/5 段：规划器 + 相机位姿转接 + 轨迹回传**三件同时起**（原来中继/回传被 20s 挡在后面）；
#   ② 原 `sleep 20` 稳定窗 → **事件等待**（等"规划器节点+转接+回传"注册齐，下限 6s / 上限 20s）；
#      20s 死等在攒的东西（相机曝光/病理带）此时在 2a 里已经并行跑够了，判据一个没动；
#   ③ 4/5 健康门 ‖ px4ctrl 活性门 ‖ 5/5 预检 ‖ 占用采样 **四路并行**（原来 8+6+5+17s 串行），
#      各路输出先落临时文件再按原顺序打印——屏幕上读到的行和以前一模一样；
#   ④ 清场 `sleep 1.5 + sleep 1` → 0.1s 步长轮询 rosmaster 归零（上限 3s）；
#   ⑤ 每步打印 [+Xs] 分段计时。
#   实测依据：2026-11-14 01:03 那轮 2a 之后本脚本还花 58s（20s 死等 + 33s 串行门区）。
# v6（2026-11-14 第二轮，用户令"不要为快丢余量，不稳的步骤留 1~3s"）：**门限/文案仍然零改动**——
#   ① 门区（健康门/px4ctrl 活性门/预检/RViz DISPLAY 探测）**提前到 3/5 段并行**：
#      依据=三路只吃 2a 已起好的流，且 VINS 日志 |Bas| 从第 1 秒就 1e-6~2.5e-3、cost 250~620
#      （带 0.8 / 1e4，三个数量级余量）；另加 **sleep 2 稳定余量**避开三件 launch 的 exec 抖动。
#   ② 余量回补：px4ctrl 活性门上限 5s→**12s**（提前测量后 px4ctrl 才起 3~5s，给 RC 识别留余），
#      健康门仍 8s 窗口、6s 事件下限不变、预检的 5s 采样与 10s 重试不变。
#   ③ 清场 pkill 全部改括号模式（`[m]avros_node`）——普通词会连调用者 shell 行一起命中，
#      实测两次把自己所在的 ssh/wrapper 杀掉；契约两个 python 读合成**一次**。
#   ④ RViz 的 DISPLAY 探测从"PASS 后串行探 3 次（无 X 时 ~9s）"改为门区并行（每次 timeout 2）。
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
# 2026-11-10（用户批准）：全局起栈锁 —— 并发执行会产生两套五件套（同名节点互覆）。
# 实现用 PID 文件而不是 flock：flock 的 fd 会被本脚本拉起的子进程继承，
# 一旦起栈失败退出、子进程还活着，锁就永远不放（实测把自己的下一次起栈挡住了）。
LOCK="$HOME/sitl_realmachine/flight_v1/runtime/stack.lock"
mkdir -p "$(dirname "$LOCK")"
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "✗ 另一个起栈进程正在运行（PID $(cat "$LOCK")）"; exit 1
fi
echo $$ > "$LOCK"
# v5：分段计时 + 并行区临时目录（锁的 trap 里一并收）
T0MS=$(date +%s%3N)
el() { awk -v a="$T0MS" -v b="$(date +%s%3N)" 'BEGIN{printf "%.1f", (b-a)/1000}'; }
mark() { printf '[+%ss] %s\n' "$(el)" "$1"; }
RUND=$(mktemp -d)
trap 'rm -rf "$RUND"; rm -f "$LOCK"' EXIT
export STACK_FROM_ORCHESTRATOR=1

echo "===== 1/5 清场 $(date '+%T') ====="
# 2026-11-07（用户令收口时补的安全门）：清场会全杀；已解锁或正在录包时绝不允许。
if pgrep -x rosmaster >/dev/null 2>&1 || pgrep -x roscore >/dev/null 2>&1; then
  if timeout 5 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: True'; then
    echo "✗ 飞控已解锁——拒绝起栈（先落地、上锁）"; exit 1
  fi
fi
if ps -eo args= 2>/dev/null | grep -qE '^[^ ]*python[0-9.]* [^ ]*rosbag record'; then
  echo "✗ 正在录包——先正常结束录制（flight.sh record stop）再起栈"; exit 1
fi
FOUND=$( { pgrep -a -x rosmaster; pgrep -a -x vins_node; pgrep -af "mavros_node|realsense2_camera|run_planner|roslaunch"; } 2>/dev/null | grep -v realflight )
if [ -n "$FOUND" ]; then echo "发现残留："; echo "$FOUND" | sed 's/^/  杀 /'; else echo "无残留（干净）"; fi
pkill -x vins_node 2>/dev/null; pkill -x rosmaster 2>/dev/null; pkill -x roscore 2>/dev/null
# v6：全部改用括号模式（`[m]avros_node`）——`pkill -f 普通词` 会连**调用者的 shell 行**一起命中，
#     实测把自己所在的 ssh/wrapper 进程杀掉过（2026-11-14 复现两次）。
pkill -f "[m]avros_node" 2>/dev/null; pkill -f "[r]ealsense2_camera" 2>/dev/null
pkill -f "[r]un_planner" 2>/dev/null; pkill -f "[r]oslaunch" 2>/dev/null
pkill -f "[c]amera_pose_relay.py" 2>/dev/null; pkill -x rviz 2>/dev/null
# 2026-11-09（P0-6）：这两个原来漏杀 —— planned_path_pub 会成孤儿挡新实例；
# vins_to_mavros 是 rosrun 起的，`pkill -f roslaunch` 永远抓不到。
pkill -f "[p]lanned_path_pub.py" 2>/dev/null
pkill -f "[v]ins_to_mavros_node" 2>/dev/null
# 2026-11-10（用户批准）：地图工具节点不在五件套里，但会抢 /grid_map 话题与 CPU。
rosnode list 2>/dev/null | grep -qx /mapping_view && rosnode kill /mapping_view 2>/dev/null
# v5：原 `sleep 1.5 + sleep 1` 固定 2.5s → 0.1s 步长轮询（等它自己退，退不掉再 -9）
W=0; while pgrep -x rosmaster >/dev/null 2>&1 && [ $W -lt 15 ]; do sleep 0.1; W=$((W+1)); done
pkill -9 -x rosmaster 2>/dev/null
W=0; while pgrep -x rosmaster >/dev/null 2>&1 && [ $W -lt 20 ]; do sleep 0.1; W=$((W+1)); done
LEFT=$(pgrep -c -x rosmaster 2>/dev/null || true)
if [ "${LEFT:-0}" -eq 0 ]; then echo "✓ 清场毕（rosmaster 0 残留）"; else echo "✗ 仍残留 ${LEFT} 个 rosmaster——手动 ps 检查后重跑"; exit 1; fi
mark "1/5 清场"
echo "===== 2/5 起五件套主栈 $(date '+%T') ====="
bash ~/sitl_realmachine/realmachine_2a_reboot_stack.sh || { echo "✗ 主栈脚本失败——停（看上方自检输出哪条流没起来）"; exit 1; }
echo "✓ 五件套自检过（mavros/IMU/infra/VINS 四流，pid 行见上）"
mark "2/5 五件套"
echo "===== 3/5 起规划器 + 相机位姿转接 + 轨迹回传（三件同时起）====="
# v6：3/5 相位起点（事件等待的 6s 下限、门区的 2s 稳定余量都从这里算）
T3=$(date +%s)
# 2026-11-07（用户令）：唯一栈入口。规划器只在本脚本启动，任务脚本不再各起一份。
# 默认地图版（带天花板/膨胀/goal_gate）；需要换版本时传 PLANNER_LAUNCH。
PLANNER_LAUNCH="${PLANNER_LAUNCH:-$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch}"
PLOG=~/sitl_realmachine/planner_$(date +%H%M%S).log
nohup roslaunch $PLANNER_LAUNCH > "$PLOG" 2>&1 &
echo "规划器 pid=$! 日志=$PLOG（悬停不依赖它）"

# 规划器 pose_type=1(POSE_STAMPED) 必须吃 /planner/camera_pose，由 camera_pose_relay.py 提供。
# 转接缺失 -> 地图永远空（实测膨胀点 0）-> 看不到箱子、天花板也不生效。起栈时必起。
# 2026-11-09（P0-6）：判活必须问**当前 master**。pgrep 会把连着旧 master 的孤儿
# 当成"已在运行"，于是新栈缺节点（planned_path 事故的同形状）。
# v5：中继/回传原来排在 sleep 20 之后 —— 挪到与规划器同起（都不依赖规划器就绪）
if rosnode list 2>/dev/null | grep -qx "/planner_camera_pose_relay"; then
  echo "  相机位姿转接已在运行（当前 master 上，跳过）"
else
  pkill -f "[c]amera_pose_relay.py" 2>/dev/null; sleep 0.5
  RELAY_LOG=~/sitl_realmachine/camera_pose_relay_$(date +%H%M%S).log
  nohup python3 "$HOME/sitl_realmachine/flight_v1/camera_pose_relay.py" > "$RELAY_LOG" 2>&1 &
  echo "  相机位姿转接 pid=$! 日志=$RELAY_LOG（/vins_estimator/camera_pose -> /planner/camera_pose）"
fi

# 2026-11-08（方案 v2 C4）：健康门的深度话题**必须**等于规划器实际消费的那条边。
# P0 实测缺陷：原来查 /camera/aligned_depth_to_color/image_raw，而规划器吃的是
# /camera/depth/image_rect_raw —— 两条流都活着时假绿灯，规划器那条死了也照样 STACK READY。
# v6：话题与门槛合成**一次** python 调用（原来起两个进程读同一份 yaml）。
CONTRACT="$HOME/sitl_realmachine/flight_v1/contract/flight_contract.yaml"
read -r DEPTH_TOPIC DEPTH_MIN <<EOF
$(python3 - "$CONTRACT" <<'PYEOF'
import sys
topic, hz = '/camera/depth/image_rect_raw', 15.0
try:
    import yaml
    with open(sys.argv[1], encoding='utf-8') as fh:
        # 2026-11-11：深度门槛真正在 seams.depth.min_hz（原来读的 health_gate.min_hz 不存在）
        _d = yaml.safe_load(fh)
    topic = _d['seams']['depth']['topic'] or topic
    hz = _d.get('seams', {}).get('depth', {}).get('min_hz', hz)
except Exception:
    pass
print(topic, hz)
PYEOF
)
EOF
[ -n "$DEPTH_TOPIC" ] || DEPTH_TOPIC=/camera/depth/image_rect_raw
[ -n "$DEPTH_MIN" ] || DEPTH_MIN=10.0
echo "  深度门话题（读契约）= $DEPTH_TOPIC（门 ${DEPTH_MIN}Hz）"

# 2026-11-08（症状4，用户令）：轨迹回传 —— 选点后 RViz 要能看到"预期轨迹"。
if rosnode list 2>/dev/null | grep -qx "/planned_path_pub"; then
  echo "  轨迹回传已在运行（当前 master 上，跳过）"
else
  # 有同名进程但不在当前 master 上 = 孤儿，先杀再起
  pkill -f "[p]lanned_path_pub.py" 2>/dev/null; sleep 0.5
  PPLOG=~/sitl_realmachine/planned_path_$(date +%H%M%S).log
  nohup python3 "$HOME/sitl_realmachine/flight_v1/planned_path_pub.py" > "$PPLOG" 2>&1 &
  echo "  轨迹回传 pid=$! 日志=$PPLOG（/flight_v1/planned_path|executed_trail|goal_marker）"
fi

# ===== v6：门区（4/5 健康门 + px4ctrl 活性门 + 5/5 预检）**在这里就后台启动** =====
# 依据：这三路只吃 2a 已经起好的流（VINS odom / 相机 / mavros 参数），不依赖规划器；
#   而实测 VINS 日志 |Bas| 从第 1 秒就是 1e-6~2.5e-3、cost 250~620（带 0.8 / 1e4，三个数量级余量），
#   不需要"等日志积累 20s"。所以让它们与下面的"规划器就绪等待"并行跑。
# 排布：预检最慢（~13s，工具内部 5s 采样 + 6 次 mavparam）→ 立刻起；
#   健康门要靠 8s 窗口算率 → 留 2s 余量避开三件 launch 的 exec 抖动后再起（这 2s 同时计入 3/5 的 6s 下限）。
PASS=1
VL=$(ls -t ~/sitl_realmachine/*/vins_*.log ~/sitl_realmachine/vins_*.log 2>/dev/null | head -1)
(
  PASS_PF=1
  if [ -n "$VL" ]; then
    echo "  [vins-log] $VL"
    # 病理带就绪等待：冷启动初始化段 cost 天文数字/零偏=0（实测 1e29），初始化完成后恢复健康
    # （实测 ~388）——预检 120s 窗会被初始化脏数据污染。等尾部 400 条 cost 中位 <1e4（≤120s），
    # 就绪后用日志尾片喂预检（预检工具本体不动）。
    SETTLE=0; C=""
    while [ $SETTLE -lt 120 ]; do
      C=$(grep -o 'final_cost=[0-9.e+-]*' "$VL" | cut -d= -f2 | tail -400 | sort -g | awk '{a[NR]=$1} END{if(NR)print a[int(NR/2)+1]}')
      if [ -n "$C" ] && awk "BEGIN{exit !($C<1e4)}"; then break; fi
      sleep 5; SETTLE=$((SETTLE+5))
    done
    SLICE=""    # 2026-11-09: set -u 下"病理带未就绪"分支原来会 unbound variable 直接崩
    if [ -n "$C" ] && awk "BEGIN{exit !($C<1e4)}"; then
      echo "  ✓ 病理带就绪（尾部 cost 中位 $C，等待 ${SETTLE}s）"
      SLICE=/tmp/pf_slice_$$.log; tail -n 800 "$VL" > "$SLICE"
      PFLOG="$SLICE"
    else
      echo "  ✗ 120s 病理带未就绪（cost 尾部中位 ${C:-无数据}）——VINS 未收敛，禁飞"; PASS_PF=0
      PFLOG="$VL"
    fi
    PRE=$(python3 ~/sitl_realmachine/tools/t1_preflight_check_v1.py --vins-log "$PFLOG" 2>&1)
    echo "$PRE" | sed 's/^/  /'
    if echo "$PRE" | grep -q "PREFLIGHT GO"; then
      echo "  ✓ 预检 GO"
    else
      # 冷启动注册瞬态（首跑参数取值 None/流判 0，复跑即 GO）——10s 后重试一次，以重跑为准
      echo "  ⚠ 首跑 NO-GO（冷启动常见瞬态）——10s 后重试一次"
      sleep 10
      # 2026-11-11 修：重试前刷新日志切片（原来首跑后即删切片，重试必 no-data 必 NO-GO）
      [ -n "$SLICE" ] && [ -f "$SLICE" ] && tail -n 800 "$VL" > "$SLICE"
      PRE=$(python3 ~/sitl_realmachine/tools/t1_preflight_check_v1.py --vins-log "$PFLOG" 2>&1)
      echo "$PRE" | sed 's/^/  /'
      echo "$PRE" | grep -q "PREFLIGHT GO" && echo "  ✓ 预检 GO（重试后）" || { echo "  ✗ 预检 NO-GO——按上面打印项处理"; PASS_PF=0; }
    fi
    [ -n "$SLICE" ] && [ -f "$SLICE" ] && rm -f "$SLICE"
  else echo "  ✗ 未找到 VINS 日志"; PASS_PF=0; fi
  echo "$PASS_PF" > "$RUND/pf_pass"
) > "$RUND/pf" 2>&1 & P5=$!
# RViz 的 DISPLAY 探测也塞进来（原来串在 PASS 之后，SSH 无 X 时要连探 3 次 ~9s 才打印 STACK READY）
( for _d in :0 :1 :1001; do
    if DISPLAY=$_d timeout 2 xdpyinfo >/dev/null 2>&1; then echo "$_d" > "$RUND/disp"; break; fi
  done ) & P6=$!

sleep 2
echo "  [并行] 预检 + 健康门 + px4ctrl 活性门 已在后台启动（与规划器就绪等待并行）"
hz() { timeout 8 rostopic hz "$1" 2>/dev/null | awk '/average rate/{r=$3} END{print r}'; }
hz "$DEPTH_TOPIC" > "$RUND/depth" & P1=$!
hz "/camera/infra1/image_rect_raw" > "$RUND/infra1" & P2=$!
hz "/vins_estimator/odometry" > "$RUND/odom" & P3=$!
# px4ctrl 活性门（2026-11-03 用户批准）：节点注册 != 控制循环在跑。
# v6：5s → 12s 上限（有输出即返回，正常 <0.3s）；提前测量后 px4ctrl 才启动 ~3-5s，给足 RC 识别余量。
( timeout 12 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state >/dev/null 2>&1 && echo 1 > "$RUND/px4act" || echo 0 > "$RUND/px4act" ) & P4=$!

# ===== 3/5 的事件等待（v6：下限 6s 从 T3=规划器 launch 起算，上限 20s）=====
# 等的是 4/5 本来就要硬判的三件（规划器节点 / 转接节点 / 回传发布者）注册齐。
# 与上面的门区**并行**：门区先跑、这里隔 0.5s 轮一次，谁慢等谁。
while :; do
  REG=$(rosnode list 2>/dev/null)
  A=0; echo "$REG" | grep -qE "ego_planner|traj_server" && A=1
  B=0; echo "$REG" | grep -qx "/planner_camera_pose_relay" && B=1
  C=0; echo "$REG" | grep -qx "/planned_path_pub" && C=1
  EL3=$(( $(date +%s) - T3 ))
  if [ "$A$B$C" = "111" ] && [ $EL3 -ge 6 ]; then
    echo "  ✓ 规划器/转接/回传三件已注册（等 ${EL3}s）"; break
  fi
  [ $EL3 -ge 20 ] && { echo "  ⚠ 等 ${EL3}s 未齐（规划器=$A 转接=$B 回传=$C）——4/5 逐项判"; break; }
  sleep 0.5
done
mark "3/5 规划器+转接+回传就绪（$(( $(date +%s) - T3 ))s）"

# 地图是否真的被填起来（软告警：场地开阔时可能本来就空）
# v5：原 14s 一次性 rospy 采样（sleep 6）→ 轮询到首次非空（cap 12s），与门区并行，不占关键路径
( timeout 14 python3 - <<'PYOCC' > "$RUND/occ" 2>/dev/null
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
) & OCCPID=$!

wait $P1 $P2 $P3 $P4 $P5 $P6
mark "门区并行过（健康门/px4ctrl/预检/占用）"
echo "===== 4/5 健康门 + px4ctrl 活性门（三路已在 3/5 段并行跑完）$(date '+%T') ====="
# 2026-11-11：相机维持 30 fps（视觉不降流）；省流靠关 RGB + 录包压缩。
# 深度门槛读契约 seams.depth.min_hz=10，左目 20（30 fps 名义值）。
declare -A NAME=( [depth]=深度流:$DEPTH_MIN [infra1]=左目流:20 [odom]=VINS里程计:8 )
declare -A TOPIC=( [depth]=$DEPTH_TOPIC [infra1]=/camera/infra1/image_rect_raw [odom]=/vins_estimator/odometry )
for k in depth infra1 odom; do
  TH=${NAME[$k]##*:}
  V=$(cat "$RUND/$k" 2>/dev/null)
  if [ -n "$V" ] && awk "BEGIN{exit !($V>=$TH)}"; then echo "  ✓ ${NAME[$k]%:*} = ${V}Hz（门 ${TH}）[${TOPIC[$k]}]";
  else echo "  ✗ ${NAME[$k]%:*} 无流/过低 = ${V:-0}Hz < ${TH} [${TOPIC[$k]}]"; PASS=0; fi
done
# v6：一次 rosnode list 供三项判活用（原来 4 次，每次 ~0.3s）
REG=$(rosnode list 2>/dev/null)
if echo "$REG" | grep -qE "ego_planner|traj_server"; then
  echo "  ✓ 规划器节点在"
else
  echo "  ⚠ 规划器节点未见（悬停可继续；任务飞行会在 flight.sh start 的任务门硬判）——查 $PLOG"
fi
# 2026-11-07：没有转接 -> 地图永远空 -> 避障与天花板都不生效。硬门。
if echo "$REG" | grep -qx "/planner_camera_pose_relay"; then
  echo "  ✓ 相机位姿转接在（/planner/camera_pose）"
else
  echo "  ✗ 相机位姿转接缺失 —— 规划器地图会是空的（避障/天花板都不生效）"; PASS=0
fi
# 2026-11-09（P0-6）：轨迹回传也必须是硬门 —— 缺了 RViz 看不到预期轨迹，
# 而且事后判读会缺 /flight_v1/planned_path（两袋实飞就是这么丢的）。
if rostopic info /flight_v1/planned_path 2>/dev/null | grep -q "/planned_path_pub"; then
  echo "  ✓ 轨迹回传发布者在（/flight_v1/planned_path <- /planned_path_pub）"
else
  echo "  ✗ 轨迹回传发布者缺失 —— RViz 没有预期轨迹、录包也会缺该话题"; PASS=0
fi
# 地图是否真的被填起来（软告警：场地开阔时可能本来就空）—— 采样在 3/5 段就已并行跑
wait $OCCPID 2>/dev/null
OCC=$(cat "$RUND/occ" 2>/dev/null)
if [ "${OCC:-0}" -gt 0 ] 2>/dev/null; then
  echo "  ✓ 规划器地图已填充（膨胀点 ${OCC}）"
else
  echo "  ⚠ 规划器地图为空（膨胀点 0）—— 场地开阔时可能正常；但箱子必须能被看到，否则避障/天花板不生效"
fi
# 2026-11-03 用户批准：px4ctrl 活性门——节点注册 != 控制循环在跑。
# RC 未连接/未开时 px4ctrl 停在 "Waiting for RC"，rosnode list 仍有 /px4ctrl（假绿）。
if [ "$(cat "$RUND/px4act" 2>/dev/null)" = 1 ]; then
  echo "  ✓ px4ctrl 控制循环在（/debugPx4ctrl/fsm_state 有输出）"
else
  echo "  ✗ px4ctrl 未进控制循环（多半 RC 未连接/未开）——STACK FAIL"; PASS=0
fi
echo "===== 5/5 预检脚本（电池/陀螺/VINS 病理带，完整输出）====="
cat "$RUND/pf" 2>/dev/null
[ "$(cat "$RUND/pf_pass" 2>/dev/null)" = 1 ] || PASS=0
# 2026-11-07（用户令）：RViz 归起栈脚本，默认开；RVIZ_CMD="" 可显式关闭。
# 无 DISPLAY（SSH 会话）时软跳过——map_rviz.sh 自己也需要桌面，硬起只会留一条假"已启动"日志。
# 2026-11-07（用户令）：DISPLAY 没设时自动探测可用 X（NoMachine 桌面通常是 :0；:1001 是其私有 display）。
# v6：探测已在门区并行做过（$RUND/disp，每次 timeout 2）——这里只取结果，SSH 无 X 时不再多等 ~9s。
if [ -z "${DISPLAY:-}" ] && [ -s "$RUND/disp" ]; then
    export DISPLAY=$(cat "$RUND/disp")
    echo "  [rviz] 自动探测到可用 DISPLAY=$DISPLAY"
fi
RVIZ_CMD="${RVIZ_CMD-bash $HOME/sitl_realmachine/rviz_mapping_v1/map_rviz.sh}"
if [ $PASS -eq 1 ]; then
    if [ -n "$RVIZ_CMD" ]; then
        if [ -z "${DISPLAY:-}" ]; then
            echo "  [rviz] 跳过：当前无 DISPLAY（SSH 会话）——需要 RViz 请在 NoMachine 桌面起栈，或另跑 flight.sh rviz"
        else
            RLOG=~/sitl_realmachine/rviz_$(date +%H%M%S).log
            nohup bash -c "$RVIZ_CMD" > "$RLOG" 2>&1 &
            echo "  [rviz] 已启动（$RVIZ_CMD），日志 $RLOG"
        fi
    fi
    echo "===== STACK READY $(date '+%T')（v6 总耗时 $(el)s），可开录起飞 ====="
else
    echo "===== STACK FAIL——禁飞 ====="; exit 1
fi
