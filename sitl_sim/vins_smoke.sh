#!/usr/bin/env bash
# vins_smoke.sh — T3-X1 VINS 同构链路一键冒烟（2026-09-28 v5 任务书）。
# 五件套起栈 + VINS init 门(裸话题 echo,wall-clock 300s+30s心跳) + T2 preflight +
# takeoff + goal(重发) + 真值/VINS 双口径到位 + 四指标 RESULT(round_result.sh) + 清场。
# --leg2 支持两段式返程(X3②⑤/X4)。紧凑 bag(~40MB/轮)。
# 用法: vins_smoke.sh [--world W] [--goal x y z] [--leg2 x y z] [--tag NAME] [--budget 秒]
# 坑位吸收(全部实证): 空world无特征init必败/echo输出 frame_id 带引号(grep须 "?world"?)/
# 字段路径echo假阴性/source基座在devel之后会覆盖ws包路径/seq门实际5s每迭代/
# 511默认50Hz/ROSTimeMovedBackwards杀watcher/goal竞态/降落投递随机/磁盘100%。
source /opt/ros/noetic/setup.bash          # 先 source 再 set -u(V3 教训)
source "$HOME/catkin_ws/devel/setup.bash"  # 必须 LAST:重复 source 基座会覆盖掉 ws 包路径(X1轮1教训)
set -u
WORLD=sitl_world_obstacles; GX=7.0; GY=-4.0; GZ=1.0; TAG=smoke; BUDGET=100; HASL2=0; L2X=0; L2Y=0; L2Z=0; PROBECHECK=0
GATE=0
WARMUP=0; STOPLOSS=0; GATE_PARAMS="$HOME/sitl_sim/t1_gate_params.json"; GATEPID=""; RTFPID=""
while [ $# -gt 0 ]; do case "$1" in
  --world) WORLD="$2"; shift 2;;
  --goal)  GX="$2"; GY="$3"; GZ="$4"; shift 4;;
  --leg2)  HASL2=1; L2X="$2"; L2Y="$3"; L2Z="$4"; shift 4;;
  --tag)   TAG="$2"; shift 2;;
  --budget) BUDGET="$2"; shift 2;;
  --probecheck) PROBECHECK=1; shift;;
  --gate) GATE=1; shift;;
  --stoploss) STOPLOSS=1; shift;;
  --warmup) WARMUP=1; shift;;
  --gate-params) GATE_PARAMS="$2"; shift 2;;
  *) echo "unknown arg $1"; exit 2;;
esac; done
LOG() { echo "[$(date +%H:%M:%S)] $*"; }

# v11.17 1.2: vins_node 按 master 域过滤杀(私有 master 回放件保护,04:26 事故机理)
kill_vins_my_domain() {
  local my_m="${ROS_MASTER_URI:-http://localhost:11311}" p m
  for p in $(pgrep -f "lib/vins/vins_nod[e]" 2>/dev/null); do
    m=$(tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep '^ROS_MASTER_URI=' | cut -d= -f2-)
    m="${m:-http://localhost:11311}"
    [ "$m" = "$my_m" ] && kill -9 "$p" 2>/dev/null
  done
  return 0
}

# -- dual-copy deploy guard (T1 2026-10-01; probe-copy-fork case d55c710 lesson) --
# repo copy = source of truth; runtime copy must md5-match repo at launch, else refuse to run.
_REPO_SH="$HOME/catkin_ws/sitl_sim/vins_smoke.sh"
if [ -f "$_REPO_SH" ] && [ "$(md5sum "$_REPO_SH" | cut -d' ' -f1)" != "$(md5sum "$0" | cut -d' ' -f1)" ]; then
  LOG "FATAL dual-copy fork: runtime($0) != repo($_REPO_SH); REFUSING. fix: cp repo -> runtime then retry"
  exit 3
fi
L="$HOME/sitl_sim"
EV="$L/vins_smoke_runs/run_${TAG}_$(date +%H%M%S)"
mkdir -p "$EV"
# ---------- hwmon 随轮遥测(任务书 v11.17 §1.3;采样面预注册冻结,纯取证;历史轮缺口不回填) ----------
HWPID=""
if [ -x "$HOME/catkin_ws/sitl_sim/t1_hwmon_probe.sh" ]; then
  setsid nohup bash "$HOME/catkin_ws/sitl_sim/t1_hwmon_probe.sh" "$EV" </dev/null >/dev/null 2>&1 &
  HWPID=$!
fi
# VINS config 全键 md5 随轮落盘(任务书 v11.17 1.2:不只四键,跨轮漂移永久可对账)
md5sum "$HOME/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml" > "$EV/vins_config.md5" 2>/dev/null || true
exec > >(tee "$EV/round.log") 2>&1

