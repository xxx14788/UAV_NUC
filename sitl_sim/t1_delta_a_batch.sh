#!/usr/bin/env bash
# t1_delta_a_batch.sh — δ 政策 A 首应用批（工程合并 v1.6 单元3；N8P 格 4 轮绿轮判读批）
# 三件首实战:
#   ①前2绿轮自动录图像=配额制(裁决语义逐字移植 t1_drill_run.sh v1.0 δA 段: PASS→KEPT+计数,
#     非绿→删图像袋保主袋, KEPT-NOBAG 不占配额, "^KEPT " 带空格计数防历史坑复发)
#   ②录制作业验证=轮毕即时(先于裁决): rosbag info 完整性+左右目帧数对齐+首末时戳抽验
#   ③批判读=绿率对照 M3 N8P 基线(0/3 FAIL) + 每轮 j0d 滚入(t3_wa_gate --j0-decomp, 失败不阻塞)
# 轮=N8P 格标准 vins_smoke 流程(无注入): goal(1.010,8.980,1.0) world=obstacles budget=300 --stoploss
# 用法: t1_delta_a_batch.sh [轮数=4]
export ROS_DISTRO=noetic ROS_VERSION=1 \
       ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311} \
       ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
L="$HOME/sitl_sim"
BATCH_DIR="$L/t1_evidence/v113_2026-10-11/delta_a"
mkdir -p "$BATCH_DIR"
OUT="$BATCH_DIR/delta_a_batch_report.csv"
N_ROUNDS="${1:-4}"
GX=1.010; GY=8.980; GZ=1.0; WORLD=sitl_world_obstacles; BUDGET=300
export T1_DELTA_IMG_QUOTA=2
export T1_DELTA_IMG_STATE="$BATCH_DIR/delta_img_state.txt"
touch "$T1_DELTA_IMG_STATE"
echo "cell,round,tag,verdict,jump,arrive,disarm,imgrec,imgbag,kept_after" > "$OUT"

img_integrity_check() {  # $1=EV dir → 输出 $1/images_check.txt
  local ev="$1" bag="$1/images_raw.bag"
  {
    echo "=== δA 录制作业验证 $(date -Is) ==="
    if [ ! -f "$bag" ]; then echo "NOBAG (录制未发生或被盘门跳过)"; return; fi
    rosbag info "$bag" 2>&1 | grep -E "duration|size|topics:|image|imu" | head -12
    python3 - "$bag" <<'PY'
import sys
try:
    import rosbag
    b = rosbag.Bag(sys.argv[1])
    t0s = {}; t1s = {}; ns = {}
    for topic, msg, t in b.read_messages():
        if topic not in ns:
            ns[topic] = 0; t0s[topic] = t; t1s[topic] = t
        ns[topic] += 1; t1s[topic] = t
    print("frame_alignment:")
    l = [k for k in ns if 'cam_left' in k]; r = [k for k in ns if 'cam_right' in k]
    if l and r:
        lk, rk = l[0], r[0]
        print(f"  left  n={ns[lk]} first={t0s[lk]} last={t1s[lk]}")
        print(f"  right n={ns[rk]} first={t0s[rk]} last={t1s[rk]}")
        d = abs(ns[lk] - ns[rk]); span = max(ns[lk], ns[rk], 1)
        print(f"  count_delta={d} ({100.0*d/span:.2f}% of span) → {'ALIGNED' if d <= max(2, 0.02*span) else 'MISALIGNED'}")
        dt0 = abs((t0s[lk]-t0s[rk]).to_sec()); dt1 = abs((t1s[lk]-t1s[rk]).to_sec())
        print(f"  first_stamp_gap={dt0*1000:.1f}ms last_stamp_gap={dt1*1000:.1f}ms")
    b.close()
except Exception as e:
    print(f"INTEGRITY-ERROR {type(e).__name__}: {e}")
PY
  } > "$ev/images_check.txt" 2>&1
  tail -6 "$ev/images_check.txt"
}

