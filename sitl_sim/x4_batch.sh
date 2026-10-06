#!/usr/bin/env bash
# x4_batch.sh — T1 v11.20 单元1d/3 X4 五位形冲刺批（**融合版**：T3 v10.3 三列分账/trichotomy
# 权威/双链 tag 为基 + T1 v11.20 双门挂载/新五位形/替补/带图条件件/凭据换代；两线共建,注记在案）
# ——T3 v10.3 基座(2026-10-07 夜,经 5bfdeee 入库)：三列分账 v1(prereg xline §2.9)：judge 分类
#   权威=analysis/t3_trichotomy.py(单点实现,selftest 锚)；green 拆 phys_green;gate_intercept=
#   门触发+完整恢复四条(受控中止/完整降落/disarm=1/无T2fail)全齐=计入5/5+成色注记;
#   intercept_incomplete=四条不齐=不计红绿,换轮重试占门拦截预算 ≤3/格,批总物理轮 ≤15;
#   5/5 判定=(物理绿+门拦截计入 ≥5)∧物理绿 ≥PHYS_FLOOR(默认 3,--phys-floor 用户窗内可改);
#   历史轮零重判;tag=双链核验制(5/5 内嵌全绿 ∧ T3 独立复核 X4_T3_REVIEW_CONFIRM,60s×60 轮询)。
# ——T1 v11.20 增量(本融合提交)：①新五位形=绿格 11 gyr 升序前 5 E12O(1.28)/NE8O(1.36)/
#   NE12O(1.39)/S12P(1.48)/E8O(1.50),goal=出生锚定(1.01,0.98,1.0)+dir_unit×dist,方向分布
#   E/NE/NE/S/E,同格双绿 E12O 保留;替补顺位 6/7=S8O(1.54)/N8P(1.56),真 FAIL 格换格 ≤2/批;
#   ②双门挂载=vins_smoke --gate --gate-params(ROC 通过后冻结版,preflight 校验 frozen);
#   ③带图条件件=批内首例跳变族真 FAIL(JUMP>0.5)∧定因全排除(10-07 在册)→后续 ≤2 轮带图
#   (1e 输入面裁决素材,13.9G/轮);④栈+config 凭据换代制(--expect-node/lib/cfg,零栈改动红线);
#   ⑤ENV-ABORT(pregate block)分支=pregate-block 类,env 重试域(不计三列);⑥force_cleanup=
#   rosmaster 域过滤(1e 回放共存保护,x5 面);⑦X4_TAG_PENDING 判读指针=动态已飞格清单。
# 碰撞注记：10-07 03:1x T1 曾误覆写 T3 工作树版(其 staged 版经 5bfdeee 已保全);本融合以
#   T3 入库版为基,T1 增量以上;两线 STATUS 在案。
# 用法: bash x4_batch.sh --arm-banner "guard=1 sane_p=50.0 sane_v=15.0" \
#   --expect-node <md5> --expect-lib <md5> --expect-cfg <md5> --gate-params <冻结版json> \
#   [--phys-floor N] [--dry] [--skip TAG,...]
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
L="$HOME/sitl_sim"
WS="$HOME/catkin_ws"
EVD="$HOME/sitl_sim/t1_evidence/v11_20_2026-10-07"
SUM="$EVD/x4_batch_report.md"
HEARTBEAT_MIN=10
ARM_EXPECT=""; EXPECT_NODE=""; EXPECT_LIB=""; EXPECT_CFG=""
GATE_PARAMS="$L/t1_gate_params.json"
GATE_ON=1
DRY=0
PHYS_FLOOR=3
PHY_ROUNDS_CAP=15
SKIP_TAGS=""
while [ $# -gt 0 ]; do case "$1" in
  --arm-banner) ARM_EXPECT="$2"; shift 2;;
  --expect-node) EXPECT_NODE="$2"; shift 2;;
  --expect-lib) EXPECT_LIB="$2"; shift 2;;
  --expect-cfg) EXPECT_CFG="$2"; shift 2;;
  --gate-params) GATE_PARAMS="$2"; shift 2;;
  --no-gate) GATE_ON=0; shift;;
  --phys-floor) PHYS_FLOOR="$2"; shift 2;;
  --dry) DRY=1; shift;;
  --skip) SKIP_TAGS=",$2,"; shift 2;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
