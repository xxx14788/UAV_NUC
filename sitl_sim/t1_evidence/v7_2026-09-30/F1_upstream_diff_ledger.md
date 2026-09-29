# T1-F1 px4ctrl 全量变更账：本仓 12 提交 + 导入源私改面（2026-09-30 夜）

状态：F1 主体完成（(a) 导入源私改 5 文件细 diff + (b) 本仓 11 提交逐条账）；
README §3 登记核对与补差未做（挂 I 收口）。执行者：T1 v7 夜 1。0 锁。

## (a) 导入源私改面（1a069ca vs 上游 master，blob-SHA 法 + 细 diff）

上游=ZJU-FAST-Lab/Fast-Drone-250@master（2022-11 冻结）。9 个 src 文件中 **4 个逐字节相同**
（PX4CtrlParam.cpp/.h、input.cpp/.h），**5 个私改**：

| 文件 | 私改内容 | 行为意义 |
|---|---|---|
| px4ctrl_node.cpp | +PositionTarget advertise（/mavros/setpoint_raw/local）+ `nh.param use_px4_position_ctrl 默认 true` | PX4 位置环模式入口 |
| PX4CtrlFSM.h | +ctrl_FCU_pos_pub 成员、+use_px4_position_ctrl{true}、publish_attitude_ctrl 签名+des、+publish_position_ctrl | 同上 |
| PX4CtrlFSM.cpp | ①:303 迁移条件私改：`(AUTO_HOVER‖CMD_CTRL)` → `+armed && !rotor_low_speed_during_land`（**上游无条件迁 MANUAL，私改版未 arm/降落低速期保持原态**）②+need_direct_thrust（起飞 spin-up/降落怠速窗用 AttitudeTarget 直推力）③use_px4_position_ctrl 分支（巡航发 PositionTarget） | **状态机行为差异**（未在上游文档/issue 出现）+架构分支 |
| controller.cpp | +`throttle_percentage = clamp[0,1]` 一行 | 油门限幅（稳健性补丁） |
| controller.h | 注释行差异 | 无行为差 |

**判定：导入源是一套完整"PX4 位置环"功能移植+FSM 迁移条件改动，作者不可考（GitHub 全域孤例，
见 F2 冲突①裁决 t1_evidence/v7_2026-09-30/F2_conflict1_branch_verdict.md）。**
FSM.cpp:303 的迁移条件改动是 F2 之外的新发现（影响：未 arm 时的状态保持语义与上游不同）。

## (b) 本仓 11 提交逐条账（1a069ca 之后）

| # | commit | 改动 | 动机（提交信息） | 验证状态 |
|---|---|---|---|---|
| 1 | a01ef22 | +ctrl_param_sitl.yaml +run_ctrl_sitl.launch（85 行） | SITL 配置与实机分离（EKF2 odom） | 当期 V 线轮验证 |
| 2 | ba05ca8 | +run_ctrl_sitl_vins.launch（17 行） | sim-VINS 基础设施（A7），odom=imu_propagate 直供同构实机 | V1.x 线验证 |
| 3 | c2210b8 | FSM.cpp/h+input+node 69 行 + t1_patch_px4ctrl.py 220 行 | sim-clock 回退冻结主环——FCU/SITL 重启韧性 | W 线轮验证 |
| 4 | 0de090e | controller.cpp 48 行+param | 姿态构造修复+RLS 防护（T3-W2） | T3 W 线+gtest |
| 5 | e460d1c | sitl yaml 2 行 | yaml 层级/takeoff v3/smoke fresh-master 批修复 | 夜批轮验证 |
| 6 | f76278e | +attitude_utils.h（67）+controller 重构+**gtest 8 用例** | 姿态抽取纯函数化+NaN 防护（T3-W9） | gtest 8/8 |
| 7 | 05edb7b | input.cpp +7 | EKF2 修复线收口配套（T3-E） | E 线轮验证 |
| 8 | 3c4d430 | run_ctrl_sitl_vins.launch +6 注释行 | R6 表回填+同构注解 | 文档性 |
| 9 | 632e0ee | run_ctrl_sitl_vins.launch 2 行 | 511-105 5000→4000us（125→223Hz 网格量化修复） | V4.2 探针+袋双源 |
| 10 | 1daf973 | CMake+yaml+Param+input 61 行（+odom_sanity.h） | **D2 odom 三层门**（vel5/jump0.6/acc10） | gtest 9 用例+实战拒毒 200+ 帧 |
| 11 | 9d78cf0 | sitl yaml 1 行 | D2 max_jump 1.0→0.6（D4 阈值反馈） | D4 门禁轮 |

## (c) 与 README §3 的登记核对

挂 I 收口（本夜未做逐条对照；已知 D1/D2/V6/V7 已在 f413439 登记，3c4d430 有 R6 注解——
缺口面小，主要补：c2210b8 韧性修复与 0de090e 姿态修复的 §3 条目核对）。

## (d) 上游后续演进对照

上游 master 2022-11-09 冻结（最后 commit "remove v5 carbon board"），无 px4ctrl 后续演进——
无对照项。fork 生态（aphasiayc/px4ctrl 等）快照级差异不在本账范围。

## 产物

- 本文件：t1_evidence/v7_2026-09-30/F1_upstream_diff_ledger.md
- 上游参照文件包：/tmp/up_px4ctrl/（NUC，5 文件）
