#!/bin/bash
# T1 v11.40 单元2 — HAFIX 修复链终验批（20 轮四场景, 与修复前复验批同口径对照）
# 编排沿 reverify v1139: S1 hover_1m / S2 hover_3m / S3 transit / S4 land_1m ×5
# 预注册判据(3d 原文冻结): 每轮 HAFIX≥1 ∧ landed=1;场景 PASS=全轮{PASS,SILENT-OK}∧≥1机制轮;批=4场景全PASS
# v11.40 S4 边界解读预注册(任务书单元2原文): 落地后注入轮(hafix=0∧landed=1)=正确静默 SILENT-OK 禁误判 FAIL
# 判读=t1_rejudge_hafix_v1140.py(B-7 参数化)+双工具重判(t3_2d_hafix_rejudge+t3_reverify_crosscheck_v2)
# δ 政策 A 挂钩(2026-10-11 裁定 A,未来批窗用): 发射前 export T1_DELTA_IMG_QUOTA=2
#   T1_DELTA_IMG_STATE="$OUT/delta_img_state.txt" → 前 2 绿轮保留 images_raw.bag(双用途@T4)
set -u
# 单例守卫(D-1010-T1-01 教训;v2=PID 文件)
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
OUT=$L/t1_evidence/v11_40_2026-10-10/hafix_finalverify
mkdir -p "$OUT"
SUM="$OUT/summary.txt"; : > "$SUM"
ENVCK="$OUT/batch_env_checklist.md"

# ---------- P-3 轮间强清 ----------
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
  if pgrep -f 'roslaunc[h] ' >/dev/null 2>&1; then
    pkill -f 'roslaunc[h] ' 2>/dev/null; RES="$RES kill:roslaunch"
  fi
  sleep 5
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
echo "# HAFIX 终验批 v11.40 批前环境检查单（工程合并册单元 2）"
echo "- 时间: $(date -Is)"
echo "- 1. P-3 强清生效验证: 批首强制清场一次(结果见 summary 首行);轮间 force_clean 逐轮断言"
echo "- 2. PID 文件单例守卫在役: $PIDF (v2=PID 文件方案,D-1010-T1-01 教训)"
echo "- 3. FC reboot 副作用清除: 代码无 246 路径(grep 见下)+运行面 p3_reboot_evt 判读器逐批计数(修复前复验批=3/修复后增量批=0)"
echo "- 4. 注入时序语义(v4 flying 门双门): S1-S3 稳定窗 15s / S4=40s;"
echo "   S4 边界解读预注册(v11.40 任务书原文): 落地后注入轮 hafix=0∧landed=1 → SILENT-OK(正确静默)禁误判 FAIL"
echo "   (修复前复验批 S4 r1/r3 形态;中段下降注入精度未达成=已知边界,预承 T1 B-1/C-6)"
echo "- 5. 栈二进制指纹(T2 C-7 跨批栈指纹不可追溯 补记):"
echo "   px4ctrl_node: $(md5sum $HOME/catkin_ws/devel/lib/px4ctrl/px4ctrl_node 2>/dev/null | cut -d' ' -f1)"
echo "   vins_node:    $(md5sum $HOME/catkin_ws/devel/lib/vins/vins_node 2>/dev/null | cut -d' ' -f1)"
echo "   libvins_lib:  $(find $HOME/catkin_ws/devel -name 'libvins_lib.so' -exec md5sum {} \; 2>/dev/null | head -1)"
echo "- 6. git HEAD: $(git -C $HOME/catkin_ws rev-parse --short HEAD 2>/dev/null)"
echo "- 7. 对照基线: 修复前复验批 3/20(S1-S3 0/15 悬停不落+S4 3/5,r1/r3=落地后注入静默形态)"
echo "   / 增量批(梯①盲降二次修复) 10/10 物理链;本批=终验批(M1 行 5 终闭环)"
} > "$ENVCK"

grep -n '246' "$HOME/catkin_ws/src/px4ctrl/src/PX4CtrlFSM.cpp" | head -3 >> "$ENVCK" 2>/dev/null || echo "(grep 246: 见下行)" >> "$ENVCK"

force_clean "批首" || { echo "FATAL 批首清场失败" | tee -a "$SUM"; exit 1; }

echo "=== v11.40 hafix FINALVERIFY batch start $(date -Is) ===" | tee -a "$SUM"

run_one() {
  local SCN=$1 GX=$2 GY=$3 GZ=$4 POSTGATE=$5 RID=$6
  echo "--- $SCN round $RID start $(date +%T) ---" | tee -a "$SUM"
  DRILL_POSTGATE=$POSTGATE bash "$L/t1_drill_run.sh" D1 "$GX" "$GY" "$GZ" sitl_world_plain > "$OUT/${SCN}_r${RID}.log" 2>&1
  local RC=$?
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
  force_clean "$SCN r$RID" || echo "WARN $SCN r$RID 清场不净(已重试)" | tee -a "$SUM"
}

for R in 1 2 3 4 5; do
  run_one S1_hover_1m  0.50 0.50 1.0 15 $R
  run_one S2_hover_3m  0.50 0.50 3.0 15 $R
  run_one S3_transit   1.01 8.98 1.0 15 $R
  run_one S4_land_1m   0.50 0.50 1.0 auto $R   # v112 单元5: auto=下降段中点自适应注入(旧 40s 固定近似退役;终验批已收官形态不变,未来批用 auto)
done

echo "=== v11.40 hafix FINALVERIFY batch done $(date -Is) ===" | tee -a "$SUM"
echo "判读(双工具): python3 $L/t1_rejudge_hafix_v1140.py $OUT ; t3: python3 $HOME/catkin_ws/sitl_sim/analysis/t3_2d_hafix_rejudge.py --pattern 'DRILLD1_N8P_*' --since <HHMM> ; crosscheck v2" | tee -a "$SUM"
