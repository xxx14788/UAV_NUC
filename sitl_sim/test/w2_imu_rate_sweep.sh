#!/usr/bin/env bash
# W2:HIGHRES_IMU 请求间隔 → 实际频率 跳档表扫描。
# 前置:SITL+mavros 在线(mavcmd 需要);px4ctrl 不需要。自持锁。
# 机制预期(见 t1_evidence/w2_imu_rate_mechanism.md):mavlink 主循环被 lockstep 4ms 节拍量化,
#   interval ≤ ~4400μs 应得 250Hz,5000μs 得 125Hz(已实测)。
source /opt/ros/noetic/setup.bash
set -u
SIM="$HOME/sitl_sim"
EV="$SIM/t1_evidence/w2_sweep_$(date +%F_%H%M%S).txt"
source "$HOME/catkin_ws/devel/setup.bash" || exit 1

bash "$SIM/sitl_lock.sh" get "T1-w2-$$" >/dev/null 2>&1 || { echo "锁被占用"; exit 1; }
trap 'bash "$SIM/sitl_lock.sh" release T1 >/dev/null 2>&1 || true' EXIT

echo "# W2 IMU rate sweep $(date)" > "$EV"
echo "# cmd: mavcmd long 511 105 <interval_us>  (HIGHRES_IMU)" >> "$EV"
printf "%-14s %s\n" "request(μs)" "measured(Hz)" >> "$EV"

for iv in 5000 4000 3000 2500 2000 1000; do
    rosrun mavros mavcmd long 511 105 "$iv" 0 0 0 0 0 >/dev/null 2>&1 || { echo "$iv MAVCMD-FAIL" >> "$EV"; continue; }
    sleep 2   # 让重配生效
    hz=$(timeout 10 rostopic hz -w 100 /mavros/imu/data 2>/dev/null | grep -o 'average rate: [0-9.]*' | grep -o '[0-9.]*' | tail -1)
    printf "%-14s %s\n" "$iv" "${hz:-timeout}" >> "$EV"
    echo "interval=${iv}us -> ${hz:-timeout} Hz"
done

echo "done -> $EV"
echo "如需 200Hz:见 w2_imu_rate_mechanism.md §3(world 500Hz 步长路径 A / 250Hz 替代路径 B)"