[ -z "$ARM_EXPECT" ] && { echo "need --arm-banner"; exit 2; }
[ -z "$EXPECT_NODE" ] || [ -z "$EXPECT_LIB" ] || [ -z "$EXPECT_CFG" ] && { echo "need --expect-node/--expect-lib/--expect-cfg(栈+config 凭据换代制)"; exit 2; }

# ---------- 五位形(goal=出生锚定 1.01,0.98,1.0+dir_unit×dist;O=obstacles/P=plain) ----------
BX=1.01; BY=0.98; BZ=1.0
POSITIONS=()
add() { # tag dist world ux uy → 追加队尾(替补动态入队可见)
  local tag="$1" dist="$2" world="$3" ux="$4" uy="$5" gx gy GA
  gx=$(python3 -c "print('%.3f' % ($BX + $ux*$dist))")
  gy=$(python3 -c "print('%.3f' % ($BY + $uy*$dist))")
  GA=""
  [ "$GATE_ON" = "1" ] && GA=" --gate --gate-params $GATE_PARAMS"
  POSITIONS+=("${tag}|--world $world --goal $gx $gy $BZ --budget 200$GA")
}
SQ=0.7071067811865476
add X4_E12O  12 sitl_world_obstacles 1  0
add X4_NE8O   8 sitl_world_obstacles $SQ $SQ
add X4_NE12O 12 sitl_world_obstacles $SQ $SQ
add X4_S12P  12 sitl_world_plain     0  -1
add X4_E8O    8 sitl_world_obstacles 1  0
# 替补顺位 6/7(真 FAIL 格处置,默认不飞;换格 ≤2/批 预注册)
SUBS=("X4_S8O|8|sitl_world_obstacles|0|-1" "X4_N8P|8|sitl_world_plain|0|1")
GOALS_MD5=$(for pos in "${POSITIONS[@]}"; do echo "$pos"; done | md5sum | cut -c1-8)

retry_budget=3
consec_door=0
subs_used=0
declare -A retried gate_retried
GREENS=0; TOTAL=0            # GREENS=物理绿;TOTAL=物理轮
GATE_INTERCEPTS=0
IMAGES_LEFT=0                # 带图条件件余量(首例跳变族真 FAIL 置 2)
FLOWN=()                     # 已飞格清单(X4_TAG_PENDING 判读指针正源)
GATEHIT_LOG="$EVD/x4_gatehit_stats.log"

w() { echo "[$(date '+%F %T')] $*" | tee -a "$SUM"; }
wl() { echo "[$(date '+%F %T')] $*" >> "$SUM"; }  # 判读内部专用(文件写;$( ) 捕获多行坑热修)
status_line() { python3 "$L/status_append.py" "$*" >/dev/null 2>&1 || true; }

force_cleanup() {  # rosmaster 域过滤(私有 master 回放件保护;1e 共存),余 pkill -x 名字级
  local p my_m="${ROS_MASTER_URI:-http://localhost:11311}" pm m
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
  local M_NODE M_LIB M_CFG DF_G CFG PXW
  M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" 2>/dev/null | cut -c1-8)
  M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" 2>/dev/null | cut -c1-8)
  M_CFG=$(md5sum "$WS/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml" | cut -c1-8)
  [ "$M_NODE" = "$EXPECT_NODE" ] && [ "$M_LIB" = "$EXPECT_LIB" ] || { w "ABORT_STACK md5=$M_NODE/$M_LIB expect=$EXPECT_NODE/$EXPECT_LIB(纯脚本面红线:门工程零栈改动)"; exit 9; }
  [ "$M_CFG" = "$EXPECT_CFG" ] || { w "ABORT_CONFIG md5=$M_CFG expect=$EXPECT_CFG(X5 批同款臂,批前恢复未完成?)"; exit 9; }
  if [ "$GATE_ON" = "1" ]; then
    python3 -c "import json,sys;sys.exit(0 if json.load(open('$GATE_PARAMS')).get('frozen') else 1)" \
      || { w "ABORT_GATE_PARAMS 未冻结(ROC 通过后冻结版才可上真轮——任务书单元3前置)"; exit 9; }
  else
    w "  --no-gate 模式(预注册分支:门不可靠→无门基线,判读不带门语义,5/5 全物理才算数)"
  fi
  DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
  [ "$DF_G" -lt 20 ] && { w "ABORT_DISK ${DF_G}G"; exit 9; }
  pgrep -x gzserver >/dev/null 2>&1 && { w "ABORT_RESIDUE gzserver alive"; exit 9; }
  for wf in sitl_world_obstacles sitl_world_plain; do
    [ -f "$WS/sitl_sim/worlds/$wf.world" ] || { w "ABORT_WORLD $wf.world missing(repo)"; exit 9; }
    PXW="$HOME/PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/$wf.world"
    [ -f "$PXW" ] || { w "ABORT_WORLD $wf.world not staged in PX4 worlds dir"; exit 9; }
    [ "$(md5sum "$WS/sitl_sim/worlds/$wf.world" | cut -d" " -f1)" = "$(md5sum "$PXW" | cut -d" " -f1)" ] \
      || { w "ABORT_WORLD $wf.world repo!=PX4-staged (md5 drift)"; exit 9; }
  done
  CFG="$WS/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml"
  grep -q '^t2_vision_loss: 0' "$CFG" && grep -q '^t2_cost_gate: 1' "$CFG" \
    && grep -q '^t2_staged_depth_gate: 1' "$CFG" && grep -q '^t2_stream_guard: 1' "$CFG" \
    || { w "ABORT_ARM_CONFIG canonical 未处 v2 臂态(须 loss=0/cost_gate=1/staged=1/guard=1): $(grep -E '^t2_(vision_loss|cost_gate|staged_depth_gate|stream_guard)' "$CFG" | tr '\n' ' ')"; exit 9; }
  w "preflight OK stack=$M_NODE/$M_LIB cfg=$M_CFG gate=$GATE_PARAMS df=${DF_G}G arm_banner='$ARM_EXPECT' goals_md5=$GOALS_MD5 cells=${#POSITIONS[@]}"
}

