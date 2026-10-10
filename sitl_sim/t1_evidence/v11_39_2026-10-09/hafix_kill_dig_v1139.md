# HAFIX 复验 FAIL 分支回挖报告（T1 v11.39 单元 1 复验分支；2026-10-10 16:3x）

> 触发：复验批 S1 r1（run_DRILLD1_N8P_160603）六环链实测=梯②③零效（136+ HAFIX 行全触发时序正确，KILL 双命令 412+413 次全 ACK ACCEPTED，但电机恒转、armed 恒 True、全轮悬停 z≈1.08m）。
> 证据正源：`run_DRILLD1_N8P_160603/{px4ctrl.log,flight.bag,round.log,sitl.log}` + PX4 ulog `build/px4_sitl_default/rootfs/log/2026-10-10/08_06_19.ulg`（pyulog 解析）+ PX4 源码树 d6f12ad1c4（commander 零改动核验）。

## 1. 三层机理定案

### 1.1 梯②400（MAV_CMD_DO_FLIGHTTERMINATION param1=1.0）——被 failsafe 覆写

- ulog：413×400 全 ACK result=0；**nav_state 终 13（TERMINATION）从未进入**（时线 14=OFFBOARD→4=AUTO_LOITER @注入点后恒定）；
- 源码机理：`Commander.cpp:2383`——`nav_state = modeFromAction(failsafe.selectedAction(), user_intention)` **每 commander 周期以 failsafe 动作覆写用户意图**。VINS 死→px4ctrl 状态弹 MANUAL→setpoint 停流→OFFBOARD 超时 failsafe（LOITER）激活→`_user_mode_intention.change(TERMINATION)` 虽返回 true（ACK ACCEPTED），但应用层每拍被 failsafe 模式盖回 AUTO_LOITER；
- **setpoint 流断 = failsafe 恒活 = 400 结构性无效**。

### 1.2 梯②179（MAV_CMD_COMPONENT_ARM_DISARM param1=0+param2=21196 forced）——ACK 无操作

- ulog：412×179(21196) 全 ACK result=0，ACK-命令延迟 8ms（真异步处理签名）；
- 物理面：actuator_outputs motor0 恒 1714-1728（5299 样本 0 次低于 0.05）；vehicle_status（2.78Hz×490s）arming_state 恒 ARMED 零翻转；事件面 23 条零 disarm 事件；console 零「Disarmed by」行——**disarm() 函数体从未生效**；
- 源码面：`Commander::disarm(forced=true)` 逐行正确（force 跳过 landed 检查直设 DISARMED）——ACK 与执行体的断链机制源级未闭（唯一 handler=commander 的 ACK 链无懈可击，但函数体零痕）。**结论按物理证据定案：该 PX4 构建（d6f12ad1c4, master-era）空中 forced-disarm 不可依赖**；
- 实机注记：旧机 FMU v6C/v1.17.0 的 179+21196 路径未测（无飞行动力），实机首飞前须台架动力套窗专项验证（动力套=用户裁定跳过项，呈报件§④已列）。

### 1.3 梯①盲降——被 decide_land 自己否决（px4ctrl 域根因，本轮可修）

- HAFIX 在 dead_s 后切 state=AUTO_LAND ✓（日志「-> AUTO_LAND」）——但 **decide_land 的首门 `!odom_ok→MANUAL_CTRL` 在下一拍把状态弹回 MANUAL**（`PX4CtrlFSM.cpp` AUTO_LAND case + `fsm_decision.h` decide_land）——「冻结 odom 盲降」从未真正下降；
- SITL 兜底真相：iris_stereo_vins 模型带 GPS 插件（sitl.log gazebo_gps_plugin 实录）→ VINS 死后 PX4 EKF2（GPS 融合）位置估计存活 → failsafe LOITER 稳定悬停——**SITL 域 VINS 死≠PX4 盲**（实机纯视觉域无此兜底，EKF2 EV 融合未启用在案）。

## 2. 二次修复（梯①盲降结构修复——px4ctrl 域内可闭环）

修复面四件（commit 待批后部署；批在跑期间禁 rebuild=轮中换二进制污染批）：

1. **decide_land odom 门旁路**：`Inputs.ha_blind_land`（ha_stage≥2 置位）——盲降中 `!odom_ok` 不弹回（rc_hover 门保留）；gtest 4 用例（旁路生效/非盲降原语义/真落地 disarm/rc_hover 门不旁路）；
2. **双锚**：HAFIX 切 AUTO_LAND 时 `set_start_pose_for_takeoff_land(odom_data)`（最后已知位）+ `toggle_takeoff_land_time=now`（时基锚）——get_takeoff_land_des=开环时基下降，陈旧 odom 无碍；
3. **OFFBOARD 重入**：`toggle_offboard_mode(true)`——流死期弹 MANUAL 时已切出；不重入=setpoint 断流=failsafe 恒活=400 永久无效。setpoint 流恢复后 failsafe 清除→**400 的 termination 意图可正常应用**（源码链推演，待干测实证）；
4. **idle 门**：`rotor_low_speed_during_land = px4_on_ground || odom_ok`——盲降期 frozen odom 伪满足 land_detector C1+C2（高位误 idle=坠落）防护；真落地判定=mavros extended_state（独立于 VINS 流）。

预期链：watch→AUTO_LAND（真降）→px4_on_ground→disarm（P-2 梯③+AUTO_LAND 正常路径双保险）；KILL 双命令保留为带弹（failsafe 清除后 400 生效链推演+179 实机待验）。

## 3. 复验批的诚实预期（20 轮跑完后的判读口径）

- 预注册判据（HAFIX≥1 ∧ landed=1）大概率大量 PASS——但**六环链的 ring4/6 来源=harness 收尾降落**（非 HAFIX kill 效果），判读器 path 列会区分（KILL 路径 vs LAND 路径）；
- 本报告=FAIL 分支核心交付：机理三层+二次修复窗+10 轮增量复验（修复部署后）。

## 4. 修复部署序（批毕后依序）

批毕 → catkin build（新二进制）→ gtest（41 用例）→ 干测单轮（S1 hover，验环4-6：armed drop@KILL 后、z 下降曲线、disarm OK 行）→ 10 轮增量批（S1/S2/S3 混合）→ 终判表 v2。
