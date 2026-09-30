# T1-F3 FSM 迁移表审计 + gtest 套件（2026-09-30 夜 4）

状态：五态×全事件迁移表审计完成；gtest 套件以"镜像式纯决策函数"落地（fsm_decision.h 逐行对齐
PX4CtrlFSM.cpp，测试穷举状态×输入）；**行为等价重构（FSM.cpp 真实调用抽取函数）留夜 5**——
T2 在飞期间不动 FSM 主文件（build 互斥+风险控制），今夜镜像式=文档性验证，诚实登记。

## 1. 迁移全表（源码逐条，PX4CtrlFSM.cpp@HEAD）

### MANUAL_CTRL (L1)
| 触发 | 前置门（全过才迁移） | 目标 | 备注 |
|---|---|---|---|
| enter_hover_mode | odom 收到+cmd 未收+‖v‖≤3.0 | AUTO_HOVER | v 门 3.0=定位异常防线 |
| TAKEOFF trigger | odom+无 cmd+‖v‖≤0.1+get_landed()+（RC 在线时：hover&cmd 开关+摇杆居中）| AUTO_TAKEOFF | **阻塞等待 RC 归位**（while 循环）|
| toggle_reboot | !armed | （FCU reboot）| armed 拒绝 ✓ |
| （无）| — | MANUAL | 静默 |

### AUTO_HOVER (L2)
| 触发 | 目标 | 备注 |
|---|---|---|
| !rc_hover **或** odom 超时 | MANUAL_CTRL | toggle offboard |
| rc_cmd && cmd 收到 && mode==OFFBOARD | CMD_CTRL | 有 OFFBOARD 确认门 |
| LAND trigger | AUTO_LAND | set_start_pose |
| else | （hover 保持）| enter_command_mode→publish_trigger |

### CMD_CTRL (L3)
| 触发 | 目标 |
|---|---|
| !rc_hover 或 odom 超时 | MANUAL_CTRL |
| !rc_cmd 或 cmd 超时 | AUTO_HOVER（set_hov_with_odom）|
| LAND trigger in CMD | **拒绝**（须先回 AUTO_HOVER）✓ 设计正确 |
| else | （cmd 跟随）|

### AUTO_TAKEOFF
| 触发 | 目标 | 备注 |
|---|---|---|
| 看门狗（speedup+abort 超时 && !armed && Δz<0.3）[T1-W1 F2] | MANUAL_CTRL | 重试出口 ✓ |
| t<MOTORS_SPEEDUP_TIME | （rotor speedup des）| — |
| Δz≥height | AUTO_HOVER | delay_trigger 武装 |
| else | （爬升 des）| — |

### AUTO_LAND
| 触发 | 目标 |
|---|---|
| !rc_hover 或 odom 超时 | MANUAL_CTRL |
| !rc_cmd | AUTO_HOVER（中止降落）|
| !get_landed() | （下降 des）|
| landed && PX4 ON_GROUND && 1s 节流 disarm 成功 | MANUAL_CTRL（offboard off）|

### 全局（STEP0，所有态）
| 触发 | 目标 |
|---|---|
| !armed && state 流断>3s && 非 MANUAL [T1-W1 F3] | MANUAL_CTRL（自愈；不调 offboard-off，链路已断）|

## 2. 审计发现项

| # | 发现 | 评级 | 处置 |
|---|---|---|---|
| 1 | MANUAL_CTRL→AUTO_TAKEOFF 的 RC 居中检查是**阻塞 while 循环**（process() 内 sleep+spinOnce 直到归位）——FCU 重启时 state 流断，此循环可能长阻 | 中 | T1-W1 F1/F2/F3 已加三道出口（offboard 拒绝回退/看门狗/STEP0 自愈）；**armed 态无影响**；登记为已知形态，非新缺陷 |
| 2 | AUTO_HOVER→CMD_CTRL 要求 `mode==OFFBOARD`，但 toggle_offboard_mode(true) 在进入 AUTO_HOVER 时已发——若 FCU 慢确认，cmd 模式切换会被拒直到下次循环（自愈）| 低 | 行为=短暂滞后非卡死；不改 |
| 3 | CMD_CTRL 中 LAND trigger 只打 ERROR 不消费 `takeoff_land_data.triggered`——回 AUTO_HOVER 后**残留 trigger 立即触发 AUTO_LAND** | 低（语义可辩）| 行为="cmd 期间按了降落，回 hover 后自动降落"——保守安全方向；登记不改 |
| 4 | AUTO_LAND 的 `!get_landed()` 分支无 armed 检查直接发下降指令——与 STEP0 自愈交互：disarmed+流断时 STEP0 先接管（3s）| 低 | 顺序正确 |
| 5 | 迁移到 MANUAL_CTRL 的三处（AUTO_HOVER/CMD_CTRL/AUTO_LAND）都调 toggle_offboard_mode(false)，STEP0 自愈**不调**（注释：链路断服务必败）| ✓ 一致性正确 | — |
| 6 | **静止门与 D1 尖峰/D2 门交互**：MANUAL→AUTO_HOVER 的 ‖v‖≤3.0 门吃的是 odom_data.v（可能为毒值帧）——D2 三层门（vel5/jump0.6/acc10）在 odom feed 层已拦截毒帧（实测拒 200+），故此处 v 已是净化后值 | ✓ 防线分层正确 | — |
| 7 | rotor_low_speed_during_land 只在 AUTO_LAND 触地后置位——STEP2 RLS 估计在降落末段停更 ✓（防触地震动污染推力模型）| ✓ | — |
| 8 | **导入源 FSM.cpp:303 私改**（F1 发现）：STEP2 RLS 条件+armed&&!rotor_low_speed——上游无条件估计。含义：SITL/实机均不在未 armed 态学推力模型 ✓ 合理私改 | 评级：合理 | 保持 |

**结论**：迁移表无危险缺口；T1-W1 三道自愈件覆盖了上游三大死角（offboard 拒绝/起飞卡死/链路断）；
发现项 3 是唯一语义残留（安全方向，登记不改）。

## 3. gtest 套件（test_fsm_decision.cpp，镜像式）

- fsm_decision.h：五态决策纯函数（逐行对齐源码，含 T1-W1 三道件的前置条件）
- 用例 ≥20（每态×主要迁移+拒绝分支+STEP0 自愈），套件总计 17+20=37 ≥ 25 ✓
- 构建挂 catkin_make 窗（T2 回放结束后与 E2 合并同批 build）
- **登记**：镜像式=文档性验证；真实调用重构夜 5
