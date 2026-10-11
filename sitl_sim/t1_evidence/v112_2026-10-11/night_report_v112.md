# 软件收官合并册夜报 v1.0（2026-10-11 12:16-13:3x；第二十周期单册制；T1ENG）

## A 完成账

**双必达 ✓✓**：

1. **C-1 SITL 验证轮执行+判决文书落盘**——判决=**复现分支确认**（c1_verdict_v1.md 620aa07f）：run_C1_124411（同构建 d6f12ad1c4 与 08_24_40 实机轮逐位同 ver_sw）：1 单发+3 连发 cmd179(param1=0,param2=21196) **全部 ACK result=0**（from_external=0 target=(1,240)=Commander 亲答签名，mavlink 回声排除）∧ 注入窗 arming_state **零翻转**（全窗仅起飞 1→2@t+22.6/落地 2→1@t+253.2）∧ actuator_armed 注入窗恒 True ∧ 悬停维持（z 带 −0.62~−0.76 稳）∧ **注入窗 nav_state=100% OFFBOARD(14)**——与实机 failsafe LOITER(4) 态不同构仍复现 → **failsafe 态依赖否证+构建差异候选排除**，三运行时候选收窄至 ①uORB 订阅代际/②Commander 线程窗 二选；六维同构对照表（5 同 1 强）；附录 A 并入定位文书（48d6fb0e）。
2. **j0d/combo 滚入终版+X7 §5 增补落地**——终验批 20 轮 j0d 补产（wa_gate 无 ROS 环境静默假成功坑修复后 20/20 available=true）+A1X 12 轮随轮 → **j0d 398→430 精确命中**（分类加性：净轮 173→194/中漂 119→130/风暴 106 持平）；combo 459→499（+40=32 有效+8 attempt1 壳，全库口径如实注记）；X7 §5 两主族终数字行（63.8pp/80.1%=293 轮，002577d1，正文不动）。

**单元 0-8 全链**：

- 单元 0：开工收件（git 最新 c733962+catkin 绿态+孤儿守护 37 清零+六工具 md5 6/6[hafixsh 锚值勘误=git HEAD 三方一致 37524fb2；crosscheck HOME 旧版同步]）+旧机巡检（VINS 2h09m/odom 14.96Hz/五件全活/df 88%+统一模型第三数据点 **1.44GB/h**≤2.18 自洽）。
- 单元 2 δA：vins_smoke --img-record（独立 images_raw.bag+盘门 23G）+drill 层绿轮抽样（配额/计数/裁决三层）+批挂钩注记；**干测抓真 bug 两条**（grep -c rc=1 双行值/计数锚失配）修复+三态复测绿；无批窗→落码+干测收口（任务书允许）。
- 单元 3：S8P goal 污染预检落码（全程监听 goal_pollution_watch 057707b3+首发窗预检+cleanup；planner.log 面假阳性弃用/话题面实证 DRILLD1_005122 seq14/15 真 UTM 帧）+E8P/E12P 毒域溯源首步（56 轮盘点四发现+三级设计稿 519c58b9）。
- 单元 4：内存取证设计+**L0 零侵入基线执行**（smaps 双快照：段级归属=malloc 堆路径/主 arena 121.6MB+64MB 群；**快照 2 增量定案=新增段型**（23min 窗共同段增量仅 2MB/新增 15 段 918MB=arena 泛滥型，主 arena 膨胀假设否证）；量子 27-40KB/帧两态一致；L1 gdb/L2 牺牲实例窗条件注记待裁，45407d0f）。
- 单元 5：S4 时序重构（早退 LANDING 行根除[t1_landing_line.py 同口径补算+四调用点；真 bag 干测 z_end=0.105 landed=1 正则逐位匹配]+auto postgate[z 持久流→悬停基线→下降沿→中点注入+90s 兜底]；四判断干测绿；批 S4 行 auto 注记）。
- 单元 6：T4 三件全毕——滚动收货（台账 §10=65040f25：20/20 判读毕联动[verdict CSV 6a6864db/链表 3dee1859/判读器 01a12705 三锚全对]+A1X 12 袋索引收讫+本周期 10 件 md5 表）+锁 v3 生产观察结论（e29cb7d7：34 把锁三批窗**零接管零冲突零孤儿零残留** vs v2 时代 10-20min/次接管循环=形态完全消失+事故轮自清理实证+池件销号）+NUC 腿（月报 111→**117 条**[本周期 6 坑全工具链级]+六工具 NUC 对账 **6/6 全绿**）。
- 单元 7：T4 池三件（75 袋对照表[exact 39+prefix 36=75 全在册]/draft2verdicts selftest 独立重跑**抓真断言 bug 并修复 PASS**[自合成出处行污染凭据计数]/引用闭环 v3 方向稿 9029719f）。
- 单元 8：呈报件 §⑤ 预授权注记补入（fe00937b，含配套现场三件登记+C-1 加硬附证）+STATUS 收工镜像+本夜报。

