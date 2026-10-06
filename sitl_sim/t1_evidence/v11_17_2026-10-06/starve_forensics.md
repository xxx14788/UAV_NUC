# planner starve 取证文书（任务书 v11.17 §1.1 取证先行；T1 2026-10-06 17:4x 落册）

## 0. 任务与材料
- 判别三支（任务书原文）：①goal 回调未触发（传输/订阅丢失）②回调进了但 FSM 停等
  （odom/TF/前置条件拒收=另一族病因）③订阅从未建立（话题面错配）。
- 标本：run_X2g3_042025 与 run_X2g1R_045147（X4 批 2/8 starve 轮）。日志在案（planner.log/
  round.log/px4ctrl.log/takeoff.log 全在轮目录）。

## 1. 硬事实（两轮逐项一致，仅 traj_server ROS 时间戳不同）
1. 两轮 planner.log **均恰 189 字节**，内容同型：
   grid_map 参数五行(hit/miss/min log/max/thresh log=构造期 initPlanModules 打印)
   → "[FSM]: from INIT to WAIT_TARGET"（首个 exec 回调已运行，且 have_odom_=true——
   INIT→WAIT_TARGET 转换的前置=odom 已到，VINS 里程计链路通）
   → "[Traj server]: ready."（traj_server 独立节点就绪，ROS 时刻≈21.1-21.3s）
   → **再无任何输出**。
2. 关键负事实："[FSM]: state:" 1s 心跳**零出现**。源码（ego_replan_fsm.cpp execFSMCallback）
   心跳=fsm_num==100 时无条件 printFSMExecState()——与 goal/target/odom 全部无关；
   即事件循环只要活着，每秒必有一行。
3. round.log 时间线：起飞正常(truth z 0.86/0.81)→goal 2×8s+两轮重发→poscmd 三查全 0Hz
   →WARN PLANNER-STARVED→TIMEOUT（机体悬停未动，min_truth=全程距 goal 7.657/8.331m）
   →降落正常。px4ctrl 侧全程健康（非控制面问题）。
4. roslaunch 无 "process has died" 行——FSM 进程存活未被监控判死。

## 2. 三支判别
- **支①（goal 回调未触发/传输丢失）：排除**。心跳打印在 goal 处理之前且与其无关；
  心跳缺失说明 FSM 事件循环本身未运行，而非"活着但收不到 goal"。若仅传输丢失，
  心跳应持续出现且停在 WAIT_TARGET——与观测相反。
- **支②（回调进了但 FSM 停等前置条件）：排除**。WAIT_TARGET 无 target 路径=goto
  force_return（trivial，无阻塞等待）；心跳打印位于 switch 之前，停等也会打心跳；
  且 have_odom_ 已 true（INIT→WAIT_TARGET 已证），"no odom."字样零出现。
- **支③（订阅从未建立/话题错配）：排除**。订阅在构造函数内注册，构造已完成
  （其全部打印在案）；launch 文件与同批健康轮逐字同源，错配应为静态必现而非 2/8 间歇。
- **实际病灶=第四面（任务书三支之外，如实落册）：FSM exec-timer 事件循环在
  第 1 次回调之后、第 100 次（≈1s 心跳）之前死亡**。timer 每回调入口 stop/出口 start
  自挂（ego_planner 上游设计），任一环节失灵或单线程 spinner 被其它回调永久阻塞
  （odometry/checkCollision/depth 首帧重活候选）即成本签名。进程存活（无 died 行）
  但循环死=「活着但冻结」，与 189B 日志完全吻合。

## 3. 修复靶点（取证结论→靶点，任务书要求）
靶点=**事件循环存活性**（非 goal 传输面）：
- a) 订阅就绪门强化为「订阅者在场 ∧ FSM 心跳首行在册」——心跳=循环存活直接证据；
- b) 首发 8s 无 target 变更（FSM 未离 WAIT_TARGET ∧ poscmd≤1Hz）→ planner 整栈
  重启一次（对"活着但冻结"唯一有效处置=重启；重发 goal 对冻结进程无效，
  与批内"goal 重发无效"观测一致）。
- d) 留痕：goal 发布 vs FSM 状态变化对表（bag 侧 /move_base_simple/goal 戳 vs
  /position_cmd 首帧戳+planner.log 心跳在场性）逐轮落盘——starve 若再现即得现场。

## 4. 注入式复现映射（DoD 证据链）
- 注入=SIGSTOP FSM（构造期/首回调后两型）+ 早发 goal burst（spawn 前，消息必丢=竞态面）。
- SIGSTOP=「进程存活+事件循环死+订阅在册」的忠实受控复刻：roslaunch 不判死、
  心跳停、goal 重发无效——与 189B 签名同型。
- A 轮（旧序列）：STARVEOLD1_172733（ctor 型，planner.log 0 FSM 行，WARN 三查 0Hz 复现✓）
  + STARVEOLD3（postinit 型=真实签名精确复刻，进行中）。
- 失真注记：注入 A1 首次尝试曾暴露旧门另一盲区——FSM 在存活窗内处理了泄漏 goal 后
  才被 STOP 时，残余轨迹回放使 poscmd 100Hz、旧门第 1 查假通过（mid-EXEC 死亡面，
  与 starve(首发未离 WAIT_TARGET)不同族，修复 b 的 target_moved 双条件已覆盖此面）。
