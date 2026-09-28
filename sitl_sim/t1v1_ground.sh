#!/usr/bin/env bash
# T1-v5 V1.2 地面轮：VINS 五件套 + px4ctrl 常驻（不起飞）+ 60s 静置 bag
# + V4.2 mavcmd 511 提频实测（5000us 30s 窗 + 2500us 15s 探顶）
# + V3 --with-sitl 在线回归。
# 编排骨架复用 T2 的 t2v3_flight.sh（致谢；差异：px4ctrl 常驻、debugPx4ctrl
# 双话题增录、60s 静置、511 探针序列、锁 owner 前缀 T1）。
# 用法: 先 sitl_lock.sh get T1-v12-HHMM 再 nohup bash t1v1_ground.sh &
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
LOG() { echo "[$(date +%H:%M:%S)] $*"; }
L="$HOME/sitl_sim"

# ---------- 锁校验（T1 前缀） ----------
cur=$(readlink "$L/SITL.lock" 2>/dev/null || true)
echo "$cur" | grep -q '^T1' || { LOG "FATAL 未持T1锁(cur=$cur)"; exit 1; }

# ---------- 清场与基座 ----------
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清($A/$B)"; exit 1; }
pgrep -x roscore >/dev/null || { nohup roscore >/dev/null 2>&1 & sleep 3; }
rosparam set /use_sim_time true 2>/dev/null || true
yes | rosnode cleanup >/dev/null 2>&1
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

# ---------- SITL + mavros ----------
SITL_WORLD=sitl_world_obstacles nohup bash "$L/start_sitl_vins.sh" \
  > "$L/t1v1_sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; bash "$L/sitl_lock.sh" release T1 >/dev/null 2>&1; exit 1; }
LOG "SITL up"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$L/t1v1_mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; bash "$L/sitl_lock.sh" release T1 >/dev/null 2>&1; exit 1; }
LOG "mavros up"

# ---------- V4.2 511 提频实测（先测频后录 bag） ----------
hz_measure() {  # $1=窗秒 → 输出平均率
  timeout $(( $1 + 5 )) rostopic hz /mavros/imu/data_raw 2>/dev/null \
    | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}'
}
rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0 2>/dev/null; sleep 3
HZ1=$(hz_measure 30); LOG "511@5000us(200Hz 请求) 实测 ${HZ1:-无输出} Hz"
rosrun mavros mavcmd long 511 105 2500 0 0 0 0 0 2>/dev/null; sleep 3
HZ2=$(hz_measure 15); LOG "511@2500us(400Hz 请求) 实测 ${HZ2:-无输出} Hz"
rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0 2>/dev/null; sleep 2
LOG "511 回落 5000us（与 T2 编排一致）"
echo "$(date '+%F %T') 511: req200=${HZ1:-NA}Hz req400=${HZ2:-NA}Hz" >> "$L/t1_evidence/v4_511_rates.log"

# ---------- VINS + px4ctrl（地面常驻,不起飞） ----------
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$L/t1v1_simvins.log" 2>&1 &
sleep 3
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$L/t1v1_px4ctrl.log" 2>&1 &
sleep 3
if ! rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers; then
  LOG "px4ctrl 无响应,重启"; pkill -f run_ctrl_sitl_vins; sleep 2
  nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch >> "$L/t1v1_px4ctrl.log" 2>&1 &
  sleep 3
fi
rostopic info /debugPx4ctrl/fsm_state 2>/dev/null | grep -q Publishers \
  && LOG "px4ctrl up, fsm_state 可读" || LOG "WARN fsm_state 不可读"

# ---------- 录制（含 init 前——捕获首条瞬态） ----------
BAG="$L/bags/t1v1_ground_$(date +%H%M%S).bag"
LOG "bag: $BAG"
nohup rosbag record -O "$BAG" \
  /iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw \
  /mavros/imu/data_raw /mavros/imu/data /mavros/local_position/odom /mavros/local_position/pose \
  /mavros/state /mavros/vision_pose/pose /vins_estimator/odometry \
  /vins_estimator/imu_propagate /vins_estimator/feature_pts \
  /debugPx4ctrl /debugPx4ctrl/fsm_state /px4ctrl/takeoff_land \
  /gazebo/model_states \
  > "$L/t1v1_record.log" 2>&1 &
REC_PID=$!
sleep 3

# ---------- V3 --with-sitl 在线回归 ----------
bash "$L/env_health_check.sh" --with-sitl > "$L/t1_evidence/v3_withsitl_regression.log" 2>&1
LOG "env_health --with-sitl rc=$? (log: t1_evidence/v3_withsitl_regression.log)"

# ---------- VINS init 等待 + 60s 静置 ----------
ok=0; for i in $(seq 1 60); do sleep 2
  rostopic echo -n1 /vins_estimator/imu_propagate/pose/pose/position 2>/dev/null | grep -q 'x:' && { ok=1; break; }; done
if [ $ok = 1 ]; then
  T0=$(date +%s)
  LOG "VINS init 完成(首条 imu_propagate)，静置 60s 起算"
  sleep 60
  LOG "静置 60s 完成(耗时 $(( $(date +%s) - T0 ))s)"
else
  LOG "WARN 120s 内未见 imu_propagate（init 未完成）——仍录满 60s 供失败分析"
  sleep 60
fi

kill -INT $REC_PID 2>/dev/null; sleep 3

# ---------- 清场（同 T2 harness） ----------
pkill -f 'simulator_mavlink' 2>/dev/null; pkill -f 'sitl_run.sh' 2>/dev/null
pkill -f 'bin/px4' 2>/dev/null; pkill -x gzserver 2>/dev/null; pkill -x gzclient 2>/dev/null
pkill -f '02_start_mavros' 2>/dev/null; pkill -x mavros_node 2>/dev/null
pkill -f 'run_ctrl_sitl_vins' 2>/dev/null
pkill -f 'src/launch/sim_vins.launch' 2>/dev/null; pkill -f 'vins_node' 2>/dev/null
sleep 3
rm -f "$L/SITL.lock"
LOG "V1.2 地面轮完成 bag=$BAG"