live_row() { echo -e "$(date '+%F %T')\t$1\t$2" >> "$EVD/x4_passmap_live.log"; }

judge_round() {  # $1=tag $2=run_dir → class（T3 v10.3：trichotomy 权威+legacy 兜底）
  local TAG="$1" D="$2" RES FAILN ANCH JUMP ARR CF WA NEVER TRI TGATE TCLASS
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
  wl "  RESULT=$RES T2fail=$FAILN neverflew=$NEVER jump=$JUMP arrive=$ARR $DISARM cf=${CF:-?}"
  wl "  ${ANCH:-no-dual-anchor}"
  wl "  ${WA:0:200}"
  TRI=$(python3 "$WS/sitl_sim/analysis/t3_trichotomy.py" "$D" --cf "${CF:-none}" 2>/dev/null || true)
  TGATE=$(echo "$TRI" | grep -m1 'GATEHIT-STAT')
  TCLASS=$(echo "$TRI" | grep -m1 -oE 'class=[a-z_-]+' | cut -d= -f2)
  if [ -n "$TGATE" ]; then
    echo "[$(date '+%F %T')] $TAG $TGATE" >> "$GATEHIT_LOG"
    wl "  $TGATE"
    wl "  $(echo "$TRI" | grep -m1 'TRICHOTOMY')"
  else
    wl "  GATEHIT-STAT: unavailable(分类器缺失→legacy 兜底,如实降级)"
  fi
  live_row "$TAG" "RES=$RES jump=$JUMP arr=$ARR cf=${CF:-?} tri=${TCLASS:-na}"
  if [ "$RES" = "ENV-FAIL" ]; then echo "env"; return; fi
  if [ "$NEVER" -ge 1 ] || [ "$FAILN" -ge 3 ]; then echo "hostile"; return; fi
  case "$TCLASS" in
    phys_green|gate_intercept|intercept_incomplete|pregate-block) echo "$TCLASS"; return;;
  esac
  # legacy 兜底（分类器不可用）
  if [ "$RES" = "PASS" ]; then echo "phys_green"; return; fi
  if [ "${CF:-}" = "controlled" ]; then echo "gate_intercept"; return; fi
  if [ "$RES" = "FAIL" ]; then
    local doorok
    doorok=$(python3 -c "print(1 if float('$JUMP')<=0.5 and 0.75<=float('$ARR')<=1.2 else 0)" 2>/dev/null || echo 0)
    [ "$doorok" = "1" ] && { echo "door"; return; }
    echo "fail"; return
  fi
  echo "fail"
}

