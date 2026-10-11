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

## 7. DFS δ 细扫增量收货（单元 3 件③补登，00:4x 实收）

- 六袋索引级登记（凭据=dfs_receipt_20261010.txt）：DFS_A_MA_d{2,3,4}_{r1,r2} 全 OK rc=0、chunks N/N 等值、duration 恒 5:54——**收讫-待判**（判读权=T2/T3 域）。v5.26 夜报遗留件就此收清。
- 观察注记（不判读）：d4_r1/d4_r2 size 与 messages 逐位同（43117229B/56451）——同场景确定性重跑形态候选，留判读者。
- 单元 3 三件全毕：75 袋 md5 补锚 ✓ + E4 cv2 重放 bitIdentical ✓ + DFS 细扫收货 ✓（超出'至少两件'下限）。

## 8. 坑账交叉引用（单元 6）

- 本台账 §5 两条 T4 新坑+第十八周期到货 23 条（T1 八+T2 六+T3 三+总设计师预录六）已全量并入月报增补节（pit_monthly_report_v526.md md5 bbbbb336，86→111 条下任基线）；月报镜像同步本目录（t4_v526_20261010/）。T2 锁 owner PID 坑（23 条之一）随单元 5 v3 根治闭环销号。

## 9. HAFIX 终验批滚动收（单元 4 §6，2026-10-11 上午收讫；批毕 02:59:33）

- 批=T1ENG v11.40 t1_hafix_finalverify_v1140（S1_hover_1m/S2_hover_3m/S3_transit/S4_land_1m ×r1-r5，00:35:20-02:59:33，POSTGATE 15/15/15/40）。
- 滚动收（凭据=finalverify_receipt_20261011.txt）：**20/20 final 轮全部 OK**（rosbag info rc=0、chunks N/N 等值、flight.bag 42-556MB）——**判读毕**（T4 v5.33 验收联动 15:4x：原"收讫-待判/判读器批毕未跑"状态推进，判读权=T1ENG 域已行使=v11.40 双工具 20/20 bit-identical，联动凭据详 §10.1）。
- 附加登记：8 个 attempt 无效/监控壳目录（NOBAG=env-only：hwmon 探针+round.log+vins_config.md5，无飞行）——S3 r1 attempt1（rc=2 HAFIX_lines=0）等重试链留痕，合理零袋。
- A1 扩批 12 轮=**已发射已收·判读毕**（a1x_receipt_20261011.txt 12/12+unit3_a1_expand_verdict_v1140.md ff1f82e4）；②b 复验 8 对=**取消**（②b 终裁定案 2b_contradiction_final_ruling_v1010.md 95ae856f）——T4 v5.33 验收联动 15:4x 状态推进（原"未发射"行），详 §10.1。
- 本会话 02:52-10:02 轮询空窗（约 7h，本机休眠/网络断=事故非收工）：批毕时刻在窗内，收讫时点=10:0x 补行（会话驻留纪律：外因断开重启首件=消费在途件产物+STATUS 补行——本节即补行）。

## 10. 滚动收·判读毕联动+本周期新产物（软件收官合并册单元6，2026-10-11 13:1x）

### 10.1 §9 状态联动：20/20 收讫-待判 → **判读毕**

- 判读产物收讫（md5 锚全对）：final_verdict_v1140.md（a8743e51）+ verdict_v1140.csv（**6a6864db=锚 ✓**，21 行=20 轮+头）+ 50 轮链表 hafix_chain50_table_v1140.md（**3dee1859=锚 ✓**）+ 判读器 t1_rejudge_hafix_v1140.py（**01a12705=锚 ✓**）——判读结论=S1-S3 全 15/15 PASS+S4 边界 2/2（判读权 T1ENG 域，结论面见其文书；本台账只登记判读毕状态）。
- §9 尾注两行状态更新：①「判读器批毕未跑」→已跑毕（v11.40 双工具 20/20 bit-identical）；②「A1 扩批 12 轮未发射」→**已发射已收**：A1X 12 袋索引级登记（凭据=a1x_receipt_20261011.txt，12/12 OK：chunks N/N 等值、duration 88-414s、bag 57-540MB）——判读毕（unit3_a1_expand_verdict_v1140.md，ff1f82e4）；②b 复验=取消（终裁定案，95ae856f 锚 ✓）。

### 10.2 本周期新产物滚动收（md5 锚表）

