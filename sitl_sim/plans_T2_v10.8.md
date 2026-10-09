# T2 任务书 v10.8 — v10.7 完成清账版（2026-10-09 08:5x；用户指令客观化款）

> 你是 **T2（VINS 质量线）**。执行域=3090（`ssh nuc2`）。红线 1-24+预注册先行。
> **本册=v10.7 战役完成清账**：A=完成账（证据指针）/B=剩余件/C=卡点客观（无方案）/D=资产/E=等待/F=坑账。v10.7 弃读。通用纪律（四册同源四条完整版）不变：①等待任何在途件禁结束会话+前台轮询 ②间隙穿插件 ③收工唯一条件=全部完成∧在途毕且消费∧穷尽三条件 ④外因断开=事故+重启首件=消费产物+补行+继续。nuc3 冻结。
> 台账=3090 `~/sitl_sim/t2_experiments.md`（2183 行）；产物=`t2_results/INPUTFACE/`。

## A. 完成账（v10.7 战役 2026-10-09 03:31-08:40，双必达 ✓✓）

- **A-1 单元 0**：night_chain 核查=23:20 完整毕（臂 A 26 轮判读在案/**臂 B/C 12 轮被旧编辑器[四 bug 修复前]误杀全 DRY-RUN FAIL=本夜补跑件/2d HAFIX rc=0/D5 rc=0/**P3 build rc=1=vins+px4ctrl 两包编译挂=T1 挂账**）；vins_node md5 84314cfe mtime 02:34 实核=未被 build 失败污染；窗口干净（零飞行进程/零锁/df 490G）；git b7e6166；册部署 md5 双端一致。
- **A-2 单元 1 goal 切换协议修复（干测 PASS）**：预注册先行 `INPUTFACE/goal_fix_prereg_v1.md`（4ac4b246，落码前冻结）；根因链=warmup 10Hz goal 流把 ego FSM 拖入 EXEC/REPLAN 自环永不回 WAIT_TARGET（标本 WU_E12O_A：尾点(0.14,-0.25,1.00) vel=0 悬停至 t=337s+FSM_LEFT_WAIT_TARGET=1+Triggered 20/97+ego_replan_fsm.cpp:158 非 WAIT 态走 REPLAN 侧路径）→案③提频重发被既有数据证伪排除（mission goal 16 发全灭）；落码=**W1 goal-silent 稳定门（20s 等 WAIT_TARGET 回转）+W2 重启兜底（复用 v11.17 starve 基建）+W4 采纳验证门（warmup_goal_adopted.txt）**，纯加性 2371B，WARMUP=0 路径逐字节不变（B 臂控制变量铁律）；干测 WU_FIX_E8P_A_r2 判定 PASS（G3 铁证=最终 planner INIT→WAIT_TARGET→Triggered!→GEN_NEW_TRAJ→EXEC_TRAJ+G4 位移=x 0.29→8.28 飞向 goal 9.01 vel 0.47；本轮 FAIL 根因=VINS 断流止损[E8P plain 毒域当夜发作]，goal 面正交）；批内 **W4-ADOPTED 7/7**（W2-RESTART 是承载路径：W1 自然回转 0/7）。
- **A-3 单元 3 三臂终判（双必达①）**：编辑器四 bug 修复版 dry 复验全过→B/C 补跑 12+1 轮（reorder r1 被编辑器第五 bug[dry-run 退出码未豁免 reorder 语义 mono-violations]误杀→当夜根修+补跑）；judge 事后重读全量：**臂 B 节奏四操作（drop3/drop10/down15/reorder 各×2）全瀑布带（maxjump 77.9-86.9+nj 1299-1861）=NO-EFFECT；臂 C 内容替换（center60/full）全瀑布（maxjump 69.2-83.2+nj 1650-1800）=NO-EFFECT**→排除法收敛=**唯一形态敏感因子=左右目时间戳配对**（臂 A δ 相变）；臂 C 消除未触发→场景改造立项条款关闭；MB 慢漂对照零作用维持；**终判表 v1.1** 落盘（`1c_runs/three_arm_final_verdict_v1.md` md5 ffee13f1，含列语义勘误+两口径注记）+judge_final_all.txt 42 行保全。T3 同夜独立判读同收敛（交叉验证一致）。
- **A-4 单元 2 预热复验批（双必达②）**：16 轮+2 env 重试（E12P_A+A1 r3 双目话题未现，1 次/轮条款内）8/8 对完整→**NOT-EFFECTIVE**（A[预热]绿率 12.5% vs B 50%，-37.5pp，方向一致 3/8<6/8，冻结判据套用）；goal 面 W4-ADOPTED 7/7 铁证前提下=**激励有效性本身干净证伪**；**v11.31"A 臂帧稳定反优"勘误=悬停混杂**（A 臂不导航=无跳变机会；修复后 A 臂到位 0.06-0.30 真导航）；新证据=**预热自伤**（A 臂 transit jump 劣于 B 4/7 数值对：S8O 1.400 vs 0.333/S8P 1.002 vs 0.142/N8P 1.308 vs 0.076/E12O 0.294 vs 0.095）；**失败分支当夜兑现=bias 约束②设计件+预注册冻结**（`1b_bias_route/bias_constraint2_design_v1.md` md5 c16f59c1：②a ceres box 物理域首案[±0.5 m/s²/±0.05 rad/s]+②b transit 相对锁备选[W∈{5,10,20} 冻结]+8 对臂判据同 2.3 口径+写码面 estimator.cpp L1429 已侦察）。预热三件套全谱：①FEED=NO_VALID_CARRIER（10-08）/②约束=设计冻结（本夜）/③预热=证伪（本夜）。
- **A-5 单元 4（池升格全消费）**：A1 observe 批 N8P 3+1 轮=**1/3 混合带=证据不足如实注记**（预注册分支逐字；机理方向性注记=两 FAIL 为自然跳变族当夜态+零拒帧结构性无 M3′ 饥饿链，判据面禁以机理替代判定；扩批条款挂池）；**δ 细扫 6 轮：δc∈(3,4]ms**（δ=3 双 rep 瀑布 74.7/80.3+nj 942/1299；δ=4 双 rep 与 δ≥5 族**逐位相同** 55.041@104.5+nj 11）→**机理翻案=H-pairing-threshold 优先于 H-td-online**（跨 δ∈{4,5,10,20} 逐位相同=门型签名；渐进吸收应呈 δ 依赖=未观测）——按预注册"δc 值本身是判别证据"条款如实翻案；实机注记=D435 硬同步流 δ=0 结构性处于配对域无共振路径+在线 td 估计域正交；判决文书 `delta_fine_scan_verdict_v1.md`（4d064051）+judge 数据保全。
- **A-6 收尾**：STATUS 夜报+《可做而未做清单》6 件全有理由（台账尾）；git **562bde3+72ced78 已推**（remote=UAV_NUC 非 origin）；台账 2183 行；飞行窗清场零残留（孤儿 watcher×5 全清）。
- **A-7 勘误账（两件）**：①**judge 列语义勘误**——正源列序=`tag,alive,j0_end,maxjump,jump_t,njumps`，终判表 v1.0 曾将第 4 列 maxjump 误标 j0_end（带判定全程同列对比=自洽，结论不变；v1.1 全修正+真 j0_end 列补齐[MB 标本 4.5-4.6 与在线 HVNET1 4.12m 互证=哨兵本可早触发]+预注册"消除=j0<1m"判据在回放域退化声明[基线瀑布轮 j0_end 0.011-0.030 自身<1m，操作化=瀑布消除 maxjump+nj 带=v11.31 口径]）；②读未完成 bag 假象——record 收尾中部分流（3488 条）读出 j0=0.0488 假终态，judge 全袋=84.194，**判读一律以批尾 judge 事后重读为唯一正源**（两次实录）。

## B. 剩余件（下周期）

- **B-1（钦定首件）约束②写码**：设计件+预注册已冻结（c16f59c1），任务书 v10.7 失败分支钦定"下周期即写码"——②a box 首案（estimator.cpp L1429 落点+parameters config 键 t2_bias_box 默认 0=原语义逐位同+T2 补丁模式沿 t2_iqg_observe 先例）→gtest→干测→8 对臂批（判据同 2.3 口径）；②b 仅在②a 批判负后开（不并行双侵入面）。
- **B-2 A1 observe 扩批**（池件）：N8P≥6 轮+E8P/S8O 各 3 轮，同夜同栈对照 base 臂；判据同 `a1_observe_prereg_v1.md`（冻结）；窗口富余时执行。
- **B-3 三臂第二标本**（可选，X7 素材域）：现全梯度仅 E8P 单标本（42 轮）；新标本=12GB/袋飞行窗新预算。
- **B-4 W2 就绪门时序余量观察件**：W2 重启后 25s 就绪门超时（planner 冷启动慢）→starve#1 二重启兜住（链路全通无功能缺陷）；仅时序余量观察，不构成缺陷不修（判据零变动纪律）。
- **B-5 X7 注记素材对接**（@T3）：δc 定量+H-pairing-threshold 翻案+预热证伪叙事+回放瀑布与实机相关性存疑注记——材料已在 `INPUTFACE/1c_runs/`。

## C. 卡点（客观状态，无方案）

- **C-1 P3 build rc=1 悬置（T1 挂账）**：vins+px4ctrl 两包编译失败（/tmp/p3_build.log 在案，T1 night_chain 尾段遗留）——约束②写码的编译窗与之互斥（编译吃 CPU 错峰纪律在册）；vins_node 现二进制未被污染（md5 84314cfe 实核）但**②写码需重编译 vins 包=编译环境当前处于红态**，根因在 T1 侧修复落地前，②的 build 验证步被阻塞。
- **C-2 bias 路线单点化**：三件套 ①③已死（NO_CARRIER/证伪），②是唯一活件——若②a②b 双判负，bias 路线整体证伪，绿率修复面收敛至现状（选格收窄 70.5%+止损件；架构级 transit 地板不修=回环不接入裁定在案）。此为结构性风险陈述，非方案。
- **C-3 A1 证据不足**：单格 3 轮 1/3 无法分辨"门计算零副作用"vs"格子×时序敏感"（两假设均与数据相容）；扩批依赖飞行窗余额（B-2 池件），无已知方法在不烧轮条件下破局。
- **C-4 E8P plain 毒域当夜态**：本夜干测轮+复验批多轮 VINS 断流止损（当夜发作率在案：干测 r1 NEVER-FLEW、r2/E8P 对/E12P 补轮均断流）——飞行批分母受跳变族当夜态影响；统计有效性依赖同夜同栈对照（复验批设计已内建），跨夜比较不可用（环境漂移在案）。
- **C-5 W1 路径 0/7**：warmup 毕后 FSM 自然回转 WAIT_TARGET 从未发生（7/7 走 W2 重启）=上游 FSM 状态机属性（EXEC/REPLAN 自环无回退转换）；harness 面只能重启兜底，上游偏离注记域。
- **C-6 判读器锚点校验缺失（工具债）**：judge 列语义勘误暴露的哨兵缺口——判读器输出消费前对已知在线锚点值（如 HVNET1 4.12m）的机械校验不存在；教训入册但工具级修复未做（属判读域资产，@T3 界面）。
- **C-7 git add 跨目录分叉**：`~/sitl_sim`（运行正源）与 `~/catkin_ws/sitl_sim`（git 检出镜像）实体并存，产物须 cp 同步后 add（本夜两次实录）；双副本守卫仅护 vins_smoke.sh 一件，其余文件无守卫。

## D. 资产（md5 对账表）

| 件 | 路径（3090 ~/sitl_sim/ 起） | md5 |
|---|---|---|
| goal 修复预注册 | t2_results/INPUTFACE/goal_fix_prereg_v1.md | 4ac4b246 |
| 约束②设计+预注册 | t2_results/INPUTFACE/1b_bias_route/bias_constraint2_design_v1.md | c16f59c1 |
| 三臂终判表 v1.1 | t2_results/INPUTFACE/1c_runs/three_arm_final_verdict_v1.md | ffee13f1 |
| δc 判决 | t2_results/INPUTFACE/1c_runs/delta_fine_scan_verdict_v1.md | 4d064051 |
| A1 执行预注册 | t2_results/INPUTFACE/a1_observe_prereg_v1.md | 4ca3330e |
| A1 判读 | t2_results/INPUTFACE/1c_runs/a1_observe_verdict_v1.md | 038d41f9 |
| vins_smoke.sh（含 W1-W4） | vins_smoke.sh（=镜像同步） | 758b02a0 |
| 复验批数据 | t2_results/INPUTFACE/1c_runs/warmup_pairs_v107.csv | — |
| B/C 判读正源 | t2_results/INPUTFACE/1c_runs/{bc_recovery_judge,judge_final_all,delta_fine_scan_judge}.txt | — |
| 臂 A 数据保全 | t2_results/INPUTFACE/1c_runs/armA_judge_nightchain.txt | — |
| 台账 | t2_experiments.md（2183 行） | — |
| git | 562bde3+72ced78（UAV_NUC main 已推） | — |

## E. 等待登记

- **W-T3 判读支持回执**：三臂终判/预热复验/δc/A1 四件判读材料在 `INPUTFACE/1c_runs/`（T3 同夜已独立判读三臂=同收敛，正式回执未至）。
- **W-T1 P3 修复**：C-1 编译红态（②写码 build 验证步前置）。
- **W-用户过目件**（DECISION 性质非阻塞）：预热证伪+预热自伤证据链；约束②设计件（含 box 域值 ±0.5/±0.05 冻结）；judge 列语义勘误波及的历史引用面。

## F. 坑账（本战役新增七条，台账详录）

1. pkill 模式串与目标文件同串=自匹配自杀（第 5/6 次实锤；规避=分步执行/PID 直杀）。
2. set -u 下 source ROS 爆 ROS_MASTER_URI 未绑定（四件套复发；脚本头 export 三件先行）。
3. 内联 git commit message 引号/括号翻车（规避=文件通道 `git commit -F`）。
4. 双副本守卫触发=runtime 与镜像不同步（补丁后必须 cp 双向同步）。
5. git add 跨正源/镜像分叉整体失败（产物 cp 进镜像再 add）。
6. 读未完成 bag 假象（record 收尾部分流；判读唯一正源=批尾 judge 重读）。
7. judge 列语义消费前锚点校验缺失（MB 4.5 vs 在线 4.12 矛盾=可用哨兵未用）。
