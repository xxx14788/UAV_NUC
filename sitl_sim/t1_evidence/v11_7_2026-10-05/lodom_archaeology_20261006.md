# L-odom U2.5 考古件（跨机；2026-10-06 04:2x；任务书 v11.13 单元 4）

> 目标：找回 E4R2-GOFF-D10-LODOM_100819（R3，L-odom 臂唯一轮，2026-10-03 10:08 NUC）的接线脚本（重建前置）。

## 考古路径与结果（全灭失定性）

| 路径 | 结果 |
|---|---|
| NUC ~/.bash_history grep l_odom/ev/cs_ev | 空 |
| NUC ~/.ros/log/4f4535aa…(R3 时段 master) roslaunch-*.log | 无 relay/odometry 节点命令行 |
| NUC ~/sitl_sim/*.sh（含 e4_wheel.sh/fly_round.sh/round.log） | 标准流程无接线段 |
| NUC catkin_ws src/px4ctrl launch（odom_topic/remap） | 无参数命中；git log px4ctrl 无接线 commit |
| NUC catkin_ws untracked + stash@{0}(autostash) | 仅 selftest json + 已知 .bak，无桥脚本 |

## 判定：灭失不阻塞

1. 接线脚本（VINS odometry → /mavros/odometry/out 桥）确已灭失——rebuild 须重写（规格完整可重写：u25_lodom_framing_verdict.md §1-2 已钉死消息/帧/stamp/协方差全语义）。
2. 但 U2.5 已判 L-odom 臂**不合格**（mavros 1.20.1 odom 插件 TF 树不连通+失败后未初始化内存=上游缺陷，J1 恒偏移 0.783/cs_ev_yaw=0 实证）——重建的前提是先修上游 mavros 或改走 L-pose 硬编码路径，**修复面决策在案（帧域）**。
3. 结论：考古=负结果如实闭卷；L-odom 臂重建挂"上游修复决策"后（非本线可独走），净窗三合一路径不受阻（P2/P3 已有净轮面，L-odom 位由 L-pose 对照补位可选）。
