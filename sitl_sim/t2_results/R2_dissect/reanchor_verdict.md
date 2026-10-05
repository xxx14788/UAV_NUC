# reanchor_verdict.md — odometry 重锚/帧跳恒量族修复定案（T2 v9.5 §1；2026-10-05 12:05-15:30；prereg_reanchor_fix 冻结+附录 A/B 迭代史）

> 战役=四代栈迭代（v1 ed4b8181→v2 c127f389→v3/v4 b7de133d+lib 686499ca→59548c6a）×验证轮 RA1-RA24（24 轮，3090，零 harness 崩溃）。commit 链 e98886f（v1）+949bea4（v2-v4）。

## 1. 机理定案（修复对象）

帧跳两子族：①**重锚/恢复跳**（2.45-2.60m 恒量族+294m 怪物）=reboot 黑out 后重 init 恢复发布时刻的帧步（MACH1 袋级取证：[T2fail]@|V|=50.3/50.4 insane 门触发→1.3s 黑out→恢复单帧 293.7m）；②**走爬拖拽**=风暴 |V|<15 段的解游走被 125Hz 流以 ≤0.12m/帧持续投喂（MACH1 25s 累计 ~50m）。既有基建盘点：T1-D1 平滑器+ULS 捕获建成但 REANCHOR_SMOOTH=0 从未启用；发布有界性门 1e3/50 过松。

## 2. 修复终态（v4=t2_stream_guard 四组件）

config 键默认 0=逐位 legacy（实机 canonical 零改动）；cfg_streamguard=1（gates+cauchy 承继+50/15）：**A** 发布 sane 门（raw+发布值双检）**B** 恢复连续性（缺口>0.15s→delta 补偿经 D1 平滑器，双采样率自适应帧数 25×dP=5m/s 释放）**C** D1 ULS 捕获启用+沉降窗（重 init 后 2s）停用+平滑器复位 **D** odom 话题发连续链快照（与 125Hz 同时间线）。[T2SGCFG]/[T2RESUME]/[E2settle] 新本线行；冻结四行零改动。gtest 10/10（含 test_t2_stream_guard 7 例）。

## 3. 验证判据执行（prereg §4 逐字）

| 判据 | 结果 | 证据 |
|---|---|---|
| 主判 1 风暴轮双流单帧 ≤0.5m | **FAIL（字面）** | 重锚族跳本身消灭（恢复 ramp 设计内 ≤0.4m/125Hz 帧+≤0.5m/10Hz 采样）；残余=走爬带 prop 0.5-0.8m 帧（RA9 18/RA20 11/RA22 27 帧）+odom 走爬采样步 |
| 主判 2 风暴窗投喂较基线（MACH1=525 帧）降 ≥90% | **PASS** | 风暴轮 prop 全轮计数 0-27 帧=95-100% 降 |
| 主判 3 j0d jump ≤0.10m | **净/静默轮 PASS；风暴轮 FAIL** | RA14 jump=**0.0**（njf=0，max_frame 0.056）；风暴轮 RA20/22 jump 29.1/30.2m=走爬净拖拽 |
| 主判 4 零回归 | **PASS（hover watch）** | ground 0fail×3（RA11/18/24）；hover n=4=0.085-0.677（2/4 超 0.35 历史 0.090-0.341 带，守恒性无机理归因，挂观测）；干净带 j0 0.493-0.981 含 0.664 基线 |
| 净窗（§5） | **达成** | **RA14=历史首个 X1prime 型净轮（j0=0.493<0.5∧0fail），已即时通告 @T1**；到位 4.443m 未达=transit 地板独立在案（净窗≠到位） |

## 4. V2 判定（prereg_binglun Part A 逐字，承 v9.3 §3）

主判"≥1/2 X1prime 型轮 j0<0.5∧无 fail"：RA13 0.981✗/RA14 0.493✓=**1/2 → V2 主判过**（在线轮；栈=guard 栈）；次判 ground 零 fail ✓+到位读数并记（4.443/自报 4.005 一致）。**D-1004-T2-02（cauchy 入 gates）重开条件成立**——修复栈内 cauchy 在场，入正源与否待收口裁定（本 verdict 只报条件，不预设）。

## 5. 残余与移交（客观）

- **风暴轮走爬带**（|V|<15 放行窗）：发布侧连续性无法救治"连续但错误"的流——走爬本体=估计器病（敌对态残余/风暴族，修复面在册状态维持：机器层归因+transit 尺度残差架构级）。sane_v 调低=门值动作，禁（prereg 冻结 15）。
- odom 话题风暴轮采样步（10Hz×走爬速率）：判读链（round_result.sh:28/j0d）消费 prop 流，不受影响；odom 消费方（rviz/path）视觉连续性已改善。
- X1' 槽解锁判据=T3 域（其 j0d 工具对 guard 栈轮的读数=净轮 0.0/风暴轮 29-30 带宽）。
- 悬停 j0 带 0.085-0.677（n=4）较历史 0.090-0.341 宽——观测项，无归因。

## 6. 资产指针

prereg_reanchor_fix.md（含附录 A/B）；ra_campaign_summary.log（24 轮逐轮+banners）；run_T2RA1-24_*；cfg_streamguard/；t2_jump_timeline.py；栈存档建议=当前 devel（node b7de133d+lib 59548c6a）另存 stack_archive/streamguard-1/。
