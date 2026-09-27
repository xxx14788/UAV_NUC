#!/usr/bin/env bash
# U3:R3 投递停滞。全链稳定→基线探测→杀 bin/px4(仅 PX4)→立即重启 SITL→
# 重启窗口内连续新 sub 建连探测(fsm=px4ctrl pub / state=mavros pub 双通道)。
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u3_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash

echo "=== U3 start $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_a.log" 2>&1 & )
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
ss -uln | grep -q ":14580 " || { echo "SITL FAIL"; exit 1; }
sleep 8
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl.log" 2>&1 & )
echo "waiting chain stable 25s..."
sleep 25
rostopic list | grep -E "fsm_state|mavros/state" > "$OUT/topics.txt"
echo "=== baseline probes ==="
for i in 1 2 3; do
  t1=$(date +%s.%N); FSM=$(timeout 8 rostopic echo -n1 --noarr /debugPx4ctrl/fsm_state 2>/dev/null | head -1); t2=$(date +%s.%N)
  echo "baseline#$i fsm=$(echo "$t2 $t1"|awk '{printf "%.2f",$1-$2}')s val=$FSM"
done
# 快照:px4ctrl 的 TCP 连接表(基线)
PXPID=$(pgrep -f "px4ctrl_nod[e]" | head -1)
ss -tnp 2>/dev/null | grep -E "$PXPID|11311" > "ss_tcp_baseline.txt"
echo "=== killing PX4 only (bin/px4) at $(date +%H:%M:%S) ==="
pkill -9 -f "bin/px[4]"
sleep 1
echo "=== restarting SITL at $(date +%H:%M:%S) ==="
( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_b.log" 2>&1 & )
bash "$HERE/u3_probe.sh" win1
echo "=== window probe done, capturing post state ==="
ss -tnp 2>/dev/null > "ss_tcp_post.txt"
PXPID2=$(pgrep -f "px4ctrl_nod[e]" | head -1)
[ -n "$PXPID2" ] && timeout 30 gdb -p "$PXPID2" -batch -ex "thread apply all bt" > "gdb_px4ctrl_post.txt" 2>&1
echo "=== U3 measurements done $(date) ==="
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
pkill -9 -f "roslaunch.*run_ctrl_sit[l]"; pkill -9 -f "px4ctrl_nod[e]"
pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"
sleep 2
pkill -9 -f "roscore" 2>/dev/null; pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U3 run complete ==="
