# 回归锚点交叉核对表（anchors.json ↔ data-pack 同口径数字）

生成：2026-10-02，汇总员 attempt=1。锚点源：`D:/drone_VINS/t4_work_20261002/raw/anchors.json`（B0 产，解析自 raw/docs/t4_verdicts_v2.md、raw/docs/t4_j2_threshold_prep.md、raw/vision_inputs/j2_threshold_table_v1.json）。判定三类：**一致**（数值相等，含明确舍入关系）/ **不一致**（进文末 diffs，列双方数值+出处，不裁断）/ **无对应**（data-pack 无同口径数字）。行内"pack 出处"= data-pack 章节（底层文件在括注）。

| # | 锚点 metric | 锚点值（anchors.json） | data-pack 同口径数字 | pack 出处 | 判定 |
|---|---|---|---|---|---|
| 1 | sigma_p25_round1_p50 | 1.02899（n=67, p10-p90=1.02447-1.03438；L143） | WC2OBS1_030927 d12_sigma_p25 袋级 p50=1.02899（json 逐位 1.0289948，n=67） | §6 D4 输入面（derived/d4_j2_plane.md §1/§0.1，源 metrics_WC2OBS1_030927_w3.json）；§4 D2 袋级表 1.029(67) 为 3 位舍入 | 一致 |
| 2 | sigma_p25_round1R_p50 | 1.02978（n=66, p10-p90=1.02125-1.03403；L144） | WC2OBS1_032005 d12_sigma_p25=1.02978（json 逐位 1.0297823，n=66）；EXF fresh 重跑同值 1.02978(n=66) | §6（d4_j2_plane.md §1/§0.1）；§11.2（exfail_matrix_real.md §4） | 一致 |
| 3 | supply_p50_norm_by_maxcnt150 | 0.85（max_cnt=150 归一 P50；L209） | 注入代池归一 0.8467=127/150，四舍五入 0.85（D7 §2.1 原文注记） | §9（derived/d7_stack_era.md §2.1，源 raw/vision_inputs/j13_supply_pooled.json pooled_inj_era_only."50"=127.0） | 一致（四舍五入口径） |
| 4 | supply_p50_j2_table_v1_crossbag | 0.823（json 精确 0.8233；L241） | M1 跨袋 P10/P50/P90=0.562/0.8233/0.9697 逐位复现 | §9（d7_stack_era.md §2.4，源 raw/vision_inputs/j2_threshold_table_v1.json） | 一致 |
| 5 | density_cloud_points_p25_p50_p90 | [115, 127, 141]（注入代分池 n=10959 云 5 轮；L208） | pooled_inj_era_only："25"=115.0 / "50"=127.0 / "90"=141.0（n=10959） | §9（d7_stack_era.md §2.1/§2.4 引；直接源 raw/vision_inputs/j13_supply_pooled.json） | 一致 |
| 6 | j2_threshold_table_v1_ten_metrics_P10_P50_P90 | 十指标表（p_sat 0/0/0；hist_range 43.9/148.5/152.6；med_gray 69.2/161.0/175.9；corners 84.3/123.5/145.45；grad_med 4.911/8.2462/8.4853；maxbin 0.1322/0.2494/0.2791；熵 0.7857/0.8268/0.9603；σ̂P25 1.0224/1.0294/1.0309；M1 0.562/0.8233/0.9697；M2 0.5875/0.8438/1.0） | 9/10 指标 |diff|≤5e-5 逐位复现（同上九行全部逐位吻合）；**p_sat 行例外：表载 0/0/0 vs 八袋袋级 p50 重算 0/1.30e-05/1.92e-05** | §9（d7_stack_era.md §2.4） | 不一致（仅 p_sat 行）→ diffs[0] |
| 7 | fb_residual_stereo_pool_p50_per_bag_px | U3PH 0.56 / X1final 2.05 / U3PO 26.0 / U3PR1 35.7 / U3PG 43.1 / U3PR2 44.4（p90 99-123px；L245-246） | stereo_pool p50 px：U3PH 0.5632 / X1final 2.047 / U3PO 26 / U3PR1 35.66 / U3PG 43.13 / U3PR2 44.44（D5 §0"逐值吻合，4 位精度内全中"）；EXF real PR2 fresh stereo_pool 44.44 | §7（derived/d5_bimodal.md §0/§6 池化表，源 fbres_*.json stereo_pool）；§11.2 | 一致（锚=1 位小数舍入） |
| 8 | era_effect_supply_p50_pre_vs_inject | pre_inject_X1img_p50=45；inject_era_pool_p50=127；normalized pre=0.30/inject=0.85（L213-214，source_line 含"供给 p50 +112%"） | 端点全复现：45.0（n=1991 非空云）/127.0（n=10959）/0.3000/0.8467（→0.85）；派生增量算术 **+182.22%（2.8222×）**，与 source_line"+112%"标签不符 | §9（d7_stack_era.md §2.1/§2.2，源 j13_supply_pooled.json+metrics_X1img_015950_density.json） | 数值一致；增量标签不一致 → diffs[1] |
| 9 | sigma_p25_eight_bags | U3PH 1.02185 / X1final 1.0227 / U3PO 1.02891 / WC2#2 1.02978 / WC2#1 1.02899 / U3PR2 1.03009 / U3PG 1.03078 / U3PR1 1.03111（八袋全非零紧聚 1.022-1.031；L218-220） | D4 §1 表八行逐值相等（1.02185/1.02270/1.02891/1.02978/1.02899/1.03009/1.03078/1.03111）；锚注"WC2#1/#2 依顺序推断"的袋名对应经 json 逐位证实（030927=1.0289948、032005=1.0297823） | §6（d4_j2_plane.md §1/§0.1）；§7（d5_bimodal.md 无涉） | 一致 |
| 10 | m1_saturation_three_bags | [U3PH_210708, U3PR1_212450, X1final_173345]（饱和形态三例 p90=1.0 级；L221-223） | 去饱和双列三袋同名单（扩展池标注）；饱和帧≡corners_gFT==150 帧级等价三袋全 True；U3PH 剔除率 0.9444（68/72）、U3PR1 0.0694（5/72）、X1final 0.2917（21/72） | §6（d4_j2_plane.md §0.1/§4，源 anchors.json m1_saturation_three_bags+各袋 metrics json per_frame） | 一致 |

