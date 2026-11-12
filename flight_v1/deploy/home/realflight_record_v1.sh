#!/bin/bash
# shellcheck disable=SC1090  # source ~/catkin_ws/... 是非恒定路径，shellcheck 无法跟随（信息级）
# realflight_record_v1.sh — 实飞数据采集唯一录制脚本 v1.8 (v1.0=10-17; v1.1=10-21; v1.2~v1.7=11-03; v1.8=11-03)
# v1.10→v1.11（2026-11-06）：修 _extract_window 时间戳解析——原来只认 VINS 的 t=<epoch>，
#   px4ctrl 的 ROS 标准 [INFO] [<epoch>] 解析不到 -> px4ctrl_window.log 恒 0 行；现两种格式都认。
#   注意：解析用「方括号切分」而非区间量词——mawk 不支持 {n}，第一版因此仍然 0 行。
# v1.9→v1.10（2026-11-05）：trap 增加 HUP（SSH 掉线不再丢索引）+ 宽限 5s→10s + 收尾兜底 reindex
# v1.8/v1.9 变更（2026-11-03）：收尾先给 rosbag 发 INT 让它优雅关袋，5s 不退再 TERM；wait 落盘后再截日志。
# v1.7 变更（2026-11-03，用户批准）：+ /mavros/imu/mag（解锁瞬间磁读数，yaw 跳变取证）
#   + /mavros/estimator_status（EKF flags/innovation） + /mavros/imu/temperature_imu（零偏温漂旁证）
# v1.6 变更（2026-11-03）：RSS 记录循环移到后台子进程，主线程停在 `wait $RECORD_PID`，
#   Ctrl+C / SIGTERM 可立即中断并执行 trap 收尾（v1.5 的 sleep 60 会挡住 trap）。
# v1.5 变更（2026-11-03）：收尾改为 trap —— Ctrl+C / SIGTERM 停止时也保证执行"日志时间窗截取"。
# v1.4 变更（2026-11-03）：默认只录左目 /camera/infra1/。
# 2026-11-05 用户指令：暂时恢复默认双目+深度（infra1+infra2+depth，约 37MB/s = 2.2GB/min）。
#   关闭方式：RECORD_STEREO=0 bash realflight_record_v1.sh（单目袋不能回放双目 VINS）。
# v1.3 变更（2026-11-03，用户批准；目的=振动诊断时减半录制量）：
#   + RECORD_MONO=1 时只录 /camera/infra1/*（单目），不录 infra2/depth/color —— 录制量约减半
#     默认（不设）= 双目+深度全录，与 v1.2 相同
#   ⚠ 单目袋不能再回放双目 VINS；只用于振动/图像质量/IMU 判读
# v1.2 变更（2026-11-03，用户批准；目的=抓"优化解 vs imu_propagate 分叉"时刻）：
#   + /vins_estimator/keyframe_pose      —— 关键帧插入时刻（验证悬停低视差时是否还打新帧）
#   + /vins_estimator/extrinsic          —— 在线外参 tic/ric 逐帧（tic 在飞/|Bas| 爆的同源取证）
#   + /vins_estimator/camera_pose        —— 窗口内相机位姿（辅助对照 odometry）
#   + 录后自动截取 VINS / px4ctrl 日志的录制时间窗 → $BAG_DIR/vins_window.log / px4ctrl_window.log
#     （日志含 [T2diag] P/V/|Bas|/tic0、[T2gate] 等逐帧量；只截窗口，避免整份几百 MB）
# v1.1 变更（审计=Win t1/2026-10-17_实飞判读预备/录制面审计_20261021.md，用户批准）：
#   + /mavros/rc/in /mavros/rc/out        —— 遥控器通道（CH5 接管/CH6 暂停判读的硬需求）
#   + /mavros/vision_pose/pose            —— VINS→mavros 桥输出=px4ctrl 实际吃到的里程计（控制输入面）
#   + /mavros/extended_state              —— 着地态（降落段判读：ON_GROUND/FLYING/LANDING）
#   + /mavros/time_reference              —— 飞控↔机载电脑时钟对齐（bag-ulog 交叉判读）
#   + /mavros/home_position               —— HOME 事件（179=DO_SET_HOME 型取证）
#   + /vins_estimator/reboot_notify       —— VINS 重初始化/重启事件直供（雪崩判读关键，本树 T1 补丁话题）
#   + /tf_static                          —— 静态外参坐标（回放/重定位必备）
#   - /vins_estimator/feature_pts         —— 死条目删除（源码树无此发布器，grep 零命中）
#   ~ /camera/rgb/image_rect_color        —— 死条目（话题名错，实袋零消息）→ 彩图改为可选：
#       RECORD_COLOR=1 bash realflight_record_v1.sh 时录 /camera/color/image_raw（真名）
#       默认关：彩图仅判读参考价值，开时录速 +27MB/s（36→63MB/s）
#   磁盘门 20G→40G（实测录速≈36MB/s≈130GB/h；原 20G 门过门后仅够录约 9 分钟）
# 原则: 录一切、NVMe 直录、磁盘水位线告警、录后即时验证
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"

