#!/usr/bin/env bash
# x4_batch.sh — T1 v11.9 单元 3 X4 五位形批处理（用户 10-06 建议款；0 锁写码备重裁）
# 设计约束（任务书原文）：本机自跑全程；预注册分支逻辑编码；两次短连接（装载+启动 / 取汇总）；
# 运行期间禁人工干预；心跳/日志自写；5/5 全绿自动 tag（打前五查内嵌），否则 PAUSE/FAIL 汇总。
# 分支预注册（编码于 judge_round()；依据=xline prereg §2.6/§2.8 + v11.9 单元 3 原文）：
#   ENV-FAIL（环境三签名）→ 重试同位形（每位形 ≤1，全程累计 ≤3）
#   风暴/敌对轮（never-flew 或 T2fail≥3）→ X1prime 域模式：不计分母，重试占同一预算（≤1/位形,≤3 累计）
#   连续 2 轮同型到位撞门（到位 FAIL ∧ jump≤0.5 ∧ 到位值≤1.2）→ PAUSE 标记停批（撞门预案人工段）
#   单轮墙钟 >900s → 超时自杀清场，记 timeout 后跳过（占位形一次机会）
#   真 FAIL（非上述类）→ 计入分母红色，不重试，继续后续位形（证据完整性）
# 绿色定义（5/5 计数）= RESULT=PASS ∨ cf=controlled（prereg §2.6 受控失败并集；报告双列呈现）
# P2 姿态：X4 五轮 P2 off（冻结判据面纯净性；P2-A 严格版挂批后独立轮）
# 用法: bash x4_batch.sh --arm-banner "guard=1 sane_p=50.0 sane_v=15.0" [--dry]
#   --arm-banner = 本批臂的 [T2SGCFG] 期望子串（重裁后按裁定臂填；不符=ABORT_ARM 不起飞）
# 坑位：source ROS 必须在 set -u 之前（ROS profile 链未绑变量爆炸，本会话坑表在册）
L="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
EVD="$WS/sitl_sim/t1_evidence/v11_7_2026-10-05"
SUM="$EVD/x4_batch_report.md"
source /opt/ros/noetic/setup.bash
source "$WS/devel/setup.bash"
set -u
HEARTBEAT_MIN=10
ARM_EXPECT=""
DRY=0
while [ $# -gt 0 ]; do case "$1" in
  --arm-banner) ARM_EXPECT="$2"; shift 2;;
  --dry) DRY=1; shift;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
[ -z "$ARM_EXPECT" ] && { echo "need --arm-banner"; exit 2; }
EXPECT_NODE="b7de133d"; EXPECT_LIB="59548c6a"
source /opt/ros/noetic/setup.bash
source "$WS/devel/setup.bash"

POSITIONS=(
  "X1final|--world sitl_world_obstacles --goal 7.0 -4.0 1.0 --budget 180"
  "X2g1|--world sitl_world_obstacles --goal 7.0 -4.0 1.0 --budget 180"
  "X2g3|--world sitl_world_obstacles --goal 8.0 -1.0 1.0 --budget 180"
  "X3l2a|--world sitl_world_obstacles --goal 7.0 -4.0 1.0 --leg2 1.0 0.0 1.0 --budget 240"
  "X3l2b|--world sitl_world_obstacles --goal 7.0 -4.0 1.0 --leg2 0.0 0.0 1.0 --budget 240"
)
retry_budget=3
consec_door=0
declare -A retried
GREENS=0; TOTAL=0

w() { echo "[$(date '+%F %T')] $*" | tee -a "$SUM"; }
status_line() { python3 "$L/status_append.py" "$*" >/dev/null 2>&1 || true; }

preflight() {
  local M_NODE M_LIB DF_G
  M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" 2>/dev/null | cut -c1-8)
  M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" 2>/dev/null | cut -c1-8)
  [ "$M_NODE" = "$EXPECT_NODE" ] && [ "$M_LIB" = "$EXPECT_LIB" ] || { w "ABORT_STACK md5=$M_NODE/$M_LIB"; exit 9; }
  DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
  [ "$DF_G" -lt 20 ] && { w "ABORT_DISK ${DF_G}G"; exit 9; }
  pgrep -x gzserver >/dev/null 2>&1 && { w "ABORT_RESIDUE gzserver alive"; exit 9; }
  w "preflight OK stack=$M_NODE/$M_LIB df=${DF_G}G arm_banner='$ARM_EXPECT'"
}

force_cleanup() {  # 超时自杀后清场（pkill -x 精确名,禁 -f 自匹配坑）
  local p
  for p in gzserver px4 rosmaster rosout roslaunch vins_node px4ctrl_node traj_server rostopic rosbag; do
    pkill -x "$p" 2>/dev/null
  done
  sleep 3
  w "  force_cleanup done (timeout residue)"
}