# ---------- 锁(T4-E1 v2 统一仲裁:死主自动接管/心跳/磁盘水位线门;流名载体=权序标签) ----------
LOCK="$L/SITL.lock"
SL="$L/sitl_lock.sh"
MYSTREAM="${SMOKE_OWNER:-T3-$TAG}"
"$SL" get "$MYSTREAM" || { LOG "FATAL 锁获取失败(活主持有或盘门拒绝,原因见上)"; exit 1; }
MYOWNER=$(readlink "$LOCK" 2>/dev/null || true)
"$SL" hbloop "$MYSTREAM" & HBPID=$!
cleanup() {
  [ -n "$HWPID" ] && kill "$HWPID" 2>/dev/null
  pkill -f "t1_hwmon_prob[e] $EV" 2>/dev/null
  [ -n "$GATEPID" ] && kill "$GATEPID" 2>/dev/null
  [ -n "$RTFPID" ] && kill "$RTFPID" 2>/dev/null
  pkill -f "t1_gate_watc[h] --inflight $EV" 2>/dev/null
  pkill -f "t1_rtf_prob[e] $EV" 2>/dev/null
  kill "$HBPID" 2>/dev/null
  pkill -f "tee $EV/round.lo[g]" 2>/dev/null   # exec>(tee) 进程替换会让 bash 退出时等 tee,tee 等 stdout 写者→挂壳;杀之解锁(E2 验收实测)
  pkill -f 'vins_to_mavro[s]' 2>/dev/null; kill_vins_my_domain
  pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
  pkill -f 'simulator_mavlin[k]' 2>/dev/null; pkill -f 'sitl_run.s[h]' 2>/dev/null
  pkill -9 -f 'bin/px[4]' 2>/dev/null; pkill -9 -x gzserver 2>/dev/null
  pkill -x gzclient 2>/dev/null
  pkill -f 'start_sitl_vin[s]' 2>/dev/null; pkill -f 'sleep infinit[y]' 2>/dev/null
  pkill -f '02_start_mavro[s]' 2>/dev/null; pkill -x mavros_node 2>/dev/null
  pkill -f 'run_ctrl_sitl_vin[s]' 2>/dev/null; pkill -f 'run_planner_sitl_vin[s]' 2>/dev/null
  pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null
  pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null
  sleep 3
}
trap 'if [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$MYOWNER" ]; then cleanup; "$SL" release "$MYSTREAM" >/dev/null 2>&1; fi' EXIT

# ---------- 清场断言(不动他人,只拒绝脏现场) ----------
A=$(pgrep -xc px4 2>/dev/null || true); A=${A:-0}
B=$(pgrep -xc gzserver 2>/dev/null || true); B=${B:-0}
[ "$A" = "0" ] && [ "$B" = "0" ] || { LOG "FATAL SITL 未清(px4=$A gz=$B),先清场再跑"; exit 1; }

# ---------- fresh master + 域配方 ----------
# v11.17 1.2 加固: 孤儿 planner 二进制路径清杀(异常死轮遗留 traj_server 持续回放
# poscmd→起飞卫兵拒飞=注入测试期 NEVER-FLEW 三连实测根因)
bash "$HOME/sitl_sim/kill_planner_all.sh" >/dev/null 2>&1
kill_vins_my_domain
pkill -f 'px4ctrl_nod[e]' 2>/dev/null; pkill -f 'rosbag recor[d]' 2>/dev/null
pkill -f 'arr_prob[e]' 2>/dev/null
pkill -f 'roslaunc[h]' 2>/dev/null; pkill -f 'roscor[e]' 2>/dev/null; sleep 3
nohup roscore >/dev/null 2>&1 & sleep 3
rosparam set /use_sim_time true
yes | rosnode cleanup >/dev/null 2>&1 || true
pgrep -x Xvfb >/dev/null || { nohup Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 & sleep 2; }
export DISPLAY=:99

# ---------- 五件套 ----------
SITL_WORLD="$WORLD" nohup bash "$L/start_sitl_vins.sh" > "$EV/sitl.log" 2>&1 &
ok=0; for i in $(seq 1 45); do sleep 2
  rostopic list 2>/dev/null | grep -q 'vins_cam_left/image_raw' && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL 双目话题未出现"; exit 1; }
LOG "SITL up ($WORLD)"
nohup bash "$HOME/catkin_ws/sitl_sim/02_start_mavros.sh" > "$EV/mavros.log" 2>&1 &
ok=0; for i in $(seq 1 30); do sleep 2
  timeout 5 rostopic echo -n1 /mavros/state/connected 2>/dev/null | grep -q True && { ok=1; break; }; done
[ $ok = 1 ] || { LOG "FATAL mavros 未连"; exit 1; }
rosrun mavros mavcmd long 511 105 ${T1_E4_IMU_US:-4000} 0 0 0 0 0 2>/dev/null; sleep 2
LOG "mavros up + 511@4000us(仓库标准 632e0ee:4ms网格量化,~223Hz;5000us实际=125Hz量化伪影)"
# T1 P0-A.1 (2026-10-01): E2 stderr probes (E2uls/E2clamp/E2gap) default-on EVERY round
# (v8.0: 此后一切飞行轮默认带探针,跳变机制数据); env gate = estimator.cpp a5cd330 form
export REANCHOR_DEBUG=1
nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
sleep 3
LOG "sim_vins up, 等 VINS init(wall-clock 300s, 30s 心跳取证)"
ok=0; T0G=$(date +%s); HB=0
while [ $(( $(date +%s) - T0G )) -lt 300 ]; do
  sleep 2
  if timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -qE 'frame_id: "?world"?'; then ok=1; break; fi
  NOW=$(( $(date +%s) - T0G ))
  if [ $NOW -ge $((HB+30)) ]; then
    HB=$NOW
    ODM=$(timeout 3 rostopic list 2>/dev/null | grep -c 'vins_estimator/odometry')
    IMU_HZ=$(timeout 8 rostopic hz /mavros/imu/data_raw 2>/dev/null | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}')
    PROP_HZ=$(timeout 8 rostopic hz /vins_estimator/imu_propagate 2>/dev/null | grep -oE 'average rate: [0-9.]+' | tail -1 | awk '{print $3}')
    LOG "gate +${NOW}s: odometry_topic=$ODM imu_raw=${IMU_HZ:-NA}Hz prop=${PROP_HZ:-NA}Hz"
  fi
