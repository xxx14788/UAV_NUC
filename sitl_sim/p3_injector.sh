#!/usr/bin/env bash
# P3 reboot 注入器(T1 v11.7 单元5 ④;p3_injection_prereg_v2 协议):
# 等 vins_node 起飞后在途 → T+90s kill → 2s 后原 cmdline relaunch(同 master)。
# 全程 /proc 扫描定位,无 inline kill 模式(自匹配四连教训)。
# 用法: nohup bash p3_injector.sh <run_dir> </dev/null > /tmp/p3_injector.log 2>&1 &
# 坑位: 勿加 set -u(ROS 链);relaunch 子进程需要完整 ROS env——这里 source 后继承
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
RUN="$1"
DEADLINE=$(( $(date +%s) + 300 ))
VPID=""
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  for p in $(pgrep -x vins_node 2>/dev/null); do
    VPID="$p"; break
  done
  [ -n "$VPID" ] && break
  sleep 2
done
[ -z "$VPID" ] && { echo "no vins_node in 300s"; exit 1; }
echo "[$(date +%T)] vins_node pid=$VPID, waiting 90s in-flight"
sleep 90
# 再核进程仍活(轮可能已结束)
if [ ! -d "/proc/$VPID" ]; then echo "vins_node gone before injection"; exit 1; fi
CMD=$(tr "\0" " " < "/proc/$VPID/cmdline")
CWD=$(readlink "/proc/$VPID/cwd")
echo "[$(date +%T)] INJECT: kill -9 $VPID (cmd=$CMD cwd=$CWD)"
kill -9 "$VPID"
sleep 2
cd "$CWD" 2>/dev/null || cd "$HOME"
setsid nohup bash -c "$CMD" >> "$RUN/vins_relaunch.log" 2>&1 &
echo "[$(date +%T)] relaunch issued -> $RUN/vins_relaunch.log"
