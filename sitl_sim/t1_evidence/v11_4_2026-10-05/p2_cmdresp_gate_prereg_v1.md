# P2 指令-响应发散门 — 在线判据预注册 v1（T1 v11.4 单元 3；2026-10-05）

> 门值冻结源=u3_hover_drift_verdict.md（VR3 悬停 8.5m 事件带）：**eps_static 0.5 m / drift_rate 0.21 m/s / win 10 s**。
> 本预注册=在线判定面（gtest 已固化判据语义；A/B 窗协议沿 P1 模式）。未预注册不出 PASS/FAIL。

## 1. 语义（冻结，与 cmdresp_gate.h 头注释一致）

- `e(t)=‖p_odom−p_des‖`、`dv(t)=‖v_odom−v_des‖`；样本仅 armed 非 MANUAL 拍喂入。
- FIRE（AND，连续 10 拍确认）：`e_now−min(e∈win) ≥ 4×0.5=2.0 m` ∧ `median(dv∈win) ≥ 0.21 m/s`。
- RECOVER：连续 100 拍（1 s）任一条件不满足；disarm 即清 latch（P1 的 latch 无清除缺口不复制）。
- 默认 OFF=逐字节旧行为（实机 yaml 无键）；仅 SITL yaml 显式开。
- 动作面（保守红线）：RJ_CMDRESP 阻断 decide_manual 的 enter_hover/takeoff 分支 + 1 Hz 限频 banner；**不新增 armed 态降级动作**（上游真值门/auto_disarm 已在册）。

## 2. gtest 固化面（test_cmdresp_gate.cpp，13 case）

DisabledPassthrough / WindowNotFullNoEval / HealthyHoverNoFire / **VR3DriftFires**（事件形态正例）/ StaticOvershootNoFire（静态超阈防误伤）/ VelocitySpikesNoFire（尖刺防误伤）/ RecoveryAfterDrift / DisarmClearResets / PoisonBeatSkipped / RJ 三接线 case。全绿=写码 DoD；编译+跑测挂 T2 收口后 build 窗（devel 换代会污染对照轮，禁窗内编译）。

## 3. A/B 飞轮判据（净窗=T2 机器对照轮出净轮即排窗）

- **A 臂**（P2 on，p2_cmdresp/enabled=true）：净轮全程 **零 latch 零 banner**（健康轮无 e 发散增量+dv 中位低于阈）；若出现 latch → 记为误报（miss 判据 FAIL-A）。
- **B 臂**（P2 off）：行为逐字节=现行栈（回归面，轮 log 无 P2 banner 字样）。
- **事件面对照**（非门控）：任何敌对轮（机器对照 12 轮若现发作）离线对账 px4ctrl.log 的 P2 banner vs truth/odom 分歧时间线——**发现面不进门**：P2 banner 与真值发散窗重合=正捕获（登记）；不重合=伪触发（登记）。此面仅记录不裁决。
- 门值参数零改动纪律：A/B 两臂只动 `p2_cmdresp/enabled` 一个键。

## 4. DoD

写码（本文件+cmdresp_gate.h+三线挂接+gtest 13 case+语法预检净）→ [挂起] T2 收口 build 窗：catkin build px4ctrl + gtest 全绿（含既有 88 用例零回归）→ 净窗 A/B 两轮 → 判读文落本目录（p2_cmdresp_verdict.md）。任一步失败如实登记不放宽。
