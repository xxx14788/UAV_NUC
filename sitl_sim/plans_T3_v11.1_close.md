# T3 任务书 v11.1 完成清账版 v2（四线第十八周期收官全量账；2026-10-10 20:0x 改写）

> 原执行版=plans/2026-10-09_T3_planner_vision_acceptance_v11.1.md（md5 966225b8，弃读存史）。
> 本件 v2=对 13:5x 首版清账的全量改写（用户指令）：补入 13:5x 后到货件的消费账（T1 HAFIX
> 复验批影子重判 20/20 闭合+终次滚入 459）——**v2 为现行，首版弃读**。
> 会话时间线：03:23 开工 → 13:5x 双必达首次收官 → 19:5x T1/T2 收官批到 → 20:0x 补消费+本件。
> 结构：A 完成了什么 / B 还没做什么 / C 卡点与阻塞（客观描述，不附方案）/ D 资产 / E 等待 / F 坑账。

## A. 完成了什么

### A.0 双必达判定（任务书保底条款核验）

| 保底项 | 结果 |
|---|---|
| ①STATUS 机制落地+四线通告+同步首例 | ✓（开工通告 03:3x；收工 HOME→repo cp+commit 双侧 md5 一致；T1 收官时按同机制镜像=机制被四线采纳首例） |
| ②锚点哨兵工具落地+selftest | ✓（v1.0；selftest 7/7；实战消费门 20261010 表三代全 PASS） |
| ③到货判读全出表 | ✓（scen0+r2 四袋全表；HAFIX 复验批=13:5x 时未到货如实注记→**20:0x 到货即消费闭合**；②a 到货即出表+②b 超额） |
| ④X7 收敛声明出稿 | ✓（注记五+附录 B/C+补记③+T2 素材包增补；f4e96bbd 基线零改动验证） |
| ⑤STATUS 诚实夜报+可做而未做清单 | ✓（13:5x 夜报行+本件 B/C 节） |
| **双必达**（机制两件 ∧ 判读全出表+X7） | **✓✓** |

### A.1 单元逐件账

**单元 0（开工收件+STATUS 机制）**：git 与 UAV_NUC 同步（behind=0/ahead=0；T1/T2 在途 M 行两件未触碰）；册部署三处 md5 966225b8；到货面勘定（实机九袋在盘+HAFIX/②a 批当时在途）；STATUS 双文件机制四线通告。

**单元 3（锚点哨兵，工具债消费升正式单元）**：t3_anchor_sentinel.py v1.0（c9312075）落地 repo analysis/。三类表签名识别（j0d/combo/threearm）+冻结锚点机械校验（j0d.j0_total=4.1185 HVNET1 锚/combo.j0=4.119 跨表互证/threearm MA 标本 j0_end 0.0143 vs maxjump 55.041=列语义探针+MB 标本 4.5462）；selftest 7/7（正例三表+列交换[C-6 事故复现]爆锚+值漂移爆锚+锚行缺失爆锚+表型未识别爆锚）。**实战用例**：combo 20261010 表三次再生（412/416/459）消费门全 PASS——判读器输出消费前机械防线建立。

**单元 1a/1b（实机袋判读）**：t3_realmachine_j0d_odom.py v1.0（e4103af7），九袋全表=realmachine_j0d_odom_20261010.{csv,md}（9371a963）。口径声明四条内嵌（静置袋 odom 流同构可比/动袋行程非漂移/jump 帧 0.1m sim 域反推/频率域注记）。判读：
- **r2 批四袋（判读正源）流形态全净**：njf=0×4+maxde≤0.0523m，与 R2_MANIFEST maxjump 逐袋互证 PASS（差≤0.0004m）。
- **scen0 静置净轮**：j0=3.5mm+零跳帧+**coh=0.0007 噪声抖动型 vs sim HVNET1 复刻 coh≈1.0 定向慢淋=方向一致度三数量级谱系分离**；窗差注记（袋 184.5s<T1 bias 病理第一周期发作 347s=未覆盖发作期）。
- **旧批四袋三型 USB 病理梯度**（判读禁用仅对照）：帧跳雪崩型（njf=2211/maxde=495m）+轻度帧跳型（njf=2/图像流 46.9Hz 异常）+断流型（odom<3 帧）。
- 判读面素材已交 @T1（《实机静态病理报告》统计侧并入——见 B-7）。

