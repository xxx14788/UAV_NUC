# -*- coding: utf-8 -*- relaunched 02:2x with ROS env fix
#!/usr/bin/env bash
# T2-U2 全库回归串行队列 (2026-10-01, 任务书 v6.0)
# 6 可回放袋, 复用 t3_replay.sh 使产出目录格式与 T3 t3_wa_gate 直接兼容
# 红线: 单机一路 vins_node; 每袋前 pgrep 检查; 私有 master 11313
set -u
# 非交互 shell 下 set -u + ROS profile.d 链会炸(unbound),预置两变量
export ROS_DISTRO=noetic ROS_MASTER_URI=http://localhost:11311
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
REP="$HOME/catkin_ws/sitl_sim/analysis/t3_replay.sh"
LOG="$HOME/sitl_sim/t2_u2_replay_queue.log"
RUNS="$HOME/sitl_sim/vins_smoke_runs"
BAGDIR="$HOME/sitl_sim/bags"

TAGS=(Y4_X1final_173345 Y4_X1img_015950 Y4B_CTRL2_route112652 Y4B_hover_203248 Y4W_t2w5_p1b_shift Y4W_t2w5_p2_215545)
PATHS=("$RUNS/run_X1final_173345/flight.bag" "$RUNS/run_X1img_015950/flight.bag" \
       "$BAGDIR/t2v3_route_112652.bag" "$BAGDIR/t2v3_hover_203248.bag" \
       "$BAGDIR/t2w5_p1b_shift.bag" "$BAGDIR/t2w5_p2_215545.bag")

echo "[u2] $(date '+%F %T') ===== U2 queue start (6 bags, canonical frozen: HEAD e29d3d3) =====" >> "$LOG"
for i in "${!TAGS[@]}"; do
  tag="${TAGS[$i]}"; bag="${PATHS[$i]}"
  if ! [ -f "$bag" ]; then echo "[u2] $(date '+%F %T') MISSING bag $bag, skip" >> "$LOG"; continue; fi
  if pgrep -x vins_node >/dev/null 2>&1; then
    echo "[u2] $(date '+%F %T') ABORT: foreign vins_node alive before $tag" >> "$LOG"; exit 1
  fi
  echo "[u2] $(date '+%F %T') ($((i+1))/6) $tag  bag=$(basename "$bag")" >> "$LOG"
  bash "$REP" "$tag" "$bag" "$CFG" 11313 >> "$LOG" 2>&1
  echo "[u2] $(date '+%F %T') ($((i+1))/6) $tag exit=$? alive=$(cat "$HOME/sitl_sim/t3_results/${tag}_$(basename "$bag" .bag)/vins_alive.txt" 2>/dev/null)" >> "$LOG"
  sleep 5
done
echo "[u2] $(date '+%F %T') ===== U2 QUEUE DONE =====" >> "$LOG"
