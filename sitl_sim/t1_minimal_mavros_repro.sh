#!/usr/bin/env bash
# t1_minimal_mavros_repro.sh — E8P 毒域最小复现+插件级定位实验 v1.0（2026-10-11 收官册补件）
# 目的: ①裸链（SITL+mavros，无 VINS/planner/px4ctrl）下污染是否独立复现
#       ②rosnode info /mavros advertise 面直查——哪个插件 advertise 了 /move_base_simple/goal
#       ③污染在场时 rostopic info 双向面（上窗嵌套引号失败的补救=独立脚本文件）
# 产物: /tmp/minimal_exp_v2/{goal_check.txt, watch.jsonl, mavros pubs 全清单}
source /opt/ros/noetic/setup.bash          # 先 source 再 set -u（V3 教训,本文件v1首跑踩回）
source "$HOME/catkin_ws/devel/setup.bash"
set -u
OUT=/tmp/minimal_exp_v2
mkdir -p "$OUT"
exec > >(tee "$OUT/exp.log") 2>&1

echo "[$(date +%T)] 清场断言"
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { echo "FATAL SITL 未清(px4=$A gz=$B)"; exit 1; }

echo "[$(date +%T)] 起 roscore + SITL(plain world, 无 vins/planner)"
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99
SITL_WORLD=sitl_world_plain nohup bash "$HOME/sitl_sim/start_sitl_vins.sh" > "$OUT/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { echo "FATAL SITL 未起"; exit 1; }
echo "[$(date +%T)] SITL up"

echo "[$(date +%T)] 起 mavros（标准 px4.launch, 14580）"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$OUT/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { echo "FATAL mavros 未连"; exit 1; }
echo "[$(date +%T)] mavros up"

echo "=== ① rosnode info /mavros Publications（goal 相关段）===" | tee "$OUT/goal_check.txt"
timeout 12 rosnode info /mavros 2>/dev/null > "$OUT/mavros_node_info.txt"
grep -iE "goal|move_base" "$OUT/mavros_node_info.txt" | tee -a "$OUT/goal_check.txt" || echo "( Publications 面无 goal 相关)" | tee -a "$OUT/goal_check.txt"
echo "Publications 总数: $(sed -n '/Publications:/,/Subscriptions:/p' "$OUT/mavros_node_info.txt" | grep -cE '^\s*\*')" | tee -a "$OUT/goal_check.txt"

echo "=== ② rostopic info /move_base_simple/goal（双向）===" | tee -a "$OUT/goal_check.txt"
timeout 8 rostopic info /move_base_simple/goal 2>&1 | tee -a "$OUT/goal_check.txt"

echo "=== ③ 120s 污染观察（裸链,无我方 pub）===" | tee -a "$OUT/goal_check.txt"
timeout 125 python3 "$HOME/catkin_ws/sitl_sim/t1_goal_pollution_watch.py" \
  --out "$OUT/watch.jsonl" --snap-publishers >/dev/null 2>&1
echo "watch 产物:" | tee -a "$OUT/goal_check.txt"
cat "$OUT/watch.jsonl" 2>/dev/null | tee -a "$OUT/goal_check.txt" || echo "(120s 零帧=话题无发布者或零流量)" | tee -a "$OUT/goal_check.txt"

echo "=== ④ mavros 插件 advertise 全谱（node_info 全文另存）==="
wc -l "$OUT/mavros_node_info.txt"

# 清场（实验毕,不留栈）
echo "[$(date +%T)] 实验毕清场"
pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
sleep 3
echo "[$(date +%T)] DONE (产物 $OUT/)"