judge_round() {  # $1=tag $2=run_dir  -> echoes classification
  local TAG="$1" D="$2" RES FAILN ANCH JUMP ARR CF WA
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL)" "$D/RESULT.txt" 2>/dev/null || echo "NO-RESULT")
  FAILN=$(grep -c "failure detection" "$D/simvins.log" 2>/dev/null || echo 0)
  NEVER=$(grep -c "never-flew" "$D/RESULT.txt" 2>/dev/null || echo 0)
  JUMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$" || echo 99.9)
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$D/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$" || echo -1)
  WA=$(python3 "$WS/sitl_sim/analysis/t3_wa_gate.py" --online "$D" 2>/dev/null | grep -m1 "run_")
  CF=$(echo "$WA" | grep -oE "cf=[a-z-]+" | head -1 | cut -d= -f2)
  ANCH=$(grep -m1 "DUAL-ANCHOR" "$D/RESULT.txt" 2>/dev/null | cut -c1-120)
  DISARM=$(grep -m1 -oE "auto_disarm->[01]" "$D/RESULT.txt" 2>/dev/null || echo "?")
  w "  RESULT=$RES T2fail=$FAILN neverflew=$NEVER jump=$JUMP arrive=$ARR $DISARM cf=${CF:-?}"
  w "  ${ANCH:-no-dual-anchor}"
  w "  ${WA:0:200}"
  # 分支预注册逻辑
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
  w "== position $TAG (attempt $(( ${retried[$TAG]:-0} + 1 )))"
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
    w "  banner: $BANNER"
    CLASS=$(judge_round "$TAG" "$D")
  fi
  w "  class=$CLASS"
  case "$CLASS" in
    green)
      GREENS=$((GREENS+1)); consec_door=0; status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG 绿($GREENS/5) | 批处理 | 自动判读,规则预注册";;
    door)
      consec_door=$((consec_door+1))
      status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG 撞门型($consec_door/2 连续) | 批处理 | 到位 $ARR@jump$JUMP"
      if [ "$consec_door" -ge 2 ]; then w "PAUSE door-collision x2 consec -> 人工段(撞门预案)"; touch "$EVD/X4_BATCH_PAUSE"; exit 7; fi;;
    env|hostile|timeout)
      consec_door=0
      if [ "${retried[$TAG]:-0}" = "0" ] && [ "$retry_budget" -gt 0 ]; then
        retried[$TAG]=1; retry_budget=$((retry_budget-1))
        w "  retry scheduled ($CLASS; budget left=$retry_budget)"
        status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG $CLASS → 重试(余 $retry_budget) | 批处理"
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

tag_if_5_5() {
  if [ "$GREENS" -ge 5 ]; then
    w ""
    w "== 5/5 GREEN — pre-tag five checks =="
    local M_NODE M_LIB DF_G UNRES
    M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" | cut -c1-8)
    M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" | cut -c1-8)
    DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
    UNRES=$(pgrep -c gzserver 2>/dev/null || echo 0)
    w "  stack=$M_NODE/$M_LIB df=${DF_G}G residue=$UNRES STATUS-自写心跳在册"
    cd "$WS" || exit 9
    git status --porcelain | head -3 >> "$SUM"
    git tag -a sitl-v0.4 -m "X4 five-position 5/5 green (batch $ARM_EXPECT arm; $(date '+%F %T')). Tag semantics: VINS closed-loop + incident controlled fallback; transit-floor annotation per unified wording; profile note only if door-contingency triggered." && w "  TAG sitl-v0.4 CREATED" || w "  TAG FAILED"
    git push UAV_NUC main --tags 2>&1 | tail -1 >> "$SUM"
    status_line "$(date +%H:%M) | T1 | **X4 五连飞 5/5 全绿 → tag sitl-v0.4 已打**(臂=$ARM_EXPECT,批处理自判) | 里程碑 | 成色=纯绿(带 transit 统一注记;剖面注记未触发除非撞门预案走过)"
  else
    w ""
    w "== BATCH END greens=$GREENS/5 (PAUSE=$([ -f "$EVD/X4_BATCH_PAUSE" ] && echo yes || echo no)) — FAIL/PAUSE 汇总待人工 =="
    status_line "$(date +%H:%M) | T1 | x4_batch 收束:$GREENS/5 绿($( [ -f "$EVD/X4_BATCH_PAUSE" ] && echo PAUSE-撞门 || echo FAIL-汇总))待人工 | 批处理 | 详见 x4_batch_report.md"
  fi
}

rm -f "$EVD/X4_BATCH_PAUSE"
w "# X4 五位形批处理报告（$(date '+%F %T')；臂=$ARM_EXPECT；规则预注册见脚本头）"
preflight
status_line "$(date +%H:%M) | T1 | x4_batch 启动(臂=$ARM_EXPECT,五连飞,禁人工干预,心跳自写) | 批处理 | 重试预算=3(env/hostile 共用,≤1/位形);撞门×2 连续=PAUSE;900s 超时自杀"
for pos in "${POSITIONS[@]}"; do
  TAG="${pos%%|*}"; ARGS="${pos#*|}"
  run_position "$TAG" "$ARGS"
done
tag_if_5_5
w "== batch complete $(date '+%F %T') =="