**git**：c9a49bc（27 件主批）+f96dfc2（单元 5 四件）+收工笔（呈报件/d2v 修复/对照表/v3 稿/取证更新/月报镜像/夜报/STATUS 镜像）全推 UAV_NUC。

## B 《可做而未做清单》（诚实账）

1. **B5 epsilon 带审计实跑/B2 转录深度对照**：定义溯源失败（v1.0 工程合并册挂起节实体文件缺失，Windows/3090 双侧 find 未中）——列此待总设计师给指针后执行，瞎猜执行风险>价值。
2. **②b 层①窗内偏差度量工具**：定义部分可考（indom>95% 锁窗 bias 度量，bias_route_final_verdict L28）——输入面（tlock 批数据）在盘可做，但 bias 路线已整体证伪定案（v10.10），工具增量价值=证据面补充非改判——列池待裁。
3. **内存 L1（gdb attach）/L2（牺牲实例）**：窗条件在但按留活纪律/预算待用户裁定（非阻塞，L0 已收口段级归属）。
4. **E8P L1 复验轮**（毒域溯源次步）：需批窗+全探针——本周期无批窗（j0d=重放/工具直跑不占批窗），列下窗首件候选。
5. **锁 v3 hbloop 属主守护面独立单测重跑**：E1 21/21 已含 hbloop 相关面，独立重跑纯冗余验证——列池低优。
6. **引用闭环 v3 执行**：方向稿已落（9029719f），执行候 NUC relay 窗。

## C 卡点（客观）

1. 动力套修复+电池=用户域纯等待（预授权链就绪：最小动力验证→首飞窗，通知即动作）。
2. 实机物理面（kill 实机验证/完整怠速版/planner 执行面）随首飞窗解锁。
3. nuc3 冻结维持（B3 阻塞不变）。
4. 旧机 VINS 泄漏限窗（5h 保守窗 ~15:13 处置重启在途——本会话执行）。
5. 并行册形态注记：Windows plans 发现 v1.4 工程册+v5.33 T4 册（双册制草稿），本册=单册制现行权威（用户指令指定）；STATUS 无并行 agent 心跳，零撞活证据——如实注记。

## D 资产 md5 表（本周期新增/更新件）

| 资产 | md5 |
|---|---|
| C-1 判决文书（v112/c1_verify/c1_verdict_v1.md） | 620aa07f |
| C-1 定位文书附录 A 版（v11_40/unit4_c1_...） | 48d6fb0e |
| C-1 轮脚本/提取器 | b2251cf3/4af2cb8d |
| j0d 表 430（t3_results/j0d_stats_20261011.csv） | 5e4dbd7a |
| combo 表 499（combo_matrix_20261011_rounds.csv） | d86720de |
| X7 材料增补版 | 002577d1 |
| δA 三件（vins_smoke 594e3ce4→6b72df48/drill d687a10b→b9015058/批 4afb158c→51bd0d67） | 终态 6b72df48/b9015058/51bd0d67 |
| S8P 监听器（t1_goal_pollution_watch.py） | 057707b3 |
| LANDING 补算器（t1_landing_line.py） | c7cabe34 |
| 毒域溯源文书 | 519c58b9 |
| 内存取证文书（含快照 2 定案） | 45407d0f |
| T4 收货台账 §10 版 | 65040f25 |
| 锁 v3 生产观察结论 | e29cb7d7 |
| 月报 117 条版 | a1f002e3 |
| 75 袋对照表 | 见 t4_v531/75bag_cohort_crossref_v112.md |
| draft2verdicts 修复版 | 4268fe2f |
| 引用闭环 v3 方向稿 | 9029719f |
| 呈报件预授权注记版 | fe00937b |

## E 等待登记（移交）

- W-动力套修复通知（用户域）→预授权链启动（最小动力验证[用户在场 ~30min]→电池净面→首飞窗[现场三件=§⑤ 注记]）。
- W-旧机 VINS 5h 保守窗（~15:13）→处置重启（watch2 RESTART 行自动续采）。
- W-内存 L1/L2 窗条件（用户裁定/预算）。
- W-NUC relay 窗（引用闭环 v3 执行）。

