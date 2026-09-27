#!/usr/bin/env bash
# U6.1:W2 路径A实测——sitl_north_500hz.world(0.002s 步长)下:
# a) sim vs wall 漂移(RTF) b) IMU 跳档表(SET_MESSAGE_INTERVAL) c) CPU
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HOME/sitl_sim/t1_evidence/u6_500hz_2026-09-28"
mkdir -p "$OUT"; cd "$OUT"
source /opt/ros/noetic/setup.bash
source $HOME/catkin_ws/devel/setup.bash
echo "=== U6.1 500Hz world $(date) ==="
pgrep -f "Xvfb :9[9]" >/dev/null || (setsid nohup Xvfb :99 -screen 0 1280x1024x24 > "$OUT/xvfb.log" 2>&1 &)
sleep 1
roscore > "$OUT/roscore.log" 2>&1 &
sleep 4
export ROS_MASTER_URI=http://localhost:11311
( cd "$HOME/sitl_sim" && PX4_SITL_WORLD=sitl_north_500hz setsid nohup bash start_sitl_depth.sh > "$OUT/sitl.log" 2>&1 & )
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 240 ]; do ss -uln 2>/dev/null | grep -q ":14580 " && break; sleep 1; done
ss -uln | grep -q ":14580 " || { echo "500Hz SITL FAIL to start 240s"; pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; exit 1; }
echo "SITL up after $(( $(date +%s) - t0 ))s"
nohup roslaunch mavros px4.launch fcu_url:=udp://:14540@127.0.0.1:14580 > "$OUT/mavros.log" 2>&1 &
sleep 12
# RTF: 60s 窗
W0=$(date +%s.%N); S0=$(timeout 3 rostopic echo -n1 /clock/secs 2>/dev/null)
sleep 60
W1=$(date +%s.%N); S1=$(timeout 3 rostopic echo -n1 /clock/secs 2>/dev/null)
python3 -c "
w=$W1-$W0
try:
    s=float('$S1')-float('$S0')
    print(f'RTF: sim {s:.1f}s / wall {w:.1f}s = {s/w:.3f}  (drift {(1-s/w)*100:.1f}%)')
except Exception as e:
    print('RTF: clock read fail', e)
" | tee rtf.txt
# 跳档表
echo "# request(us) measured(Hz)" > imu_sweep.txt
for us in 5000 3000 2000 1000; do
  mavcmd long 511 105 "$us" >/dev/null 2>&1
  sleep 4
  HZ=$(timeout 6 rostopic hz -w 60 /mavros/imu/data 2>/dev/null | grep -o "average rate: [0-9.]*" | grep -o "[0-9.]*" | tail -1)
  echo "$us ${HZ:-FAIL}" | tee -a imu_sweep.txt
  mavcmd long 511 105 20000 >/dev/null 2>&1; sleep 2
done
top -bn1 | head -12 > cpu_snapshot.txt
echo "=== cleanup ==="
pkill -9 -f "roslaunch.*mavro[s]"; pkill -9 -f "lib/mavros/mavros_nod[e]"
pkill -9 -f "bin/px[4]"; pkill -9 -f "gzserve[r]"; pkill -9 -f "make px4_sit[l]"; sleep 2
pkill -9 -f "rosmaste[r]"; pkill -9 -f "rosou[t]"
echo "=== U6.1 done $(date) ==="; cat imu_sweep.txt rtf.txt