**单元 4（在线域 δ 分布）**：t3_online_delta_stats.py v1.0（04364025），17 袋全表=online_delta_stats_20261010.{csv,md}（c932878b）。**17/17 袋 δ≡0.000**（sim 含图像在线轮全集 13[全 FAIL 跳变族]+实机 r2 对照 4）：左右目 header.stamp 逐位相同，无一例进入 δc∈(3,4]ms 带或任何非零带——**跳变族的时戳配对条件在 sim 在线域天然全量成立（压死瀑布带最深端），时戳病理覆盖在线域=结构性证据闭合**；D435 δ=0 健康对照→病理主因=渲染时戳域本身非 δ 数值。绿组袋无图像=样本域开口如实注记（见 C-3）。

**单元 2（X7 收敛声明）**：docs/t3_xline_acceptance_report_X7.md（a9b610c2）追加 85 行纯尾部（git diff 零删改=f4e96bbd 追加制纪律验证）：
- 注记五=绿率归因线收敛声明（用户裁定兑现）：「渲染时戳域×估计器内部」双因子两支族框架+限定条款五条（绿组开口/D435 反例/下界口径/B-C 保持 open/T2 素材增补制）。
- 定量附录 B=饼图数据（t3_x7_pie_attribution.py aa77720c，combo 350×j0d 286 联算）：**失分 283/350 中跳变族 37.4pp+慢淋 transit 族 24.0pp=61.4pp 占失分 76.0%（下界）**；未分解 16.9pp=DRILL/诊断批非常规池主体。
- 定量附录 C=δ 分布（单元 4 产出入册）。
- 补记③=单元 1/4 产出落账。
- T2 素材包（x7_convergence_material_v1010.md md5 f4b21500）到货消费=增补段：全要素核对一致+增量两则入册（**δc 物理意义=双流配对窗时间域宽度 3-4ms；δ≥4ms"安全"语义=右目弃用[配对截断域]**）。

**单元 1d（T2 ②a 臂批）**：t3_bias2a_greenrate_table.py v1.1（48e1e364，②a/②b 双 schema 兼容），warmup_greenrate_bias2a_20261010.{csv,md}（f7d6e8ff）：
- **判负：A(box) 1/8=12.5% vs B 6/8=75.0% = −62.5pp**（判据 ≥+15pp 拒绝）+方向 2/8（单绿对 5/5 全 B 优；dir 2 对=jump-NA 代理非绿对证据如实降格）。
- 层① box 物理生效铁证：A 臂 indom_pct=100%×8（max_bas≤0.5366 压域）vs B 臂 51.8-99.9（max_bas 高至 7.1195 越域）。
- 层② transit dbadt 6/8 对改善=约束压制 bias 漂移速度但绿率反降（N8P_A/E12P_A 到位崩=误差转位置域吸收）。
- 层③ 预分类条款间边界如实（过紧型第二条款缺[tic0 全 0.0000]+机理负型措辞=无改善非反降）→归 T2 裁定。
- 与 T2 自判（box_arm_verdict_v1.0 2db067fb）交叉对照一致。

**单元 1d 超额（T2 ②b 臂批，②a 判负升级条款触发后到货）**：warmup_greenrate_bias2b_20261010.{csv,md}（e55aab72）：
- **判负：A(tlock W=10) 2/8=25.0% vs B 2/8=25.0% = 0.0pp**；方向 6/8 达标但双臂同绿率下无判读力（如实降格）。
- **层① 失效：tlock_banner=0×8/8 A 轮=锁未 ENGAGE**（预注册无效型——A 臂实质=第二 B 臂，本批不构成 ②b 机理检验）。
- **同夜基线大幅波动发现**：②a B 75.0% vs ②b B 25.0%（同夜同栈 vins_node md5 d198718f 全 32 轮一致）=**50pp 落差**；三批 B 臂 50%/75%/25% 全摆动（见 C-2）。
- 异常面：E12P_A RELEASE 谓词 300s budget 内未触发（窗 24.41→61.92）+S8P 对 indom 0.5%/5.1% 孤立。