BAG_DIR=~/flight_data/$(date +%Y%m%d_%H%M%S)
mkdir -p $BAG_DIR
START_EPOCH=$(date +%s)

# --- v1.5: 收尾（正常结束 / Ctrl+C / SIGTERM 都执行）——截取录制时间窗内的 VINS/px4ctrl 日志 ---
FINISHED=0

  # 2026-11-12 P10：落地后再停录。**必须在杀掉 rosbag 之前调用**（trap 里先 wait_landing 再 kill），
  # 否则袋已经关了，等落地只是空等。
  wait_landing() {
      # 2026-11-12 质量修复 G：参数=最多等几秒；0=用户主动中止，立即返回。
      local _max=${1:-30}
      if [ "$_max" -le 0 ]; then echo "  (中止：跳过落地等待)"; return 0; fi
      echo "--- 等待落地（最多 ${_max}s）---"
      local _t0=$(date +%s) _landed=0 _armed=0
      # 2026-11-12：未解锁=已落地，立即返回。否则正常停录也要等 30s，会撞 flight.sh stop 的等待窗。
      if [ "$(timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -c 'armed: True')" -eq 0 ]; then
          echo "  ✓ 未解锁（视为已落地），跳过等待"; return 0
      fi
      while [ $(( $(date +%s) - _t0 )) -lt $_max ]; do
          _landed=$(timeout 2 rostopic echo -n1 /mavros/extended_state 2>/dev/null | grep -c "landed_state: 1")
          _armed=$(timeout 2 rostopic echo -n1 /mavros/state 2>/dev/null | grep -c "armed: False")
          if [ "${_landed:-0}" -ge 1 ] && [ "${_armed:-0}" -ge 1 ]; then
              echo "  ✓ 已落地+已上锁（等了 $(( $(date +%s) - _t0 ))s）"; return 0
          fi
          sleep 1
      done
      echo "  ⚠ ${_max}s 未确认落地，强制停录"
      return 0
  }

