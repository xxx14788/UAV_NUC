# δ 政策 A 首应用批判读判决 v1.0（2026-10-11；工程合并 v1.6 单元3）

> 批=N8P 格 8 轮（任务书 4 轮 + 短尾全清制扩展 4 轮），标准 vins_smoke 流程（无注入），
> goal=(1.010,8.980,1.0) world=sitl_world_obstacles budget=300 --stoploss。
> 批跑器=t1_delta_a_batch.sh（δA 配额+裁决语义逐字移植 t1_drill_run.sh v1.0；扩展批参数 R_START）。
> 配额=T1_DELTA_IMG_QUOTA=2；状态机=delta_img_state.txt（8×ROUND_START img=on）。

## 1. 绿率判读（0/8 全 FAIL）

| 轮 | verdict | jump(pre-post) | j0_total | j0 dominant | njf | arrive(真值) | 图像袋 |
|---|---|---|---|---|---|---|---|
| 1 | FAIL | 0.647 | 0.647 | mixed | 2 | 8.462 | 14G→DISCARD |
| 2 | FAIL | 0.153 | 0.153 | transit | 0 | 8.125 | 13G→DISCARD |
| 3 | FAIL | 0.090 | 0.090 | transit | 0 | 8.697 | 14G→DISCARD |
| 4 | FAIL | 1.783 | 1.783 | transit | 0 | **0.105** | 3.7G→DISCARD |
| 5 | FAIL | 2.492 | 2.492 | transit | 1 | 8.633 | 14G→DISCARD |
| 6 | FAIL | 0.135 | 0.135 | mixed | 3 | 7.790 | 14G→DISCARD |
| 7 | FAIL | 2.832 | 2.832 | transit | 0 | 9.466 | 14G→DISCARD |
| 8 | FAIL | 7.955 | 7.955 | transit | **31** | 8.508 | 14G→DISCARD |

- **绿率对照基线**：本批 0/8 vs M3 N8P 0/3（2026-10-08）vs M3' N8P base 3/3（2026-10-07 前时代）——
  近期 N8P 实飞绿率累计 0/11（彩票带冷期，二项噪声约束下与历史一致，A1 observe 结构性不收敛注记维持证据面）。
- 失败分型（j0d 面）：transit 主导 6/8（含轮 3/6 的"VINS 干净但未达"型——j0 0.09/0.135+零跳变帧，
  到位失败在执行/规划段非 VINS 段）；mixed 2/8；轮 8 njf=31 风暴型；轮 4 物理到位 0.105m 被 VINS 帧跳变
  （pre-post 1.783m>0.5 门）判负=彩票签名正型。

## 2. δ 政策 A 应用验证终态

| δA 三件 | 验证面 | 结果 |
|---|---|---|
| ①前 2 绿轮自动录图像（配额制） | 8×ROUND_START img=on（配额门 8/8 正确放行）| **PASS** |
| ②录制作业验证 | 8/8 袋 rosbag info 完整+帧对齐（左右目 7.5-7.7k 帧，count_delta=0，首末时戳差 0.0ms，ALIGNED 8/8）| **PASS** |
| ③批判读（j0d 滚入+绿率对照） | j0_decomp.json available=true 8/8；绿率对照 §1 | **PASS** |
| 附：非绿裁决（DISCARDED 删袋保主袋） | 8/8 执行（主 flight.bag 全保留，图像袋按策略删除）| **PASS** |
| **KEPT 面（绿轮保留+@T4 双用途）** | **未触发——0 绿轮样本**（配额 2 未满）| **未触发（如实注记，非失败）** |

**结论：δ 政策 A 从"落码毕"升"应用验证毕"——判据为机制四件全验证（配额/录制/验证/裁决）+j0d 滚入 8/8；
KEPT 保留分支无绿轮可触发，其代码路径已由此前干测覆盖（v1.6 落码时），现场触发留待后续批自然绿轮
（非本册待办——机制在册、样本未至，定性注记）。**

## 3. 图像袋规格注记（对 δA 尺寸预估的勘误）

实测 N8P 全程袋 13-14G/袋（非设计注释"~1-3GB/袋"——drill 轮短窗低估），磁盘门 23G 对单袋仍有效
（逐袋录→判→删，峰值 1 袋）；8 轮磁盘峰值占用无超门（df 425G 余量）。对冲=δA 尺寸注释更新需求登记，
盘门逻辑不变（单袋预算制）。

## 4. 证据索引

- 批报表：t1_evidence/v113_2026-10-11/delta_a/{delta_a_batch_report_r1-4.csv, delta_a_batch_report.csv, delta_img_state.txt}
- 轮产物：vins_smoke_runs/run_DAn8p_{1..8}_*（RESULT.txt/j0_decomp.json/images_check.txt[删袋前验证快照]/flight.bag）
- 上游：M3 批=m3_batch_report.csv（N8P 0/3）；M3'=t2_results/INPUTFACE（N8P base 3/3）；X5 批绿率 11/40=28%（跨格）