done
[ $ok = 1 ] || { LOG "FATAL 300s 内 VINS 未 init"; exit 1; }
LOG "VINS init 完成 (+$(( $(date +%s) - T0G ))s)"
# ---------- 1a 起飞前门(v11.20 单元1a;--gate 1 启用;纯脚本面) ----------
# init 健康度三指标(init 终值 cost/|Bas| 中位/track) vs 健康分位带(t1_gate_params.json,
# T2 科学包填参冻结;null=OBSERVE 直通)。不健康→vins 重启再 init(≤2)→仍不健康→
# ENV-ABORT 轮作废(不计红不计入,留痕 pregate_<tag>.json)。
if [ "$GATE" = "1" ]; then
  pg_try=0
  while :; do
    PGOUT=$(python3 "$HOME/catkin_ws/sitl_sim/t1_gate_watch.py" --pregate "$EV" --params "$GATE_PARAMS" 2>&1)
    PGV=$(echo "$PGOUT" | head -1 | python3 -c "import json,sys
try: print(json.loads(sys.stdin.readline()).get('verdict','ABORT'))
except Exception: print('ABORT')" 2>/dev/null || echo ABORT)
    LOG "pregate[$pg_try]: $PGV"
    case "$PGV" in
      PASS*) break;;
      block|ABORT*)
        LOG "pregate ABORT(硬缺陷/解析失败)→ENV-ABORT 轮作废"
        python3 - "$EV" "$PGOUT" <<'PYEOF'
import json, glob, sys
rd, why = sys.argv[1], sys.argv[2][:200]
for f in glob.glob(rd + "/pregate_*.json"):
    try:
        j = json.load(open(f)); j["verdict"] = "block"; j["block_reason"] = why
        json.dump(j, open(f, "w"), ensure_ascii=False, indent=1)
    except Exception:
        pass
PYEOF
        echo "RESULT=ENV-ABORT (pregate: $(echo "$PGOUT" | head -c 300))" > "$EV/RESULT.txt"
        exit 6;;
      *)
        if [ "$pg_try" -ge 2 ]; then
          LOG "pregate 重试耗尽(2)→ENV-ABORT(不健康 init 三连=环境域,不计红不计入)"
          python3 - "$EV" "$PGOUT" <<'PYEOF'
import json, glob, sys
rd, why = sys.argv[1], sys.argv[2][:200]
for f in glob.glob(rd + "/pregate_*.json"):
    try:
        j = json.load(open(f)); j["verdict"] = "block"; j["block_reason"] = "retries exhausted: " + why
        json.dump(j, open(f, "w"), ensure_ascii=False, indent=1)
    except Exception:
        pass
PYEOF
          echo "RESULT=ENV-ABORT (pregate retries exhausted: $(echo "$PGOUT" | head -c 300))" > "$EV/RESULT.txt"
          exit 6
        fi
        pg_try=$((pg_try+1))
        LOG "pregate REINIT → vins 重启 #${pg_try}(sick log 保全=simvins_pregate_fail_${pg_try}.log)"
        mv "$EV/simvins.log" "$EV/simvins_pregate_fail_${pg_try}.log" 2>/dev/null
        kill_vins_my_domain
        pkill -f 'src/launch/sim_vins.launc[h]' 2>/dev/null; sleep 3
        nohup roslaunch "$HOME/catkin_ws/src/launch/sim_vins.launch" > "$EV/simvins.log" 2>&1 &
        ok=0; T0G=$(date +%s)
        while [ $(( $(date +%s) - T0G )) -lt 300 ]; do
          sleep 2
          if timeout 3 rostopic echo -n1 /vins_estimator/imu_propagate 2>/dev/null | grep -qE 'frame_id: "?world"?'; then ok=1; break; fi
        done
        [ $ok = 1 ] || { LOG "FATAL pregate 重启后 300s 未 init"; echo "RESULT=ENV-ABORT (pregate reinit no-init)" > "$EV/RESULT.txt"; exit 6; }
        LOG "pregate reinit 完成 (+$(( $(date +%s) - T0G ))s)";;
    esac
  done
fi
if [ "$PROBECHECK" = "1" ]; then
  E2ULS=$(grep -c "E2uls" "$EV/simvins.log" 2>/dev/null || true); E2ULS=${E2ULS:-0}
  E2CLAMP=$(grep -c "E2clamp" "$EV/simvins.log" 2>/dev/null || true); E2CLAMP=${E2CLAMP:-0}
  E2GAP=$(grep -c "E2gap" "$EV/simvins.log" 2>/dev/null || true); E2GAP=${E2GAP:-0}
  LOG "PROBECHECK: E2uls=$E2ULS E2clamp=$E2CLAMP E2gap=$E2GAP (init-only round, no takeoff)"
  grep -m 3 "E2uls" "$EV/simvins.log" 2>/dev/null || true
  if [ "$E2ULS" -ge 1 ]; then LOG "PROBECHECK PASS: probe chain transmits (E2uls lines in simvins.log)"; exit 0
  else LOG "PROBECHECK FAIL: VINS init but zero E2uls lines - probe chain broken"; exit 1; fi
fi
if ! python3 "$HOME/catkin_ws/sitl_sim/analysis/t2_preflight_check.py" 10 > "$EV/preflight.txt" 2>&1; then
  REDS=$(grep -c '红' "$EV/preflight.txt" || true); REDS=${REDS:-0}
  IMU_RED=$(grep -c 'IMU 频率.*>200' "$EV/preflight.txt" || true); IMU_RED=${IMU_RED:-0}
  IMU_HZ=$(grep -oE 'IMU 频率: [0-9.]+' "$EV/preflight.txt" | grep -oE '[0-9.]+$' | head -1)
  if [ "$REDS" = "1" ] && [ "$IMU_RED" = "1" ] && [ -n "$IMU_HZ" ] && awk "BEGIN{exit !($IMU_HZ+0>=100)}"; then
    LOG "preflight IMU>200 门豁免:实测${IMU_HZ}Hz≥100(原v3标准)。依据=5000us+默认config为T2-W1.3实证飞行配对;4000us+默认config实证VINS飞行爆散(X1_232055,odom冲740m,已移交T2域)"
  else
    LOG "preflight 红项"; tail -8 "$EV/preflight.txt"; exit 1
  fi
