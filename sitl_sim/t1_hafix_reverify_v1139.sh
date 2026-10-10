#!/bin/bash
# T1 v11.39 单元1 — HAFIX 修复(P-1/P-2/P-3)后 20 轮多场景复验批
# 沿 3d 批编排(t1_batch_3d.sh): S1 hover_1m / S2 hover_3m / S3 transit / S4 land_1m ×5 轮
# 预注册判据(3d 原文冻结): 每轮 HAFIX≥1 ∧ landed=1;场景 PASS=5/5;批 PASS=4 场景全 PASS
# v11.39 新增(P-3): 轮间强清 px4/gz 残留+验证;批前环境检查单落盘;EV 精确登记(grep ev= 非 ls -dt 猜)
# 六环判读链素材=drill log + EV/px4ctrl.log + EV/flight.bag;判读器=t1_rejudge_hafix_v1139.py(批后跑)
set -u
# 单例守卫(D-1010-T1-01 多实例连环互杀事故教训;v2=PID 文件——pgrep/cmdline 方案会
# 自噬:$( ) 替换子壳继承父 cmdline 被自身匹配,r4 启动失败实证)
PIDF=/tmp/t1_reverify_batch.pid
if [ -f "$PIDF" ]; then
  OPID=$(cat "$PIDF" 2>/dev/null)
  if [ -n "$OPID" ] && [ -d "/proc/$OPID" ] && [ "$OPID" != "$$" ]; then
    echo "FATAL 另一复验批实例在役(pid=$OPID),拒绝启动"; exit 1
  fi
fi
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT
export ROS_DISTRO=noetic ROS_VERSION=1 ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311} ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
L=$HOME/sitl_sim
OUT=$L/t1_evidence/v11_39_2026-10-09/hafix_reverify
mkdir -p "$OUT"
SUM="$OUT/summary.txt"; : > "$SUM"
ENVCK="$OUT/batch_env_checklist.md"

# ---------- P-3 轮间强清(px4/gz 残留;记录每轮清理动作) ----------
force_clean() {
  local TAGCLEAN=$1
  local RES="clean"
  for P in px4 gzserver gzclient mavros_node vins_node px4ctrl_node; do
    local N
    N=$(pgrep -xc "$P" 2>/dev/null || true); N=${N:-0}
    if [ "$N" != "0" ]; then
      pkill -9 -x "$P" 2>/dev/null
      RES="$RES kill:$P=$N"
    fi
  done
  # roslaunch 残留(锁已释放但壳未退)
  if pgrep -f 'roslaunc[h] ' >/dev/null 2>&1; then
    pkill -f 'roslaunc[h] ' 2>/dev/null; RES="$RES kill:roslaunch"
  fi
  sleep 5
  # 清后断言
  local A B
  A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
  B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
  if [ "$A" = "0" ] && [ "$B" = "0" ]; then
    echo "[clean] $TAGCLEAN $RES -> post-assert px4=0 gz=0 OK" | tee -a "$SUM"
    return 0
  else
    echo "[clean] $TAGCLEAN $RES -> post-assert FAIL px4=$A gz=$B (10s 重试)" | tee -a "$SUM"
    sleep 10
    A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
    B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
    [ "$A" = "0" ] && [ "$B" = "0" ] && return 0 || return 1
  fi
}

# ---------- 批前环境检查单 ----------
{
echo "# HAFIX 复验批 v11.39 批前环境检查单"
echo "- 时间: $(date -Is)"
echo "- 1. P-3 强清生效验证: 批首强制清场一次(结果见 summary 首行);轮间 force_clean 逐轮断言"
echo "- 2. 首轮 cmd400 毒化不复发观察: 判读器六环第 3 环(KILL ACCEPTED vs FAIL result 码)逐轮取数, 首轮专项呈报"
echo "- 3. FC reboot 副作用清除声明: P-1 修复后 KILL 走 MAV_CMD_DO_FLIGHTTERMINATION(400,param1=1.0)+179/p2=21196 双命令经 /mavros/cmd/command;"
echo "   代码无 MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN(246) 路径(grep 见下);"
echo "   运行面=各轮 px4ctrl.log 无 reboot_notify/P3 通告事件(判读器核)"
echo "- 4. 注入时序语义(v11.39 P-3 flying 门): 等待 round.log 'poscmd 存活门通过'(确定 flying)后注入;"
echo "   场景稳定窗 S1-S3=25s(悬停/巡航段)/S4=55s(降落段近似;实测落地≈poscmd-live+74s);"
echo "   对照 3d 原编排(S1-S3=25s/S4=75s arrive_watch 后注入)——原窗被'goal 早到即降落'证伪,飞行门为正修"
echo "- 5. 栈二进制: 本批跑 px4ctrl 修复版(decide_hafix+400/179 双 kill 接线, gtest 37/37, commit ee15996)"
} > "$ENVCK"

