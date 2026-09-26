#!/usr/bin/env bash
# 清场：杀掉所有 planner 相关进程（roslaunch/node/traj_server/重启脚本自身）。
# 注意 kill 顺序：先 node 可执行名，再 roslaunch，最后兜底两轮，确认归零。
for round in 1 2; do
  for p in $(pgrep -x ego_planner_node);           do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -x traj_server);                do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "roslaunch ego_planner");    do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "restart_planner.sh");       do kill -9 "$p" 2>/dev/null; done
  sleep 2
done
n1=$(pgrep -cx ego_planner_node); n2=$(pgrep -cx traj_server); n3=$(pgrep -cf "roslaunch ego_planner")
echo "after_kill=$n1/$n2/$n3"
