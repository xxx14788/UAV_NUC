# T3 任务书 v10.4 — 完成清账版（2026-10-07 晨;tag sitl-v0.4 已打后的 X7 终稿窗执行版）

> 你是 **T3（规划/场景验收线）**。执行域=3090（`ssh nuc2`）。红线 1-29+判据器流程+锚表双门；等待协议 v2。
> 台账=3090 `~/sitl_sim/t3_evidence/`+repo `sitl_sim/t3_results/`。
> **v10.3 已执行完毕（02:32-04:13）且头号目标达成：tag sitl-v0.4 已打已推（04:10:54，5/5 全物理无门基线+T3 影子 7/7 双链闭合）**。本册=完成清账+X7 终稿 24h 窗（截至 2026-10-08 04:15）执行版。
> 默认案推进制/等待协议 v2 沿用。v10.3 弃读。

## A. v10.3 完成清账（六件全落）

1. **单元 0 开工收尾** ✓（02:35-02:38，3min）：STATUS 开工行；git pull（ahead=0，remote 名 UAV_NUC 勘误——`origin` 不存在）；册 v10.3 双树部署 md5 c87ed84a 一致；承件核对=X2g1_041509/X2g1R/X2g3R j0d 三行与 T1 v11.18 册逐位一致；**分叉发现并修复**=运行树 analysis 滞后（缺 STARVE/PLAINCHK/REGCHK 排除面+j0d 表整体）→repo→运行树同步（combo f1a945aa/j0d 表 8a986ddb 双树一致）；t3_evidence 目录补建。
2. **单元 1 三列分账计数口径 v1 落码（头号件，红线 24 全流程）** ✓：
   - 分类权威 `analysis/t3_trichotomy.py`（252ee661→de47b1a0 含 n/a 澄清）：物理绿[无门干预全绿]/门拦截计入[门触发∧恢复链四条=受控中止+完整降落 z_end<0.15∨landed+disarm=1+无T2fail（legacy 门轮 cf 豁免）]/真 FAIL；selftest 6/6（三类各≥1+legacy/cost 兼容+incomplete 边界）双树双端。
   - x4_batch 消费改造（5e9df0a1）：计数器拆分 GREENS/GATE_INTERCEPTS+5/5 双条件判定（合计≥5∧物理绿≥PHYS_FLOOR，--phys-floor 可调）+intercept_incomplete 重试 ≤3/格+物理轮 ≤15+GATEHIT-STAT 行冻结格式进 x4_gatehit_stats.log+成色注记段+tag 消息含成色。后被 T1 融合版 a655cae 吸收（三列锚点 22 处零丢失实证+T1 扩展 pregate-block 域）。
   - round_result.sh v1.4+（7e907b7d）：增 LANDING/GATEHIT-STAT/TRICHOTOMY 三行；**VRFY2 历史轮回归 diff=仅 3 新增行**（旧行逐字不变=历史零重判 §2.9-b 实证）。
   - prereg §2.9+v1.5 冻结（9e655eb7→d3720770 含 n/a 措辞）；.bak_tricho_20261007 双树四件。
   - 呈报件 trichotomy_briefing（b64cf9cb 双树）：物理绿下限两案（默认案 ≥3 生效/备选不设限纯注记），STATUS 异步呈报=通知非请示。
   - **事故一（裹挟）**：T1 提交 5bfdeee 在我 add 后 commit 前落地，裹挟 T3 staged 8 件（内容零损，md5 核对在册）→e008349 登记性提交归位；"commit 前必查 staged 列"红线双向确认。
