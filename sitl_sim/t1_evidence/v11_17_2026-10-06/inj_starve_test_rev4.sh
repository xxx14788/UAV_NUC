#!/usr/bin/env bash
# inj_starve_test.sh — v11.17 starve DoD 注入器 rev3（pid 门控 burst）
# usage: inj_starve_test.sh <TAG> <mode>  (ctor|postinit|postbeat)
# 教训链：A1(burst 落存活窗被处理)→收紧窗→STARVEOLD3(spawn<1s 仍泄漏)→pid 门控
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
TAG="$1"; MODE="$2"; GX=8.0; GY=-1.0; GZ=1.0
D=""
for i in $(seq 1 300); do D=$(ls -dt "$HOME"/sitl_sim/vins_smoke_runs/run_${TAG}_* 2>/dev/null | head -1); [ -n "$D" ] && break; sleep 0.2; done
[ -n "$D" ] || { echo "INJ-FAIL no rundir for $TAG"; exit 1; }
# burst=round 起点即发(rundir 出现即 SITL 未起,订阅者必无;rostopic pub -1 闩锁 3s
# 窗也远早于 spawn——rev3 教训:pid 门控挡不住闩锁跨 spawn 投递)
sleep 1
for i in 1 2 3; do
  timeout 1 rostopic pub -1 /move_base_simple/goal geometry_msgs/PoseStamped     "{header: {frame_id: 'world', }, pose: {position: {x: $GX, y: $GY, z: $GZ}}}" >/dev/null 2>&1
done
echo "INJ: early-goal x3 at round-start (race sim, pre-SITL, provably lost)"
while [ ! -f "$D/planner.log" ]; do sleep 0.1; done
P=""
for i in $(seq 1 600); do P=$(pgrep -f "lib/ego_planner/ego_planner_nod[e]" | head -1); [ -n "$P" ] && break; sleep 0.05; done
[ -n "$P" ] || { echo "INJ-FAIL no fsm pid"; exit 1; }
case "$MODE" in
  postinit) while ! grep -q "from INIT to WAIT_TARGET" "$D/planner.log" 2>/dev/null; do sleep 0.05; done;;
  postbeat) while ! grep -q "\[FSM\]: state:" "$D/planner.log" 2>/dev/null; do sleep 0.05; done;;
esac
kill -STOP "$P" && echo "INJ: SIGSTOP ego_planner_node pid=$P mode=$MODE"
