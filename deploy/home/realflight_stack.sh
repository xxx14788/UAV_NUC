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
trap 'rm -f "$LOCK"' EXIT
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
pkill -f "mavros_node" 2>/dev/null; pkill -f "realsense2_camera" 2>/dev/null
pkill -f "run_planner" 2>/dev/null; pkill -f "roslaunch" 2>/dev/null
pkill -f "[c]amera_pose_relay.py" 2>/dev/null; pkill -x rviz 2>/dev/null
# 2026-11-09（P0-6）：这两个原来漏杀 —— planned_path_pub 会成孤儿挡新实例；
# vins_to_mavros 是 rosrun 起的，`pkill -f roslaunch` 永远抓不到。
pkill -f "[p]lanned_path_pub.py" 2>/dev/null
pkill -f "[v]ins_to_mavros_node" 2>/dev/null
# 2026-11-10（用户批准）：地图工具节点不在五件套里，但会抢 /grid_map 话题与 CPU。
rosnode list 2>/dev/null | grep -qx /mapping_view && rosnode kill /mapping_view 2>/dev/null
sleep 1.5; pkill -9 -x rosmaster 2>/dev/null; sleep 1
LEFT=$(pgrep -c -x rosmaster 2>/dev/null || true)
if [ "${LEFT:-0}" -eq 0 ]; then echo "✓ 清场毕（rosmaster 0 残留）"; else echo "✗ 仍残留 ${LEFT} 个 rosmaster——手动 ps 检查后重跑"; exit 1; fi
echo "===== 2/5 起五件套主栈 $(date '+%T') ====="
bash ~/sitl_realmachine/realmachine_2a_reboot_stack.sh || { echo "✗ 主栈脚本失败——停（看上方自检输出哪条流没起来）"; exit 1; }
echo "✓ 五件套自检过（mavros/IMU/infra/VINS 四流，pid 行见上）"
echo "===== 3/5 起规划器（后台）====="
# 2026-11-07（用户令）：唯一栈入口。规划器只在本脚本启动，任务脚本不再各起一份。
# 默认地图版（带天花板/膨胀/goal_gate）；需要换版本时传 PLANNER_LAUNCH。
PLANNER_LAUNCH="${PLANNER_LAUNCH:-$HOME/sitl_realmachine/flight_v1/run_planner_realmachine_map_v1.launch}"
PLOG=~/sitl_realmachine/planner_$(date +%H%M%S).log
nohup roslaunch $PLANNER_LAUNCH > "$PLOG" 2>&1 &
echo "规划器 pid=$! 日志=$PLOG（悬停不依赖它）——等节点出现（≤40s 轮询）+20s 稳定窗..."
W=0
until timeout 4 rosnode list 2>/dev/null | grep -qE "ego_planner|traj_server"; do
  sleep 2; W=$((W+2)); [ $W -ge 40 ] && { echo "⚠ 40s 未见规划器节点（后面 4/5 会再查）"; break; }
done
sleep 20

# 规划器 pose_type=1(POSE_STAMPED) 必须吃 /planner/camera_pose，由 camera_pose_relay.py 提供。
# 转接缺失 -> 地图永远空（实测膨胀点 0）-> 看不到箱子、天花板也不生效。起栈时必起。
# 2026-11-09（P0-6）：判活必须问**当前 master**。pgrep 会把连着旧 master 的孤儿
# 当成"已在运行"，于是新栈缺节点（planned_path 事故的同形状）。
if rosnode list 2>/dev/null | grep -qx "/planner_camera_pose_relay"; then
  echo "  相机位姿转接已在运行（当前 master 上，跳过）"
else
  pkill -f "[c]amera_pose_relay.py" 2>/dev/null; sleep 0.5
  RELAY_LOG=~/sitl_realmachine/camera_pose_relay_$(date +%H%M%S).log
  nohup python3 "$HOME/sitl_realmachine/flight_v1/camera_pose_relay.py" > "$RELAY_LOG" 2>&1 &
  echo "  相机位姿转接 pid=$! 日志=$RELAY_LOG（/vins_estimator/camera_pose -> /planner/camera_pose）"
  sleep 2
fi

# 2026-11-08（方案 v2 C4）：健康门的深度话题**必须**等于规划器实际消费的那条边。
# P0 实测缺陷：原来查 /camera/aligned_depth_to_color/image_raw，而规划器吃的是
# /camera/depth/image_rect_raw —— 两条流都活着时假绿灯，规划器那条死了也照样 STACK READY。
CONTRACT="$HOME/sitl_realmachine/flight_v1/contract/flight_contract.yaml"
DEPTH_TOPIC=$(python3 - "$CONTRACT" <<'PYEOF'
import sys
try:
    import yaml
    with open(sys.argv[1], encoding='utf-8') as fh:
        print(yaml.safe_load(fh)['seams']['depth']['topic'])
except Exception:
    print('/camera/depth/image_rect_raw')
PYEOF
)
[ -n "$DEPTH_TOPIC" ] || DEPTH_TOPIC=/camera/depth/image_rect_raw
# 2026-11-08 二审 F15：阈值也读契约（原来脚本硬编码 15，契约里的 min_hz 是死字段）
DEPTH_MIN=$(python3 - "$CONTRACT" <<'PYEOF'
import sys
try:
    import yaml
    with open(sys.argv[1], encoding='utf-8') as fh:
        # 2026-11-11：原来读 health_gate.min_hz（不存在）-> 实际用的是硬编码 15。
        # 契约里真正的深度门槛在 seams.depth.min_hz。
        _d = yaml.safe_load(fh)
        print(_d.get('seams', {}).get('depth', {}).get('min_hz', 10.0))
except Exception:
    print(15.0)
PYEOF
)
[ -n "$DEPTH_MIN" ] || DEPTH_MIN=10.0
echo "  深度门话题（读契约）= $DEPTH_TOPIC"

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