3. **单元 2 X7_DRAFT 续推 v0.9→v0.95** ✓（564390c0）：§8 R12 前兆条目更新（1e=材料不可行定案注记+X5 H1 单调素材回填[gyr 四分位绿率 50/40/20/0%=可操作前兆指标]+间歇性补强）；R12 主表行更新；附录 A 补失效形态轴（上游官方 case2 表型与我方 z 塌落精确吻合=实机同病注记）；§6 X5 槽回填确认（与 x5_passmap 正源无分叉）；§9 fig 再生条件核查通过（生成器 e78dce4a 双树+语法活+dry-run 产物在档）；§7.6 Z1.2 措辞更新（未接线→已接线终态，10-06 19:19 build 窗）；R12 两联动注记（T2 门科学包六面全负/T2 定因批闭合零翻案）。
4. **单元 3 X4 背书链（就绪→当夜实战兑现）** ✓：
   - 就绪件：`t3_endorse_rerun.sh`（ad631063，goal.txt 正源+round.log world 实读+影子独立重跑三位逐位比对+GATEHIT-STAT 链复核；VRFY2 回归三位全中）；就绪文档 x4_endorsement_readiness（cda7d0a1，抽验计划 ≥5 全抽/门拦截轮必抽/90min 时限承诺/悬停格默认案不入选/tag 三链前置清单）。
   - 实战：X4 新批（五位形绿格 E12O/NE8O/NE12O/S12P/E8O+替补 S8O/N8P，T1 融合版）**影子抽验 7/7 全中**（三位逐位+TRICHOTOMY 独立分类，与 T1 手动重账双源一致）；背书记录 x4_batch_endorsement_20261007（501f31dd，含 D 节 wl-bug 事故全录）。
   - **tag 第二链**：X4_T3_REVIEW_CONFIRM 写入（5/5 CONFIRM，7/7 抽验+三列计数物理绿 5/拦截 0+与终账 206506c5 逐行一致）→T1 轮询检出→**tag sitl-v0.4 04:10:54 已打已推**（注解含成色+wl-bug 注记+双链声明）。背书时限 33min<<90min 承诺。
   - **事故二（wl-bug 定案）**：judge_round 内 w()（tee 双写 stdout）被 CLASS=$(...) 捕获→case 永不匹配→批级计数/换格/重试/带图条件件全瘫（批曾显示假 0/5，真 4 绿被吞）；本地复现实证；谱系=v9.9 批起潜伏（0/5 无绿表观无害掩盖）→T3 落码继承骨架同坑→T1 融合→爆发→T1 热修 64f81b8+手动重账；**损害边界=轮判读落盘（RESULT/TRICHOTOMY/GATEHIT-STAT）独立于 case 不受染**；v9.9 批回溯注记=其账面结论经独立双源复核维持有效。
5. **单元 4 判读统计续件** ✓（注记面全落）：Z1.2 移除（X7 §7.6 已更新）；hover j0 带宽=X4 批后补轮件 @T2 池注记；门科学包/定因闭合两联动注记入 X7 R12（70de75d+8d244c6）。
6. **收官手续** ✓：STATUS 收工行 04:13（含 X7 24h 窗登记）；T3 侧 commit 链全推（5bfdeee 段 T3 8 件+e008349+d650dc1+70de75d+7b38319+8d244c6+3206678）；记忆 t3-v103-trichotomy-tag-campaign 落盘。

## B. 剩余件（X7 终稿 24h 窗主体，截至 2026-10-08 04:15）

1. **X4 新批 j0d 批跑**：9 个 run_X4_* 目录（7 批轮+2 个 1e 标本）**零 j0_decomp.json**（10:06 实查）——X7 §3 逐轮表的 j0d 三列缺料；袋全在盘（含 S8O 12G/N8P 11G 带图），可跑。
2. **X7 终稿依赖槽销号**（X4 已定局，24h 窗内）：§2 续飞/§3 逐轮表（新批 7 轮四指标+到位双口径+p95+特征数+锚差漂移+fj_raw/smj+j0d 三列）/§4 判决表/§6 X 线批轮子集 CI/§7.10 综合陈述（引 §7.1-7.9+T4-J3 六维基线）/§9 figs 终版再生（fig2/3/5/6）+再生命令行留档。
3. **组合矩阵/j0d 统计扩切口**：t3_combo_matrix 对 X4_* 轮的收录（banner 实读为主，但 CAMPAIGN_ARM 战役名映射无 X4 前缀条目，provenance 注记需核对）；j0d 统计表（118 袋轮版）扩至含新批。
4. **统计口径一致性核对**：§6 n 与 CI 数字与 legs 框架输出一致（检查单在册项）；新批尚无 legs/x4judge 统计框架输出（只有逐轮判读+终账）。
5. **终稿手续**：同名去 _DRAFT 替换+git 标记；.bak 凭据族清理（条件=终稿后）；交叉引用刷新（runbook §/台账节号/STATUS 时戳）；X4 七轮带图袋处置 @T4（口径 22，终稿后）。
6. **依赖 T2 两件**（未到货）：X5 j0d 批跑（T2 单元 3）→§6 扩切口+fig 完整再生；hover j0 补轮（悬停 8.5m 素材在 T2 册）。
7. **残留清理**：X4_TAG_PENDING 陈旧件在档（tag 已打已推，负责移除它的批循环已死）；t1_evidence/v11_7 与 v11_20 两份 x4_batch_report 并存（旧批/新批各一，引用需带日期限定）。

## C. 卡点（客观陈述面临的问题；不含解决方案）

