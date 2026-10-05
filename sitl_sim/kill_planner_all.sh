#!/usr/bin/env bash
# 清场：杀掉所有 planner 相关进程。
# 注意：进程 comm 名最长 15 字符，ego_planner_node 会被截断，必须用 pgrep -f
# 匹配完整命令行。2026-10-05 3090 勘误：catkin build(catkin_tools) 的进程真实路径=
# devel/.private/ego_planner/lib/...(旧 catkin_make 时代=devel/lib/ego_planner/)。
# 2026-10-05 v11.7 模式修复(单元1 disarm 五连败根因,disarm_fix_prereg_v1 §2-F1):
#   旧模式两支都匹配不到 catkin build 真实路径 devel/.private/ego_planner/lib/
#   ego_planner/traj_server("lib/" 后是 "ego_planner/" 不是 "traj_server")→
#   traj_server 漏杀续发 /position_cmd→px4ctrl 卡 CMD_CTRL→LAND 全拒→
#   auto_disarm=0(X2g1/g3/g4/X3l2a/l2b 五轮同根,取证=prereg §1 E1-E5 链)。
#   统一改两路径形共同后缀 "lib/ego_planner/<bin>"(catkin_make 与 catkin build 通吃)。
# 2026-10-05 强化:三轮(X2g3 轮实证两轮后仍有孤儿存活,当时疑 roslaunch respawn 竞态;
# v11.7 取证定案=模式失配而非 respawn——launch 无 respawn=true;三轮循环保留作兜底)
for round in 1 2 3; do
  for p in $(pgrep -f "lib/ego_planner/ego_planner_node"); do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "lib/ego_planner/traj_server");      do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "roslaunch ego_planner");           do kill -9 "$p" 2>/dev/null; done
  sleep 2
done
n=$(pgrep -cf "lib/ego_planner/ego_planner_node|lib/ego_planner/traj_server")
echo "after_kill=$n"
