# 组合矩阵/j0d 扩切口预案 v1 + provenance 三源列框架（T3 v10.6 单元 2）

> 起草时点=2026-10-08 01:3x（3090 断网期本地预产；恢复后随部署包落 3090）。
> 现状基线：j0d_stats **v3=185 袋轮切口**；组合矩阵 CSV=按日版本化落 `t3_results/`。
> 触发源：①T2 M3′ 批轮（若跑，预计 +18 袋轮 → ~203）；②筛选解冻后筛选轮（另行）。

## 1. 扩切口流程（M3′ 或任何新批轮到达时）

1. **前置核**：新轮目录齐件（RESULT.txt/simvins.log/flight.bag 或 bag 索引/wa_gate_online.json
   或可判读原始 log）；轮名带 T2 通告的前缀（M3′ 前缀以 T2 STATUS 通告为准，校验不过=呈报）。
2. **全量重生成（版本化，禁覆写）**：
   - `t3_combo_matrix.py --out t3_results/combo_matrix_<新日期>` （现有脚本全库扫描自带新轮）
   - `t3_j0d_stats.py`（同口径重跑，输出带新日期戳）
   - 冻结纪律：旧表不动；新旧表并存。
3. **加性校验（零重判纪律的扩切口形态）**：`t3_combo_expand_check.py --old <旧CSV> --new <新CSV>`
   - 旧表每一行必须在新表**逐字节重现**（字段级一致）——任何旧行字段变动=零重判违规，
     **HALT+呈报**（禁以新表覆盖旧口径静默改史）。
   - 新行清单+分类汇总输出（新增轮的 净轮/风暴/中漂移 计数、格归属）。
4. **j0d 同法**：新 j0d 表对旧表行做同校验（j0_total/jump/transit/dominant 字段）。
5. **落账**：扩切口结果（+N 袋轮、新行分类、加性校验 PASS）记 STATUS；数字进
   M3′ 格级前后对比（见 m3p_judge_support_plan_v1.md）。

## 2. provenance 三源列框架（nuc3 / uav4 / 3090；解冻后启用，框架先行）

### 2.1 列语义（新增三列，旧 `machine` 列语义保持=出生机器）

| 列 | 取值 | 推导规则（优先级序） |
|----|------|---------------------|
| `birth_machine` | 3090 / uav4 / nuc3 / ? | ①轮名前缀 `n3_`→nuc3、`u4_`→uav4；②RESULT.txt 证据路径 `/home/ghj`→3090、`/home/uav`→uav4（历史轮）；③3090 boot 窗推定（仅 3090 历史无证据行轮，沿组合矩阵现行规则）；④?=以上全不中（呈报） |
| `sync_channel` | native / uav4-synced / nuc3-shipped | 3090 本机出生=native；uav4 历史同步轮（mtime=同步时刻≠飞行时刻，现行代码已有此注记）=uav4-synced；nuc3 经汇聚目录回传原始 log（bag 本地保全）=nuc3-shipped |
| `judge_site` | 3090 | **恒 3090**——判读单源化（T1 2d：T3 以原始 log 在 3090 统一重判为权威，本地快速判读件不入统计） |

### 2.2 框架实现位

- 组合矩阵脚本加列=**解冻后**的代码改动（本预案只定契约，不改现行冻结判读产物）；
  M3′ 轮全为 3090-native，新列在 M3′ 扩切口时可以先行落 `native` 值不破坏任何旧轮
  （旧轮列值按 §2.1 规则回填，`?` 类如实标注）。
- 轮名前缀校验已入筛选判读前置（screening_report_template_v1_frozen.md P2）——
  与本框架同源同规则，防两处口径漂移。

## 3. 与既有纪律的接口

- **零重判**：扩切口的加性校验=VRFY2 纪律在新表上的投影；旧行变动即违规（§1.3）。
- **预注册**：j0d 三列口径（风暴=T2fail>0；净轮=T2fail=0∧j0_total<0.5；中漂移=其余）
  沿 v3 表头声明，扩切口不改口径——若需改=预注册重冻结，禁静默。
- **止损契约**：新增轮若带止损文件→trichotomy（de47b1a0）分类执行复核（v10.6 单元 3）。

## 4. 部署清单（网络恢复后）

1. `t3_combo_expand_check.py` → `~/catkin_ws/sitl_sim/t3_tools/`（或现行工具目录，随repo）
2. 本预案落 `~/sitl_sim/t3_evidence/` + repo `sitl_sim/t3_results/plans/`
3. 若 T2 M3′ 已有轮在盘：立即按 §1 执行扩切口并出对比数字
