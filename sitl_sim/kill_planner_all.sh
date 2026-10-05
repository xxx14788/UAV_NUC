#!/usr/bin/env bash
# 清场：杀掉所有 planner 相关进程。
# 注意：进程 comm 名最长 15 字符，ego_planner_node 会被截断，必须用 pgrep -f
# 匹配完整命令行。2026-10-05 3090 勘误：catkin build(catkin_tools) 的进程真实路径=
# devel/.private/ego_planner/lib/...(旧 catkin_make 时代=devel/lib/ego_planner/)——
# 双模式兼容(grep -E 交替),after_kill 统计同改;漏杀实证=T2MACH8 轮+X2g1 轮孤儿(3090)。
# 2026-10-05 强化:三轮(X2g3 轮实证两轮后仍有孤儿存活,疑 roslaunch respawn 竞态——
# node 先杀会触发 respawn 拉新;roslaunch 主进程死透需时间,第三轮兜底)
for round in 1 2 3; do
  for p in $(pgrep -f "devel/lib/ego_planner/ego_planner_node|ego_planner/lib/ego_planner_node"); do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "devel/lib/ego_planner/traj_server|ego_planner/lib/traj_server");          do kill -9 "$p" 2>/dev/null; done
  for p in $(pgrep -f "roslaunch ego_planner");                                                  do kill -9 "$p" 2>/dev/null; done
  sleep 2
done
n=$(pgrep -cf "devel/lib/ego_planner/ego_planner_node|ego_planner/lib/ego_planner_node|devel/lib/ego_planner/traj_server|ego_planner/lib/traj_server")
echo "after_kill=$n"
