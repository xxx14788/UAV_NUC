# starve 根治评估（4d）：ego_planner FSM timer 生命周期代码审计 v1（T1 v11.23；2026-10-07 13:2x）

## 事实链（v11.17 定案+W8P/S8O 实战）
- starve 签名=FSM 事件循环冻结→poscmd traj_id 冻结→STARVE-DETECT→重启→恢复（两轮实战恢复）
- 重启绕行检测器已在批链常态（S8O=starve 恢复后 C 型慢收卷在案）

## 代码审计（src/planner/plan_manage/src/ego_replan_fsm.cpp）

### timer 生命周期本体=**无缺陷**
- execFSMCallback:入口 `exec_timer_.stop()`（防重入）→ 三处 `goto force_return` + 正常落穿
  **全部**汇于 `force_return:; exec_timer_.start();`（455-623 行区）——无漏 start 早退路径；
- checkCollisionCallback:无 stop/start 对，早退 return 安全（timer 自续）。

### 冻结载体=**两处 spinOnce 等待循环**（上游骨架原生）
1. init 期（77-82 行，起飞前，非 starve 载体但同骨架）：
   `while(ros::ok() && (!have_odom_ || !have_trigger_)) { ros::spinOnce(); ros::Duration(0.001).sleep(); }`
2. **waypointCallback 内（187-190 行，在飞路径=starve 主嫌）**：
   `while (exec_state_ != EXEC_TRAJ) { ros::spinOnce(); ros::Duration(0.001).sleep(); }`

### 机理链（触发假设，按嫌疑排序）
- **H-s1（主嫌）：sim 时钟永眠**——`ros::Duration::sleep()` 在 use_sim_time 下等 /clock 推进；
  lockstep SITL 时钟停摆（IMU 频率网格锁工作中已证时钟供给可抖）→ sleep 永不返回→
  单线程 spinner（ego_planner_node.cpp:19 `ros::spin()`）整个进程冻结=FSM/安全 timer/odom 全停。
- H-s2（次嫌）：spinOnce 重入——waypointCallback 在循环内 spinOnce 可再入自身（新 goal 排队）
  →嵌套循环栈膨胀/死锁窗。
- H-s3（弱）：EXEC 态机活锁——GEN_NEW_TRAJ↔REPLAN_TRAJ 自旋（planFromGlobalTraj 失败循环），
  但有 emergency 逃生门，与"完全冻结"签名不符。

## 修复评估：**维持重启绕行+登记（高风险分支）**
- 低侵入修复案（文本化备审，未落码）：
  两循环 sleep 改 `ros::WallDuration(0.001).sleep()`（墙钟）+ 循环上界（如 3000 次=3s 墙钟超时
  →break+ROS_ERROR 留痕）；waypointCallback 加 `static std::atomic<bool> in_cb_` 重入门。
- 不落码理由（客观）：①注入验证=需受控 /clock 停摆注入 harness（不存在，需造）+修复前后
  对照批——跨夜工作量级；②planner C++ 重建动栈姿态（X4 后 721cad40/5bacc2e9 谱系仅 VINS 面，
  planner 段另有 lineage；批后重建=引入新变量无绿率对冲）；③重启绕行已实战恢复 2/2，风险
  已有缓解在位。落码窗=INPUTFACE-SCREEN 修复链同窗（跨夜里程碑 M2）合并执行+注入验证。