| 产物 | md5 | 域 |
|---|---|---|
| C-1 SITL 验证判决文书（c1_verdict_v1.md，复现分支确认） | 620aa07f | T1ENG |
| C-1 定位文书（附录 A 并入版） | 48d6fb0e | T1ENG |
| j0d 表 430 轮（j0d_stats_20261011.csv 滚入版） | 5e4dbd7a | T1ENG/T3 工具 |
| combo 表 499 轮（combo_matrix_20261011_rounds.csv） | d86720de | T3 工具 |
| X7 材料增补行版（x7_convergence_material_v1010.md） | 002577d1 | T2/T3 交接件 |
| δ 政策 A 落码件（vins_smoke/drill/批脚本 3 件） | 594e3ce4/d687a10b/4afb158c | T1ENG |
| S8P goal 污染监听器（t1_goal_pollution_watch.py） | 057707b3 | T1ENG |
| E8P/E12P 毒域溯源首步（unit3_toxic_domain_trace_v1.md） | 519c58b9 | T1ENG |
| 内存取证设计+L0 基线（unit4_memleak_forensics_design_v1.md） | f4008a4b | T1ENG |
| C-1 轮脚本+提取器（t1_c1_verify_v1.sh/t1_c1_extract_ulog.py） | b2251cf3/4af2cb8d | T1ENG |

- δ 政策 A 双用途注记：绿轮抽样图像袋（2 袋/批）落码毕——未来批窗首应用时袋到即收，E4 像素重放可直接复用（@T4 消费面在案）。
- 零三态口径维持：本节全部登记=索引级+md5 锚，无 T4 预注册判据面收货判读。

### 10.3 T4 v5.33 会话独立验收章（2026-10-11 15:3x；第二十周期 T4 执行会话，定位=独立验收工程册合并册代执件+补缺+收口）

- **终验批四件锚复核（逐位一致 ✓×4）**：final_verdict_v1140.md=a8743e51 / verdict_v1140.csv=6a6864db / hafix_chain50_table_v1140.md=3dee1859 / t1_rejudge_hafix_v1140.py=01a12705（~/sitl_sim 侧独立重测；判读器双位同值）——§10.1 锚全数复核通过。
- **A1X 实物抽验 ✓**：run_A1X_* 目录计数=12/12；a1x_receipt_20261011.txt 行格式（chunks N/N 等值）抽读一致；unit3_a1_expand_verdict_v1140.md=ff1f82e4 双位 ✓；②b 终裁 2b_contradiction_final_ruling_v1010.md=95ae856f 双位 ✓。
- **§10.2 抽验**：c1_verdict_v1.md=620aa07f ✓ / x7_convergence_material_v1010.md=002577d1 ✓（双位）；**j0d 锚换代注记：j0d_stats_20261011.csv 现 md5=1876a9f8（437 行=436 轮+头），§10.2 所记 5e4dbd7a 为 430 轮时点值，承 15:24 合并册收工行"j0d 430→终版 436"滚入，锚以 1876a9f8（终版）为准**。
- **六工具对账（v5.32 D 表锚口径，3090 双位）**：三判读工具 j3_image_metrics=3721399e / j3_fb_residual=08cb8829 / j3_feature_density=7f45974b 双位逐位一致 ✓；t4_ref_closure_v2=c3d233c5 权威位（catkin_ws analysis）✓；u3_hover_drift=628faa64（t1_evidence/v10）✓；sitl_lock.sh v3=d7b3efa0 双树 ✓；**draft2verdicts 换代注记：87593eb4→4268fe2f 双位**（承合并册 13:26 selftest 断言自污染修复，凭据 d2v_selftest_rerun_v112.txt，T4 抽读 [1]-[4] 全 OK ✓）。
- **锁 v3 文书验收通过**：lock_v3_production_conclusion_v1.md（t4_evidence 双位）——数据面 34 把锁（终验批 20+A1X 12+C-1 轮 2）零接管/零冲突/零孤儿/零残留，v2 时代 10-20min 接管循环对照谱在册，C-1 v1 事故轮失败路径自清理实证；其 §3.4 自认 hbloop 独立重跑未做，T4 本会话补做（§10.4）。
- **NUC 腿独立抽验 ✓**：ssh nuc md5sum analysis/j3_image_metrics.py=3721399e（承 13:09 六工具 6/6 的第三方复核）。
- **月报核验**：117 条基线确认（第二十周期 6 条=第 26-31 条，"111+6=117 条为下任并入基线"收尾行在册）；**"周期增补节模板 v1.1"缺空**（全文无并入规则模板节）——T4 本会话补做（月报新章+§10.5 注记）。
- 正本零触碰复核：verdicts 正本 docs/t4_verdicts_v2.md=4f34d500 复测一致 ✓；草稿 bd042be6 未动（主会话认领转录悬置维持）。

### 10.4 hbloop 属主守护面单测补做（T4 v5.33，2026-10-11 15:4x；销号合并册 B 清单"锁hbloop独立重跑"）