fi
LOG "preflight 全绿(双目纹理/域/IMU/真值 X1.1 覆盖)"
nohup roslaunch px4ctrl run_ctrl_sitl_vins.launch > "$EV/px4ctrl.log" 2>&1 &
sleep 3
rostopic info /px4ctrl/takeoff_land 2>/dev/null | grep -q Publishers || { LOG "FATAL px4ctrl 无响应"; exit 1; }
nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
sleep 4
rostopic info /position_cmd 2>/dev/null | grep -q Publishers || { LOG "FATAL planner 无 position_cmd"; exit 1; }
LOG "五件套齐(px4ctrl+ego)"

# ---------- 紧凑录制(无图像,~40MB/轮;磁盘两次100%教训) ----------
IMG_TOPICS=""
[ "${VINS_SMOKE_IMAGES:-0}" = "1" ] && IMG_TOPICS="/iris_stereo_vins/vins_cam_left/image_raw /iris_stereo_vins/vins_cam_right/image_raw"
BAG="$EV/flight.bag"
nohup rosbag record -O "$BAG" \
  /vins_estimator/imu_propagate /vins_estimator/odometry /vins_estimator/feature_pts \
  /mavros/imu/data /mavros/imu/data_raw /mavros/local_position/odom /mavros/state \
  /mavros/setpoint_raw/attitude /mavros/setpoint_raw/local /debugPx4ctrl/fsm_state /debugPx4ctrl \
  /gazebo/model_states /px4ctrl/takeoff_land /position_cmd /move_base_simple/goal /clock \
  $IMG_TOPICS \
  > "$EV/record.log" 2>&1 &
REC=$!
sleep 3

# ---------- 1b 飞行中前兆门 watchdog+RTF 探针(v11.20 单元1b;--gate 1;纯脚本面) ----------
# 数据源=simvins.log([T2slv] cost 主+[T2diag] |Bas| 副,10Hz);双门=绝对+轮内自适应;
# 触发→gatehit.flag;本脚本各相位轮询点收到→gate_abort 受控中止(预注册降级序)。
# [4c 常态化 v11.23] rtf 探针移出 GATE 块——--no-gate 路径亦随轮挂载
setsid nohup python3 "$HOME/catkin_ws/sitl_sim/t1_rtf_probe.py" "$EV" >/dev/null 2>&1 &
RTFPID=$!
LOG "rtf probe up(pid=$RTFPID) [常态化 v11.23 4c]"
if [ "$GATE" = "1" ]; then
  setsid nohup python3 "$HOME/catkin_ws/sitl_sim/t1_gate_watch.py" --inflight "$EV" --params "$GATE_PARAMS" >/dev/null 2>&1 &
  GATEPID=$!
  PGVER=$(python3 -c "import json;p=json.load(open('$GATE_PARAMS'));print(p.get('version','?'),'frozen' if p.get('frozen') else 'OBSERVE')" 2>/dev/null || echo unreadable)
  LOG "inflight gate watchdog up(pid=$GATEPID);params=$PGVER"
  export GATE_FLAG="$EV/gatehit.flag"
fi
# [4a 止损件挂点 v11.23] jump 后置止损(用户已批);thresh=1.0m(§3 预注册锚,无门值变动)
if [ "$STOPLOSS" = "1" ]; then
  setsid nohup python3 "$HOME/catkin_ws/sitl_sim/t1_stoploss_watch.py" --inflight "$EV" >/dev/null 2>&1 &
  SLPID=$!
  LOG "stoploss watchdog up(pid=$SLPID);trichotomy=真 FAIL 提前终止形态(不重复判 jump 面)"