**单元 1c（T1 HAFIX 复验批——13:5x 外因注记后 20:0x 到货消费闭合）**：
- 影子重判：t3_2d_hafix_rejudge --pattern run_DRILLD1_N8P_1[6-9]*（T1 复验批 20 轮 16:06-17:47+增量批 10 轮 18:40-19:22 全捕）→t2d_hafix_rejudge_20261010.{csv,md}。
- 交叉对照：t3_reverify_crosscheck.py（4a0d5c94）对 T1 终判正源（reverify_verdict_v1139.csv+ev_index.txt 场景映射）逐轮比对——**20/20 逐位一致**（hafix_lines/landed/prereg 判定三元组全吻合）；场景汇总同判（S1 0/5+S2 0/5+S3 0/5+S4 3/5）→ **3/20 NOT-PASS 同判**；产物=t2d_hafix_reverify_crosscheck_20261010.csv。
- T3 判读注记（判据面外的机理面，引 T1 账）：S1-S3 全轮悬停 z≈1.08m 未落地（ring4-6 未达）+KILL 双命令全 ACK ACCEPTED 但电机恒转（hafix_kill_dig_v1139.md=梯②③零效三层机理在 T1）；本轮 T3 面贡献=判读链独立性验证（双通道同判）。

**单元 1e（滚动入表）**：combo 三次再生 350→412→416→**459**（终态 0282a93d），每次对冻结基 350 **drifted=0/missing=0**；累计 added=109（DRILLD1 49[B:晨间干测 6+复验 20+增量 10+10-08 夜 13 迟到]/BX 20/TK 17/WU2 17[10-09 晨迟到]/A1OBS 4/WU 2）。文档化例外外科恢复×1 每代重放（run_X4_E12O j0d 三字段，E12O json 10-08 被背书冒烟覆写案——v10.9 纪律工具化=t3_surgical_recovery_e12o.py 6bfc5ec2）。j0d_stats_20261010（7336a88b）=286→286 **零漂移**（109 新轮无 j0_decomp 产物=客观注记，见 C-4）。滚入台账=expansion_20261010.md（81c461f1，含三代再生记录）。锚点哨兵门三代全 PASS。

**单元 5（尾件池）**：
- **B2 前基线转录**✓（m3_prebaseline_v1.csv ca4d4bdd：M3 v1.1 十八轮，源 m3_batch_report.csv 988af441；grid/round/j0/four_green 契约列齐+t2fail 源缺如实空+脏行 9 剔除注记；T2 已回执消费）。
- **bc CSV alive 伪影回执消费=PASS 销号**✓（11 行 0→1 逐位吻合+.bak_pre_alive_fix 在盘+批尾 t2_bc_alive_join.py 未来同口径）。
- **goal_adopted 归因面注记**✓（goal_adopted_attribution_note_20261010.md 0da6ce7e：协议层 W4-ADOPTED 7/7 修复闭环 vs 激励层 NOT-EFFECTIVE 两层分离——归因纯净度升级材料，@T2 消费）。
- **B6 provenance 三源列抽验**✓（t3_b6_provenance_spotcheck.py 4a0d5c94 同号注记：新旧分层 5+5 共 10/10 PASS，banner↔simvins.log 逐轮核+judge_site 恒 3090；触发条款=本次矩阵消费，v10.7 挂账件闭）。
- 池自补给≥3 维持（B3/B5/HAFIX 终验批影子重判一键在册）。

### A.2 git 账

四笔推送全绿：8bd17f1（中期件）→72888c4（②a 表+滚入）→ca3d4d3（收官件+STATUS 镜像；**裹挟 T2 staged 写码件 12 文件=共享树交错常态，已归属注记**）→a899d01（注记行+T2 一件）。本笔（v2 册+1c 闭合件+459 表）为第五笔。

## B. 还没做什么

1. **HAFIX 修复链终验级复验批的影子重判**（若 T1 下周期立项 20 轮级再复验）：工具一键就绪（--pattern+crosscheck 脚本在册）；当前状态=复验批 3/20 NOT-PASS 是二次修复前判定，二次修复后增量批 10/10 物理链通过（T1 账）——完整批级终验未跑（排程权在 T1）。
2. **②b banner=0 根因定位后的复验轮+W∈{5,20} 梯度轮判读面**：T2 侧定位（env 通路/谓词阈值/banner 发射三候选在 T2 写码域）；轮到即表（--label 参数化就绪）。
3. **B3 筛选批统计章**：nuc3 冻结阻塞（C-5），模板/对账/SOP 就绪态"只差轮次数据"沿 v10.7 册。
4. **B5 epsilon 带审计实跑**：低优池件（工具就绪未跑）。
5. **A1 observe 扩批**：授权在 T2/用户侧（T2 判 1/3 PASS="格子×时序敏感"形态+扩批条款挂池）。
6. **109 新轮 j0_decomp 补跑**：DRILLD1/BX/TK/WU2 等批轮 j0d 分型面空缺（C-4）；v10.6 批补跑先例在册。
7. **T1《实机静态病理报告》统计侧并入**：T1 的 v12 文件实为 v1.1 原文副本（grep 零 j0d/T3/coh 引用=未并入）；T3 素材（realmachine_j0d_odom MD §1/§2.2）已 04:1x 件行交付，改版动作在 T1 侧。
8. **绿组 δ 对照**：物理不可得（C-3），非动作项——录制政策变更后可解（政策面在 T1/T2 harness 设计）。

