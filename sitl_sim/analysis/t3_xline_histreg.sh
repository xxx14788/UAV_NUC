#!/usr/bin/env bash
# t3_xline_histreg.sh — 单元2.6 历史在线轮全量回归判读（零翻转验证）
# 对 31 个 RBG 完整轮重跑 round_result.sh（场景名正源，world=sitl_world_obstacles→0.75 门），
# 与历史 RESULT.txt 判定对比；顺产历史到位分布数据。
# 输出: ~/sitl_sim/t3_results/xline_histreg/<run>.new.txt + summary.csv

source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
OUT="$HOME/sitl_sim/t3_results/xline_histreg"
mkdir -p "$OUT"
WORLD=sitl_world_obstacles
echo "run,old,new,flipped,leg1_min_old,leg1_min_new,gate_m" > "$OUT/summary.csv"
for d in "$HOME"/sitl_sim/vins_smoke_runs/run_*; do
  n=$(basename "$d")
  [ -f "$d/RESULT.txt" ] || continue
  [ -f "$d/flight.bag" ] || continue
  [ -f "$d/goal.txt" ] || continue
  # goal.txt: "goal: 7.0 -4.0 1.0 leg2: 0 0 0 0"  (leg2 0=hasl2)
  read -r _ GX GY GZ _ H L2X L2Y L2Z < "$d/goal.txt"
  if [ "$L2X" = "0" ] && [ "$L2Y" = "0" ] && [ "$L2Z" = "0" ]; then H=0; fi
  ARR1=$(tail -1 "$d/arrive_watch.txt" 2>/dev/null || echo absent)
  ARR2=$(tail -1 "$d/arrive_watch2.txt" 2>/dev/null || echo absent)
  bash "$HOME/sitl_sim/round_result.sh" "$d/flight.bag" "$GX" "$GY" "$GZ" "$WORLD" "$d" "$ARR1" "$ARR2" "$H" "$L2X" "$L2Y" "$L2Z" > "$OUT/$n.new.txt" 2>&1
  old=$(grep -m1 '^RESULT=' "$d/RESULT.txt" | cut -d= -f2 | awk '{print $1}')
  new=$(grep -m1 '^RESULT=' "$OUT/$n.new.txt" | cut -d= -f2 | awk '{print $1}')
  l1o=$(grep -m1 -o 'leg1 到位(真值) min=[0-9.-]*' "$d/RESULT.txt" | grep -o '[0-9.-]*$')
  l1n=$(grep -m1 -o 'leg1 到位(真值) min=[0-9.-]*' "$OUT/$n.new.txt" | grep -o '[0-9.-]*$')
  [ "$old" = "$new" ] && fl=0 || fl=1
  echo "$n,$old,$new,$fl,$l1o,$l1n,0.75" >> "$OUT/summary.csv"
  echo "== $n old=$old new=$new flip=$fl leg1 $l1o->$l1n"
done
echo "---- flips ----"
awk -F, 'NR>1 && $4==1' "$OUT/summary.csv"
echo "---- dist (leg1_min_new buckets) ----"
awk -F, 'NR>1{v=$6+0; if(v<0.5)b="<0.50(PASS-zone)"; else if(v<0.75)b="0.50-0.75(flip-zone)"; else if(v<2)b="0.75-2"; else b=">=2"; print b, $1}' "$OUT/summary.csv" | sort | uniq -c | sort -rn