finish() {
    [ "$FINISHED" = "1" ] && return 0
    FINISHED=1
    END_EPOCH=$(date +%s)
    echo "DONE: $BAG_DIR"

    _extract_window() {
        local log="$1" out="$2"
        [ -f "$log" ] || return 0
        # 时间戳解析（2026-11-06 v1.11）：
        #   ① VINS 自定义格式：行内有 t=<epoch> token
        #   ② ROS 标准格式：[INFO] [1793971430.085048098]: ...（px4ctrl 走这条）
        # 坑：第一版用 `[0-9]{10}` 区间量词，**mawk 不支持**，仍抽出 0 行。
        # 现改为"按方括号切分、取第一个纯 数字.数字 段"，不依赖区间量词。
        awk -v lo="$START_EPOCH" -v hi="$((END_EPOCH + 5))" '
        {
            t = -1
            for (i = 1; i <= NF; i++) if ($i ~ /^t=/) { t = substr($i, 3) + 0; break }
            if (t < 0) {
                n = split($0, p, /[][]+/)
                for (k = 1; k <= n; k++)
                    if (p[k] ~ /^[0-9]+[.][0-9]+$/) { t = p[k] + 0; break }
            }
        }
        t >= lo && t <= hi' "$log" > "$out" 2>/dev/null
        echo "WINDOW-LOG: $out ($(wc -l < "$out" 2>/dev/null) lines, src=$log)"
    }
    # 2026-11-05：不再只取"最新那个日志"——VINS 在录包期间被重启过时，最新日志可能
    # 恰好不含本窗口的行（20261105_222957 的 vins_window.log 因此为 0 字节）。
    # 改为对最新 3 个候选日志逐个抽取再合并；只保留落在本时间窗内的行，混入无害。
    # 参数展开后 ~ 不会再被展开，所以 glob 必须由调用方(caller)展开后传入
    _extract_all() {
        local out="$1"; shift
        local n=0
        : > "$out"
        for L in "$@"; do
            _extract_window "$L" "$out.tmp"
            cat "$out.tmp" >> "$out" 2>/dev/null
            n=$((n + $(wc -l < "$out.tmp" 2>/dev/null || echo 0)))
        done
        rm -f "$out.tmp"
        echo "WINDOW-LOG-ALL: $out ($n lines from $# logs)"
    }
    # 2026-11-07 shellcheck SC2046：未加引号的命令替换会做词分割（路径带空格就拆错参数）。
    # 改成 mapfile 数组逐项传入。
    mapfile -t _vlogs < <(ls -t ~/sitl_realmachine/vins_*.log ~/sitl_realmachine/*/vins_*.log 2>/dev/null | head -3)
    _extract_all "$BAG_DIR/vins_window.log" "${_vlogs[@]}"
    mapfile -t _plogs < <(ls -t ~/sitl_realmachine/px4ctrl_*.log ~/sitl_realmachine/*/px4ctrl_*.log 2>/dev/null | head -3)
    _extract_all "$BAG_DIR/px4ctrl_window.log" "${_plogs[@]}"

    # 2026-11-08（用户令）：rosbag 被强杀时会只剩 .active（今晚 22:41 那袋）。
    # 先把 .active 收编成正式 bag，再走下面的 reindex，否则 `[ -f flight.bag ]` 为假，
    # 兜底逻辑整个被跳过 —— 包就永远停在"未索引"状态。
    if [ ! -f "$BAG_DIR/flight.bag" ] && [ -f "$BAG_DIR/flight.bag.active" ]; then
        echo "REINDEX: 只有 .active，先收编再重建索引"
        cp "$BAG_DIR/flight.bag.active" "$BAG_DIR/flight.bag"
        if rosbag reindex -f "$BAG_DIR/flight.bag" >/dev/null 2>&1; then
            rm -f "$BAG_DIR/flight.bag.orig"
            mv "$BAG_DIR/flight.bag.active" "$BAG_DIR/flight.bag.active.bak"
            echo "REINDEX: OK（.active 已收编，原文件留 .active.bak）"
        else
            echo "REINDEX: FAIL（.active 原样保留）"
        fi
    fi

    # 2026-11-05 兜底：rosbag 被强杀（SSH 掉线/ kill -9）会留下未索引包，自动重建
    if [ -f "$BAG_DIR/flight.bag" ]; then
        if ! python3 -c "import rosbag,sys; rosbag.Bag(sys.argv[1]).close()" "$BAG_DIR/flight.bag" 2>/dev/null; then
            echo "REINDEX: 包未索引，自动重建"
            rosbag reindex -f "$BAG_DIR/flight.bag" >/dev/null 2>&1
            if python3 -c "import rosbag,sys; rosbag.Bag(sys.argv[1]).close()" "$BAG_DIR/flight.bag" 2>/dev/null; then
                rm -f "$BAG_DIR/flight.bag.orig"
                echo "REINDEX: OK（.orig 已删）"
            else
                echo "REINDEX: FAIL（.orig 保留，人工处理）"
            fi
        fi
    fi

    # 2026-11-08（用户令）：收尾审计 —— 关键话题没录到就大声报，别让人拿废袋下结论
    if [ -f "$BAG_DIR/flight.bag" ]; then
        python3 "$HOME/sitl_realmachine/flight_v1/record_audit.py" "$BAG_DIR/flight.bag"             | tee "$BAG_DIR/record_audit.txt" || true
    fi

    # 2026-11-12 P10：空袋自动判废。rosbag info 的 duration 形如 "1:34s (94s)"，
    # 旧正则 duration: \K[\d.]+ 只会抓到 "1"（错）；改为取括号里的秒数。
    # position_cmd 取**消息数**（话题行 "  /position_cmd  6212 msgs"），不是行数。
    if [ -f "$BAG_DIR/flight.bag" ]; then
        # 2026-11-12（实测）：短袋 human 格式是 "21.1s"（无括号），长袋是 "1:34s (94s)"；
        # 统一改用 --yaml（duration 是纯秒数，实测 21.133527 / 94.3），不再解析 h:m:s。
        _dur=$(timeout 15 rosbag info --yaml "$BAG_DIR/flight.bag" 2>/dev/null | awk '/^duration:/{print $2; exit}')
        _ncmd=$(timeout 15 rosbag info "$BAG_DIR/flight.bag" 2>/dev/null | grep -oP "/position_cmd\s+\K[0-9]+" | head -1)
        if [ -n "$_dur" ] && awk -v d="$_dur" "BEGIN{exit !(d<30)}" && [ "${_ncmd:-0}" -eq 0 ]; then
            mkdir -p ~/flight_data/_empty
            mv "$BAG_DIR" ~/flight_data/_empty/ 2>/dev/null
            echo "  ⚠ 空袋（${_dur}s 无 position_cmd），已移至 _empty/"
        fi
    fi
}
on_stop() {
    # 2026-11-12 质量修复 G：TERM/HUP=优雅停（等落地 30s）；INT=用户主动中止（立即停）。
    wait_landing "$1"
    kill -INT $RECORD_PID 2>/dev/null
    for _i in 1 2 3 4 5 6 7 8 9 10; do kill -0 $RECORD_PID 2>/dev/null || break; sleep 1; done
    kill -TERM $RECORD_PID 2>/dev/null
    [ -n "${RSS_PID:-}" ] && kill ${RSS_PID} 2>/dev/null
    wait $RECORD_PID 2>/dev/null
    finish
    exit 0
}
trap 'on_stop 30' TERM HUP
trap 'on_stop 0' INT

