# F3 FSM 全接线 — git diff 逐行审计表（T1 v11.0 单元 1 验收件之三；2026-10-04）

> 对象=commit 6ef1acb（PX4CtrlFSM.cpp 109+/67-；fsm_decision.h 生产版 src/ 迁移）。方法=逐块旧条件→新判定映射+副作用序列逐行核对+日志保真核对（RejectReason 原因码→原文案 1:1）。

## 0. 总则

- **转移判定权威移交**：六块的条件判定全部改为 `fsm_decision::decide_*`（纯函数，gtest 37/37 含 25 既有回归+7 U2.7+5 P1）；**副作用（日志/服务/成员写）留在 FSM.cpp 按原因码逐分支映射**。
- Inputs 装填=process() 每拍一次（STEP0 前），字段与源查询 1:1（odom_is_received/cmd_is_received/rc_*/triggered&&cmd/armed/odom_v/get_landed/px4_on_ground/stale/dt_takeoff/no_rc/birth_mismatch）。
- fd_state_of=显式枚举映射（无 reinterpret 差位假设）。

## 1. 逐块审计

| 块 | 旧判定（源码行） | 新判定 | 副作用序列核对 | 日志保真 |
|---|---|---|---|---|
| STEP0 | `!armed && rcv_stamp!=0 && state!=MANUAL && stale>3` | `rcv_stamp!=0 && step0_global(...).next==MANUAL`（rcv_stamp!=0 首帧保护留调用点，审计#S0） | 重置序列逐行原样（triggered 清/cmd 过期/birth_mismatch 清[新增 P1]/reset/set_hov/不调 offboard） | WARN 原文原样 |
| MANUAL hover-entry | 三连 if 拒（:73-84） | `decide_manual` reject+原因码 | 成功序列原样（state/reset/set_hov/toggle_on） | 三条 ROS_ERROR 原文案 1:1（RJ_NO_ODOM/RJ_CMD_ACTIVE/RJ_VEL）+P1 新增一条 |
| MANUAL takeoff | 四连拒+RC 阻塞等待+接受序列（:96-158） | reject+原因码分派 | RC_GUARD 的**阻塞 while 等待循环逐行保留**；接受序列（offboard 失败回退 F1/10×spinOnce/auto_arm/toggle_time）逐行原样 | 五条文案 1:1 |
| MANUAL land（U2.7 新增） | 无（静默丢弃） | decide_manual LAND 分支（新） | 新行为=接受序列（hover 同构）/disarm 忽略/RC 优先拒 | 新文案三条（登记为预期新增） |
| AUTO_HOVER | 四分支链（:174-216） | `decide_hover` next 分派 | 四路副作用原样（MANUAL 回退 offboard_off/CMD 进入 get_cmd_des/LAND 进入 set_start/else set_hov_with_rc+delay_trigger/publish_trigger） | 四条文案 1:1 |
| CMD_CTRL | 三分支+LAND 拒（:218-247） | `decide_cmd` | 三路原样；LAND 拒的 ROS_ERROR 多行原文逐字保留（含续行缩进） | 1:1 |
| AUTO_TAKEOFF | 看门狗+speedup/reached/climb（:249-282） | `decide_takeoff`（参数实传 MOTORS_SPEEDUP_TIME/ABORT_TIMEOUT/height/start_z/cur_z） | 看门狗副作用原样（offboard_off+ERROR）；reached 的 delay_trigger 副作用原样；**speedup/climbing 的 des 选择保留原条件**（副作用选择非转移判定，登记#T1） | 三条文案 1:1 |
| AUTO_LAND | 四分支（:284-336） | `decide_land` | MANUAL/HOVER 回退原样；descending 的 des 原样；**disarm 序列逐行原样**（print_once/1s 重试/armed 服务/disarm 成功三连+[P1 新增 birth 清零]） | 四条文案 1:1 |

## 2. 行为差异清单（全部预期内）

1. **U2.7 新行为**（用户已批+预注册）：MANUAL_CTRL+armed+no_RC+odom_ok+v≤3 的 LAND→AUTO_HOVER（两拍降落路径）；RC 在场保持手动优先（显式拒）；disarmed 忽略。旧行为=静默丢弃（U3PO 取证在册）。
2. **P1 新行为**（预注册 p1_rebirth_prereg）：birth_mismatch 锁存时 hover-entry 与 U2.7-LAND 拒绝（RJ_BIRTH_MISMATCH）；disarm/STEP0 双解锁。
3. **decide_hover 镜像修正**（对齐源码非改变源码行为）：v1 镜像在 rc_cmd&&cmd_ok&&!offboard_confirmed 时错误 fall-through 到 LAND；v2 严格镜像源 else-if 链（该拍不评估 LAND）——**修正的是镜像层，源码行为不变**（边界测试 CmdWaitOffboardBlocksLandSameTick 在册）。
4. #S0/#T1 两处调用点保留注释登记（首帧保护/speedup-climb 副作用选择）。

## 3. 验收状态

- ①53 gtest 基线：**60/60 全绿**（超额：fsm 32[P1 后 37]+sanity 9+v2 11+attitude 8）
- ②悬停 smoke A/B：A=R8（J1 0.041 在袋）；B=F3B 首飞 FATAL（环境性：PX4 ninja 与 T2 build 窗资源交叠，非码面——02:44 STATUS 在册）→**重跑挂 T2 验证轮后窗**（B 轮栈=fixface-3，A/B 跨栈注记在册）
- ③本审计表 ✓