echo "===== 4/5 健康门（三话题并行实测 8s）====="
hz() { timeout 8 rostopic hz "$1" 2>/dev/null | awk '/average rate/{r=$3} END{print r}'; }
PASS=1
TMPD=$(mktemp -d)
hz "$DEPTH_TOPIC" > "$TMPD/depth" & P1=$!
hz "/camera/infra1/image_rect_raw" > "$TMPD/infra1" & P2=$!
hz "/vins_estimator/odometry" > "$TMPD/odom" & P3=$!
wait $P1 $P2 $P3
# 2026-11-11：相机维持 30 fps（视觉不降流）；省流靠关 RGB + 录包压缩。
# 深度门槛读契约 seams.depth.min_hz=10，左目 20（30 fps 名义值）。
declare -A NAME=( [depth]=深度流:$DEPTH_MIN [infra1]=左目流:20 [odom]=VINS里程计:8 )
declare -A TOPIC=( [depth]=$DEPTH_TOPIC [infra1]=/camera/infra1/image_rect_raw [odom]=/vins_estimator/odometry )
for k in depth infra1 odom; do
  TH=${NAME[$k]##*:}
  V=$(cat "$TMPD/$k" 2>/dev/null)
  if [ -n "$V" ] && awk "BEGIN{exit !($V>=$TH)}"; then echo "  ✓ ${NAME[$k]%:*} = ${V}Hz（门 ${TH}）[${TOPIC[$k]}]";
  else echo "  ✗ ${NAME[$k]%:*} 无流/过低 = ${V:-0}Hz < ${TH} [${TOPIC[$k]}]"; PASS=0; fi
done
rm -rf "$TMPD"
if rosnode list 2>/dev/null | grep -qE "ego_planner|traj_server"; then
  echo "  ✓ 规划器节点在"
else
  echo "  ⚠ 规划器节点未见（悬停可继续；任务飞行会在 flight.sh start 的任务门硬判）——查 $PLOG"
fi
# 2026-11-07：没有转接 -> 地图永远空 -> 避障与天花板都不生效。硬门。
if rosnode list 2>/dev/null | grep -qx "/planner_camera_pose_relay"; then
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
# 地图是否真的被填起来（软告警：场地开阔时可能本来就空）
OCC=$(timeout 14 python3 - <<'PYOCC' 2>/dev/null
import rospy
from sensor_msgs.msg import PointCloud2
rospy.init_node("occchk", anonymous=True)
w = []
rospy.Subscriber("/drone_0_ego_planner_node/grid_map/occupancy_inflate",
                 PointCloud2, lambda m: w.append(m.width))
rospy.sleep(6)
print(w[-1] if w else 0)
PYOCC
)
if [ "${OCC:-0}" -gt 0 ] 2>/dev/null; then
  echo "  ✓ 规划器地图已填充（膨胀点 ${OCC}）"
else
  echo "  ⚠ 规划器地图为空（膨胀点 0）—— 场地开阔时可能正常；但箱子必须能被看到，否则避障/天花板不生效"
fi
# 2026-11-03 用户批准：px4ctrl 活性门——节点注册 != 控制循环在跑。
# RC 未连接/未开时 px4ctrl 停在 "Waiting for RC"，rosnode list 仍有 /px4ctrl（假绿）。
if timeout 5 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state >/dev/null 2>&1; then
  echo "  ✓ px4ctrl 控制循环在（/debugPx4ctrl/fsm_state 有输出）"
else
  echo "  ✗ px4ctrl 未进控制循环（多半 RC 未连接/未开）——STACK FAIL"; PASS=0
fi
echo "===== 5/5 预检脚本（电池/陀螺/VINS 病理带，完整输出）====="
VL=$(ls -t ~/sitl_realmachine/*/vins_*.log ~/sitl_realmachine/vins_*.log 2>/dev/null | head -1)
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
    echo "  ✗ 120s 病理带未就绪（cost 尾部中位 ${C:-无数据}）——VINS 未收敛，禁飞"; PASS=0
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
    echo "$PRE" | grep -q "PREFLIGHT GO" && echo "  ✓ 预检 GO（重试后）" || { echo "  ✗ 预检 NO-GO——按上面打印项处理"; PASS=0; }
  fi
else echo "  ✗ 未找到 VINS 日志"; PASS=0; fi
# 2026-11-07（用户令）：RViz 归起栈脚本，默认开；RVIZ_CMD="" 可显式关闭。
# 无 DISPLAY（SSH 会话）时软跳过——map_rviz.sh 自己也需要桌面，硬起只会留一条假"已启动"日志。
# 2026-11-07（用户令）：DISPLAY 没设时自动探测可用 X。
# 场景：从 SSH 起栈时 DISPLAY 为空 -> 原来直接软跳过 RViz，用户以为"起栈没带 RViz"。
# NoMachine 桌面通常是 :0（本机实测 :0 可用、:1001 是 NoMachine 的私有 display）。
if [ -z "${DISPLAY:-}" ]; then
    for _d in :0 :1 :1001; do
        if DISPLAY=$_d timeout 3 xdpyinfo >/dev/null 2>&1; then
            export DISPLAY=$_d
            echo "  [rviz] 自动探测到可用 DISPLAY=$_d"
            break
        fi
    done
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
    echo "===== STACK READY $(date '+%T')，可开录起飞 ====="
else
    echo "===== STACK FAIL——禁飞 ====="; exit 1
fi
