#!/usr/bin/env bash
# x5_batch.sh — T1 v11.17 单元 1.2/3.1 X5 剂量网格批（派生自 x4_batch.sh 9592f96c）
# 正源设计：docs/xline_x5_grid_design_v1.md §A.2/§A.3/§C v1.1（T3 冻结；臂构成/goal 清单/
# 录制口径逐字执行；零门值变更）。46 轮=36 基础网格(6 向×3 距离×2 world)+leg2 抽样 6
# +温和剖面专轮 4（E12/W12×两 world 复刻=稳定性验证）。全紧凑模式（零带图格；P3 未
# 明确要图像证据=带图档不启用，A.4 预算表推荐主模式）。
# goal 口径（预注册）：出生锚定 goal=birth(1.01,0.98,1.0)+dir_unit×dist（VINS/规划器
# 坐标系；world 文件头注释同源口径 gazebo=odom+(1.01,0.98)；逐轮实测位移=A* 实测差
# 由 passmap 记账列承载）。leg2 抽样极值两轮=E12×obstacles+S5×plain（设计文"两距离
# 极值"歧义解=远近各一/两 world 两方向对称，@T3 回场复核）。
# 批规则预注册（沿 x4_batch 冻结面零变动）：ENV-FAIL 重试 ≤1/轮 ≤3 累计；敌对域
# （never-flew 或 T2fail≥3）不计分母；900s 超时自杀；真 FAIL 计分母不重试；撞门×2
# 连续=PAUSE。starve 修复内嵌=vins_smoke.sh 订阅就绪门+一次性重启（1.1 DoD 闭合件）。
# 加固三坑（10-06 实锤+预防）：①会话关闭连带死→nohup setsid 全脱链+trap BATCH END
# 必落；②清理调用全文件化/模式串与自身命令行零交集（pkill -x 名字级）；③rosmaster
# 域过滤（force_cleanup 不杀私有 master 回放件——1e 回放共存保护）。
# PX4 参数随轮 dump+VINS config 全键 md5=vins_smoke 内嵌（口径见其注释）。
# 用法: bash x5_batch.sh --arm-banner "guard=1 sane_p=50.0 sane_v=15.0" \
#        --expect-node <md5> --expect-lib <md5> [--dry] [--skip T1,T2]
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
L="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
EVD="$HOME/sitl_sim/t1_evidence/v11_17_2026-10-06"
SUM="$EVD/x5_batch_report.md"
PASSMAP="$EVD/x5_passmap_live.csv"
HEARTBEAT_MIN=10
ARM_EXPECT=""
EXPECT_NODE=""; EXPECT_LIB=""
DRY=0; SKIP_TAGS=""
while [ $# -gt 0 ]; do case "$1" in
  --arm-banner) ARM_EXPECT="$2"; shift 2;;
  --expect-node) EXPECT_NODE="$2"; shift 2;;
  --expect-lib) EXPECT_LIB="$2"; shift 2;;
  --dry) DRY=1; shift;;
  --skip) SKIP_TAGS=",$2,"; shift 2;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
[ -z "$ARM_EXPECT" ] && { echo "need --arm-banner"; exit 2; }
[ -z "$EXPECT_NODE" ] || [ -z "$EXPECT_LIB" ] && { echo "need --expect-node/--expect-lib (栈凭据换代制:批前显式登记)"; exit 2; }

# ---------- 网格展开(出生锚定;O=obstacles 0.75 门/P=plain 0.5 门) ----------
BX=1.01; BY=0.98; BZ=1.0
POSITIONS=()
add() { # dir_name dist world_suffix world goalvec...
  local dn="$1" dist="$2" ws="$3" world="$4" ux="$5" uy="$6" extra="$7"
  local gx gy tag
  gx=$(python3 -c "print('%.3f' % ($BX + $ux*$dist))")
  gy=$(python3 -c "print('%.3f' % ($BY + $uy*$dist))")
  tag="X5_${dn}${dist}${ws}"
  POSITIONS+=("${tag}|--world $world --goal $gx $gy $BZ --budget 200 $extra")
}
# T1 优先级1(P3 直接消费面): E/S×8×两 world
add E 8 O sitl_world_obstacles 1 0 ""
add S 8 O sitl_world_obstacles 0 -1 ""
add E 8 P sitl_world_plain 1 0 ""
add S 8 P sitl_world_plain 0 -1 ""
# T2 优先级2: 8m 补全 + E/S×{5,12}
for dn_ux_uy in "W:-1:0" "N:0:1" "SE:0.7071067811865476:-0.7071067811865476" "NE:0.7071067811865476:0.7071067811865476"; do
  IFS=: read -r dn ux uy <<< "$dn_ux_uy"
  for ws_world in "O:sitl_world_obstacles" "P:sitl_world_plain"; do
    IFS=: read -r ws world <<< "$ws_world"
    add "$dn" 8 "$ws" "$world" "$ux" "$uy" ""
  done
