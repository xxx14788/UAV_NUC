#!/bin/bash
# T1 v11.39 单元1 — HAFIX 修复(P-1/P-2/P-3)后 20 轮多场景复验批
# 沿 3d 批编排(t1_batch_3d.sh): S1 hover_1m / S2 hover_3m / S3 transit / S4 land_1m ×5 轮
# 预注册判据(3d 原文冻结): 每轮 HAFIX≥1 ∧ landed=1;场景 PASS=5/5;批 PASS=4 场景全 PASS
# v11.39 新增(P-3): 轮间强清 px4/gz 残留+验证;批前环境检查单落盘;EV 精确登记(grep ev= 非 ls -dt 猜)
# 六环判读链素材=drill log + EV/px4ctrl.log + EV/flight.bag;判读器=t1_rejudge_hafix_v1139.py(批后跑)
set -u
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
echo "- 1. P-3 强清生效验证: 批首强制清场一次(结果见 summary 首行)"
echo "- 2. 首轮 cmd400 毒化不复发观察: 判读器六环第 3 环(KILL ACCEPTED vs FAIL result 码)逐轮取数, 首轮专项呈报"
echo "- 3. FC reboot 副作用清除声明: P-1 修复后 KILL 走 MAV_CMD_DO_FLIGHTTERMINATION(400,param1=1.0) 经 /mavros/cmd/command;"
echo "   代码无 MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN(246) 路径(修复面=px4ctrl KILL 块, grep 无 246);"
echo "   运行面=各轮 px4ctrl.log 无 reboot_notify/P3 通告事件(判读器核)"
echo "- 4. 栈二进制: 本批跑 px4ctrl 修复版(decide_hafix 接线, gtest 37/37)"
} > "$ENVCK"

grep -n '246' "$HOME/catkin_ws/src/px4ctrl/src/PX4CtrlFSM.cpp" | head -3 >> "$ENVCK" 2>/dev/null || echo "(grep 246: 见下行)" >> "$ENVCK"

force_clean "批首" || { echo "FATAL 批首清场失败" | tee -a "$SUM"; exit 1; }

echo "=== v11.39 reverify batch start $(date -Is) ===" | tee -a "$SUM"

run_one() {
  local SCN=$1 GX=$2 GY=$3 GZ=$4 WAIT=$5 RID=$6
  echo "--- $SCN round $RID start $(date +%T) ---" | tee -a "$SUM"
  # v11.39 P-3: WAIT 语义=flying 门超时(注入前 in_air 门,起飞即注入;≥90 覆盖起飞窗)
  DRILL_WAIT=90 bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
  local RC=$?
  # EV 精确登记(P-3: 从 drill log 取, 不 ls -dt 猜)
  local EV
  EV=$(grep -o 'ev=[^ ]*' "$OUT/${SCN}_r${RID}.log" | head -1 | cut -d= -f2)
  [ -z "$EV" ] && EV=$(grep -oP 'EV=\K\S+' "$OUT/${SCN}_r${RID}.log" | head -1)
  echo "$SCN r$RID drill_rc=$RC ev=$EV" | tee -a "$SUM" | tee -a "$OUT/ev_index.txt"
  # 轮间强清(P-3)
  force_clean "$SCN r$RID" || echo "WARN $SCN r$RID 清场不净(已重试)" | tee -a "$SUM"
}

for R in 1 2 3 4 5; do
  run_one S1_hover_1m  0.50 0.50 1.0 25 $R
  run_one S2_hover_3m  0.50 0.50 3.0 25 $R
  run_one S3_transit   1.01 8.98 1.0 25 $R
  run_one S4_land_1m   0.50 0.50 1.0 75 $R
done

echo "=== v11.39 reverify batch done $(date -Is) ===" | tee -a "$SUM"
echo "判读: python3 $L/t1_rejudge_hafix_v1139.py" | tee -a "$SUM"
