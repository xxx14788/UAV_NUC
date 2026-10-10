# T4 v5.31 收货面大扩台账（单元 4，2026-10-10 夜；承 v5.26 台账口径续册）

> 口径承 bag_receipt_ledger_v526.md §0/§12/§13：批次袋=逐袋 rosbag info（rc+duration+chunks N/N+messages）索引级登记；全量 md5 仅锚袋/指令面（本夜九袋+75 袋两指令面执行）；**收讫-待判，零三态**（四族批次无 T4 预注册收货判据；判读权=T1/T2/T3 各域）。
> IO 纪律：STATUS 预告行 00:08 在案；T1ENG 飞行批未发射窗内执行；全程读面+索引级。

## 1. 九袋实机预录 md5 锚全量（必达①）

目录=`~/sitl_sim/t4_evidence/realmachine_pre_record/bags/`（33.3GB，串行 md5sum 全 rc=0，凭据=ninebag_md5_20261010.txt）：

| 袋 | md5 | 角色 |
|---|---|---|
| scen0_static_baseline.bag | 516f282a...3d2b6bc | 唯一 50Hz 静置基线（正源） |
| scen1_handheld_microshake.bag | f319406c...0031982 | 旧批=病理标本（Bas 爆） |
| scen2_handheld_slowmove.bag | 36df2658...0b78d8 | 旧批=病理标本 |
| scen3_handheld_walk.bag | 34ef760e...d0558522 | 旧批=病理标本（断流） |
| scen4_desktop_slide.bag | f612f3cd...07cb98 | 旧批=病理标本（断流） |
| r2_scen1_microshake.bag | 48e32646...843601f | **r2 批=正源** |
| r2_scen2_slowmove.bag | a218893a...27b | **r2 批=正源**（与 R2_MANIFEST 在册抽验锚 a218893a **互证一致** ✓） |
| r2_scen3_walk.bag | 947949e6...65f694 | **r2 批=正源** |
| r2_scen4_slide.bag | 49308d80...a85632 | **r2 批=正源** |

- 两 manifest 核对：PRE_RECORD_MANIFEST.md（5 袋表+环境事实+判读归属）与 R2_MANIFEST.md（4 袋表+质量判定+原版保留作病理标本注记）与实物逐袋一致（9/9 名称/大小/角色吻合）；任务书"scen0+旧批四袋[病理标本]+r2 批四袋[正源]"构成确认 ✓。

## 2. 75 袋 md5 补锚（单元 3 IO 件①，必达②联动）

- 清单=78 袋普查（cohort1-7：15+16+29+12+2+3+1）−§9 已锚 A1OBS 三袋=75；串行 md5sum 全 rc=0；凭据=75bag_md5_20261010.txt。
- 族计数断言逐位命中：C1_WU=15/C2_WU2=16/C3_3ARM_TA=29/C4_3ARM_BC=12/C5_WUFIX=2/C7_WU1B=1，TOTAL=75 ✓。
- 承 v5.26 §9 口径更新：彼时"红线④不做非必要大 IO、size+mtime 代记"——本夜 v5.31 任务书明示补锚指令（IO 窗件），75 袋 md5 自此全量在册；v5.26 台账 md5 栏'-'行以本凭据回填。

## 3. 四族批次袋索引级收讫（103 行，batch_receipt_fixed.tsv）

| 族 | 轮数 | rosbag info | chunks | 备注 |
|---|---|---|---|---|
| HAFIX_REVERIFY20 | 20 | 20/20 rc=0 | 全 N/N 等值 | T1 v11.39 复验批（16:06-18:05；S1-S4×r1-r5） |
| HAFIX_INCREMENT10 | 10 | 10/10 rc=0 | 全 N/N 等值 | T1 v11.39 增量批（18:30-19:22） |
| BIAS_BX_2A（②a box 臂） | 20 目录 | 18 OK+2 NOBAG | 全 N/N 等值 | 16 飞行轮+2 DRY（E12O/052019 N8P）+1 E8P_B_r2 重跑；NOBAG 两行=run_BX_DRY_N8P_043039（干测零袋，合理）+run_BX_E8P_B_054025（原轮零袋，r2_054222 为载体——与 T2 ②a 批 8/8 对账一致） |
| BIAS_TK_2B（②b tlock 臂） | 17 目录 | 17/17 rc=0 | 全 N/N 等值 | 16 飞行轮+1 DRY（DRY_N8P_121840 有袋） |
| M3P36 | 36 | 35 OK+1 NOBAG | 全 N/N 等值 | manifest 逐目录核对 36/36；NOBAG=run_M3pv2_N8P_3_065958（**manifest 头注明文 ZERO flight.bag=NO-RESULT 环境轮，如实注记** ✓）；base N8P_3_051012 有袋正常 |