- 被测件=sitl_lock.sh v3 d7b3efa0（repo 权威位，零改动）；侧锁制（SITL_LOCK_FILE=/tmp/t4_hbloop_test_v533.lock，SITL_LOCK_SKIP_DISK_GATE=1 非飞行用途）。
- 四机制点 **8/8 PASS rc=0**：①get 显式 $$ owner 契约 ②heartbeat 阳性（匹配前缀 symlink mtime 刷新）③heartbeat 属主守卫阴性（非属主前缀 rc=1 拒代心跳+mtime 零改动）④hbloop 易主自退（易主后一个 300s 心跳周期内自退，新主 get/heartbeat 不受影响）。
- 凭据=hbloop_owner_guard_test_v533.md（本目录+Windows t4/v533_out/ 同步存档，md5 75528603 三方一致）；与 E1 v3 回归新例 7/7（hbloop 相关）互证=守护面双覆盖。
- v3.1 候选面：本轮测试未发现新缺陷，无候选项产生（守卫面维持 v3 原样）；锁 v3 文书 §3.4 未跑项就此闭合。

### 10.5 月报口径维护 v1.1（T4 v5.33，2026-10-11 15:5x；销号合并册 B 清单移交件"月报口径模板化"）

- 月报新增"周期增补节模板 v1.1"节（六条并入规则：节头节尾算术闭合/流水号+实证面+对冲/来源归属/去重复发/销号不删史/条数可加总校验）+第二十周期六条（第 26-31 条）逐条符合性验证=**全部合规**（节头节尾格式 ✓、111+6=117 算术闭合 ✓、六条实证面齐 ✓、归属 T1ENG 与 13:09 通告一致 ✓）。
- 月报文件换代：a1f002e3→**cfa5f41d**（双树同步；条目基线 117 不变，纯附录节追加）；文件内不写自身 md5（自指发散坑与 d2v selftest [5] 断言同族，T4 v5.33 当场抓获修正，入本会话坑账）。
- 销号：合并册 B 清单"月报口径维护 v1.1"移交件→销号（合并册 13:09 已并入 6 条但模板化未做，本件补齐规则面）。

### 10.6 池件验收毕+月报 T4 补录（T4 v5.33，2026-10-11 15:5x）

- **75 袋对照表独立复算=逐位一致 ✓**：exact=39+prefix=36=75、miss=0（未列 0），与 75bag_cohort_crossref_v112.md 断言及 COUNTS 尾行（C1=15/C2=16/C3=29/C4=12/C5=2/C7=1/TOTAL=75）三方吻合；复算脚本+三次自抓工具坑（ssh 控制流引号炸/sed 分隔符撞车/取字段方向反+尾注行混入）存 Windows t4/v533_out/bag75_indep_recount_v533.sh，坑账已按月报模板 v1.1 并入（#22 复发+新增 32/33/34）。
- **月报 T4 补录**：第二十周期追加 T4 小节（#22 复发注记+新增 32/33/34 三条）=基线 117→**120 条**；月报文件换代 cfa5f41d→**1a570555**（双树）。
- **池自补给 ≥3 维持**（在册五件）：①引用闭环 v3 执行（方向稿 9029719f 在册，候 NUC relay 窗）②内存 L1/L2 取证（L0 基线 f4008a4b，候牺牲实例窗/预算批）③E8P 插件级定位+最小复现（watch v1.5 在役，候批窗）④②b 层① indom 锁窗 bias 度量工具 ⑤B5/B2 定义溯源（v1.0 册挂起节实体缺失，如实维持）。本会话销号两件：合并册 B"锁hbloop独立重跑"（§10.4）、"月报口径模板化"（§10.5）。

### 10.7 滚动收·E8P 毒域根除链（合并册续行 16:19 通告；T4 v5.33 会话 16:2x 收）

- 插件级定位终局=guided_target（extras 库符号级实证；mission/waypoint 两轮排除+黑名单判 VERDICT=PASS advertise 面消失——判读权 T1ENG 域，本台账只登记收货面）。
- 根除链资产 md5 锚（T4 独立实测）：noMission pluginlist=**a0cdda9a** ✓（与通告逐位一致）/ mavros_nomission.launch=**47c66460** / 02_start_mavros.sh v2=**ead14328** ✓（与通告逐位一致；工作树 M 态=工程册在途件，T4 零触碰）。
- **W-R8PFIX 登记**：终验轮 run_E8PFIX_161914 发射中（16:19 发射，判据预注册=T1ENG 域：watch 零污染帧∧非 2min 短轮=毒域抢救成功）；袋落盘即索引级收讫-待判（rosbag info 凭据），判读权 T1ENG 域。
- 备注：本会话收工行（15:58）后新通告按滚动收语义续收（会话驻留①在途件禁收工），非中断重入。