fi
gate_hit() { [ -f "$EV/gatehit.flag" ]; }
stoploss_hit() { [ -f "$EV/stoploss.flag" ]; }
gate_abort() {  # $1=相位标签;$2=模式(gate|stoploss,默认gate);完整恢复=受控中止+完整降落+disarm=1+无T2fail(预注册)
  local PH="${1:-?}" MODE="${2:-gate}" DISARMED=0 STREAM_OK=1 K J
  local PFX=gatehit; [ "$MODE" = stoploss ] && PFX=stoploss
  LOG "GATE-HIT@$PH 前兆门触发→goal 停发+受控中止链(预注册降级序①odom可信段LAND②流断→悬停+kill)"
  echo "$(date '+%F %T') GATE-ABORT@$PH" >> "$EV/${PFX}_actions.txt"
  bash "$HOME/sitl_sim/kill_planner_all.sh" > "$EV/planner_kill.log" 2>&1; sleep 2
  STREAM_OK=$(python3 - "$EV" <<'PYEOF'
import json, glob, sys, os
ok = 1
for f in glob.glob(os.path.join(sys.argv[1], sys.argv[3] + "_*.json")):
    try:
        j = json.load(open(f)); gap = (j.get("vins_stream") or {}).get("gap_s")
    except Exception:
        continue
    if gap is not None and gap > 10:
        ok = 0
print(ok)
PYEOF
)
  if [ "$STREAM_OK" = "1" ]; then
    LOG "降级①: odom 可信段完成 LAND(5 轮重掷,60s 上限)"
    for K in 1 2 3 4 5; do
      timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
      for J in $(seq 1 12); do
        timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { DISARMED=1; break 2; }
        sleep 1
      done
    done
    if [ "$DISARMED" != "1" ]; then
      LOG "LAND 未 disarm(60s)→降级②兜底: 悬停 5s+kill 电机(SITL 可接受;实机语义=需人工接管协议)"
      sleep 5
      for K in 1 2 3; do rosrun mavros mavcmd long 400 0 1 0 0 0 0 0 >/dev/null 2>&1; sleep 1; done
      for J in $(seq 1 8); do
        timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { DISARMED=1; break; }
        sleep 1
      done
    fi
  else
    LOG "降级②: VINS 流断/滞后>10s(中止依赖 odom 而门触发=VINS 正在病)→悬停 5s+kill 电机"
    sleep 5
    for K in 1 2 3; do rosrun mavros mavcmd long 400 0 1 0 0 0 0 0 >/dev/null 2>&1; sleep 1; done
    for J in $(seq 1 8); do
      timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { DISARMED=1; break; }
      sleep 1
    done
  fi
  REC=$([ $DISARMED = 1 ] && echo COMPLETE || echo DEGRADED)
  PTH=$([ "$STREAM_OK" = 1 ] && echo LAND || echo KILL)
  echo "RECOVERY=$REC path=$PTH phase=$PH" > "$EV/${PFX}_outcome.txt"
  # gatehit json 回写 landed/disarm(T3 trichotomy 契约:landed=1 ∧ RESULT 带 auto_disarm)
  python3 - "$EV" "$DISARMED" "$PFX" <<'PYEOF'
import json, glob, sys
landed = int(sys.argv[2])
for f in glob.glob(sys.argv[1] + "/" + sys.argv[3] + "_*.json"):
    try:
        j = json.load(open(f)); j["landed"] = landed; j["disarm"] = landed
        j["recovery"] = "COMPLETE" if landed else "DEGRADED"; j["recovery_path"] = "recorded"
        json.dump(j, open(f, "w"), ensure_ascii=False, indent=1)
    except Exception:
        pass
PYEOF
  if [ "$MODE" = stoploss ]; then
    echo "RESULT=FAIL (STOPLOSS-ABORT@$PH jump 后置止损触发; recovery=$REC; auto_disarm->$DISARMED; 留痕=stoploss_<tag>.json+actions; 真FAIL 提前终止形态——jump 面判读归 round_result 帧稳定性不重复判)" > "$EV/RESULT.txt"
    LOG "STOPLOSS-ABORT 收束 recovery=$REC path=$PTH"
    cleanup
    exit 43
  fi
  echo "RESULT=GATE-INTERCEPT (前兆门@$PH; recovery=$REC; auto_disarm->$DISARMED; 留痕=gatehit_<tag>.json+gate_timeline+actions; $([ "$REC" = COMPLETE ] && echo '完整恢复=计入分子' || echo '降级=不完整恢复不计入分子,如实'))" > "$EV/RESULT.txt"
  LOG "GATE-INTERCEPT 收束 recovery=$REC path=$PTH"
  cleanup
  exit 42
}

# ---------- 起飞 ----------
LOG "起飞触发 (04_takeoff 120s 预算,重启后首boot慢投递余量)"
if ! bash "$L/04_takeoff.sh" 120 > "$EV/takeoff.log" 2>&1; then
  LOG "FATAL takeoff 失败"; tail -5 "$EV/takeoff.log"; exit 1
fi
sleep 13
# ---------- 离地真值门(2026-10-04 加固;X2g1=armed 但 truth z≡0 全程 never-flew 实证) ----------
# T1-H4b fix (2026-10-04): pose[0]=ground_plane z==0.0 ALWAYS (models[0] is the
# ground plane in every world) -> gate false-killed healthy rounds at 37s
# (F3B3/F3B4 truth z max 0.93/0.95m actually flying). Read iris by NAME.
LZ=$(timeout 8 python3 "$L/smoke_truthz.py" 2>/dev/null | tail -1)
[ -n "$LZ" ] || LZ=NA
if [ "$LZ" != NA ] && awk "BEGIN{exit !($LZ < 0.3)}"; then
  LOG "WARN NEVER-FLEW: truth z=$LZ<0.3(armed 但未离地)——早停+降落收尾,标本保全(@T1 域取证面)"
  bash "$L/06_land.sh" >> "$EV/takeoff.log" 2>&1 || true
  echo "RESULT=FAIL (证据: never-flew 离地真值门 truth z=$LZ; 判读面标本保全)" > "$EV/RESULT.txt"
  exit 1
fi
LOG "已等离地稳定(truth z=$LZ)"
[ "$GATE" = "1" ] && gate_hit && gate_abort hover
[ "$STOPLOSS" = "1" ] && stoploss_hit && gate_abort hover stoploss