done
for dn_ux_uy in "E:1:0" "S:0:-1"; do
  IFS=: read -r dn ux uy <<< "$dn_ux_uy"
  for dist in 5 12; do
    for ws_world in "O:sitl_world_obstacles" "P:sitl_world_plain"; do
      IFS=: read -r ws world <<< "$ws_world"
      add "$dn" "$dist" "$ws" "$world" "$ux" "$uy" ""
    done
  done
done
# T3a: 其余 16 格(W/N/SE/NE×{5,12}×两 world)
for dn_ux_uy in "W:-1:0" "N:0:1" "SE:0.7071067811865476:-0.7071067811865476" "NE:0.7071067811865476:0.7071067811865476"; do
  IFS=: read -r dn ux uy <<< "$dn_ux_uy"
  for dist in 5 12; do
    for ws_world in "O:sitl_world_obstacles" "P:sitl_world_plain"; do
      IFS=: read -r ws world <<< "$ws_world"
      add "$dn" "$dist" "$ws" "$world" "$ux" "$uy" ""
    done
  done
done
# T3b: leg2 抽样 6(E/S×8×两 world 返程 + 距离极值两轮 E12×O/S5×P)
L2G="$BX $BY $BZ"
add E 8 O sitl_world_obstacles 1 0 "--leg2 $L2G"
add S 8 O sitl_world_obstacles 0 -1 "--leg2 $L2G"
add E 8 P sitl_world_plain 1 0 "--leg2 $L2G"
add S 8 P sitl_world_plain 0 -1 "--leg2 $L2G"
add E 12 O sitl_world_obstacles 1 0 "--leg2 $L2G"
add S 5 P sitl_world_plain 0 -1 "--leg2 $L2G"
# T3c: 温和剖面专轮 4(E12/W12×两 world 复刻=同格第二飞,tag 后缀 _R2)
POSITIONS+=("X5_E12O_R2|--world sitl_world_obstacles --goal $(python3 -c "print('%.3f'%($BX+12))") $BY $BZ --budget 200")
POSITIONS+=("X5_E12P_R2|--world sitl_world_plain --goal $(python3 -c "print('%.3f'%($BX+12))") $BY $BZ --budget 200")
POSITIONS+=("X5_W12O_R2|--world sitl_world_obstacles --goal $(python3 -c "print('%.3f'%($BX-12))") $BY $BZ --budget 200")
POSITIONS+=("X5_W12P_R2|--world sitl_world_plain --goal $(python3 -c "print('%.3f'%($BX-12))") $BY $BZ --budget 200")

