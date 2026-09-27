#!/usr/bin/env bash
# env_health_check.sh — SITL 环境健康五项自检（T3-P0 产物，2026-09-28）。
# 供每晚开工与 smoke 前置调用；退出码 0=健康 1=有 FAIL。
# 用法: env_health_check.sh [--with-sitl]   # SITL+mavros 在跑时加 --with-sitl
#   做参数与深度流两项在线检查
# 五项:
#   1) PX4 磁/EKF 参数卫生（--with-sitl: CAL_MAG*_ID 应为 0/默认、
#      EKF2_MAG_DECL 应为 0、SENS_BOARD_ROT 默认——2026-09-27 磁污染事故后防线）
#   2) /dev/shm 残留与 gazebo 共享内存段
#   3) SITL 相关进程孤儿（无锁却跑着 gzserver/px4/Xvfb/rosbag）
#   4) 深度流频率（--with-sitl: 名义 30Hz，<20Hz 判 FAIL——llvmpipe 饱和前兆）
#   5) 日志体量（~/.ros/log >2GB WARN）
set -u
source /opt/ros/noetic/setup.bash 2>/dev/null || true
WITH_SITL=0
[ "${1:-}" = "--with-sitl" ] && WITH_SITL=1
FAILS=0; WARNS=0
pass() { echo "  [PASS] $1"; }
warn() { echo "  [WARN] $1"; WARNS=$((WARNS+1)); }
fail() { echo "  [FAIL] $1"; FAILS=$((FAILS+1)); }

echo "== env_health_check $(date '+%F %T') =="

echo "-- 1) PX4 磁/EKF 参数卫生 --"
if [ "$WITH_SITL" -eq 1 ] && rostopic list 2>/dev/null | grep -q mavros; then
    for p in CAL_MAG0_ID CAL_MAG1_ID EKF2_MAG_DECL SENS_BOARD_ROT; do
        v=$(timeout 10 rosservice call /mavros/param/get "param_id: '$p'" 2>/dev/null \
            | grep -oE 'integer: [0-9]+|real: [-0-9.e]+' | head -1 | awk '{print $2}')
        case "$p" in
            CAL_MAG0_ID|CAL_MAG1_ID) [ "${v:-1}" = "0" ] && pass "$p=0 (复位态)" || fail "$p=$v 非零(磁校准残留,见 t1_evidence/w4_cert_runbook.md)";;
            EKF2_MAG_DECL) v2=$(echo "${v:-1}" | awk '{printf "%.3f", $1}'); [ "$v2" = "0.000" ] && pass "$p=0" || fail "$p=$v 非0(195°磁偏注入事故同源)";;
            SENS_BOARD_ROT) [ "${v:-x}" = "0" ] && pass "$p=0" || warn "$p=$v (非默认,人工确认)";;
        esac
    done
else
    warn "mavros 未运行,跳过参数检查(加 --with-sitl 且 SITL 在跑时执行)"
fi

echo "-- 2) /dev/shm 与共享内存 --"
n_shm=$(ls /dev/shm 2>/dev/null | wc -l)
[ "$n_shm" -le 2 ] && pass "/dev/shm 条目 $n_shm" || warn "/dev/shm 条目 $n_shm (重启后应近空)"
n_ipc=$(ipcs -m 2>/dev/null | grep -c '^0x')
n_ipc_dest=$(ipcs -m 2>/dev/null | grep '^0x' | grep -c dest)
[ "$n_ipc_dest" -eq "$n_ipc" ] && pass "shm 段 $n_ipc 全为 dest 态" || warn "shm 段 $n_ipc 中非 dest 态 $((n_ipc-n_ipc_dest)) 个(gazebo 泄漏迹象,ipcs -m 复核)"

echo "-- 3) SITL 进程孤儿 --"
LOCK="$HOME/sitl_sim/SITL.lock"
orphans=""
pgrep -f "bin/px[4]" >/dev/null && orphans="$orphans px4"
pgrep -f "gzserve[r]" >/dev/null && orphans="$orphans gzserver"
pgrep -f "rosbag recor[d]" >/dev/null && orphans="$orphans rosbag"
if [ -n "$orphans" ]; then
    if [ -L "$LOCK" ]; then
        pass "运行中进程:$(echo $orphans)(锁属 $(readlink "$LOCK"),非孤儿)"
    else
        fail "无锁但有进程在跑:$orphans —— 先 t3_clean.sh 清场"
    fi
else
    pass "无 SITL 孤儿进程"
fi

echo "-- 4) 深度流频率 --"
if [ "$WITH_SITL" -eq 1 ] && rostopic list 2>/dev/null | grep -q iris_depth_camera; then
    hz=$(timeout 22 rostopic hz /iris_depth_camera/camera/depth/image_raw 2>/dev/null | tail -1 | grep -oE 'average rate: [0-9.]+' | awk '{print $3}')
    if [ -z "$hz" ]; then fail "深度流 20s 无输出(渲染饿死,relay 事故签名)"; \
    elif awk "BEGIN{exit !($hz < 20)}"; then fail "深度流 ${hz}Hz < 20Hz(llvmpipe 饱和前兆)"; \
    else pass "深度流 ${hz}Hz"; fi
else
    warn "深度相机话题不可达,跳过(--with-sitl 且 SITL 在跑时执行)"
fi

echo "-- 5) 日志体量 --"
sz=$(du -sm ~/.ros/log 2>/dev/null | cut -f1)
[ "${sz:-0}" -lt 2000 ] && pass "~/.ros/log ${sz:-0}MB" || warn "~/.ros/log ${sz}MB >2GB(可清:rm -rf ~/.ros/log/*)"
sz2=$(du -sm /tmp 2>/dev/null | cut -f1)
[ "${sz2:-0}" -lt 500 ] && pass "/tmp ${sz2:-0}MB" || warn "/tmp ${sz2}MB"

echo "== 结果: FAIL=$FAILS WARN=$WARNS =="
[ "$FAILS" -eq 0 ] && exit 0 || exit 1
