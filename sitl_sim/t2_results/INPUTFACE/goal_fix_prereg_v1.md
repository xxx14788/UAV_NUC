# 单元 1 预热 goal 切换协议修复预注册（v1.0 FROZEN）

任务书：2026-10-09_T2_vins_quality_v10.7.md 单元 1
冻结时刻：2026-10-09 03:5x（T2 v10.7 会话；落码前冻结）

## 1. 根因定案（证据链，已钉死）

标本 run_WU_E12O_A_164025（A 臂，FAIL 到位 14.047m）：

- F1 warmup 流（t2_warmup_segment.py --hz 10, 8s, 81 goal）把 ego FSM 从 WAIT_TARGET 拖入
  EXEC/REPLAN 循环：planner.log "[FSM]: from REPLAN_TRAJ to REPLAN_TRAJ" 连续自环；
  FSM_LEFT_WAIT_TARGET=1（INIT→WAIT 仅此一次，此后全程未回 WAIT_TARGET）。
- F2 mission goal 发布 16 次（goal_pub 2×8s×1Hz），Triggered 仅 20 次（全部集中在
  warmup 段处理窗口；订阅队列=1 + planNextWaypoint 内含 while(spinOnce) 死等 +
  planGlobalTraj 重计算 → 大量丢弃）。
- F3 waypointCallback→planNextWaypoint 源码路径（plan_manage/src/ego_replan_fsm.cpp:158）：
  exec_state_==WAIT_TARGET → GEN_NEW_TRAJ（B 臂正路）；否则死等 EXEC_TRAJ →
  changeFSMExecState(REPLAN_TRAJ)——mission goal 全部走了 REPLAN 侧路径，失效。
- F4 终态铁证：tsdiag 尾部连续 pos=(0.14,-0.25,1.00) vel=0 traj_id=15（=warmup 尾点
  悬停），t_cur=329-337s 全程未向 mission goal (13.01,0.98,1.0) 移动一毫米级；
  poscmd_hz=100.000（traj_server 活=starve-detect 假阴性放行的机理）。
- F5 B 臂同 harness 无 warmup 段：mission goal 到 WAIT_TARGET 态走 GEN_NEW_TRAJ 正路
  →4/8 PASS（正常绿率分布）→ 病灶唯一差异=warmup 段的 FSM 状态污染。

结论：goal 切换协议缺陷=harness 层（warmup 流结束时 FSM 处于非 WAIT_TARGET 态，
mission goal 在该态走 REPLAN 路径失效）；激励本身（VINS 段预热）未被证伪。

## 2. 修复案三支评估（选案依据写死）

- 案① warmup 终止 goal 消隐：warmup 毕后 harness 进入 goal-silent 窗，让 FSM
  自行收敛回 WAIT_TARGET 再发 mission goal。【采纳，与案②联合】
- 案② FSM 稳定门：warmup 毕后 grep planner.log 等 "to WAIT_TARGET" 转换证据，
  证据在案才发 mission goal；等不到→planner 整栈重启一次（复用 v11.17 starve
  基建 kill_planner_all+relaunch）→重启后 FSM=INIT→WAIT_TARGET 干净态。
  【采纳，为主承载】
- 案③ mission goal 提频重发：【证伪，排除】——A 臂既有数据 mission goal 已发 16 次
  （8s×1Hz×2）全部失效，失效与频率无关与 FSM 态有关；提频只会重复踩 REPLAN 路径。

## 3. 落码方案（harness 面，零栈改动）

落点：vins_smoke.sh（WARMUP 段后插入 W1-W3；W4 复用既有 target_moved）。

- W1 goal-silent 稳定门：warmup 毕后不发 goal，轮询 planner.log 新增
  "to WAIT_TARGET" 行（fsm_back_to_wait()：以 warmup 完成时刻的字节偏移为基线
  grep 后缀），上限 20s。
- W2 重启兜底：20s 无回转→starve 基建重启 planner 一次（mv planner.log→
  planner_starved_wu_1.log + kill_planner_all + relaunch + wait_planner_ready 25）；
  重启后仍无 WAIT_TARGET（初始化期短暂出现后离开属正常——以 fsm_beat+goal_sub_ok
  就绪即视为可发）→WARN 注记后照发（判读面如实，勿盲续口径不变）。
- W3 mission goal 发布：WAIT_TARGET 证据在案（或重启后就绪）→goal_pub 2×8s 照旧
  （B 臂同构路径）。WARMUP=0 臂路径逐字节不变（B 臂控制变量铁律）。
- W4 采纳验证门（判读面）：mission goal 发毕 8s 内 target_moved（"from WAIT_TARGET
  to"）或 poscmd>1Hz+到位监视位移——记录 warmup_goal_adopted.txt；无证据=WARN 行
  入 RESULT 判读面。

## 4. 干测判据（单元 1 DoD，≥1 轮）

goal 采纳验证轮（WU_FIX_E8P_A，E8P 格 9.010,0.980,1.0 plain，--warmup）证据链
四件全要：
- G1 goal_trace 记录 mission goal 发布（区别于 warmup 81 goal 的 seq 序列）；
- G2 planner.log 出现 warmup 后的 "to WAIT_TARGET" 回转行（W1 门放行依据）；
- G3 mission goal 后 "from WAIT_TARGET to"（=GEN_NEW_TRAJ 转换=采纳证据）；
- G4 tsdiag/到位监视：机体向 mission goal 位移（到位 min 显著小于 A 臂旧病理值
  7-14m；参照 B 臂健康分布 0.1-0.4m）。
四件齐=修复 PASS→单元 2 复验批放行；任一缺=受阻如实记录（双必达②的"修复受阻
如实记录"分支）。

## 5. 冻结声明

判据门值零变动（复验批沿 1b prereg §2.3 冻结口径：≥15pp+方向一致 ≥6/8）；
本修复不改 VINS/planner 源码一行；WARMUP=0 路径逐字节不变。
