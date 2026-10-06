# T3 v10.3 单元 1 呈报件 — 三列分账计数口径说明段（门设计冻结版配套；2026-10-07）

> 性质=通知非请示（默认案推进制）：呈报后按默认案继续执行，用户窗内响应则改道。
> 正源=prereg xline_prereg_v1_1.md §2.9（v1.5 冻结）；实施=commit 5bfdeee（T3 8 件）+e008349（登记归位）。

## 一、三列分账口径（计数口径 v1）

| 列 | 定义 | 5/5 计数 |
|---|---|---|
| 物理绿 phys_green | RESULT=PASS ∧ 门干预证据=0（gatehit/pregate-block/COSTGATE-FIRE/faildet 全无） | 计入 |
| 门拦截计入 gate_intercept | 门触发 ∧ 完整恢复四条全齐（受控中止∨cf=controlled / 完整降落 z_end<0.15∨landed / disarm=1 / 无 T2fail） | 计入（成色注记） |
| 真 FAIL true_fail | 其余（四指标红面；door 撞门型另注） | 不计 |

- **5/5 判定 = 物理绿+门拦截计入 ≥5 ∧ 物理绿 ≥ 下限（默认 3）**。
- 拦截不完整（四条不齐）=不计红不计绿，换轮重试占门拦截预算 ≤3/格；批总物理轮 ≤15（防凑数终止）。
- 每轮拦截统计行格式冻结：`GATEHIT-STAT: n/ts/val/kind + chain=abort,land,disarm,not2fail`（round_result 单轮输出+x4_batch 汇总 x4_gatehit_stats.log → batch_report 成色注记段）。
- 历史轮零重判：口径只对 2026-10-07 后新批生效（§2.9-b）。
- 判据器：分类权威=analysis/t3_trichotomy.py（selftest 6/6：三类各 ≥1+legacy/cost 兼容+incomplete 边界）；round_result 回归=VRFY2 历史轮 diff 仅 3 新增行，旧行零变动。

## 二、物理绿下限两案（用户窗内可改；默认案已生效）

- **默认案（已生效）：物理绿 ≥3**。理由：防"全靠拦截凑 5"成色滑坡——若 5 个达成全来自门拦截计入，说明系统在无门时几乎不能自主完成任务，tag 的"VINS 闭环达标"语义不成立；≥3 保证过半数为无干预自主完成。
- 备选案：不设限纯注记分级（5/5=物理绿+拦截合计，tag 注记物理绿 X+拦截 Y 分级呈现）。理由：门本身是系统设计的一部分，拦截+完整恢复也是合格行为；由成色注记承载区分度。
- 落码面：`x4_batch.sh --phys-floor N`（默认 3）；两案切换=参数级，零判读器改动。
- tag 消息模板已含成色：`phys=$N + gate-intercept=$M ... phys-floor>=$F`。

## 三、@T1 对接契约（W-T1 双门集成）

- `gatehit_<round>.json` 字段=t_trig/metric/value/baseline/gate/action/landed
- `pregate_<round>.json` 字段=verdict(pass|block)/action/metrics/restart_chain
- T1 v11.20 单元 1 双门工程按此落盘 → 本判读面即消费（cf 状态仍由 t3_wa_gate --online 现场判，x4_batch 自动传参）。