1. **三列分账 v1 的拦截分支无实战正样本**：门科学包（T2 六面+T1 同核 ROC 双线）判运行时预防门不可靠→X4 走无门基线→本批 7 轮 GATEHIT n=0 全绿零触发。gate_intercept/intercept_incomplete/pregate-block 三个分类分支只有合成样例+selftest 6/6 验证；分类器对 gatehit_\<round\>.json/pregate_\<round\>.json 实战文件的消费面（字段名/嵌套/时戳格式）未经真实文件检验——T1 双门工程契约测试用的是自己构造的合成 gatehit。
2. **wl-bug 为结构性坑且有未排查面**：判读/批处理族脚本中"被 $(...) 捕获的函数体内使用 tee-stdout 写法"即瘫痪 case 接线；x4_batch 自 v9.9 潜伏两夜才爆发（潜伏期表观无害=0/5 无绿轮掩盖了计数失效）。t3_endorse_rerun.sh 已核查无此模式（纯 python 子进程捕获）+实战 7/7 验证；但 sitl_sim 域内其他含 w()/tee+捕获结构的脚本未做系统性排查，潜伏存量不明。
3. **X7 §6 统计框架缺口**：X 线批轮子集 CI 的计算管线（legs/x4judge 框架）未对新批运行——新批现有产出=逐轮判读+终账+影子背书，无统计框架输出；与既有 118 袋轮口径的合并 n/CI 计算方式未定。且 §6 完整版还依赖 T2 的 X5 j0d 批跑（未到货）。
4. **T2 依赖件两件未到货**（X5 j0d/hover j0），X7 §6 扩切口与 fig 完整再生被阻塞；仅含 X4 新批 7 轮的部分再生可行。
5. **STATUS 时戳纪律问题（对侧）**：观察到 T2 交付行时戳在两次读取间由 03:52 变为 02:53（同内容行，与 3090 系统钟均不符/相符关系混乱）；T1 里程碑行使用"04:2x"占位时戳。判读史引用跨线事件时序不能直接信 STATUS 自报时戳，需以文件 mtime/commit 时戳佐证（本轮 VRFY2/S8O 时序核对已如此处理）。
6. **背书重跑器已知缺陷**：t3_endorse_rerun.sh 表格末列一致性符号用聚积 FAIL 变量——多轮抽验中任一前序轮失配后，后续绿行的末列显示"见上列"而非 ✓（单轮三位符号列仍准确；7/7 全中场景未触发）。
7. **tag 证明力语义边界（在册事实，非新问题）**：无门基线 5/5=绿格选格收窄后的通过率证明，门拦截列空列；绿格重飞绿率≈70.5%/5/5 独立≈17% 的概率面在 T2 科学包在案——tag 不改变该概率面；S12P/S8O 两红轮如实计红。X4 新批在组合矩阵的臂×boot 归位、以及"绿格位形域 vs (7,-4,1) 位形簇"的对照叙述尚未生成。
8. **1e 回放裁决材料域属 T2**（E8P 3.12m+HVNET1 悬停 4.12m 两带图标本已移交）：X7 R12 的"sim 域特有注记"终措辞挂其结果。

## D. 资产 md5 表（10:06 实查，双树一致）

| 资产 | md5 | 说明 |
|---|---|---|
| round_result.sh | 7e907b7d | v1.4+三行扩展；.bak_tricho_20261007 在档 |
| x4_batch.sh | 6cfef742 | 演化链 5e9df0a1(T3)→fc51277c(T1 融合 a655cae)→6cfef742(T1 热修 64f81b8 后) |
| analysis/t3_trichotomy.py | de47b1a0 | 分类权威；selftest 6/6（2d813d16） |
| analysis/t3_endorse_rerun.sh | ad631063 | 影子背书重跑器 |
| docs/xline_prereg_v1_1.md | d3720770 | §2.9+v1.5 冻结 |
| docs/t3_xline_acceptance_report_X7_DRAFT.md | 564390c0 | v0.95 |
| t1_evidence/v11_20/x4_final_tally.md | 206506c5 | X4 正账（T1 产，T3 复核一致） |
| t3_results/x4_batch_endorsement_20261007.md | 501f31dd | 背书记录+D 节事故全录 |
| t3_evidence/trichotomy_briefing_20261007.md | b64cf9cb | 物理绿下限两案材料 |
| t3_evidence/x4_endorsement_readiness_20261007.md | cda7d0a1 | 背书链就绪文档 |
| tag sitl-v0.4 | 2992ccc9 | 已推 UAV_NUC（04:10:54） |

## E. 等待登记

- **W-T2 X5 j0d 批跑**（单元 3 到货）→§6 扩切口+fig 完整再生。
- **W-T2 hover j0 补轮**（@T2 池）。
- **W-T2 1e 回放裁决结果**（E8P+HVNET1 标本）→X7 R12 终措辞。
- **W-T4 X4 七轮袋处置**（X7 出稿后，口径 22）。
- **X7 终稿 24h 窗**：截至 2026-10-08 04:15；下任首件=B.1 X4 新批 j0d 批跑（零依赖，料在盘）→B.2/B.3 正账消费与 fig 部分再生。
