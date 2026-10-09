# T3 任务书 v10.9 完成清账版 — 判读支持+目录收敛战役收官（2026-10-09；四线恢复）

> 你是 **T3（规划/场景验收+判读统计线）**。执行域=3090（`ssh nuc2`）。红线 1-29+判据器流程；等待协议 v2。
> **本版=v10.9 会话完成清账版**（原执行版弃读存史，md5 68cf08e3；本版落 Windows 权威+3090 双份）。
> **通用纪律（四条完整版，四册同源逐字）**：①等待任何在途件（批/链/build/采集/判读材料/IO 窗）禁结束会话——前台轮询（sleep 60 盯产物/STATUS/进程存活）保持在场；②轮询间隙=穿插件时间（禁空转也禁离场）；③会话收工唯一条件=任务书全部单元完成 ∧ 在途件全部毕且结果全部消费 ∧ 穷尽制三条件；④会话因外因（网络/token）断开=事故而非收工模式——重启首件=消费在途件产物+STATUS 补行+继续+默认案推进制；判据/门值零变动；nuc3 冻结。

## A. 完成账（双必达 ✓✓ + 全单元 + 等待面全消费）

**双必达**：①双 t3_results 目录收敛+生成器消歧落地（零漂移验证链）✓ ②X7 注记版四条正文+补记①②出稿 ✓

### A.1 单元 0 开工收尾 ✓
- STATUS 开工行；git 与 UAV_NUC 同步（behind=0/ahead=0；**远端名=UAV_NUC 非 origin**）；册部署三处 md5 68cf08e3 一致。
- 附带收敛：STATUS 双文件分叉 30 行（repo=HOME 严格前缀）同步归一。

### A.2 单元 1 目录收敛+生成器消歧 ✓（commit 352b031）
- **病灶勘定**：j0d 生成器 v2 OUT 硬编码 HOME 侧（双目录病源）；20261008 表实为临时改行（OUT+COMBO 联表双 sed）跑出=谱系不可追溯（实证：v2.1 联表默认保持 legacy 时重生成 drifted=111）。
- **v2→v2.1**：OUT 默认 repo 正源+argparse 化（--out-dir/--date/--combo/--version）+combo 联表自动取最新（自描述打印）+txt 头版本行；CSV 行逻辑零改动。
- **v1 退役归档** `analysis/retired_generators/`（README 谱系+禁跑）；combo_matrix→v1.1 加版本行。
- **两侧对账**：正源表 07/08 双侧 SAME；HOME 散件 10 件收录 `reconciled_home_strays_20261009/`（md5 10/10）+改前基线快照。
- **零漂移验证链**：正向=v2.1 复现 20261008 表 205 轮 drifted=0 PASS RC=0；反向=联表错配 drifted=111 HALT；护栏负例=单字段篡改 RC=1（此前观测 RC=0 系测试管道吃 RC 假象，工具无缺陷）。
- j0d_stats_20261009=收敛见证件（内容=20261008 复现）。

### A.3 单元 2 判读支持 ✓（commit da19fe4+7b22540）
- **新轮滚入**：combo **250→350**（+100：DRILL27/M3pv2 26/M3pbase 18/WU16/1aO-P 11/排除面 11）；加性校验两类文档化例外——补全型×5（run_M3RE12O_2，wa json 02:31 写入晚于旧表生成=迟到补全面）+外科恢复×3（run_X4_E12O，见 C.5）；j0d **205→286**（+81 纯加性 RC=0；81 袋 17.9GB nice19/ionice idle 批跑避让在途回放批）。
- **预热第一批统计面**：A 0/8 vs B 4/8=−50pp、方向 0/8、bias 收敛 8/8 NOT-CONVERGED → NOT-EFFECTIVE 与 T1 同判。
- **预热复验批统计面（07:05 到货即消费）**：A 1/8=12.5% vs B 4/8=50%=**−37.5pp**、方向 0/8 → **NOT-EFFECTIVE 维持**（两批 16 对同向；预热自伤面复触）。
- **三臂终判判读面**（双口径列；等 B/C 恢复批 05:13 毕后完整重跑）：**strong=0/weak=12/noop=23——C1 时戳配对（δ≥5ms）=唯一命中因子**；B（帧节奏四操作）+C（帧内容重绘）11 轮全 alive=1 且形态面全在 base_MA 瀑布带=全无作用；prefix-dryrun 残留轮（无 _bc_ 后缀）标记隔离。判读口径与 T2 终判表 v1.1 勘误（judge 第 4 列=maxjump；回放域「消除」操作化=瀑布消除）数值逐位同源。
- **2d HAFIX 统一重判读**（销 T1 C-9）：summary.txt=场景映射正源（4 场景×5 轮 20/20 对齐；批毕 23:14:31 后轮正确排除）；预注册判据（HAFIX≥1∧landed=1）下 **4/20 轮 PASS、零场景 5/5 → 批 NOT-PASS**（7 轮 ENV-FAIL 无判读面如实分栏）。
- **2d j0d 分型×悬停谱系**：有跳变病理的 5 轮**全=transit 慢淋主导族=与 sim 悬停自跳同族**（hover_lineage_v1 冻结口径）；净轮 9=odom 死亡≠跳变病理（两病理面分栏）。
- **口径边界**：3ARM 回放轮不入 combo/j0d（无 truth/键=smoke run）——独立判读面承担。

