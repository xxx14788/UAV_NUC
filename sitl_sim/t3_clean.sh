#!/usr/bin/env bash
# T3 会话清理（写成文件防 pkill -f 模式自匹配 ssh 复合命令行）。
# W14 升级（2026-09-28）：加 /dev/shm 与 ipcs 共享内存段清理、Xvfb 管理、
# 按修改时间报告 SITL 相关残留文件。用法同旧版：bash t3_clean.sh [--keep-xvfb]
KEEP_XVFB=0
[ "${1:-}" = "--keep-xvfb" ] && KEEP_XVFB=1

echo "== t3_clean $(date '+%F %T') =="
pkill -f 't3_verify_flight.s[h]'
pkill -f 'two_leg_flight.s[h]'
sleep 2
pkill -f 'devel/lib/ego_planne[r]'
pkill -f 'roslaunch.*run_planner_sit[l]'
pkill -9 -f 'bin/px[4]'
pkill -9 -f 'gzserve[r]'
pkill -f 'px4ctrl_nod[e]'
pkill -f 'roslaunch.*run_ctrl_sit[l]'
pkill -f 'roslaunch.*px4launc[h]'
pkill -f 'rosbag recor[d]'
pkill -f 'roslaunc[h]' 2>/dev/null
pkill -f 'rosmaste[r]' 2>/dev/null
pkill -f 'roscore' 2>/dev/null
pkill -f 'rosout' 2>/dev/null
sleep 2

# /dev/shm 残留（gazebo 传感器/transport 段）
n_shm=$(ls /dev/shm 2>/dev/null | wc -l)
if [ "$n_shm" -gt 0 ]; then
    echo "清 /dev/shm 残留 $n_shm 项"
    ls /dev/shm 2>/dev/null | while read -r f; do rm -f "/dev/shm/$f"; done
fi
# gazebo 共享内存段（SysV）
n_ipc=$(ipcs -m 2>/dev/null | grep -c '^0x' || true)
if [ "${n_ipc:-0}" -gt 0 ]; then
    echo "清 SysV shm 段 $n_ipc 个"
    ipcs -m 2>/dev/null | grep '^0x' | awk '{print $2}' | while read -r id; do ipcrm -m "$id" 2>/dev/null; done
fi
# Xvfb：默认一并杀（--keep-xvfb 保留长驻 rviz 用）
if [ "$KEEP_XVFB" -eq 0 ]; then
    pkill -f 'Xvfb :9[9]' 2>/dev/null && echo "Xvfb :99 已停"
fi

rm -f "$HOME/sitl_sim/SITL.lock"

# 残留报告：>1h 的 active bag / 超大 bag（10GB 级，录制清单含深度流后易膨胀）
echo "-- 残留大文件（>500MB，含未关闭 .active）--"
find "$HOME/sitl_sim" -name '*.bag*' -size +500M -printf '%s\t%p\n' 2>/dev/null \
    | awk -F'\t' '{printf "%.1fGB\t%s\n", $1/1073741824, $2}' | head -8
echo "-- 遗留进程复核 --"
pgrep -a -f 'bin/px[4]|gzserve[r]|px4ctrl_nod[e]|rosbag recor[d]|Xvf[b]' | head -4 || true
echo CLEANED