# ---------- goal（v11.17 starve 修复：订阅就绪门+停摆一次性重启，任务书 1.1a/1.1b） ----------
# 病灶（X4 批 2/8 轮；X2g3_042025=189B planner.log 实证）：FSM 事件循环停摆——
# "[FSM]: state:" 1s 心跳缺席=回调链死（timer stop/start 自愈路径失灵面）,goal 重发无效；
# 旧 /position_cmd publisher 检查只验 traj_server,对 FSM 死活结构性失明。
# 修复（harness 面,不改 planner 源码）：a) 首发前订阅就绪门=/move_base_simple/goal 有
# ego_planner 订阅者 ∧ FSM 心跳首行在册；b) 首发 8s 无 target 变更（FSM 未离
# WAIT_TARGET ∧ poscmd≤1Hz）→ planner 整栈重启一次再投递（sick log 保全为
# planner_starved_1.log）；重启后仍死=WARN 注记（判读面如实,勿盲续口径不变）。
echo "goal: $GX $GY $GZ leg2: $HASL2 $L2X $L2Y $L2Z" > "$EV/goal.txt"
goal_pub() {
  timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
    "{header: {frame_id: 'world'}, pose: {position: {x: $GX, y: $GY, z: $GZ}}}" >/dev/null 2>&1
}
fsm_beat()      { grep -q "\[FSM\]: state:" "$EV/planner.log" 2>/dev/null; }
goal_sub_ok()   { rostopic info /move_base_simple/goal 2>/dev/null | sed -n '/Subscribers:/,$p' | grep -q "ego_planner_node"; }
planner_ready() { goal_sub_ok && fsm_beat; }
target_moved()  { grep -q "from WAIT_TARGET to" "$EV/planner.log" 2>/dev/null; }
poscmd_rate()   { timeout 4 rostopic hz /position_cmd 2>&1 | grep -o 'average rate: [0-9.]*' | head -1 | grep -o '[0-9.]*$' || echo 0; }
wait_planner_ready() {  # $1=秒; 0=就绪
  local k; for ((k=0; k<$1; k++)); do planner_ready && return 0; sleep 1; done
  planner_ready
}
# a) 订阅就绪门（首发前；超时不 abort——转入 b 重启路径处置）
if ! wait_planner_ready 15; then LOG "订阅就绪门超时(15s 无 goal 订阅者或 FSM 心跳)——直入停摊重启路径"; fi
if [ "$WARMUP" = "1" ]; then
  python3 "$L/t2_tools/t2_warmup_segment.py" --publish --hz 10 --goal-topic /move_base_simple/goal > "$EV/warmup.log" 2>&1
  LOG "WARMUP 段完成(8s 预热 goal 流): $(tail -1 "$EV/warmup.log" 2>/dev/null)"
  # ---- goal 切换协议修复 W1/W2 (T2 v10.7 单元1; prereg INPUTFACE/goal_fix_prereg_v1.md) ----
  # 病理: warmup 10Hz goal 流把 FSM 拖入 EXEC/REPLAN 循环不回 WAIT_TARGET(v11.31 A臂8/8;
  # 标本 WU_E12O_A: FSM_LEFT_WAIT_TARGET=1 恒定+尾点(0.14,-0.25,1.00) vel=0 悬停),
  # mission goal 在非 WAIT_TARGET 态走 planNextWaypoint 的 REPLAN 侧路径=失效。
  # W1: goal-silent 稳定门——等 FSM 回 WAIT_TARGET 证据(以 warmup 毕时字节偏移为基线), 上限 20s。
  # W2: 等不到→planner 整栈重启一次(复用 v11.17 starve 基建)→干净 INIT→WAIT_TARGET 走正路。
  WU_OFF=$(stat -c %s "$EV/planner.log" 2>/dev/null || echo 0)
  wu_wait_ok=0
  for wk in $(seq 1 20); do
    if tail -c +$((WU_OFF+1)) "$EV/planner.log" 2>/dev/null | grep -q "to WAIT_TARGET"; then wu_wait_ok=1; break; fi
    sleep 1
  done
  if [ "$wu_wait_ok" = "1" ]; then
    LOG "WU-goal-fix W1 PASS: warmup 毕后 FSM 回 WAIT_TARGET(${wk}s)——mission goal 走 GEN_NEW_TRAJ 正路"
    echo "$(date '+%F %T') W1-PASS wait_target_after=${wk}s" >> "$EV/warmup_goal_adopted.txt"
  else
    LOG "WU-goal-fix W2: 20s 无 WAIT_TARGET 回转(EXEC/REPLAN 自环病理)→planner 重启#wu(sick log 保全)"
    echo "$(date '+%F %T') W2-RESTART no_wait_target_20s" >> "$EV/warmup_goal_adopted.txt"
    mv "$EV/planner.log" "$EV/planner_starved_wu_1.log" 2>/dev/null
    bash "$L/kill_planner_all.sh" > "$EV/planner_kill_wu.log" 2>&1
    sleep 2
    nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
    if ! wait_planner_ready 25; then
      LOG "WARN WU-goal-fix W2: 重启后就绪门超时(25s)——照发 mission goal, 判读面注记"
      echo "$(date '+%F %T') W2-READY-TIMEOUT" >> "$EV/warmup_goal_adopted.txt"
    fi
    sleep 3   # INIT→WAIT_TARGET 状态机首拍
  fi