### A.4 单元 3 X7 注记 ✓（commit e3af799+7b22540）
- 四条正文（追加制，终稿 346 行基线 **f4e96bbd 零改动验证**）：三臂 δ 相变判决（含 δc∈(3,4]ms 细化引用+T2 v1.1 列语义勘误对齐）/预热终态条件式（复验落定=NOT-EFFECTIVE 维持）/emitter 零代价定案/实机静态三症状链联动补充。
- 补记①（B/C 终值）+补记②（复验落定+δ 细扫）。

### A.5 单元 4 尾件池 ✓（commit b8a0267）
- **B6 provenance 三源列抽验 PASS**：judge_site=3090 全 350/350（单源化维持）；3090/native 240+uav4 40 配对一致；?=70（旧表遗留 50+新滚入 20[全为无 RESULT 的 ENV-FAIL 轮，按 §2.1 冻结规则诚实归类，禁推定]）；nuc3 零轮。
- **epsilon 带审计双表实跑**：combo(350)与 j0d(286) 均 0 带轮 → **C.2 记录项关闭**；工具 0/%d 显示瑕疵顺手修复。

### A.6 收尾 ✓（commit 7b22540）
- STATUS 收官行+会话记忆+全推送。git 链：352b031→da19fe4→e3af799→b8a0267→7b22540（UAV_NUC main）。

## B. 剩余（未做/未毕，如实）

1. **实机静态病理实机袋 j0d 分解**：注记四的"漂"段同族性目前=SITL 域方向性证据（5 轮 transit 主导族），实机袋分解未做——袋源在实机侧（旧机/实机采集）。
2. **B2 前基线转录**（v10.7 遗留，T2 依赖件）：未动。
3. **B3 筛选统计章**（v10.7 遗留）：筛选期冻结维持，解冻依赖未变。
4. **bc_recovery_results.csv alive 列伪影修复**：@T2 已登记（正源=批尾统一判读器输出），T2 侧修复未回执。
5. **STATUS 双文件机制**：本会话手工双写维持双侧一致；长期机制（symlink 化等）未定，需四线共识。
6. **A1 observe 扩批**：T2 判 1/3 PASS="格子×时序敏感"形态+扩批条款挂池（当夜飞行窗余额耗尽）——扩批授权与排程在 T2/用户侧，非本线义务。
7. **WU2 复验批 goal_adopted 新列的机理归因**：A 臂全标 W2-RESTART 修复后到位仍 1/8+E12P 一例 W4-ADOPTED(stoploss)——goal 采纳面修复有效性归因未定（T2 v10.7 线产物，本线统计面如实呈现）。

## C. 卡点（客观描述，不附方案）