run_position() {  # $1=tag $2=args
  local TAG="$1" ARGS="$2" D RC CLASS BANNER KNOBS IMGENV
  if [ "$TOTAL" -ge "$PHY_ROUNDS_CAP" ]; then
    w "== position $TAG SKIPPED (批物理轮上限 $PHY_ROUNDS_CAP 达到;预注册防凑数终止)"
    return 0
  fi
  TOTAL=$((TOTAL+1)); FLOWN+=("$TAG")
  w ""
  w "== position $TAG (物理轮 #$TOTAL/$PHY_ROUNDS_CAP;满足 $((GREENS+GATE_INTERCEPTS))/5|phy=$GREENS gate=$GATE_INTERCEPTS)"
  if [ "$DRY" = "1" ]; then w "  DRY: would run vins_smoke $ARGS"; return 0; fi
  IMGENV=""
  if [ "$IMAGES_LEFT" -gt 0 ]; then
    IMGENV="VINS_SMOKE_IMAGES=1"; IMAGES_LEFT=$((IMAGES_LEFT-1))
    w "  带图轮启用(1e 输入面裁决素材,余 $IMAGES_LEFT)"
  fi
  eval "${IMGENV} timeout 900 bash $L/vins_smoke.sh $ARGS --tag $TAG" </dev/null > "/tmp/${TAG}_console.log" 2>&1
  RC=$?
  [ "$RC" = "124" ] && force_cleanup
  D=$(ls -dt "$L"/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1)
  if [ -z "$D" ]; then
    w "  NO-RUNDIR rc=$RC (timeout-suicide?)"; CLASS="timeout"
  elif grep -aq "RESULT=ENV-ABORT" "$D/RESULT.txt" 2>/dev/null; then
    w "  ENV-ABORT(pregate block/重试耗尽)→pregate-block 类(分母外,env 重试域)"
    CLASS="pregate-block"
  elif [ ! -s "$D/simvins.log" ] || grep -aq "FATAL" "$D/round.log" 2>/dev/null; then
    w "  ENV-EARLY-DEATH: simvins.log 缺席/轮 FATAL 环境门(非臂面)→env 类"
    CLASS="env"
  else
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
    phys_green)
      GREENS=$((GREENS+1)); consec_door=0
      status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG 物理绿($GREENS 物理+${GATE_INTERCEPTS} 拦截=$((GREENS+GATE_INTERCEPTS))/5) | 批处理 | 三列分账v1(phys-floor=$PHYS_FLOOR)";;
    gate_intercept)
      GATE_INTERCEPTS=$((GATE_INTERCEPTS+1)); consec_door=0
      w "  门拦截计入:恢复链四条全齐=位形达成(成色注记=非物理绿;GATEHIT-STAT 在案)"
      status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG 门拦截计入($GREENS 物理+${GATE_INTERCEPTS} 拦截=$((GREENS+GATE_INTERCEPTS))/5) | 批处理 | 明细=$GATEHIT_LOG";;
    intercept_incomplete|pregate-block)
      consec_door=0
      if [ "${gate_retried[$TAG]:-0}" -lt 3 ] && [ "$TOTAL" -lt "$PHY_ROUNDS_CAP" ]; then
        gate_retried[$TAG]=$(( ${gate_retried[$TAG]:-0} + 1 ))
        w "  retry scheduled ($CLASS;gate-retry ${gate_retried[$TAG]}/3, 物理轮 $TOTAL/$PHY_ROUNDS_CAP;不计红不计绿)"
        status_line "$(date +%H:%M) | T1 | x4_batch 心跳: $TAG $CLASS→换轮重试(门拦截预算 ${gate_retried[$TAG]}/3) | 批处理"
        run_position "$TAG" "$ARGS"
      else
        w "  no gate-retry left for $TAG ($CLASS;cap ${gate_retried[$TAG]:-0}/3 或物理轮上限 $PHY_ROUNDS_CAP)——位形未达成,如实计未达"
      fi;;
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
      w "  real FAIL -> 计入分母红色,不重试;处置=换格(预注册)"
      awk "BEGIN{exit !($JUMP>0.5)}" 2>/dev/null && echo "$TAG $JUMP $(date '+%F %T')" >> "$EVD/x4_jump_events.txt"
      if [ "$IMAGES_LEFT" = "0" ] && [ -s "$EVD/x4_jump_events.txt" ]; then
        IMAGES_LEFT=2; w "  跳变族真 FAIL 在册+定因全排除(10-07 在册)→带图条件件激活:后续 2 轮带图(1e)"
      fi
      if [ "$subs_used" -lt 2 ]; then
        IFS='|' read -r ST SD SW SUX SUY <<< "${SUBS[$subs_used]}"
        subs_used=$((subs_used+1))
        w "  换格 #$subs_used/2: $ST 替补 $TAG(STATUS 呈报=通知非请示,替补即飞)"
        status_line "$(date +%H:%M) | T1 | x4_batch: $TAG 真 FAIL→换格 $ST(#$subs_used/2,预注册处置) | 批处理"
        add "$ST" "$SD" "$SW" "$SUX" "$SUY"
      else
        w "  换格耗尽(2/2)——真 FAIL 格不再替补"
      fi;;
  esac
}