fi
# W4 采纳证据基线: mission goal 发布前的 planner.log 偏移(W1 路径=原文件; W2 路径=新文件)
MGOFF=$(stat -c %s "$EV/planner.log" 2>/dev/null || echo 0)
for k in 1 2; do goal_pub; sleep 2; done
LOG "goal 已发(2×8s)"
# b) 首发 8s 无 target 变更→一次性重启再投递
sleep 8
PC=$(poscmd_rate); case "$PC" in ''|*[!0-9.]*) PC=0;; esac
if ! target_moved && ! awk "BEGIN{exit !($PC > 1.0)}"; then
  LOG "STARVE-DETECT: 首发 8s 无 target 变更(poscmd=${PC}Hz,FSM 未离 WAIT_TARGET)→ planner 重启#1(sick log 保全)"
  echo "$(date '+%F %T') STARVE-DETECT poscmd=${PC}Hz target_moved=no" >> "$EV/starve_fix_events.txt"
  mv "$EV/planner.log" "$EV/planner_starved_1.log"
  bash "$L/kill_planner_all.sh" > "$EV/planner_kill_starve.log" 2>&1
  sleep 2
  nohup roslaunch ego_planner run_planner_sitl_vins.launch > "$EV/planner.log" 2>&1 &
  if ! wait_planner_ready 25; then LOG "重启后订阅就绪门仍超时(25s)——二次停摆,按 WARN 走"; fi
  for k in 1 2; do goal_pub; sleep 2; done
  LOG "goal 再发(重启后 2×8s)"
  sleep 8
  PC=$(poscmd_rate); case "$PC" in ''|*[!0-9.]*) PC=0;; esac
  if ! target_moved && ! awk "BEGIN{exit !($PC > 1.0)}"; then
    LOG "WARN PLANNER-STARVED: 重启后再 8s 无变更(末次 poscmd=${PC}Hz)=goal 未达/规划器死——本轮判读面注记,勿盲续"
    echo "$(date '+%F %T') RESTART-FAILED poscmd=${PC}Hz" >> "$EV/starve_fix_events.txt"
  else
    LOG "poscmd 存活门通过(重启后 rate=${PC}Hz)"
    echo "$(date '+%F %T') RESTART-OK poscmd=${PC}Hz" >> "$EV/starve_fix_events.txt"
  fi
else
  LOG "poscmd 存活门通过(首发 rate=${PC}Hz)"
  # W4 采纳验证门(T2 v10.7 单元1): poscmd 活≠采纳(A臂病理=traj_server 发旧轨迹尾);
  # 采纳证据=mission goal 后 planner.log 新增 "from WAIT_TARGET to"(GEN_NEW_TRAJ 转换)。
  if [ "$WARMUP" = "1" ]; then
    if tail -c +$((MGOFF+1)) "$EV/planner.log" 2>/dev/null | grep -q "from WAIT_TARGET to"; then
      echo "$(date '+%F %T') W4-ADOPTED gen_new_traj_after_mission_goal poscmd=${PC}Hz" >> "$EV/warmup_goal_adopted.txt"
      LOG "WU-goal-fix W4 PASS: mission goal 已被采纳(GEN_NEW_TRAJ 转换在案)"
    else
      echo "$(date '+%F %T') W4-NO-EVIDENCE poscmd=${PC}Hz" >> "$EV/warmup_goal_adopted.txt"
      LOG "WARN WU-goal-fix W4: poscmd 活但无 from-WAIT_TARGET 转换证据——判读面注记"
    fi
  fi
fi
[ "$GATE" = "1" ] && gate_hit && gate_abort pursuit-start
[ "$STOPLOSS" = "1" ] && stoploss_hit && gate_abort pursuit-start stoploss

# ---------- 到位监视(真值口径,锚点自推导;外部wall超时+异常吞噬) ----------
arrive_watch() {  # $1..3 goal; $4 tag后缀
  local WX="$1" WY="$2" WZ="$3" WTAG="$4"
  timeout -s INT $BUDGET python3 - "$WX" "$WY" "$WZ" "$BUDGET" > "$EV/arrive_watch${WTAG}.txt" 2>&1 <<'PYEOF'
import sys, math, time, os
import rospy
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
gx, gy, gz, budget = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
gx, gy, gz = float(gx), float(gy), float(gz)
rospy.init_node('vsmoke_arrive', disable_signals=True)
gf = os.environ.get('GATE_FLAG')
st = {'anchor': None, 'p0': None, 'min_t': 1e9, 'min_v': 1e9,
      'last': None, 'ok_since': None, 'arrived': False,
      'n_odom': 0, 'n_truth': 0}  # V8-DEF-1: sample counters for diagnostics
def odom_cb(m):
    st['n_odom'] += 1  # V8-DEF-1
    p = m.pose.pose.position
    if st['p0'] is None: st['p0'] = (p.x, p.y, p.z)
    d = math.sqrt((p.x-gx)**2 + (p.y-gy)**2 + (p.z-gz)**2)
    st['min_v'] = min(st['min_v'], d)
def truth_cb(m):
    st['n_truth'] += 1  # V8-DEF-1
    try: i = m.name.index('iris_stereo_vins')
    except ValueError: return
    p = m.pose[i].position
    if st['anchor'] is None and st['p0'] is not None:
        st['anchor'] = (p.x - st['p0'][0], p.y - st['p0'][1], p.z - st['p0'][2])
        print('anchor: (%.3f, %.3f, %.3f)' % st['anchor'], flush=True)
    if st['anchor'] is None: return
    tx, ty, tz = gx + st['anchor'][0], gy + st['anchor'][1], gz + st['anchor'][2]
    d = math.sqrt((p.x-tx)**2 + (p.y-ty)**2 + (p.z-tz)**2)
    st['last'] = d; st['min_t'] = min(st['min_t'], d)
    now = time.monotonic()
    if d < 0.5:
        if st['ok_since'] is None: st['ok_since'] = now
        if now - st['ok_since'] >= 2.0: st['arrived'] = True
    else: st['ok_since'] = None
rospy.Subscriber('/vins_estimator/imu_propagate', Odometry, odom_cb, queue_size=2)
rospy.Subscriber('/gazebo/model_states', ModelStates, truth_cb, queue_size=2)
t_end = time.monotonic() + budget - 10
r = rospy.Rate(10)
while time.monotonic() < t_end and not st['arrived'] and not rospy.is_shutdown():
    if gf and os.path.exists(gf):
        print('GATE-FLAG-BREAK (前兆门触发,到位监视让位中止链)'); break
    try: r.sleep()
    except Exception: time.sleep(0.1)
# V8-DEF-1: triage the zero-sample cases (E-4 window root cause: VINS stopped streaming post-burst)
if st['n_odom'] == 0:
    print('NO_ODOM n_odom=0 n_truth=%d (VINS imu_propagate never flowed; anchor impossible)' % st['n_truth'])
elif st['n_truth'] == 0 or st['anchor'] is None:
    print('NO_GT n_odom=%d n_truth=%d (model_states or anchor unavailable)' % (st['n_odom'], st['n_truth']))
elif st['arrived']:
    print('ARRIVED_TRUTH min_d=%.3f n_odom=%d n_truth=%d' % (st['min_t'], st['n_odom'], st['n_truth']))
else:
    print('TIMEOUT min_truth=%.3f last=%.3f min_vins=%.3f n_odom=%d n_truth=%d' % (
        st['min_t'], st['last'] or -1, st['min_v'], st['n_odom'], st['n_truth']))
PYEOF
  tail -2 "$EV/arrive_watch${WTAG}.txt"
}
arrive_watch "$GX" "$GY" "$GZ" ""
ARR=$(tail -1 "$EV/arrive_watch.txt")
[ "$GATE" = "1" ] && gate_hit && gate_abort pursuit
[ "$STOPLOSS" = "1" ] && stoploss_hit && gate_abort pursuit stoploss

