# 单元 1 修复预注册 v1 — disarm 五连败根因（harness 侧）与修复判据冻结

> 2026-10-05 22:3x 冻结（T1 v11.7 单元 1;取证=五轮 px4ctrl.log+planner.log+kill 脚本+活体进程面）。
> 判据未预注册不出 PASS-FAIL——本文先冻结,修复与验证后按本判据落判。

## 1. 根因定案（取证链）

**根因=kill_planner_all.sh traj_server 模式漏配 catkin build 真实路径（harness 侧浅问题,非 px4ctrl 状态机深病）。**

证据链（五点闭环）:
- E1 模式失配:脚本 pgrep 模式 `devel/lib/ego_planner/traj_server|ego_planner/lib/traj_server`;
  3090 实际进程路径=`devel/.private/ego_planner/lib/ego_planner/traj_server`——
  两选一都不含该串（catkin_make 路径靠第一支匹配;catkin build 路径两支皆 miss,因其
  `lib/` 后是 `ego_planner/traj_server` 不是 `traj_server`）。ego_planner_node 模式
  `ego_planner/lib/ego_planner/ego_planner_node` 碰巧含于实际路径→只漏 traj_server。
- E2 活体:取证时刻 3090 在跑 **8 个僵尸 traj_server**（round log UUID c015..c01b）,路径
  全为 .private 形——模式可证从不匹配。
- E3 未杀实证:X2g4 planner.log tsdiag traj_id=18 以 1Hz **连续穿过 kill 窗**
  （kill 落盘 wall 03:05:45≈sim187;sim184→196→248 无断点无重启横幅）——traj_server
  全程存活续发 /position_cmd（终点悬停 (9.30,0.93,-2.75)）。planner_kill.log 报
  after_kill=0=假清净（计数模式同漏）。
- E4 px4ctrl 消费面:LAND 到达时 cmd 新鲜→CMD_CTRL;decide_cmd 对 LAND **按设计拒绝**
  （"Reject AUTO_LAND, which must be triggered in AUTO_HOVER",cmd 超时 0.5s）。
  五轮 S1（进入 AUTO_LAND）全零——**无一轮进入降落状态机**。
- E5 形态分型:①X2g1_024637/X2g3=纯 S9 列车（全程 CMD_CTRL）;②X2g4/X3l2a=U2.7 接纳
  （MANUAL→AUTO_HOVER）后 **1 秒内** cmd 复鲜回 CMD_CTRL（S4+S9）;③X3l2b=终态 odom
  劣化退 MANUAL 后 U2.7 拒（S3 终端）;④X2g1_041203=未建立飞行早死型（在册勘误面,
  disarm=0 为其从属后果）。①②③同根。
- 附:launch 无 respawn=true（grep 空）→"respawn 竞态"旧猜排除;脚本头注"漏杀实证=
  T2MACH8 轮+X2g1 轮孤儿"早已记录此面但只改了循环次数未改模式。

**U2.7 修复不完整的谜底**:U2.7 只修"LAND 到达时已在 MANUAL"的静默丢弃;本族 LAND 到达时
px4ctrl 在 CMD_CTRL（cmd 新鲜）,路径不同,U2.7 无责——px4ctrl 行为全部符合 FSM 设计。

## 2. 修复案（小修,harness 面;px4ctrl 零改动）

- **F1（根）**:kill_planner_all.sh traj_server 与 ego_planner_node 的 pgrep/计数模式改
  `lib/ego_planner/traj_server` / `lib/ego_planner/ego_planner_node`
  （两路径形共同后缀串:匹配 catkin_make `devel/lib/ego_planner/X` 与 catkin build
  `devel/.private/ego_planner/lib/ego_planner/X`;roslaunch 主进程杀行不动）。
- **F2（belt）**:06_land.sh 发 LAND 前加 /position_cmd 静默门:1s 采样窗内收到消息→
  "position_cmd 仍活跃,planner 清场失败"告警+exit 2（不进 90s 空等）。
- px4ctrl 侧零改动（判决依据=其拒绝消息本为正确诊断）。

## 3. 验证判据（冻结）

- **J1 模式覆盖（静态）**:合成 cmdline 表 {catkin_make,catkin_build}×{traj_server,
  ego_planner_node} 四行,修复后模式 4/4 匹配,修复前 traj_server×catkin_build 0/1
  （回归对照）。
- **J2 活体清场**:修复后脚本对取证时 8 僵尸执行→after_kill=0 且 pgrep -af traj_server
  空（kill 前后进程面留档）。
- **J3 门行为**:F2 门在 position_cmd 活跃时 exit=2+告警行;静默时放行（shell 级测试）。
- **J4 飞行验证（终判）**:单元 5 供给轮（带 planner 的 X1prime 型/route 型）降落段
  round_result 实读 auto_disarm=1；S1 签名（AUTO_HOVER→AUTO_LAND）在场。
- 通过面=J1-J3 即时+J4 随供给轮;**判据未过前 X 线禁飞**（X4 前置②口径）。

## 4. 深浅判定登记

浅问题（harness 模式漏配+缺门）,非状态机级——X 线时程不受影响（W-deep 不触发）。