for r in $(seq 1 "$N_ROUNDS"); do
  TAG="DAn8p_${r}"
  # δA 配额门(drill 层语义逐字移植)
  KEPT=$(grep -c "^KEPT " "$T1_DELTA_IMG_STATE" 2>/dev/null || true); KEPT=${KEPT:-0}
  IMG_ARGS=""
  if [ "${KEPT:-0}" -lt "${T1_DELTA_IMG_QUOTA:-0}" ]; then
    IMG_ARGS="--img-record"
    echo "$(date -Is) ROUND_START quota=${T1_DELTA_IMG_QUOTA} kept=${KEPT} img=on" >> "$T1_DELTA_IMG_STATE"
  else
    echo "$(date -Is) ROUND_START quota_full img=off" >> "$T1_DELTA_IMG_STATE"
  fi
  echo "[$(date +%H:%M:%S)] == $TAG goal=($GX,$GY,$GZ) world=$WORLD img=${IMG_ARGS:--}"
  setsid bash "$L/vins_smoke.sh" --world "$WORLD" --goal "$GX" "$GY" "$GZ" \
      --tag "$TAG" --budget "$BUDGET" --stoploss $IMG_ARGS > "/tmp/da_${TAG}.log" 2>&1
  EV=$(find "$L/vins_smoke_runs" -maxdepth 1 -name "run_${TAG}_*" ! -name "*envfail*" 2>/dev/null | sort | tail -1)
  RES=$(grep -m1 -oE "RESULT=(PASS|FAIL|ENV-FAIL|GATE-INTERCEPT)" "$EV/RESULT.txt" 2>/dev/null | cut -d= -f2)
  [ -n "$RES" ] || RES="NO-RESULT"
  JMP=$(grep -m1 -oE "pre-post\|=[0-9.]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.]+$")
  ARR=$(grep -m1 -oE "leg1 到位\(真值\) min=[0-9.-]+" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[0-9.-]+$")
  DIS=$(grep -m1 -oE "auto_disarm->[01]" "$EV/RESULT.txt" 2>/dev/null | grep -oE "[01]$")
  # ②录制作业验证(先于裁决, 裁决可能删袋)
  IMGSIZE="-"
  if [ -n "$EV" ] && [ -d "$EV" ]; then
    if [ -f "$EV/images_raw.bag" ]; then
      echo "[$(date +%H:%M:%S)] 录制作业验证:"; img_integrity_check "$EV"
      IMGSIZE=$(du -h "$EV/images_raw.bag" | cut -f1)
    fi
    # ③ j0d 滚入(失败不阻塞)
    python3 "$HOME/catkin_ws/sitl_sim/analysis/t3_wa_gate.py" --j0-decomp "$EV" >/dev/null 2>&1 || true
  fi
  # ① δA 保留/删除裁决(轮毕即时, drill 层逐字移植)
  IMGBAG="$EV/images_raw.bag"
  if [ -n "$IMG_ARGS" ] && [ -n "${T1_DELTA_IMG_STATE:-}" ] && [ -n "$EV" ]; then
    if [ -f "$EV/RESULT.txt" ] && head -5 "$EV/RESULT.txt" | grep -q "RESULT=PASS"; then
      if [ -f "$IMGBAG" ]; then
        echo "KEPT $(date -Is) ev=$EV size=$(du -h "$IMGBAG" | cut -f1) @T4 双用途(E4 像素重放可复用+L2 回放源候选)" >> "$T1_DELTA_IMG_STATE"
        echo "  δA: 绿轮图像袋保留 $(du -h "$IMGBAG" | cut -f1)"
      else
        echo "KEPT-NOBAG $(date -Is) ev=$EV (录制被盘门跳过,见 images_raw.SKIPPED;不占配额)" >> "$T1_DELTA_IMG_STATE"
      fi
    else
      if [ -f "$IMGBAG" ]; then
        rm -f "$IMGBAG"
        echo "DISCARDED $(date -Is) ev=$EV (非绿轮,图像袋删;主 flight.bag 保留)" >> "$T1_DELTA_IMG_STATE"
        echo "  δA: 非绿轮图像袋已删"
      fi
    fi
  fi
  KEPT2=$(grep -c "^KEPT " "$T1_DELTA_IMG_STATE" 2>/dev/null || true); KEPT2=${KEPT2:-0}
  echo "$TAG,$r,$TAG,$RES,${JMP:-NA},${ARR:-NA},${DIS:-NA},${IMG_ARGS:+on},${IMGSIZE},$KEPT2" >> "$OUT"
  echo "  -> $RES jump=${JMP:-NA} arrive=${ARR:-NA} disarm=${DIS:-NA} img=${IMGSIZE} kept=$KEPT2"
  # 机器死亡保护
  if ! pgrep -x gzserver >/dev/null && [ "$RES" != "PASS" ] && [ "$RES" != "FAIL" ]; then
    echo "[δA] 机器死亡保护触发(RES=$RES)——批中止,如实收卷"; exit 3
  fi
done
echo "[δA] 批毕 -> $OUT"; cat "$T1_DELTA_IMG_STATE"