- **C.1 实机域阻塞链**：预热有效性终验依 prereg §3.4 SITL 外推性声明属实机台架域；实机侧状态=T1 v11.32 在册登记（旧机断电、FC 一并断电需重探测 ttyACM0、磁盘断电完整性待验）——实机窗开启条件不在本线。
- **C.2 2d 批 NOT-PASS 的根因层**：T1 v11.34 已定位批根因（cmd400 param1 未设=reboot+log-before-call+重启残留毒化下一轮）；判读面 4/20=含毒化轮的预注册口径如实读数；重跑批决策在 T1 侧，重跑前不可改判。
- **C.3 三臂终判后的归因线开口**：B/C 全无作用→在线跳变族主因不可由回放形态隔离（唯一命中 C1 只作用于回放特有瀑布分支）；在线主因候选的下一证据面（哪条线/什么实验）未定——臂 A 判决文本已注明"臂 B/C 判决价值上升"随 B/C 未产生收敛态而保持 open。
- **C.4 3ARM 回放域判读口径限制**：回放轮无 /gazebo/model_states truth——j0d 冻结口径（jump_prepost 双锚）在回放域无实现；只能以独立判读面（end-start+瀑布形态面）承担，两口径不可互换。
- **C.5 X4_E12O 判读源覆写（不可逆）**：wa_gate_online.json 于 10-08 02:30 被背书重跑器冒烟测试覆写（bag 已处置轮→内嵌 decomp 降级 False）；覆写前值仅存 combo_20261008 表三字段，源文件状态不可恢复（五绿轮 bag 处置边界+冒烟测试覆写行为的双因素）。
- **C.6 共享树在途改动**：t1_three_arm_campaign_v1131.sh / t2_tools/t2_bag_editor.py 两 M 文件=T1/T2 线在途，提交权在各自线；本线提交全程绕行未裹挟。
- **C.7 nuc3 冻结**（红线不变，零轮维持）。
- **C.8 预热两批 16 对同向 NOT-EFFECTIVE 后**：SITL 域内该激励实现形态（8s×10Hz goal 流）有效性证据面已穷尽——继续在 SITL 域重复该形态=无预期信息量（判据面事实，非决策）。

## D. 资产

- **新工具**（analysis/）：t3_warmup_greenrate_table.py（冻结判据逐字+bias 复用收敛器）/ t3_three_arm_verdict_view.py（双口径+双面归因+prefix-dryrun 隔离）/ t3_2d_hafix_rejudge.py（summary 场景映射正源）/ t3_2d_j0d_family_compare.py（谱系同族判读面）。
- **改造**：t3_j0d_stats_v2.py→v2.1 / t3_combo_matrix.py→v1.1 / t3_epsilon_band_audit.py 显示修复；**退役**：retired_generators/t3_j0d_stats_v1_retired.py+README。
- **新表**（t3_results/）：combo_matrix_20261009（350）/ j0d_stats_20261009（收敛见证）+20261009b（286）/ warmup_greenrate_batch1+batch2_goalfix_v107 / three_arm_verdict_view_20261009（终版）/ t2d_hafix_rejudge_20261009 / t2d_j0d_family_20261009。
- **文档**：dir_convergence_20261009.md / expansion_20261009.md / unit4_tail_20261009.md / reconciled_home_strays_20261009/（10 件+MANIFEST+基线快照）/ X7 注记+补记①②。
- **引用面**（他线产物，本线消费）：T2 三臂终判表 v1.1+δ 细扫判决 v1.0（δc∈(3,4]ms）+a1_observe 判决 v1.0 / T1 v11.34 night closure（2d 根因）。

## E. 等待登记

- **W-T2**：bc CSV alive 伪影修复回执（消费面口径确认：批尾统一判读器为正源）。
- **W-T1**：2d 毒化根因修复后的重跑批（若立项）→重判读工具一键重跑（--pattern/--summary 参数化就绪）。
- **W-用户**：①三臂终判终值+C1 唯一命中后的归因线走向（C.3）②A1 observe 扩批授权（T2 池条款）③STATUS 双文件长期机制裁定。
- **W-实机窗**（T1 侧 FC/旧机恢复后）：实机静态病理袋 j0d 分解请求→t3_j0d_family_compare 谱系面可直接复用。

## F. 坑账（本会话新增 6 条）

1. **bc CSV alive 列伪影**：恢复脚本记 alive=0 但轮目录 vins_alive.txt=1×11 全证——与 3d 批 grep 错文件同族（判读以直读轮目录的批尾统一判读器为正源）。
2. **背书重跑器冒烟测试覆写非目标轮 json**：bag 缺失轮被降级覆写（X4_E12O 实害）——冒烟测试触碰已处置轮=不可逆判读源损伤。
3. **管道吃 RC 复发**：`cmd | head; echo $?`=head 的退出码——退出码验证必须 `cmd > out; RC=$?` 两段式。
4. **ssh 复合命令 heredoc 引号冲突**：内嵌 python heredoc 与外层引号嵌套报 EOF——脚本文件走 scp 两段式，禁远端内联。
5. **时间格式两制**：summary.txt 时间带冒号（HH:MM:SS）vs 轮名时间戳无冒号（HHMMSS）——复用解析函数前必须核对格式（本会话实错一次）。
6. **T2 CSV tag 无时间戳**（WU_E12O_A 等）——run 目录匹配需 glob run_<tag>_* 容纳后缀。

---
*下任首件建议：按 E 节等待面轮询；到货件（复验/扩批/重跑批）均有一键工具就绪；无到货则 B.2/B.3 承接或按用户裁定的 C 节走向开新件。*
