#!/usr/bin/env bash
# T3 会话清理(写成文件防 pkill -f 模式自匹配 ssh 复合命令行)
pkill -f 't3_verify_flight.s[h]'
sleep 2
pkill -f 'devel/lib/ego_planne[r]'
pkill -f 'roslaunch.*run_planner_sit[l]'
pkill -9 -f 'bin/px[4]'
pkill -9 -f 'gzserve[r]'
pkill -f 'px4ctrl_nod[e]'
pkill -f 'roslaunch.*run_ctrl_sit[l]'
pkill -f 'roslaunch.*px4launc[h]'
pkill -f 'rosbag recor[d]'
sleep 2
rm -f $HOME/sitl_sim/SITL.lock
echo CLEANED