N_TOTAL=${#POSITIONS[@]}
[ "$N_TOTAL" = "46" ] || { echo "FATAL grid count=$N_TOTAL expect 46"; exit 9; }
GOALS_MD5=$(for pos in "${POSITIONS[@]}"; do echo "$pos"; done | md5sum | cut -c1-8)

retry_budget=3
consec_door=0
declare -A retried
GREENS=0; TOTAL=0; ENVFAILS=0

w() { echo "[$(date '+%F %T')] $*" | tee -a "$SUM"; }
status_line() { python3 "$L/status_append.py" "$*" >/dev/null 2>&1 || true; }
batch_end() {  # 加固坑①:BATCH END 必落(trap 兜底)
  w "== BATCH END $(date '+%F %T') greens=$GREENS/$TOTAL envfails=$ENVFAILS md5_goals=$GOALS_MD5 =="
}
trap 'batch_end' EXIT

force_cleanup() {  # 加固坑③:rosmaster/rosout 不杀(私有 master 回放件保护);余 pkill -x 名字级
  local p my_m="${ROS_MASTER_URI:-http://localhost:11311}" pm
  for p in gzserver px4 roslaunch vins_node px4ctrl_node traj_server rostopic rosbag; do
    pkill -x "$p" 2>/dev/null
  done
  for pm in $(pgrep -x rosmaster 2>/dev/null); do
    m=$(tr '\0' '\n' < "/proc/$pm/environ" 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    m="${m:-http://localhost:11311}"
    [ "$m" = "$my_m" ] && kill -9 "$pm" 2>/dev/null
  done
  sleep 3
  w "  force_cleanup done (timeout residue; rosmaster domain-filtered)"
}

preflight() {
  local M_NODE M_LIB DF_G CFG
  M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" 2>/dev/null | cut -c1-8)
  M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" 2>/dev/null | cut -c1-8)
  [ "$M_NODE" = "$EXPECT_NODE" ] && [ "$M_LIB" = "$EXPECT_LIB" ] || { w "ABORT_STACK md5=$M_NODE/$M_LIB expect=$EXPECT_NODE/$EXPECT_LIB"; exit 9; }
  DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
  [ "$DF_G" -lt 20 ] && { w "ABORT_DISK ${DF_G}G"; exit 9; }
  pgrep -x gzserver >/dev/null 2>&1 && { w "ABORT_RESIDUE gzserver alive"; exit 9; }
  for wf in sitl_world_obstacles sitl_world_plain; do
    [ -f "$WS/sitl_sim/worlds/$wf.world" ] || { w "ABORT_WORLD $wf.world missing(repo)"; exit 9; }
    PXW="$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/$wf.world"
    [ -f "$PXW" ] || { w "ABORT_WORLD $wf.world not staged in PX4 worlds dir"; exit 9; }
    [ "$(md5sum "$WS/sitl_sim/worlds/$wf.world" | cut -d" " -f1)" = "$(md5sum "$PXW" | cut -d" " -f1)" ]       || { w "ABORT_WORLD $wf.world repo!=PX4-staged (md5 drift)"; exit 9; }
  done
  CFG="$WS/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
  grep -q '^t2_vision_loss: 0' "$CFG" && grep -q '^t2_cost_gate: 1' "$CFG" \
    && grep -q '^t2_staged_depth_gate: 1' "$CFG" && grep -q '^t2_stream_guard: 1' "$CFG" \
    || { w "ABORT_ARM_CONFIG canonical 未处 v2 臂态(loss=0/cost_gate=1/staged=1/guard=1): $(grep -E '^t2_(vision_loss|cost_gate|staged_depth_gate|stream_guard)' "$CFG" | tr '\n' ' ')"; exit 9; }
  w "preflight OK stack=$M_NODE/$M_LIB df=${DF_G}G arm_banner='$ARM_EXPECT' goals_md5=$GOALS_MD5 n=$N_TOTAL"
}

passmap_row() {  # $1=tag $2=class $3=RESULT行摘要
  echo -e "$1\t$2\t$3\t$(date '+%F %T')" >> "$PASSMAP"
}

judge_round() {  # $1=tag $2=run_dir -> echoes classification（沿 x4_batch 修复版逐字）
  local TAG="$1" D="$2" RES FAILN ANCH JUMP ARR CF WA NEVER
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL)" "$D/RESULT.txt" 2>/dev/null | head -1 | cut -d= -f2)
  [ -n "$RES" ] || RES="NO-RESULT"
  FAILN=$(grep -c "failure detection" "$D/simvins.log" 2>/dev/null); case "$FAILN" in ''|*[!0-9]*) FAILN=0;; esac
  NEVER=$(grep -c "never-flew" "$D/RESULT.txt" 2>/dev/null); case "$NEVER" in ''|*[!0-9]*) NEVER=0;; esac
  JUMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$" || echo 99.9)
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$" || echo -1)
  WA=$(python3 "$WS/sitl_sim/analysis/t3_wa_gate.py" --online "$D" 2>/dev/null | grep -m1 "run_")
  CF=$(echo "$WA" | grep -oE "cf=[a-z-]+" | head -1 | cut -d= -f2)
  ANCH=$(grep -m1 "DUAL-ANCHOR" "$D/RESULT.txt" 2>/dev/null | cut -c1-120)
  DISARM=$(grep -m1 -oE "auto_disarm->[01]" "$D/RESULT.txt" 2>/dev/null || echo "?")
  w "  RESULT=$RES T2fail=$FAILN neverflew=$NEVER jump=$JUMP arrive=$ARR $DISARM cf=${CF:-?}"
  w "  ${ANCH:-no-dual-anchor}"
  w "  ${WA:0:200}"
  passmap_row "$TAG" "?" "$RES jump=$JUMP arr=$ARR"
  if [ "$RES" = "ENV-FAIL" ]; then echo "env"; return; fi
  if [ "$NEVER" -ge 1 ] || [ "$FAILN" -ge 3 ]; then echo "hostile"; return; fi
  if [ "$RES" = "PASS" ]; then echo "green"; return; fi
  if [ "${CF:-}" = "controlled" ]; then echo "green"; return; fi
  if [ "$RES" = "FAIL" ]; then
    local doorok
    doorok=$(python3 -c "print(1 if float('$JUMP')<=0.5 and 0.75<=float('$ARR')<=1.2 else 0)" 2>/dev/null || echo 0)
    [ "$doorok" = "1" ] && { echo "door"; return; }
    echo "fail"; return
  fi
  echo "fail"
}