## C. 卡点与阻塞（客观描述；不附方案）

- **C-1 HAFIX 修复链的批级终验缺口**：复验批 20 轮（16:06-17:47）判 NOT-PASS 3/20——机理面（T1 kill_dig）：梯②③全链触发时序正确+KILL 双命令 412/413 次全 ACK ACCEPTED，但电机恒转/armed 恒 True/全轮悬停 z≈1.08m（S1-S3 ring4-6 未达）；二次修复（梯①盲降）后增量批 10/10 物理链通过，但该增量批=10 轮非 20 轮级、且场景覆盖面窄于复验批四场景。修复有效性的批级终验（≥20 轮四场景同口径再复验）不存在——判读链双通道已同判验证（T3 影子×T1 终判 20/20），缺的是飞行轮本身（排程权在 T1）。
- **C-2 同夜同栈基线绿率波动 50pp**：WU2 B 臂 4/8=50.0%（10-09 晨）→②a B 臂 6/8=75.0%（05:38-06:41）→②b B 臂 2/8=25.0%（07:0x-13:40），三批 B 臂全摆动；②a/②b 同夜同栈（vins_node md5 d198718f 全 32 轮逐位一致）仍 50pp 落差。观测事实：B 臂（无干预基线）的绿率波动幅度>臂间判据阈值（±15pp）三倍以上。受此约束：任何单夜臂对 ±15pp 级判读均存在夜态时间维度混杂；②a 的 −62.5pp 判负幅度大于波动面（判负结论本身稳），②b 的 0.0pp 与"同夜基线不可比"两种解释不可分离（本批判读力受限的根本原因）。该波动的时间尺度、触发因子（跳态夜/批间时段/场景顺序）当前无数据可分解。
- **C-3 sim 绿轮图像面为零**：全库含图像在线轮=13 个全 FAIL（绿轮袋不录图像：X5 批袋 50-60M 无图像 topic；X4 批四绿五轮袋已清理 NOBAG[10-01 处置]）。后果：在线域绿/跳 δ 对照（"绿轮是否也在 δ=0 域"）不可直读；δ=0→跳变的因果方向只完成必要条件面（跳轮全 δ=0）+实机反例（D435 δ=0 流净），充分性面无样本。录制政策（绿轮是否录图像）在 T1/T2 harness 设计域。
- **C-4 j0_decomp 产物通道单源**：该 json 仅 T1 标准 harness 产；今晚 109 新轮（T2 box/tlock 批脚本+T1 drill 变体+复验/增量批）轮目录均无此件——j0d 表冻结在 286，新轮的 jump/transit 分型、谱系族归属（跳变族/慢淋族/净轮）全部不可判；X7 饼图归因对新轮不可增量。批脚本是否内置 j0-decomp 步=harness 设计面（T1/T2 域）。
- **C-5 nuc3 冻结（用户裁定）**：B3 筛选统计章整体不触发；解冻=用户明示。
- **C-6 A1 observe 扩批授权悬置**：在 T2/用户侧；T3 无可推进面（判读工具就绪）。
- **C-7 ②b ENGAGE 未触发的根因不可判读**：批数据面仅有 banner 结果值（0×8）与 transit 窗时刻（t0/t1），无谓词内部状态（V 阈值穿越时刻/快照值/RELEASE 判定）日志——T3 判读只能到"无效型"粒度，三候选（env 通路/谓词首过阈值/banner 发射逻辑）不可分辨；定位需 T2 写码域日志或代码审。
- **C-8 实机域物理状态**：旧机（192.168.0.6）被用户断电+FC 一并断电（T1 10-09 22:58 登记）；下次实机窗前置=重起栈+FC 重探测+md5 抽验（T1 台账 2f/2c 件）。实机域后续动作（台架/录制）全部挂此。
- **C-9 共享 git 树交错提交**：本会话 ca3d4d3/a899d01 两笔裹挟 T2 已 staged 未 commit 件共 13 文件（内容无损已推+归属注记行）；机制原因=两线同树工作+git add/commit 时序窗重叠；对账成本客观存在（T2 已按注记对账）。

