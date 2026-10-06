# X4 背书链就绪文档（T3 v10.3 单元 3;2026-10-07 冻结）

> 性质：X4 批批判读到货前就绪件（tag 三链之第二链——复核行是 tag 前置）。
> 协议正源=实战版 x4_batch_endorsement_20261006.md（5+2 轮抽验 7/7 全中先例）。

## 一、背书抽验制（沿用+扩展）

1. **goal.txt 正源协议**（VRFY2 首次传错 goal 教训）：抽验参数一律从轮目录 `goal.txt` 实读，禁手抄位形表；world 从 `round.log` `SITL up (<world>)` 行实读。
2. **影子目录独立重跑制**：`analysis/t3_endorse_rerun.sh <run_dir>...`——独立目录重跑 round_result+t3_wa_gate+t3_trichotomy，与原 RESULT.txt 逐位比对（jump/arrive/RESULT 三位一致=抽验中）；stdout=背书表行直接入背书记录。
3. **三列分账链复核（新增）**：每轮输出 GATEHIT-STAT（n/ts/val/kind+恢复链四条）+TRICHOTOMY class——**门拦截轮必抽**（恢复链完整性[受控中止/完整降落/disarm/无T2fail]独立复核=独立于批内嵌判读的第二判读面）。

## 二、X4 批期抽验计划（预注册）

- **规模**：≥5 轮全抽（批 5 位形轮全量）为默认；批含拦截轮/重试轮时按 **≥7 抽验**扩（每位形轮+关键拦截轮）。门拦截计入轮**必抽**；intercept_incomplete 轮抽验复核恢复链缺口定性；phys_green 轮抽验复核"无门干预"证据面。
- **时限承诺**：批判读到货=本线最高优先级（压过 X7 续推/统计件）；逐轮背书随到随做；**批到货 90 分钟内背书未齐=STATUS 升级行说明卡点（禁静默拖）**。
- **tag 前置件**（三链判据齐=机械执行直接打+成色注记随发，零人工窗）：
  1. T1 内嵌判读全绿（5/5=物理绿+门拦截计入≥5 ∧ 物理绿≥3 默认案，三列分账口径 v1）
  2. 本线复核行（抽验全中+门拦截轮恢复链复核齐 → X4_T3_REVIEW_CONFIRM 写 'T3-REVIEW: 5/5 CONFIRM'）
  3. 成色注记随发（物理绿 X+门拦截计入 Y+GATEHIT-STAT 明细）。
  - 判据不满足=永不打（诚实由判据和留痕保证）。

## 三、悬停型格呈报（通知非请示）

- **默认案（生效）**：悬停型格**不入选** X4 新五位形——绿格 gyr 升序顺位满 5 继续执行（X5 曲线 H1 剂量单调=gyr_peak 高位格绿率高，导航位形优先）。
- 用户窗内明确选悬停格 → prereg 位形表修订件当晚支持（§7 位形表增行+冻结注记，零门值变更）。

## 四、就绪自检（2026-10-07 02:5x）

- [x] 判读链 md5：round_result 7e907b7d / x4_batch 5e9df0a1 / t3_wa_gate bee17577 / t3_trichotomy 252ee661（双树一致）
- [x] 背书重跑器 t3_endorse_rerun.sh 部署+selftest（VRFY2 历史轮抽验回归）
- [x] 抽验计划预注册（本文件 §二）
- [ ] X4 批到货 → 背书记录开卷（t3_results/x4_batch_endorsement_<date>.md，沿用 A-D 表结构+三列分账链列）
