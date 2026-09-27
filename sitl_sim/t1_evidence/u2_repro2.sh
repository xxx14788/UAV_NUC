#!/usr/bin/env bash
# U2 v2:深度 SITL(gazebo_ros 注册)+px4ctrl 复刻白天流水线;同 master 连续 boot,
# kill -9 清场(复刻 smoke)。慢连(>30s)触发捕获。用法: u2_repro2.sh [rounds]
HERE="$(cd "$(dirname "$0")" && pwd)"
ROUNDS="${1:-4}"
OUT="$HOME/sitl_sim/t1_evidence/u2v2_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash

clean9() {  # 复刻 smoke 的 -9 清场:故意不留注销(白天场景),保留 roscore
  pkill -9 -f "roslaunch.*mavro[s]" 2>/dev/null
  pkill -9 -f "lib/mavros/mavros_nod[e]" 2>/dev/null
  pkill -9 -f "roslaunch.*run_ctrl_sit[l]" 2>/dev/null
  pkill -9 -f "px4ctrl_nod[e]" 2>/dev/null
  pkill -9 -f "bin/px[4]" 2>/dev/null
  pkill -9 -f "gzserve[r]" 2>/dev/null
  pkill -9 -f "make px4_sit[l]" 2>/dev/null
  pkill -9 -f "sitl_gazeb[o]" 2>/dev/null
  sleep 4
}

master_state() {  # master 注册表快照(含死注册)
  python3 - <<'PYEOF'
import xmlrpc.client, json
m = xmlrpc.client.ServerProxy('http://localhost:11311')
code, msg, state = m.getSystemState('/snapshot')
pubs, subs, svcs = state
dead_names = set()
import socket
def alive(name):
    try:
        code, _, uri = m.lookupNode('/probe', name)
        host, port = uri.split('//')[1].split(':')
        s = socket.socket(); s.settimeout(0.3)
        s.connect((host, int(port))); s.close(); return True
    except Exception:
        return False
names = sorted({n for grp in pubs+subs for _, nl in grp for n in nl})
alive_set = {n for n in names if alive(n)}
print(json.dumps({
  'topics_total': len(pubs)+len(subs),
  'nodes_total': len(names),
  'nodes_dead': sorted(set(names)-alive_set),
}, ensure_ascii=False, indent=1))
PYEOF
}

capture() {
  local L="$1"
  ss -ulnp > "ss_$L.txt" 2>&1
  master_state > "master_state_$L.json" 2>&1
  local MPID
  MPID=$(pgrep -f "lib/mavros/mavros_nod[e]" | head -1)
  if [ -n "$MPID" ]; then
    timeout 40 gdb -p "$MPID" -batch -ex "thread apply all bt" > "gdb_mavros_$L.txt" 2>&1
  fi
  timeout 25 sudo tcpdump -i lo -s 0 -c 4500 -w "flood_$L.pcap" "udp port 14540 or udp port 14580" 2> "tcpdump_$L.txt"
}

probe() {  # $1=label:计时到第一条 connected:True
  local L="$1" t0 now
  t0=$(date +%s.%N)
  timeout 180 rostopic echo -p /mavros/state/connected 2>/dev/null | grep --line-buffered -m1 "1$" > "/tmp/u2v2_hit_$L" || true
  now=$(date +%s.%N)
  if [ -s "/tmp/u2v2_hit_$L" ]; then
    echo "PROBE_RESULT=CONNECTED elapsed=$(echo "$now $t0" | awk '{printf "%.1f", $1-$2}')s" | tee "probe_$L.txt"
  else
    echo "PROBE_RESULT=TIMEOUT after=180s" | tee "probe_$L.txt"
  fi
}

echo "=== U2v2 start $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 2
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311

for i in $(seq 1 "$ROUNDS"); do
  B="boot$i"
  echo "=== $B $(date +%H:%M:%S) ==="
  master_state > "master_pre_$B.json" 2>&1
  ( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_$B.log" 2>&1 & )
  t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt 150 ]; do
    ss -uln 2>/dev/null | grep -q ":14580 " && break
    sleep 1
  done
  if ! ss -uln | grep -q ":14580 "; then echo "[$B] SITL FAILED"; clean9; continue; fi
  echo "[$B] 14580 up +$(( $(date +%s) - t0 ))s"
  sleep 10   # 等 gazebo 话题+EKF 就绪(白天同款节奏)
  nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557 > "$OUT/mavros_$B.log" 2>&1 &
  ( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl_$B.log" 2>&1 & )
  probe "$B"
  EL=$(grep -o "elapsed=[0-9.]*" "probe_$B.txt" 2>/dev/null | cut -d= -f2 | tr -d s)
  SLOW=$(awk -v e="${EL:-999}" 'BEGIN{print (e>30)?1:0}')
  [ "$SLOW" = 1 ] && { echo "=== $B SLOW (${EL}s) capturing ==="; capture "$B"; }
  clean9
done
pkill -9 -f "roscore" 2>/dev/null; pkill -9 -f "rosmaste[r]" 2>/dev/null; pkill -9 -f "rosou[t]" 2>/dev/null
sleep 3
roscore > "$OUT/roscore2.log" 2>&1 &
sleep 4
echo "=== bootF fresh master $(date +%H:%M:%S) ==="
( cd "$HOME/sitl_sim" && setsid nohup bash start_sitl_depth.sh > "$OUT/sitl_bootF.log" 2>&1 & )
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 150 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
sleep 10
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14557 > "$OUT/mavros_bootF.log" 2>&1 &
( cd "$HOME/sitl_sim" && setsid nohup ./03_start_px4ctrl.sh > "$OUT/px4ctrl_bootF.log" 2>&1 & )
probe "bootF"
clean9
pkill -9 -f "roscore" 2>/dev/null; pkill -9 -f "rosmaste[r]" 2>/dev/null; pkill -9 -f "rosou[t]" 2>/dev/null
echo "=== U2v2 done $(date) ==="
grep -H "PROBE_RESULT" probe_*.txt
