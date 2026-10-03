# P1 rebirth 出生位差检查 — 设计预注册（T1 v11.0 单元 2；2026-10-04）

> 用户已批写码（10-03 裁定 P1+P2 同窗）。本预注册先于 A/B 飞轮（判据未预注册不出 PASS/FAIL）。

## 1. 命题与机理依据

**命题**：px4ctrl 消费侧增加 rebirth 出生位差检查——odom 供给断流（gap）后复流首帧位置与断流前末帧位置差超阈值时锁存 birth_mismatch，阻止 AUTO_HOVER 进入（含 U2.7 LAND 接管路径），disarm 解锁。

**机理依据**：
- U9 取证：VINS 重启（rebirth）后 odom 新出生点与旧坐标系恒偏 (+1.01,+0.99,+0.10)=|1.42|m；
- P1-1b 预算表：出生偏移族 1.42-1.46m 跨三栈代稳定（cf0384→285278cc→d43504d9）=结构性出生对齐缺口；
- armed 状态下 rebirth=px4ctrl 在错位坐标系继续控制（G-1 域：armed 卡 True 与 rebirth 叠加为最危险组合）；
- 健康对照：健康悬停帧间 |dp|=cm 级；gap 窗内真实漂移=v×gap（0.1m/s×2s=0.2m 上界）——与 1.42 族分离 ~20×。

## 2. 参数预注册（初值）

| 参数 | 值 | 依据 |
|---|---|---|
| p1_rebirth/enabled | SITL true / 实机默认 false（yaml 无键） | 沿 D2 门模式 |
| p1_rebirth/gap_sec | **2.0** | 223Hz 流正常 gap p999≪1s（τ_pipe supply gap p50 4ms）；VINS 重启窗≫10s；2.0 居无误伤带 |
| p1_rebirth/birth_thresh | **0.75** | 1.42-1.46 族 vs 健康面 cm 级：分离 ~20×，0.75≈几何中点；**上修容许至 1.0 不失分离度；禁下修<0.5**（0.5=D2 jump 门与 U3PO odom 跳口径域，下修会造成两层门语义重叠） |

**阈值调整纪律**：标定复核后如需改值=DECISION_LOG 登记（判据门值放宽永远禁——本门只允许更严或等价平移）。

## 3. 判据（A/B 预注册）

| 轮 | 配置 | 判据 |
|---|---|---|
| A 轮（对照） | enabled=false | 杀 vins_node→重启复流（错位 1.42 族）→hover-entry 不受阻（旧行为保持=回归面） |
| B 轮（实验） | enabled=true | 同注入场景→①"[px4ctrl] P1: odom REBIRTH birth-offset"ROS_ERROR 在案②fsm_state 串行可见 hover-entry 拒绝（RJ_BIRTH_MISMATCH）③disarm 后锁存清零（再入不受阻）|
| 健康回归 | enabled=true 正常悬停 | **零 P1 日志+零 hover-entry 拒绝（误伤=0）** |

A/B 同栈同剖面（悬停 smoke），B 轮三判据全中=PASS；任一不中=FAIL 如实。

## 4. 与 D2 三层门挂接序（对账）

D2（帧级，odom feed 内拒毒帧）→ P1（rebirth 级，gap 复流锁存+FSM 入口门）。两层正交；**语义注记（保守面，故意）**：D2 持续拒帧>gap_sec 造成的"拒帧型 gap"同样触发 P1 检查——毒帧风暴后大幅位移复流与 rebirth 同危险类，锁存是正确行为；D2 误伤恢复路径（20 帧平稳）不产生 2s 级 gap，不受影响。

## 5. 实现状态（2026-10-04 02:5x）

- 码：input.h（p1_cfg+birth_mismatch）/input.cpp（feed ACCEPT 路径 gap 检测）/PX4CtrlParam（三键）/px4ctrl_node（注入）/PX4CtrlFSM（fd_in 装填+STEP0 与 AUTO_LAND disarm 双解锁+两入口 RJ_BIRTH_MISMATCH 映射）/fsm_decision.h（Inputs.birth_mismatch+RJ_BIRTH_MISMATCH+decide_manual 两入口检查）/ctrl_param_sitl.yaml（三键）
- gtest：FsmP1BirthMismatch×5（37/37 全绿）
- A/B 飞轮：挂 T2 验证轮后窗（F3B 重跑同窗顺带）

## 6. 标定复核计划（增强证据，非阻塞）

E-4 R1-R8 八轮 flight.bag 静置段帧间 |dp| 分位（p99/p999）+P1-1b 三袋 gap 事件位差——若健康面 p999>0.25m 或 rebirth 面 p1<1.0m（分离度<4×）→阈值复裁入 DECISION_LOG。