**无对应**：0 项（10 锚点全部在 data-pack 找到同口径数字）。
脚注：锚点 #3 的 source_line 另载 P10=0.55/P90=0.94（归一），此两值不在锚 value 字段内，derived/ 未做该两分位的独立重算（同口径底层值见 j13_supply_pooled.json pooled_inj_era_only "10"=82.0/"90"=141.0，82/150=0.5467→0.55、141/150=0.94）。

## diffs（不一致项，双方数值+各自文件出处，不裁断）

- **diffs[0] p_sat 行（j2 阈值表 v1 十指标锚 #6）**
  - 甲方数值：P10=0 / P50=0 / P90=0。出处：`raw/vision_inputs/j2_threshold_table_v1.json` threshold_table_v1.p_sat；`raw/docs/t4_verdicts_v2.md` L239"p_sat 全零"；`raw/anchors.json` j2_threshold_table_v1_ten_metrics_P10_P50_P90。
  - 乙方数值：八袋袋级 p50 重算跨袋 P10=0 / P50=1.30e-05 / P90=1.92e-05。出处：`derived/d7_stack_era.md` §2.4（输入=8 袋 metrics json 袋级 p50，含 U3PH/X1final 袋级 p50=0、其余袋 1e-5 量级，见 `derived/d4_j2_plane.md` §1）。
  - 双方均有的登记：`raw/data_dictionary.md` L36 注记"verdicts L239 j2 表「p_sat 全零」为袋级 p50 截断显示"；`derived/d4_j2_plane.md` §5.6 同口径登记。本表仅并列，不裁断。
- **diffs[1] 年代效应增量标签（锚 #8 source_line）**
  - 甲方数值：供给 p50 **+112%**。出处：`raw/docs/t4_verdicts_v2.md` L213-214（"注入前代 X1img p50=45（0.30）vs 注入代池 p50=127（0.85）——供给 p50 +112%"）；`raw/anchors.json` era_effect_supply_p50_pre_vs_inject.source_line。
  - 乙方数值：**+182.22%**（=(127−45)/45，倍率 2.8222×，绝对增量 +82.0 点/云；归一用舍入值 0.85/0.30 计为 +183.33%）。出处：`derived/d7_stack_era.md` §2.2（端点 45/127 本身复现，见 §2.1；D7 登记语："verdicts L214 与任务书所载'+112%'标签与自身端点算术不符，本机素材内未找到 +112% 推导口径"）。
  - 锚 value 字段（45/127/0.30/0.85）与乙方端点一致；出入仅在增量标签数字。本表仅并列，不裁断。

## 附录：非锚点数字的口径出入登记（供复核，不入 diffs）

1. WC2 两袋爆止窗长三口径（`derived/d3_truncation.md` §1）：工作口径（odom 首–末）46.120s/109.364s vs features.bag rosbag info 46.136s/109.343s vs verdicts L204-205 记载 43.7s/102.0s——data-pack §2.3 三方并列。anchors.json 无窗长锚点项。
2. X1img_015950 corners_gFT 袋级 p50=37.0（`derived/d4_j2_plane.md` §1/§5.7，源 metrics_X1img_sim.json）与锚 #8 的 pre_inject 45 属不同指标（45=特征云每云点数 p50，源 j13_supply_pooled.json per_round.X1img_015950.p50=45.0；37=每帧角点数 p50=verdicts L72"37/帧"）——两值并存，出处均登记（d4_j2_plane.md §5.7、d7_stack_era.md §2.3）。
3. 五面矩阵计数与本地实有差异：matrix_5faces.md（B0 时点）fb json ✓=7/density ✓=3，B1 补算后本地 raw/ 实有 fb 10/density 6（`derived/d2_ndim_corr.md` §6、`derived/d7_stack_era.md` §6④ 登记；data-pack §2.4 已并列两时点口径）。