# ---------- leg2(两段式返程,X3②⑤) ----------
ARR2="N/A"
if [ $HASL2 = 1 ]; then
  LOG "leg1 后悬停 8s, 发 leg2 ($L2X $L2Y $L2Z)"
  sleep 8
  for k in 1 2; do
    timeout 8 rostopic pub -r 1 /move_base_simple/goal geometry_msgs/PoseStamped \
      "{header: {frame_id: 'world'}, pose: {position: {x: $L2X, y: $L2Y, z: $L2Z}}}" >/dev/null 2>&1
    sleep 2
  done
  arrive_watch "$L2X" "$L2Y" "$L2Z" "2"
  ARR2=$(tail -1 "$EV/arrive_watch2.txt")
  LOG "leg2 到位: $ARR2"
fi
timeout 8 rostopic hz /position_cmd 2>/dev/null | grep 'average rate' | tail -1 > "$EV/poscmd_hz.txt"

# ---------- 停 planner(H-1 修复 2026-10-04: LAND 前置) ----------
# H-1: CMD_CTRL 态 LAND 被 px4ctrl 设计性拒(ROS_ERROR 在案)且 position_cmd 流不断则永不回 AUTO_HOVER
# → 5 轮重掷降落全拒 → auto_disarm 恒 0(F3B2/U25FIX 实证;序列对齐 sitl_smoke 的 kill→land)
bash "$HOME/sitl_sim/kill_planner_all.sh" > "$EV/planner_kill.log" 2>&1
sleep 2
LOG "planner 已停(kill_planner_all, 见 planner_kill.log; H-1)"

# ---------- 降落(重掷制) ----------
LOG "降落指令(5 轮重掷)"
disarmed=0
for k in 1 2 3 4 5; do
  timeout 12 rostopic pub -r 1 /px4ctrl/takeoff_land quadrotor_msgs/TakeoffLand "takeoff_land_cmd: 2" >/dev/null 2>&1 &
  for j in $(seq 1 12); do
    timeout 3 rostopic echo -n1 /mavros/state 2>/dev/null | grep -q 'armed: False' && { disarmed=1; break 2; }
    sleep 1
  done
done
[ $disarmed = 1 ] && LOG "已 disarm" || LOG "WARN 降落未确认 disarmed"
sleep 3
# PX4 全参数随轮 dump(任务书 v11.17 1.2;口径预注册:dump 点=disarm 后飞行末态——
# MAVLink 带宽不与起飞投递窗竞争;boot 态漂移由 disarm 态跨轮一致对比代理;60s 预算非致命)
timeout 60 rosrun mavros mavparam dump "$EV/px4_params_$(date +%H%M%S).txt" >/dev/null 2>&1 \
  || LOG "WARN px4 param dump 失败/超时(对账面注记)"
kill -INT $REC 2>/dev/null; sleep 3

# ---------- 轮中环境死亡活体检查(E4.2;清场前栈应在,缺=崩) ----------
if ! pgrep -x gzserver >/dev/null 2>&1 || ! pgrep -x px4 >/dev/null 2>&1; then
  echo "$(date +%T) gzserver/px4 活体检查缺席(gz=$(pgrep -xc gzserver || echo 0) px4=$(pgrep -xc px4 || echo 0))" > "$EV/ENVDEAD"
fi

# ---------- 四指标 RESULT(独立脚本 round_result.sh,与 resume 共用) ----------
bash "$HOME/sitl_sim/round_result.sh" "$BAG" "$GX" "$GY" "$GZ" "$WORLD" "$EV" "$ARR" "$ARR2" "$HASL2" "$L2X" "$L2Y" "$L2Z" > "$EV/RESULT.txt" 2>&1
tail -10 "$EV/RESULT.txt"
grep -q "RESULT=ENV-FAIL" "$EV/RESULT.txt" && LOG "ENV-FAIL 环境性崩溃口径(E4.2):重试不计入飞行预算"

# ---------- 留痕落盘(任务书 v11.17 §1.1d): goal 发布 vs FSM 状态变化对表 ----------
python3 "$HOME/catkin_ws/sitl_sim/t1_goal_trace.py" "$EV" >/dev/null 2>&1 || LOG "WARN goal_trace 失败(留痕面注记)"

# ---------- 清场(函数已前置+EXIT trap;正常路径显式调一遍) ----------
cleanup
LOG "轮完成 bag=$BAG"
