#!/usr/bin/env bash
# 清场：杀掉所有 planner 相关进程。
# 注意：进程 comm 名最长 15 字符，ego_planner_node 会被截断，必须用 pgrep -f
# 匹配完整命令行（devel/lib/ego_planner/ 路径是稳定的特征）。
for round in 1 2; do
  for p in $(pgrep -f "devel/lib/ego_planner/ego_planner_node");  do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "devel/lib/ego_planner/traj_server");      do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "roslaunch ego_planner");                  do kill -9 "$p" 2>/dev/null; done
  sleep 2
done
n=$(pgrep -cf "devel/lib/ego_planner")
echo "after_kill=$n"
