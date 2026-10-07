# 判读统一流程 SOP v1（T3 v10.6 保底①：md5 对账+回归抽查——筛选轮/M3′ 轮同链）

> 适用：筛选批轮（解冻后）与 M3′ 批轮（T2 若跑）——两链同构，判读单源化。
> 本 SOP=各就绪件的执行索引；工具均在 `sitl_sim/t3_tools/`（部署位）。

## 前置（每批一次）

1. **判读器自证**：`md5sum round_result*`（在册 7e907b7d 系）+ `t3_wa_gate` md5 记档；
   与上批不一致=换代→**先跑 VRFY2 回归**（`python3 t3_vrfy2_regress.py`，零重判 PASS
   才可继续；漂移=HALT 呈报）——round_result 换代后零重判纪律。
2. **跨机 md5 对账**（筛选批专属，M3′ 跳过——同机单源）：两机各自
   `t3_md5_reconcile.sh ref -o <manifest>` → T3 侧 `cmp <对侧manifest>`；
   四件任一 DIFF=判读前呈报，禁带差判读（模板 P1）。
3. **轮名前缀校验**：`n3_`/`u4_`（筛选）或 T2 通告前缀（M3′）——无前缀/冲突=呈报（P2）。

## 逐轮判读（原始 log 在 3090 统一重判=权威；本地快速判读件不入统计）

- `round_result`（四指标+RESULT）+ `wa_gate` j0d（j0_total/jump/transit/dominant）；
- 止损文件在轮目录→trichotomy（de47b1a0）分类复核入脚注；
- 产物落轮目录/侧文件（判读落盘独立纪律沿用）。

## 统计与入册

- **M3′**：格级前后对比表（m3p_judge_support_plan_v1.md §3；前基线=M3 v1.1 十八轮）。
- **筛选**：screening_report_template_v1_frozen.md 六节填充（P1-P5 全过才进统计章）；
  绿率差 CI 用 `t3_greenrate_ci.py`（Newcombe，跨机结论必须带 CI）。
- **扩切口**：`t3_combo_matrix.py`/`t3_j0d_stats.py` 全量重生成（版本化）→
  `t3_combo_expand_check.py --old --new` 加性校验（旧行变动=HALT 禁覆写）→
  provenance 三列按 combo_j0d_expansion_plan_v1.md §2.1 规则填。

## 红线自查（每批收口前）

- [ ] 判据零变动（三层判据逐字/REGEN v2 预注册失败语义）
- [ ] 零重判（VRFY2 或加性校验 PASS 在档）
- [ ] 判读单源（统计输入全部=3090 重判产物）
- [ ] 平手/追加批按预注册文案，无事后阈值
