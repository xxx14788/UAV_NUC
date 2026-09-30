#!/usr/bin/env bash
# T2-U2 续跑 (bags 3-6; bag1/2 已完成): 修复竞态自保误报
set -u
export ROS_DISTRO=noetic ROS_MASTER_URI=http://localhost:11311
CFG="$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo"
REP="$HOME/catkin_ws/sitl_sim/analysis/t3_replay.sh"
LOG="$HOME/sitl_sim/t2_u2_replay_queue.log"
BAGDIR="$HOME/sitl_sim/bags"

# 等待残留 vins_node 消失(僵尸忽略), 最多 30s
wait_vins_free() {
  for i in $(seq 1 15); do
    busy=0
    for pid in $(pgrep -x vins_node 2>/dev/null); do
      st=$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ')
      [ "$st" != "Z" ] && [ -n "$st" ] && busy=1
    done
    [ "$busy" = "0" ] && return 0
    sleep 2
  done
  return 1
}

TAGS=(Y4B_CTRL2_route112652 Y4B_hover_203248 Y4W_t2w5_p1b_shift Y4W_t2w5_p2_215545)
PATHS=("$BAGDIR/t2v3_route_112652.bag" "$BAGDIR/t2v3_hover_203248.bag" \
       "$BAGDIR/t2w5_p1b_shift.bag" "$BAGDIR/t2w5_p2_215545.bag")

echo "[u2] $(date '+%F %T') ===== U2 resume (bags 3-6; 1-2 done: X1final_173345 alive=1 fail@38.8s / X1img_015950 alive=0-but-odom-to-275.4/276s) =====" >> "$LOG"
for i in "${!TAGS[@]}"; do
  tag="${TAGS[$i]}"; bag="${PATHS[$i]}"
  if ! [ -f "$bag" ]; then echo "[u2] $(date '+%F %T') MISSING bag $bag, skip" >> "$LOG"; continue; fi
  if ! wait_vins_free; then
    echo "[u2] $(date '+%F %T') ABORT: live vins_node persists >30s before $tag" >> "$LOG"; exit 1
  fi
  echo "[u2] $(date '+%F %T') ($((i+3))/6) $tag  bag=$(basename "$bag")" >> "$LOG"
  bash "$REP" "$tag" "$bag" "$CFG" 11313 >> "$LOG" 2>&1
  echo "[u2] $(date '+%F %T') ($((i+3))/6) $tag exit=$? alive=$(cat "$HOME/sitl_sim/t3_results/${tag}_$(basename "$bag" .bag)/vins_alive.txt" 2>/dev/null)" >> "$LOG"
  sleep 5
done
echo "[u2] $(date '+%F %T') ===== U2 QUEUE DONE (all 6) =====" >> "$LOG"