tag_if_5_5() {
  # 5/5 判定 v1（T3 v10.3 三列分账口径）：物理绿+门拦截计入 ≥5 ∧ 物理绿 ≥PHYS_FLOOR
  if [ $((GREENS + GATE_INTERCEPTS)) -ge 5 ] && [ "$GREENS" -ge "$PHYS_FLOOR" ]; then
    w ""
    w "== 5/5 达成（物理绿 $GREENS + 门拦截计入 $GATE_INTERCEPTS；phys-floor ≥$PHYS_FLOOR 满足）— pre-tag five checks =="
    w "== 成色注记（三列分账 v1;prereg §2.9）== 物理绿=$GREENS / 门拦截计入=$GATE_INTERCEPTS / 物理绿下限 ≥$PHYS_FLOOR(默认案,生效) / 拦截统计行如下 =="
    if [ -f "$GATEHIT_LOG" ]; then
      while IFS= read -r _gl; do w "  $_gl"; done < "$GATEHIT_LOG"
    fi
    local M_NODE M_LIB DF_G UNRES
    M_NODE=$(md5sum "$WS/devel/.private/vins/lib/vins/vins_node" | cut -c1-8)
    M_LIB=$(md5sum "$WS/devel/lib/libvins_lib.so" | cut -c1-8)
    DF_G=$(df -BG --output=avail "$HOME" | tail -1 | grep -oE "[0-9]+")
    UNRES=$(pgrep -c gzserver 2>/dev/null || echo 0)
    w "  stack=$M_NODE/$M_LIB df=${DF_G}G residue=$UNRES STATUS-自写心跳在册"
    cd "$WS" || exit 9
    git status --porcelain | head -3 >> "$SUM"
    # 双链核验制（v11.13 单元2 终审：单点判读禁发证）——链1=本批内嵌判读;链2=T3 独立复核行
    rm -f "$EVD/X4_T3_REVIEW_CONFIRM"
    { echo "X4 TAG PENDING (batch $(date '+%F %T'); arm=$ARM_EXPECT) — 本批判读指针(动态已飞格):"
      for t in "${FLOWN[@]}"; do
        echo "  $(ls -dt "$L"/vins_smoke_runs/run_${t}_* 2>/dev/null | head -1)"
      done
      echo "复核口径：各轮 phys_green ∨ gate_intercept(恢复链四条全齐)+四指标；可复算=python3 sitl_sim/analysis/t3_trichotomy.py <run_dir> --cf <state>(cf 来自 t3_wa_gate --online)；确认写本目录 X4_T3_REVIEW_CONFIRM（含行 'T3-REVIEW: 5/5 CONFIRM'）"
    } > "$EVD/X4_TAG_PENDING"
    status_line "$(date +%H:%M) | T1 | x4_batch 5/5 内嵌全绿——tag 前 T3 独立复核(双链核验制,禁单链发证;确认件=X4_TAG_PENDING→X4_T3_REVIEW_CONFIRM) @T3 | 待复核 | 轮询 60s×60 上限 1h"
    local n=0
    while [ $n -lt 60 ]; do
      [ -f "$EVD/X4_T3_REVIEW_CONFIRM" ] && grep -q "T3-REVIEW: 5/5 CONFIRM" "$EVD/X4_T3_REVIEW_CONFIRM" && break
      sleep 60; n=$((n+1))
    done
    if [ "$n" -ge 60 ]; then
      w "  TAG STALLED: T3 复核 1h 未到——tag 冻结待复核（双链制），人工段"
      touch "$EVD/X4_TAG_STALLED"
      status_line "$(date +%H:%M) | T1 | x4_batch tag 冻结:T3 复核 1h 未到(X4_TAG_STALLED 在案) @T3 @用户 | 待复核 | 5/5 内嵌绿保持有效,复核到即补 tag"
      exit 6
    fi
    w "  T3 复核确认收到: $(grep -m1 'T3-REVIEW' "$EVD/X4_T3_REVIEW_CONFIRM")"
    git tag -a sitl-v0.4 -m "X4 five-position 5/5 green (phys=$GREENS + gate-intercept=$GATE_INTERCEPTS; batch $ARM_EXPECT arm; $(date '+%F %T')). Tag semantics: VINS closed-loop + incident controlled fallback; trichotomy v1 (prereg s2.9, phys-floor>=$PHYS_FLOOR); dual-chain verification (batch embedded + T3 independent review)." && w "  TAG sitl-v0.4 CREATED (双链核验制;成色=物理绿$GREENS+拦截计入$GATE_INTERCEPTS)" || w "  TAG FAILED"
    git push UAV_NUC main --tags 2>&1 | tail -1 >> "$SUM"
    rm -f "$EVD/X4_TAG_PENDING"
    status_line "$(date +%H:%M) | T1 | **X4 五连飞 5/5 达成+T3 复核双链闭合 → tag sitl-v0.4 已打**(臂=$ARM_EXPECT) | 里程碑 | 成色=物理绿$GREENS+门拦截计入$GATE_INTERCEPTS(phys-floor=$PHYS_FLOOR;三列分账v1)"
  else
    w ""
    if [ $((GREENS + GATE_INTERCEPTS)) -ge 5 ] && [ "$GREENS" -lt "$PHYS_FLOOR" ]; then
      w "== 总数 $((GREENS+GATE_INTERCEPTS))/5 达成但物理绿 $GREENS < 下限 $PHYS_FLOOR（默认案 ≥3 生效）——按预注册口径 tag 不打（防'全靠拦截凑 5'成色滑坡），待用户窗 =="
    fi
    w "== BATCH END 物理绿=$GREENS 门拦截计入=$GATE_INTERCEPTS 合计=$((GREENS+GATE_INTERCEPTS))/5 (PAUSE=$([ -f "$EVD/X4_BATCH_PAUSE" ] && echo yes || echo no)) — FAIL/PAUSE 汇总待人工 =="
    w "== 成色注记（三列分账 v1）== 物理绿=$GREENS / 门拦截计入=$GATE_INTERCEPTS / 物理绿下限 ≥$PHYS_FLOOR(默认案) / 明细=$GATEHIT_LOG =="
    status_line "$(date +%H:%M) | T1 | x4_batch 收束:物理绿$GREENS+拦截$GATE_INTERCEPTS=$((GREENS+GATE_INTERCEPTS))/5($( [ -f "$EVD/X4_BATCH_PAUSE" ] && echo PAUSE-撞门 || echo FAIL-汇总))待人工 | 批处理 | 三列分账v1;详见 x4_batch_report.md"
  fi
}

