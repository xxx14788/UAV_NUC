#!/usr/bin/env bash
# 【v7 定位声明 2026-09-29】本脚本已降级为 511 三档探针/地面静置专用；
# 飞轮（起栈+init 门+起飞+goal+四指标）一律用 vins_smoke.sh（仓库标准,9c7cee9+）。
# 遗留坑已修: init 门 echo 引号(下方 v7 注释处)。分析口径注记见 round_result.sh 头
# 与 docs/vision_acceptance_protocol.md（W3 协议 8de82a9）；PX4 实机参数导出扫描
# 由 param_hygiene.sh 的 PX4_PARAM_EXPORT 环境变量挂接（未设=WARN 跳过,非 FAIL）。
# T1-v5 V1 飞行轮编排（V1.2 地面 60s + V4.2 mavcmd 511 实测；MODE=hover 为 V1.3 备用）。
# 用法: bash v1_flight.sh ground|hover
# 前置: SITL.lock 空闲（本脚本自取 owner=T1-V1，结束时 t3_clean 顺带释放）。
# 产物: ~/catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28/{rate511.txt,RESULT_ground.txt,
#       bag(无图像版,60s+)、各段日志}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
MODE="${1:?ground|hover}"
EV="$HOME/catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28"
mkdir -p "$EV"
LOG() { echo "[$(date +%H:%M:%S)] $*"; }

# ---------- 锁 ----------
LOCK="$HOME/sitl_sim/SITL.lock"
bash "$HOME/sitl_sim/sitl_lock.sh" get T1-V1 || { LOG "FATAL 锁获取失败(原因见上)"; exit 1; }

# ---------- 清场（补杀 t3_clean 不管的 vins/mavros 子进程） ----------
pkill -f 'vins_nod[e]' 2>/dev/null; pkill -f 'vins_to_mavro[s]' 2>/dev/null
pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -f 'gzserve[r]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
sleep 3

# ---------- fresh master + 域配方（use_sim_time 必须在 mavros 前置真, T2b-U6） ----------
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

# ---------- SITL（V1.2 修正: 默认 obstacles world——empty world 无纹理,VINS 走
# "无条件 init" 劣化路径(T2 W3 已立案);obstacles=T2 全部已验证轮次的世界） ----------
export SITL_WORLD="${SITL_WORLD:-sitl_world_obstacles}"
nohup bash "$HOME/sitl_sim/start_sitl_vins.sh" > "$EV/sitl_${MODE}.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
    rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; exit 1; }
LOG "SITL up"

# ---------- mavros（14580 链路） ----------
nohup bash "$HOME/sitl_sim/02_start_mavros.sh" > "$EV/mavros_${MODE}.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
    timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; exit 1; }
T_CONN=$(date +%s); LOG "mavros up (${i}x2s)"

hz_of() { timeout "${2:-20}" rostopic hz "$1" 2>/dev/null | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}'; }

# ---------- V4.2: mavcmd 511 提频实测（105=HIGHRES_IMU→/mavros/imu/data_raw） ----------
# hover 模式不发三档探针，但必须应用 511（否则 T2 preflight 的 IMU>100Hz 门红项中止）
if [ "$MODE" = "ground" ]; then
    R_DEF=$(hz_of /mavros/imu/data_raw 15)
    A1=$(rosrun mavros mavcmd long 511 105 5000 0 0 0 0 0 2>&1 | tail -1); sleep 2
    R_5K=$(hz_of /mavros/imu/data_raw 25)
    A2=$(rosrun mavros mavcmd long 511 105 2500 0 0 0 0 0 2>&1 | tail -1); sleep 2
    R_25=$(hz_of /mavros/imu/data_raw 20)
    A3=$(rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 2>&1 | tail -1)
    {
        echo "V4.2 mavcmd 511 实测 $(date '+%F %T')"
        echo "默认档(未 511):        ${R_DEF:-无输出} Hz"
        echo "511 105 5000(200Hz req): ${R_5K:-无输出} Hz   ack: $A1/$A3"
        echo "511 105 2500(400Hz req): ${R_25:-无输出} Hz   ack: $A2"
    } | tee "$EV/rate511.txt"
    LOG "511 实测完成: def=${R_DEF:-NA} 5000us=${R_5K:-NA} 2500us=${R_25:-NA}"
    sleep 2
else
    rosrun mavros mavcmd long 511 105 4000 0 0 0 0 0 >/dev/null 2>&1
    sleep 2
    R_5K=$(hz_of /mavros/imu/data_raw 20)
    LOG "hover 模式 511 105 4000 应用: ${R_5K:-NA} Hz"
fi

# ---------- VINS + 转发 + px4ctrl ----------
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins_${MODE}.log" 2>&1 &
sleep 3
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl_${MODE}.log" 2>&1 &
sleep 3
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "WARN px4ctrl 未注册(重掷)"; sleep 4; }

# ---------- VINS init 门 ----------
T0=$(date +%s)
ok=0; for i in $(seq 1 40); do sleep 2
    # 注意: rostopic echo 的字段路径订阅(/topic/field)在本环境假阴性("not published"
    # 而 hz 正常)——两度误杀活链的教训;必须用裸话题 echo 判流
    # v7 (2026-09-29): echo 输出 frame_id 带引号("world"), 裸 'frame_id: world' 永不匹配(T3 23:06 实锤类) -> 宽松匹配
    timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -q 'frame_id:.*world' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 80s 内 VINS 未 init(imu_propagate 无消息)"; exit 1; }