- 与 T3 滚入计数对账：BX 目录 20/TK 目录 17 与 T3 combo added「BX20/TK17」逐位一致 ✓（T3 计目录数，本台账同口径并细分 DRY/r2）。
- 全部 100 OK 行 chunks 列 N/N 等值+messages>0+duration 合理：索引级完整性通过（注：awk 反引用 \1 不可用，MISMATCH 检验以人工核读+等值模式分布为准——见 §5 坑②）。

## 4. T2 判读件消费确认（六件 md5 锚）

| 件 | md5 | 消费确认 |
|---|---|---|
| 1b_bias_route/box_arm_verdict_v1.md | 2db067fb... | 与 T2 v10.10 收官行"文书 2db067fb"引用一致 ✓ |
| 1b_bias_route/box_pairs_v1010.csv | b4bf860b... | ②a 配对表 |
| 1b_bias_route/tlock_pairs_v1010.csv | c709dd6c... | ②b 配对表 |
| 1b_bias_route/tlock_pairs_v1010.csv.bak_banner_fix | d6210c74... | banner 修复前备份（T2 v10.7 banner=0×8 无效型勘误链留痕） |
| 1b_bias_route/bias_route_final_verdict_v1.md | 33020dc7... | 与 T2 收官行"bias 路线整体证伪定案 33020dc7"一致 ✓ |
| 1c_runs/bc_recovery_results.csv | de70a1b2... | **bc CSV alive 修复件**——T2 已修产物，本行即消费确认；【销号】"bc CSV alive 修复件消费"等待项 |
| 1c_runs/x7_convergence_material_v1010.md | f4b21500... | X7 素材包（@T3 交付件顺带在册） |

- E8P_A 销记确认：T2 v10.10 尾件"E8P_A 销记@T4"——cohort1 缺袋 run_WU_E8P_A_*（glob 0 命中）正式销记为不补飞（补飞证据链=WU_FIX_E8P_A{,_r2}+WU2_E8P_A_054552 承接）；v5.26 cohort1"未到货-缺失注记"行就此闭账。

## 5. 本夜新坑（入月报/台账坑账）

1. **bash 5.0.17 `local a="$1" b="$a/x"` 一行多赋值非左到右**：b 展开取**旧值**（实测 f() { local a="$1" b="$a/x"; }; f TESTVAL → b="[/x]"）。本夜首版收货脚本 38 行 NOBAG 假象根因（M3P 族 36 行 tilde stale+2 行侥幸暴露）；HAFIX/BX/TK 族"侥幸撞对"=循环变量 stale 值恰为绝对路径。修复=拆行赋值。同族于引用闭环 v1 的 tilde 缺陷（I5b 三源之三），本质相邻：**展开时序/展开域缺陷**。
2. **awk POSIX ERE 无反引用**：`\1` 回引匹配全假阳性（100 行 N/N 等值被判 MISMATCH=100）——等值校验用 `^([0-9]+)\/\1$` 在 awk 不可用，改 grep -P 或人工分布核读。
3. （工具链既知重申）rosbag info 的 chunks 在 compression 行 `[N/N chunks]` 格式，非 `chunks:` 前缀行——正则按前者写。

## 6. 今晚工程册新批滚动收（W-工程册飞行批窗）

- 截至 00:2x：T1ENG v11.40 飞行批（HAFIX 终验批 20 轮→A1 扩批 12 轮→②b 复验 8 对）**未发射**（vins_smoke_runs 无 10-10 20:00 后新 run 目录）；滚动收挂 W-工程册飞行批窗，批毕即按本台账口径续册登记。