rm -f "$EVD/X4_BATCH_PAUSE" "$EVD/x4_jump_events.txt"
: > "$GATEHIT_LOG"; echo "# GATEHIT 拦截统计行(冻结格式;三列分账 v1 正源) $(date '+%F %T')" >> "$GATEHIT_LOG"
w "# X4 五位形冲刺批报告($(date '+%F %T');臂=$ARM_EXPECT;栈=$EXPECT_NODE/$EXPECT_LIB cfg=$EXPECT_CFG;gate=$GATE_PARAMS;goals_md5=$GOALS_MD5;规则预注册=任务书 v11.20 单元1d/3+T3 v10.3 三列分账v1;融合版注记见脚本头)"
preflight
status_line "$(date +%H:%M) | T1 | x4_batch 启动(五位形 E12O/NE8O/NE12O/S12P/E8O 绿格 gyr 前 5,双门挂载,三列分账,物理轮上限 15,禁人工干预) | 批处理 | 门重试≤3/格;换格≤2;撞门×2=PAUSE;900s 超时自杀;批飞行窗 T2/T3/T4 禁回放大IO(互斥纪律升格)"
# 动态队消费(替补追加可见;for 数组展开一次坑规避)
qi=0
while [ "$qi" -lt "${#POSITIONS[@]}" ]; do
  pos="${POSITIONS[$qi]}"; qi=$((qi+1))
  TAG="${pos%%|*}"; ARGS="${pos#*|}"
  if [[ "$SKIP_TAGS" == *",$TAG,"* ]]; then
    TOTAL=$((TOTAL+1)); w "== position $TAG SKIPPED (续跑条款:已定案,attempt 1 计分母在案)"
    continue
  fi
  run_position "$TAG" "$ARGS"
  if [ $((GREENS + GATE_INTERCEPTS)) -ge 5 ] && [ "$GREENS" -ge "$PHYS_FLOOR" ]; then
    break
  fi
done
tag_if_5_5