run_position() {  # $1=tag $2=args
  local TAG="$1" ARGS="$2" D RC CLASS BANNER
  TOTAL=$((TOTAL+1))
  w ""
  w "== position $TAG (attempt $(( ${retried[$TAG]:-0} + 1 ))) [$TOTAL/$N_TOTAL]"
  if [ "$DRY" = "1" ]; then w "  DRY: would run vins_smoke $ARGS --tag $TAG"; return 0; fi
  timeout 900 bash "$L/vins_smoke.sh" $ARGS --tag "$TAG" </dev/null > "/tmp/${TAG}_console.log" 2>&1
  RC=$?
  [ "$RC" = "124" ] && force_cleanup
  D=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1)
  if [ -z "$D" ]; then w "  NO-RUNDIR rc=$RC (timeout-suicide?)"; CLASS="timeout"; else
    BANNER=$(grep -m1 -oE "\[T2SGCFG\][^]]*" "$D/simvins.log" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')
    if ! echo "$BANNER" | grep -qF "$ARM_EXPECT"; then
      w "  ABORT_ARM banner='$BANNER' expect='$ARM_EXPECT'"; exit 8
    fi
    KNOBS=$(grep -m1 "T2 knobs" "$D/simvins.log" 2>/dev/null | grep -oE "loss=[0-9]+ cauchy=[0-9.]+" || echo "KNOBS-MISSING")
    echo "$KNOBS" | grep -q "loss=0" || { w "  ABORT_ARM_KNOBS '$KNOBS' (expect loss=0; CauchyLoss(0) 防线)"; exit 8; }
    w "  banner: $BANNER | knobs: $KNOBS"
    CLASS=$(judge_round "$TAG" "$D")
  fi
  w "  class=$CLASS"
  case "$CLASS" in
    green)
      GREENS=$((GREENS+1)); consec_door=0
      status_line "$(date +%H:%M) | T1 | x5_batch 心跳: $TAG 绿($GREENS/$TOTAL) | 批处理 | X5 网格 46 轮自跑";;
    door)
      consec_door=$((consec_door+1))
      status_line "$(date +%H:%M) | T1 | x5_batch 心跳: $TAG 撞门型($consec_door/2 连续) | 批处理"
      if [ "$consec_door" -ge 2 ]; then w "PAUSE door-collision x2 consec -> 人工段(撞门预案)"; touch "$EVD/X5_BATCH_PAUSE"; exit 7; fi;;
    env|hostile|timeout)
      consec_door=0
      [ "$CLASS" = "env" ] && ENVFAILS=$((ENVFAILS+1))
      if [ "${retried[$TAG]:-0}" = "0" ] && [ "$retry_budget" -gt 0 ]; then
        retried[$TAG]=1; retry_budget=$((retry_budget-1))
        w "  retry scheduled ($CLASS; budget left=$retry_budget)"
        status_line "$(date +%H:%M) | T1 | x5_batch 心跳: $TAG $CLASS → 重试(余 $retry_budget) | 批处理"
        run_position "$TAG" "$ARGS"
      else
        w "  no retry left for $TAG ($CLASS; budget=$retry_budget, retried=${retried[$TAG]:-0})"
        [ "$CLASS" = "hostile" ] && w "  (hostile 不计分母——X1prime 域模式,分母口径在册)"
      fi;;
    fail)
      consec_door=0
      w "  real FAIL -> 计入分母红色,不重试";;
  esac
}

rm -f "$EVD/X5_BATCH_PAUSE"
echo -e "tag\tclass\tsummary\twall" > "$PASSMAP"
w "# X5 剂量网格批报告（$(date '+%F %T')；臂=$ARM_EXPECT；栈=$EXPECT_NODE/$EXPECT_LIB；goals_md5=$GOALS_MD5；规则预注册见脚本头；设计正源=xline_x5_grid_design_v1.md §C v1.1）"
preflight
status_line "$(date +%H:%M) | T1 | x5_batch 启动(臂=$ARM_EXPECT,46 轮网格,出生锚定 goal,禁人工干预,批窗内禁 build) | 批处理 | 重试预算=3;撞门×2=PAUSE;900s 超时自杀;预计时长 5-7h"
for pos in "${POSITIONS[@]}"; do
  TAG="${pos%%|*}"; ARGS="${pos#*|}"
  if [[ "$SKIP_TAGS" == *",$TAG,"* ]]; then
    TOTAL=$((TOTAL+1)); w "== position $TAG SKIPPED (续跑条款)"
    continue
  fi
  run_position "$TAG" "$ARGS"
done
w ""
w "== BATCH COMPLETE greens=$GREENS/$TOTAL (PAUSE=$([ -f "$EVD/X5_BATCH_PAUSE" ] && echo yes || echo no)) =="
status_line "$(date +%H:%M) | T1 | x5_batch 收束:$GREENS/$TOTAL 绿 | 批处理 | 详见 x5_batch_report.md+x5_passmap_live.csv;下件=4.1 剂量-稳定性曲线"