AVAIL=$(df -BG --output=avail $HOME | tail -1 | tr -d 'G ')
# 2026-11-06：门限 40G -> 35G。实测录速约 36MB/s；rosbag 自身还有 --min-space 10G 兜底，
# 所以 35G 门 = 实际可用 25G ≈ 11 分钟 ≈ 3-4 轮，安全余量不变。
# （起因：飞了几轮后磁盘到 38G，40G 门直接把录制挡了，而不是真的空间不够。）
if [ "$AVAIL" -lt 35 ]; then
    echo "DISK-FAIL: ${AVAIL}G available (need >=35G)"
    exit 1
fi

CAM_TOPICS=(
    /camera/infra1/image_rect_raw
    /camera/infra1/camera_info
)
if [ "${RECORD_STEREO:-1}" = "1" ]; then   # 2026-11-05 用户指令：暂时默认录双目+深度（33->63MB/s）
    # 2026-11-05：深度话题暂时移出录制——18MB/s 占总量一半，实测双目+深度录制时
    # px4ctrl 出现 2.385s 控制流断流（PX4 因此掉出 OFFBOARD）。先只录双目验证。
    CAM_TOPICS+=(
        /camera/infra2/image_rect_raw
        /camera/infra2/camera_info
    )
fi

TOPICS=(
    "${CAM_TOPICS[@]}"
    /mavros/imu/data
    /mavros/imu/data_raw
    /mavros/imu/mag
    /mavros/imu/temperature_imu
    /mavros/estimator_status
    /mavros/state
    /mavros/battery
    /mavros/local_position/odom
    /mavros/rc/in
    /mavros/rc/out
    /mavros/vision_pose/pose
    /mavros/extended_state
    /mavros/time_reference
    /mavros/home_position
    /mavros/setpoint_raw/attitude
    /mavros/setpoint_raw/local
    /vins_estimator/odometry
    /vins_estimator/imu_propagate
    /vins_estimator/reboot_notify
    /vins_estimator/keyframe_pose
    /vins_estimator/extrinsic
    /vins_estimator/camera_pose
    # 2026-11-08 (user order #8) depth into the bag: 16UC1 640x480@30 ~18 MB/s
    # (2 min ~ 2.2 GB; --min-space 10G still guards)
    /camera/depth/image_rect_raw
    /camera/depth/camera_info
    /position_cmd
    # 2026-11-08（症状4）：预期轨迹回传 + 目标点 + 规划器原始样条（离线判读用）
    /flight_v1/planned_path
    /flight_v1/executed_trail
    /flight_v1/goal_marker
    /flight_v1/goal_gate
    /drone_0_planning/bspline
    /move_base_simple/goal
    /px4ctrl/takeoff_land
    /debugPx4ctrl
    /debugPx4ctrl/fsm_state
    /tf
    /tf_static
    /rosout
)
[ "${RECORD_COLOR:-0}" = "1" ] && [ "${RECORD_STEREO:-1}" = "1" ] && TOPICS+=(/camera/color/image_raw)

# 2026-11-07：起录前检查历史遗留的未收尾 bag（.active）。
# 2026-11-07 11:55 那袋 2.1GB 至今是 .active —— rosbag 被强杀/终端断开时 trap 没跑到，
# 索引没写完 -> 事后 rosbag info 读不了，数据等于差点丢。这里主动报出来并给恢复命令。
_ACTIVE=$(find ~/flight_data -maxdepth 2 -name "*.bag.active" -size +10M 2>/dev/null | head -5)
if [ -n "$_ACTIVE" ]; then
  echo "⚠ 发现未收尾的 bag（.active，索引未写完）："
  echo "$_ACTIVE" | sed "s/^/    /"
  echo "  恢复方法（会生成同名 .bag，不动原件）："
  echo "    cp <xxx.bag.active> /tmp/fix.bag && rosbag reindex /tmp/fix.bag"