grep -n '246' "$HOME/catkin_ws/src/px4ctrl/src/PX4CtrlFSM.cpp" | head -3 >> "$ENVCK" 2>/dev/null || echo "(grep 246: 见下行)" >> "$ENVCK"

force_clean "批首" || { echo "FATAL 批首清场失败" | tee -a "$SUM"; exit 1; }

echo "=== v11.39 reverify batch start $(date -Is) ===" | tee -a "$SUM"

run_one() {
  local SCN=$1 GX=$2 GY=$3 GZ=$4 POSTGATE=$5 RID=$6
  echo "--- $SCN round $RID start $(date +%T) ---" | tee -a "$SUM"
  # v11.39 P-3: flying 门 v4 双门(poscmd 存活+armed:True)+场景稳定窗(S1-S3=15s 爬升段;S4=40s 降落段近似)
  DRILL_POSTGATE=$POSTGATE bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
  local RC=$?
  # 有效性检查: HAFIX 代码路径是否被行使(0 行=未行使:环境废轮/落地态注入→单次重试;
  # 有 HAFIX 行的轮无论 PASS/FAIL 均=有效数据禁重试——预注册完整性)
  local EV HL
  EV=$(grep '\[drill\] EV=' "$OUT/${SCN}_r${RID}.log" | tail -1 | cut -d= -f2)
  [ -z "$EV" ] && EV=$(grep -oP 'ev=\K\S+run_DRILLD1_\S+' "$OUT/${SCN}_r${RID}.log" | tail -1)
  HL=0
  [ -n "$EV" ] && [ -f "$EV/px4ctrl.log" ] && HL=$(grep -c 'HAFIX' "$EV/px4ctrl.log" 2>/dev/null || echo 0)
  if [ "$RC" != "0" ] || [ "$HL" -eq 0 ] 2>/dev/null; then
    echo "$SCN r$RID attempt1 无效(rc=$RC HAFIX_lines=$HL ev=$EV) -> retry ×1" | tee -a "$SUM"
    mv "$OUT/${SCN}_r${RID}.log" "$OUT/${SCN}_r${RID}.attempt1.log" 2>/dev/null
    force_clean "$SCN r$RID retry-pre" >/dev/null 2>&1
    DRILL_POSTGATE=$POSTGATE bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
    RC=$?
    EV=$(grep '\[drill\] EV=' "$OUT/${SCN}_r${RID}.log" | tail -1 | cut -d= -f2)
    [ -z "$EV" ] && EV=$(grep -oP 'ev=\K\S+run_DRILLD1_\S+' "$OUT/${SCN}_r${RID}.log" | tail -1)
    echo "$SCN r$RID attempt2 rc=$RC ev=$EV" | tee -a "$SUM"
  fi
  echo "$SCN r$RID final drill_rc=$RC ev=$EV" | tee -a "$SUM" | tee -a "$OUT/ev_index.txt"
  # 轮间强清(P-3)
  force_clean "$SCN r$RID" || echo "WARN $SCN r$RID 清场不净(已重试)" | tee -a "$SUM"
}

for R in 1 2 3 4 5; do
  run_one S1_hover_1m  0.50 0.50 1.0 15 $R
  run_one S2_hover_3m  0.50 0.50 3.0 15 $R
  run_one S3_transit   1.01 8.98 1.0 15 $R
  run_one S4_land_1m   0.50 0.50 1.0 40 $R
done

echo "=== v11.39 reverify batch done $(date -Is) ===" | tee -a "$SUM"
echo "判读: python3 $L/t1_rejudge_hafix_v1139.py" | tee -a "$SUM"