## D. 资产（md5 前 8 位记档）

| 件 | md5 | 说明 |
|---|---|---|
| analysis/t3_anchor_sentinel.py | c9312075 | 锚点哨兵 v1.0（selftest 7/7） |
| analysis/t3_realmachine_j0d_odom.py | e4103af7 | 实机袋 odom 流分解 |
| analysis/t3_online_delta_stats.py | 04364025 | δ 分布统计 |
| analysis/t3_bias2a_greenrate_table.py | 48e1e364 | ②a/②b 臂批统计面 v1.1 |
| analysis/t3_x7_pie_attribution.py | aa77720c | 饼图归因联算 |
| analysis/t3_b2_prebaseline.py | e91414c9 | B2 转录器 |
| analysis/t3_surgical_recovery_e12o.py | 6bfc5ec2 | 外科恢复重放器 |
| analysis/t3_b6_provenance_spotcheck.py | 4a0d5c94 | provenance 抽验 |
| analysis/t3_reverify_crosscheck.py | 4a0d5c94 | 复验批交叉对照 |
| t3_results/realmachine_j0d_odom_20261010.csv | 9371a963 | 九袋分解表 |
| t3_results/online_delta_stats_20261010.csv | c932878b | 17 袋 δ 表 |
| t3_results/warmup_greenrate_bias2a_20261010.csv | f7d6e8ff | ②a 统计面 |
| t3_results/warmup_greenrate_bias2b_20261010.csv | e55aab72 | ②b 统计面 |
| t3_results/combo_matrix_20261010_rounds.csv | 0282a93d | 459 轮终态（三代再生） |
| t3_results/j0d_stats_20261010.csv | 7336a88b | 286 零漂移 |
| t3_results/t2d_hafix_rejudge_20261010.{csv,md} | — | 影子重判（复验+增量批） |
| t3_results/t2d_hafix_reverify_crosscheck_20261010.csv | — | 20/20 交叉对照 |
| t3_results/m3_prebaseline_v1.csv | ca4d4bdd | B2 转录（源 988af441） |
| t3_results/expansion_20261010.md | 81c461f1 | 滚入台账 |
| t3_results/goal_adopted_attribution_note_20261010.md | 0da6ce7e | 归因面注记 |
| docs/t3_xline_acceptance_report_X7.md | a9b610c2 | 终稿+追加 85 行（基线 f4e96bbd 零改动） |
| plans_T3_v11.1_close.md | 本件 | 完成清账 v2 |

## E. 等待登记

- **W-T1**：HAFIX 终验级复验批（若立项）→影子重判一键+crosscheck；T1 报告 v1.2 统计侧真改版→销 B-7。
- **W-T2**：②b banner=0 根因回执+复验轮/W 梯度轮→判读面（--label 就绪）。
- **W-用户**：①A1 observe 扩批授权 ②nuc3 解冻 ③实机窗重开（FC/旧机重探测后）。
- 池（≥3 维持）：B5 epsilon 实跑/B3[冻结]/HAFIX 终验影子一键。

## F. 坑账（本会话三条+沿用一条）

1. **STATUS 时间标签纪律自违反×1**：多段长轮询累计耗时>会话主观时长，尾行时间戳错标（08:2x vs 实际 13:4x）——**每条 STATUS 行写入前必须 date 先行**；修正走 python（sed 中文坑规避）。
2. **pgrep 自匹配复发×1**：轮询命令自身含关键字被 pgrep -f 命中（在册坑家族第三例）——精确锚定（'^bash <script>' 全路径）解。
3. **STATUS 尾区显示层乱码误判**：Git Bash 终端把 UTF-8 正常字节显示为 GBK 乱码——**判别法=字节级 python 取证（decode+特征字节搜索），禁据显示层结论动文件**（本例文件本体干净零修复）。
4. 沿用：ssh 远端 git add/commit 前必查 staged 列（共享树裹挟 C-9；本会话两次实证）。