LOG "VINS init 完成, 等待 $(( (i)*2 ))s"
sleep 5

# ---------- preflight（T2 共享门：域/双目/IMU/真值/connected） ----------
if ! python3 "$HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py" 10 2>&1 | tee "$EV/preflight_${MODE}.txt"; then
    LOG "preflight 红项, 中止"; exit 1
fi

# ---------- 录制（无图像版） ----------
BAG="$EV/v1_${MODE}_$(date +%H%M%S).bag"
TOPICS="/vins_estimator/imu_propagate /vins_estimator/odometry \
/mavros/imu/data_raw /mavros/imu/data /mavros/local_position/odom \
/mavros/vision_pose/pose /mavros/state /mavros/setpoint_raw/attitude \
/debugPx4ctrl/fsm_state /debugPx4ctrl /gazebo/model_states \
/px4ctrl/takeoff_land /position_cmd /clock"
nohup timeout -s INT 95 rosbag record -O "$BAG" $TOPICS > "$EV/record_${MODE}.log" 2>&1 &
REC=$!
sleep 3
LOG "bag: $BAG"

# ---------- 轮体 ----------
if [ "$MODE" = "ground" ]; then
    LOG "地面静置 60s"
    sleep 60
else
    LOG "起飞触发 (04_takeoff 60s 预算)"
    bash "$HOME/sitl_sim/04_takeoff.sh" 60 > "$EV/takeoff_${MODE}.log" 2>&1
    T_HOV=$(date +%s)
    LOG "悬停 30s 计时"
    sleep 30
    LOG "降落指令(重掷制,防 U3 投递随机失败)"
    for k in 1 2 3; do
        timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
        for j in $(seq 1 12); do
            timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && break 2
            sleep 1
        done
        wait $! 2>/dev/null
    done
    sleep 15
fi
kill -INT $REC 2>/dev/null; sleep 3
LOG "录制结束"

# ---------- 内联速报 ----------
python3 - "$BAG" "$MODE" <<'PYEOF' 2>&1 | tee "$EV/RESULT_${MODE}.txt"
import rosbag, sys, math
bag_path, mode = sys.argv[1], sys.argv[2]
b = rosbag.Bag(bag_path)
def stats(stamps):
    if len(stamps) < 3: return None
    ts = sorted(stamps); n = len(ts)
    dur = ts[-1] - ts[0]
    dts = [ts[i+1]-ts[i] for i in range(n-1)]
    return dict(n=n, hz=n/dur, maxgap=max(dts), med_dt=sorted(dts)[n//2])
prop_t, prop_p, gt_t, gt_p, fsm, imu_t, ekf_t, vis_t = [], [], [], [], [], [], [], []
for topic, msg, t in b.read_messages():
    if topic == "/vins_estimator/imu_propagate":
        prop_t.append(msg.header.stamp.to_sec())
        prop_p.append((msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z))
    elif topic == "/gazebo/model_states":
        try:
            k = msg.name.index([n for n in msg.name if "iris" in n][0])
            gt_t.append(t.to_sec()); gt_p.append(tuple(msg.pose[k].position)[:3])
        except (ValueError, IndexError): pass
    elif topic == "/debugPx4ctrl/fsm_state": fsm.append(msg.data)
    elif topic == "/mavros/imu/data": imu_t.append(msg.header.stamp.to_sec())
    elif topic == "/mavros/local_position/odom": ekf_t.append(msg.header.stamp.to_sec())
    elif topic == "/mavros/vision_pose/pose": vis_t.append(msg.header.stamp.to_sec())
b.close()
print("== V1 %s 速报 %s ==" % (mode, bag_path.split("/")[-1]))
for name, arr in [("imu_propagate", prop_t), ("imu/data", imu_t), ("ekf_odom", ekf_t), ("vision_pose", vis_t), ("model_states", gt_t)]:
    s = stats(arr)
    print("  %-13s %s" % (name, ("%.1fHz n=%d maxgap=%.3fs" % (s["hz"], s["n"], s["maxgap"])) if s else "n/a"))
if prop_p:
    xs = [p[0] for p in prop_p]; ys = [p[1] for p in prop_p]; zs = [p[2] for p in prop_p]
    def rng(v): return max(v) - min(v)
    print("  imu_propagate 静态: x∈[%.3f,%.3f] y∈[%.3f,%.3f] z∈[%.3f,%.3f] (漂移幅度 %.3f/%.3f/%.3f m)" % (
        min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), rng(xs), rng(ys), rng(zs)))
if gt_p:
    xs = [p[0] for p in gt_p]; ys = [p[1] for p in gt_p]; zs = [p[2] for p in gt_p]
    print("  真值(gazebo) 静态: 漂移幅度 %.4f/%.4f/%.4f m" % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)))
if fsm:
    uniq = {}
    for f in fsm: uniq[f] = uniq.get(f, 0) + 1
    print("  fsm_state: %s (共 %d 帧, %d 态)" % (uniq, len(fsm), len(uniq)))
PYEOF

# ---------- 收尾 ----------
pkill -f 'vins_nod[e]' 2>/dev/null; pkill -f 'vins_to_mavro[s]' 2>/dev/null
sleep 1
bash "$HOME/sitl_sim/t3_clean.sh" > "$EV/clean_${MODE}.log" 2>&1
LOG "V1 ${MODE} 轮结束(锁已随 t3_clean 释放)"