## F 坑账（本周期新 6 条，已入月报 26-31）

1. PX4 logger logger_topics.txt 替换语义毁默认主题集（84KB 空壳 ulg）——配置回滚+禁用该路径。
2. grep -c 无匹配 rc=1 ×||echo 0 双行值——||true+空值兜底。
3. 计数锚与写入格式失配（^KEPT 恒 0）——锚定词置行首。
4. wa_gate 无 ROS 环境静默假成功（available=False rc=0）——j0d 首跑失收 12 轮。
5. mavros 订阅触发型流+瞬时 echo -n1 空采——持久后台流。
6. 数字签名 grep 命中 ROS 时间戳小数假阳性——字段前缀锚定。

（另：本日 ssh 中文 STATUS 行显示层乱码再现——文件内容验证正常，显示层≠文件坏坑既有在册。）

## 追加：E8P 毒域六轮连环战果（13:28-14:04，5h 窗等待间隙件→单元 3 L1+L2a 提前完成）

- **6/6 复现**（L1+L2A-E）+**假说 B 直证**：UTM 污染帧七帧实捕 (642719.x, 4671811.x)——watch 探针四代迭代至 v1.5（callerid 帧级）；
- **发布者节点定案=/mavros**（L2E `callerid:"/mavros"` 帧级实证）；harness 全清白链（参数逐字正常+seq 域+零重映射+world 零插件+api 插件二进制核）；插件级单查=下窗 30 秒件（rosnode info /mavros）；
- 机理链闭合：UTM goal→planner 1e6 目标→VINS 风暴（njf 138/109 族）→流断→STOPLOSS 2min 短轮——E8P 毒域谜题主链破案（域内污染源=goal 话题 mavros 桥），剩余=插件级定位+处置（拦截/重映射）；
- 「当夜耗尽」语义修正：毒域=当日活跃/跨日持续（本日全复现窗在案）；
- j0d 终滚 **436**（+6：中漂 133/风暴 109）+combo 505 数据行——md5 1876a9f8/c92bc3bf；
- 文书 unit3_toxic_domain_trace_v1.md §5-6（1e5ac6ab）；机器防线（watch v1.5+首发窗预检）自此默认在役。

## 追加 B 清单（E8P 战果衍生，14:3x 补）

7. **mavros 插件级定位+最小复现实验**：污染在场时 `rosnode info /mavros` advertise 面 30 秒件+裸 mavros 链最小复现（本窗嵌套引号 launch 失败如实注记，清场零残留）——下窗首件候选（连同拦截/重映射处置设计）。

## 终局补遗（16:0x-16:3x 用户督导续跑件——五件全清）

1. **E8P 毒域根除链**（上节 L2a 的完成态）：插件级定位终局=**guided_target**（extras 库符号级；mission/waypoint 两轮排除法）+修复三件（pluginlist 三黑名单/launch 包装/02 脚本 v2）+双验证（裸链 VERDICT=PASS advertise 消失；E8PFIX 整轮 watch **零污染帧** vs 修复前 7 帧）——**双层病理定案**：层1 污染已根除/S8P 间歇污染一并闭；层2 场景原生风暴（njf=270 无污染仍在）归 T2 δ 渲染时戳域。文书 f339ef2a。
2. **B5 epsilon 带审计=结案**：W/R 分支核对定**分支 W**（estimator.cpp printf %.4f/%.6f 写侧截断，二进制在案）；审计实跑 505 轮 **0/505 边界带（0.0%）**→按意见 §3 记录项关闭。
3. **B2 M3′ 前基线转录=毕**：m3_baseline_transcription_v1.csv（18 轮 grid/round/j0/four_green/t2fail+t2fail simvins 实查；四绿 6/18 与 M3 v1.1 史账一致；md5 c33f2e3b 记档）。
4. **引用闭环 v3 面①=执行**：v3 工具（2→12 固定文档面+自动近期族）扫描 46 源/287 refs/450 occ/present 197/dangling 1（锁瞬态预期）/missing 89（/tmp 易失+Windows 异机+瞬态三预期族，无 typo 型）；报告 closure_v3_scan_20261011.txt。
5. **锁 v3 hbloop 属主守护面单测=PASS**：三面（活 owner 心跳✓/非属主流拒✓/无 preclaim 强抢拒✓=防误抢保护在位）；首测"FAIL"定性=测例前提错（force 无凭被拒正是 v3 保护设计）。
