# 双 t3_results 目录收敛+生成器消歧记录（T3 v10.9 单元1，2026-10-09）

> 任务书 v10.9 单元1 落账件。两起实害史：①j0d_stats v2 生成器 OUT 硬编码 HOME 侧
> （`~/sitl_sim/t3_results/`），repo 侧表靠人工拷贝同步（分叉风险实害）；②生成器双谱系
> （v1 repo 侧/v2 HOME 侧）无版本自描述，20261008 表实为 v2 临时改行（OUT+COMBO 联表
> 双 sed）跑出——谱系不可追溯。

## 1. 病灶勘定（本次实证）

| 生成器 | 改前 OUT | 联表 | 判定 |
|---|---|---|---|
| `t3_j0d_stats.py`(v1) | repo 侧 ✓ | 硬编码 | 双谱系之一，退役 |
| `t3_j0d_stats_v2.py`(v2) | **HOME 侧** ✗ | 硬编码 combo_20261006；20261008 表实为临时改行联 20261008 | 病源，改造 |
| `t3_combo_matrix.py` | repo 侧 ✓ | --l3 可传 | 仅缺版本自描述 |

实证：v2.1 初版（联表默认保持 legacy 1006）重生成即现 drifted=111（M3 批 20 轮
CAMPAIGN_ARM 列空+H15 分类翻），证明 20261008 表正源行为=联 **20261008** combo 表
——改行史实锤。

## 2. 收敛措施

1. **v2 → v2.1**（`analysis/t3_j0d_stats_v2.py`）：
   - OUT 默认=repo 正源 `~/catkin_ws/sitl_sim/t3_results/`；
   - argparse 化：`--out-dir/--date/--combo/--smoke/--l3/--version`；
   - **combo 联表默认自动取 out-dir 内最新 `combo_matrix_*_rounds.csv`**（自描述打印，
     杜绝改行换表）；表 txt 头加生成器版本+联表路径+生成时刻行。
   - CSV 行输出逻辑零改动（同输入逐字节等价，见 §3）。
2. **v1 退役归档**：`git mv` → `analysis/retired_generators/t3_j0d_stats_v1_retired.py`
   + `README_retired.md`（谱系+禁跑纪律）。
3. **combo_matrix.py → v1.1**：banner 加生成器版本行（OUT 本就 repo 正源，无行为改动）。
4. **两侧历史对账同步一次**：正源表双侧已一致（20261007/08 SAME）；HOME 根目录台账级
   散件 10 件（plannerdom 时间线×5/y4_full_verdicts/xline dryrun/ledger_fix_append/
   x1prime selftest/commit_msg_fix）收录 `reconciled_home_strays_20261009/`（md5 10/10
   一致，MANIFEST.md 在册）。
5. **约定固化**：repo `t3_results/`=表与文档正源（git 追踪）；HOME `~/sitl_sim/t3_results/`
   =轮产物（bag/日志，不入 git）落点。生成器一律写 repo 侧。

## 3. 零漂移验证（改前后护栏，全部在案）

| 步骤 | 命令面 | 结果 |
|---|---|---|
| 改前基线 | 两侧全表 md5 快照 `/tmp/t3_unit1_baseline.txt`（118 行） | 在案 |
| 正向：同输入复现 | v2.1（自动联表=20261008）`--date 20261009` → expand_check vs 20261008 | **old=205 new=205 drifted=0 RESULT: PASS-纯加性 RC=0**；风暴=86/中漂移=63/净轮=56 与 20261008 逐位一致 |
| 反向：联表错配（谱系病演示） | v2.1 显式联 legacy 1006 → expand_check vs 20261008 | drifted=111 HALT（M3 批 20 轮列空+H15 风暴→中漂移）——即 v2 时代改行病的自动检出 |
| 护栏负例 | 单字段篡改 drift_test → expand_check | drifted=1 HALT **RC=1**（退出码正确；此前观测 RC=0 系测试管道吃 RC 假象，工具无缺陷） |

## 4. 坑账（本次新增）

- **管道吃 RC 复发**：`cmd | head; echo $?` 捕获的是 head 退出码——expand_check 退出码
  验证必须 `cmd > out; RC=$?` 两段式。
- **sed 中文乱码风险规避**：生成器改造一律走"拉取→本地编辑→scp→py_compile"链，禁远端 sed。

## 5. 后续接口（单元 2 用）

新批轮滚入流程（按 `v10_6_docs/combo_j0d_expansion_plan_v1.md` §1）：combo v1.1 全量
重生成（新日期戳）→ 加性校验 → j0d v2.1（自动联新 combo 表）重生成 → 加性校验。
20261009 j0d 表=收敛后首件（内容=20261008 之复现，作为收敛见证件保留）。