fi

# 2026-11-07：录包前清掉 master 里的僵尸注册。
# 症状：rosbag 启动后刷 "Error in XmlRpcClient::writeRequest: write error (Connection refused)"。
# 机理：rosbag 订阅时向 master 要发布者列表，master 把**已死节点**的 XMLRPC URI 也返回，
#       rosbag 挨个去连 -> Connection refused。根因是节点被强杀没注销（pkill -9 / 掉线）。
# 修法：起录前 rosnode cleanup 把死节点从 master 摘掉（只读动作，不动活节点）。
# 2026-11-10：默认**不做** rosnode cleanup —— 它按 XMLRPC ping 判活，忙在求解里的 VINS/相机可能被误摘，表现为'进程还在/话题断流'。
# 确实有僵尸注册时再手动：RECORD_CLEANUP=1 bash realflight_record_v1.sh
if [ "${RECORD_CLEANUP:-0}" = "1" ]; then
  yes 2>/dev/null | timeout 10 rosnode cleanup >/dev/null 2>&1 || true
fi
# 2026-11-08（用户令⑤）：录包清单由 flight_v1/sync_params.py 生成，这里直接读；
# 需要临时手工清单时设 RECORD_USE_GENERATED=0 回退到上面的数组。
GEN_TOPICS="$HOME/sitl_realmachine/flight_v1/generated/record_topics.txt"
if [ "${RECORD_USE_GENERATED:-1}" = "1" ] && [ -s "$GEN_TOPICS" ]; then
  mapfile -t TOPICS < <(grep -v "^#" "$GEN_TOPICS" | sed "/^$/d")
  echo "  [topics] 用生成清单 $GEN_TOPICS（${#TOPICS[@]} 个）"
fi
# 2026-11-10（用户批准）：lz4 压缩。38 话题未压缩 31 MB/s 时磁盘 await 到 0.95 s，
# 把 camera_pose 拖停 2.46 s；压缩只减写盘量，不丢任何话题。
# 2026-11-11（用户令：视觉不降流 + 压缩录包）：bag 里录"降频副本"，
# VINS 仍消费 30 fps 原始流，互不影响。RECORD_THROTTLE=0 可关。
if [ "${RECORD_THROTTLE:-1}" = "1" ]; then
  # 2026-11-11：换成自写的精确定时器节流（topic_tools 实测只有 8.1/11.4/12.8 Hz）
  python3 "$HOME/sitl_realmachine/flight_v1/record_throttle.py" >/dev/null 2>&1 &
  TH1=$!; TH2=; TH3=
  echo "  [throttle] 录包副本: infra1/2 15Hz, depth 10Hz（VINS 仍用原始 30Hz）"
  sleep 2
else
  # 2026-11-11：RECORD_THROTTLE=0 时必须把 /record/* 还原成原始话题，
  # 否则录的是没人发布的副本（实测 120 s 只录到 25 MB）。
  TOPICS=("${TOPICS[@]/\/record\/depth//camera/depth/image_rect_raw}")
  TOPICS=("${TOPICS[@]/\/record\/infra1//camera/infra1/image_rect_raw}")
  TOPICS=("${TOPICS[@]/\/record\/infra2//camera/infra2/image_rect_raw}")
  echo "  [throttle] 关闭：录原始话题（全速）"
fi

rosbag record -O $BAG_DIR/flight.bag --lz4 --min-space 10G "${TOPICS[@]}" &
RECORD_PID=$!
echo "RECORDING pid=$RECORD_PID dir=$BAG_DIR topics=${#TOPICS[@]} mode=$([ "${RECORD_STEREO:-1}" = "1" ] && echo STEREO-only || echo MONO-left)"

VINS_PID=$(pgrep -f vins_node | head -1)
if [ -n "$VINS_PID" ]; then
    ( while kill -0 $VINS_PID 2>/dev/null && kill -0 $RECORD_PID 2>/dev/null; do
          RSS=$(ps -o rss= -p $VINS_PID 2>/dev/null | tr -d ' ')
          echo "$(date +%s),$RSS" >> $BAG_DIR/vins_rss.csv
          sleep 60
      done ) &
    RSS_PID=$!
fi
wait $RECORD_PID
[ -n "${RSS_PID:-}" ] && kill $RSS_PID 2>/dev/null
finish
