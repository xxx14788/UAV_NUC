#!/usr/bin/env bash
# t1_fix_validate_bare.sh — E8P 毒域修复裸链验证 v1.0（2026-10-11 收官册补件）
# 判据(预注册): 修复后 /mavros Publications 不含 /move_base_simple/goal → 源根除。
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
OUT=/tmp/fix_validate
mkdir -p "$OUT"
exec > >(tee "$OUT/exp.log") 2>&1
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { echo "FATAL SITL 未清"; exit 1; }
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99
SITL_WORLD=sitl_world_plain nohup bash "$HOME/sitl_sim/start_sitl_vins.sh" > "$OUT/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { echo "FATAL SITL 未起"; exit 1; }
echo "[$(date +%T)] SITL up — 起 mavros v2（noMission pluginlist）"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$OUT/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { echo "FATAL mavros 未连"; exit 1; }
echo "[$(date +%T)] mavros up — 插件加载面:"
grep -E "Plugin (mission|waypoint)" "$OUT/mavros.log" | head -3 || echo "(mission 插件零加载行=黑名单生效)"
echo "=== 判据: /mavros Publications 是否仍含 goal 话题 ==="
timeout 12 rosnode info /mavros 2>/dev/null > "$OUT/mavros_node_info.txt"
if grep -q "move_base_simple/goal" "$OUT/mavros_node_info.txt"; then
  echo "VERDICT=FAIL: 仍 advertise /move_base_simple/goal"
else
  echo "VERDICT=PASS: /move_base_simple/goal 已从 advertise 面消失（源根除）"
fi
grep -c "mission" "$OUT/mavros_node_info.txt" | sed "s/^/mission 相关话题数: /"
pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
sleep 3; echo "[$(date +%T)] DONE"
