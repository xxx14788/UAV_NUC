# X4 五位形批终判（v11.13 单元 2；2026-10-06 05:1x；FAIL 汇总态收卷）

> 臂=v2 修复臂（loss=0/cost_gate=1/staged=1/guard=1，D-1006-T1-09）；栈=b7de133d/59548c6a；boot-2。
> 判读=补判版权威（rejudge_rounds.sh，judge 三 bug 修复后语义）；tag **不打**（0/5，诚实认证条款）。

## 1. 五位形全景表（8 物理轮）

| 位形 | 轮 | 判读 | 到位(m) | jump(m) | faildet | 主病灶 |
|---|---|---|---|---|---|---|
| X1final (7,-4,1) | X1final_040931 | **fail**（计分母） | 5.026 | 5.765 | 0 | goal 段帧跳变 |
| X2g1 (7,-4,1) | X2g1_041509 | 未定案（判读被杀） | ~41 飞丢 | anchor y=-37 | ? | goal 段帧跳变（巨幅） |
| X2g1 补飞 | X2g1R_045147 | **fail** | 8.331（未动） | 0.011 | 0 | **planner starve**（VINS 面完美） |
| X2g3 (8,-1,1) | X2g3_042025 | **fail** | 7.657（未动） | 0.042 | 0 | **planner starve**（goal 未达） |
| X2g3 补飞 | X2g3R_050113 | **fail** | 4.792 | **24.219** | 0 | goal 段帧跳变（巨幅） |
| X3l2a +leg2 | X3l2a_042631 | **hostile**（不计分母） | 4.452 | 5.039 | **14** | 跳变+faildet 族 |
| X3l2b +leg2 | X3l2b_043724 | **fail** | 4.181 | 1.200 | 0 | goal 段帧跳变 |
| （同夜佐证） | VRFY2_040542 | **PASS** | 0.176 | 0.100 | 0 | 无（绿；04:05） |

**X4 计数：0/5 绿。分母=4（X1final/X2g1R/X2g3R/X3l2b），hostile 1（X3l2a 不计），未定案 1（X2g1_041509）。**

## 2. 三层病灶分离（本轮批的核心知识产出）

1. **NaN 风暴层=v2 臂已消灭**：8 轮全零 NaN（对比 VRFY1 1066）；T2fail 除 X3l2a(14,跳变伴生) 全零；CauchyLoss(0) 根因修复在全部位形成立（D-1006-T1-09 闭环的批级确认）。
2. **goal 段 VINS 帧跳变族（主导病灶，5/8 轮）**：巨幅 24-37m 级两例+中幅 1.2-5.8m 三例；判读语"T2 瞬态发散类"。时空分布：**(8,-1,1) 位形 04:05 绿（0.100）→05:01 跳 24m**——同 boot/同臂/同位形 56 分钟内绿→巨跳=时间维度转折在 04:05-04:09 之间；机器态歧（M 线）材料@T2 @T3。
3. **planner starve（harness 竞态，2/8 轮）**：planner 停 INIT→WAIT_TARGET 终静默，goal 2×8s+三查+重发未接住；两例轮 VINS 面极稳（jump 0.011/0.042）——纯 goal 话题订阅竞态；T1 域修复件（就绪探测/订阅确认门）遗留。

## 3. 双链核验制执行注记

0/5 未触发 tag 链（PENDING 流程未启动）；判读链=补判版（批内嵌判读因三 bug+批进程被会话关闭连带死亡而失权，全部以 rejudge_rounds.sh 输出为准，报告内两版判读并存如实保全）。

## 4. 处置

- X4=FAIL 汇总态收卷待用户；tag sitl-v0.4 不打（诚实认证）。
- X2g3 位形绿佐证（VRG1/VRFY2）与 FAIL 轮并列在册（时间维度转折材料）。
- 遗留件：①planner starve 修复（T1 harness 域）②goal 段跳变族机理（T2 X1prime/瞬态域主战材料=本表）③串行链 pkill 自匹配坑入册（vins_smoke 字样 cmdline 被轮清理误杀）④批启动会话关闭连带死亡坑（setsid 不足以防，改单轮发射制）。

## 5. 证据指针

- 批报告：x4_batch_report.md（判读行全量）+本终判
- 补判输出：rejudge_rounds.sh（本夜 4+2 轮）
- 机理链：boot_diff_report.md（NaN 层）；verify_verdict_v119（v1 臂时代）；T3 矩阵=DECISION_LOG 三歧结论行
