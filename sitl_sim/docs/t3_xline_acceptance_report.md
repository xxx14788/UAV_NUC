# T3 X 线验收全数据包（SKELETON v0.2 预填充版；2026-10-02 v8.3 单元 2.3 立 / 2026-10-03 v8.7 单元 1.3 注记）

> 状态：**骨架（已预填充段以【预填】标注）**——章节结构/图表脚本/残余风险模板就位；
> 未标注【预填】的 `[DATA:*]` 槽位=待填，禁止在 X 线轮未跑前预填任何数字（防跳步）。
> 填数时逐槽替换为实测+证据路径。
> 产出纪律（任务书 v7.4 X7 节）：五连飞逐轮四指标+双口径+特征数+锚差漂移+法证摘要；
> 统计口径=多轮置信区间；sim2real 差距声明；已知残余风险清单；**全部图表可由脚本再生**（§9）。

## 1. 验收范围与口径

- **主判口径**：在线为主判，回放为机理分析不作 gate（总设计师 2026-10-01 裁定，用户可推翻；红线 11）。
- **判决器**：`analysis/t3_wa_gate.py --online`（xline gate 层=四指标+J0 锚差+J0 修订口径
  raw==0 且 smj≤10+ENV-FAIL 硬证据；vins 域层=零 failure 零 reboot+Bas 三重口径+ATE 出生点对齐；
  **受控失败层 v1.1（2026-10-03 增）**=触发+恢复双证→PASS-CONTROLLED 计数态，判据=
  prereg v1.1 §2.6，selftest 三格全绿+U3PO 零漂移 @0d434030；回放模式零回归复验 PASS）。
  **受控失败层 v1.3（2026-10-04 增,池件③同步）**=L1 任一门拦截（用户 10-03 12:09 裁定②:
  legacy 与 cost 同等）+§2.6-h 误触发排除（真实事故证据三面）;判读器 **6fb9ccb4**
  （修正链 v1.1→v1.2→v1.3=prereg §7 三条目;runbook §9.1 凭据表正源）;X4 5/5 计数判定=
  x4judge v1.1（counting_pass/controlled.state 两键接线,4e02bddb,SYN_CTRL×5 模板电池）;
  18 样本 re-regression 判值面零漂移+U3″ 舰队表 v1.3 仅 035509 翻 controlled。逐轮表
  [DATA:*] 槽增受控层两列槽位:controlled_state 五态/counting_pass。
- **架构红线**：纯视觉（VINS 唯一位置源，R1-R6 同构）；zb 轴姿态判读；帧跳变测法双注明
  （帧间 |dp| vs 锚差）；J0 修订+出生点对齐（不对齐=+0.65m 级假误差）。
- **栈代一致性凭据**：[DATA: git HEAD + sim_stereo/*.yaml md5 快照（runbook §0.5）]
  【预填·流程与分水岭】凭据栈定案=**285278cc**（T2 20:40 U7 无害性三向互证成案，cf0384
  退役为标注史；分水岭 2026-10-01 20:35）。X 线每轮起飞前 §0.5 实读 md5 记台账；
  重放判读亦须登记 vins_node md5（T4 红线）。历史轮已核 42/42 world=sitl_world_obstacles。
- **解锁门凭据**：T2 U4 正式通告（STATUS 时戳 [DATA:]+U3 六轮统计表）＋
  U2 双签 `docs/t3_wa_fullregression.md`（[DATA: 双签时戳]）。
- **X4 tag 前置**：T1-E2 跳变修复落地凭据 [DATA: 提交链+在线验证轮]（2.45m 级跳变
  致 J0 FAIL 的轮，修复前不计入 5/5）。

## 2. X1' 验收轮（①同形）

- 判据：`vins_smoke.sh --tag X1final` 四指标全绿＋J0 修订口径（raw==0 且 smj≤10）＋出生点对齐。
- [DATA: 四指标行/j0_jump/fj_raw/fj_smj/vins 域面板一行判决（wa_gate_online.json）]
- 连败 2 轮即回挖不放宽的执行记录：[DATA]

## 3. X2 矩阵（①③④）与 X3 两段式（②⑤）

逐轮表（判决=`--online` 一行判决；特征数=T2diag track_med；锚差漂移=forensics
end_state.final_drift_prop_truth_m，--leg2 轮不重启 ATE 用锚差漂移替代）：

| 轮 | 命令 | 四指标 | 到位双口径(min_truth/min_vins) | p95 | 特征数 | 锚差漂移 | fj_raw/smj | 判决 | 证据路径 |
|---|---|---|---|---|---|---|---|---|---|
| ① | --tag X1final | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] |
| ③ | --tag X2g3 --goal 8 -1 1 | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] |
| ④ | --tag X2g4 --world sitl_world_obstacles_v2 --goal 8 -1 1 | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] |
| ② | --tag X3l2 --goal 7 -4 1 --leg2 1 0 1 | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] |
| ⑤ | --tag X3l5 --goal 7 -4 1 --leg2 0 0 1 | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] | [DATA] |

## 4. X4 五连飞与 tag sitl-v0.4

- 5/5 判定（legs 框架自动出，不手工数）：[DATA: 判决表]
- T1-D1 域轮清单（受跳变域影响，按 J0 判 FAIL 不计入 5/5 但计入回挖清单）：
  [DATA: 轮号+wa_gate t1d1_domain 标注]
- 环境性重试记录（每轮允许 1 次）：[DATA]
- tag 前检查单（runbook §6）：①5/5 台账行齐＋附件在档 [DATA]；②T2 STATUS 尾无未决异议
  [DATA: 查验时戳]；③T1-E2 修复落地 [DATA]；④git 干净+远端一致 [DATA]；⑤X6 收口件齐
  （README §3 并账：外参 z/est0/图像开关/odom_gate enabled/j0 口径/gyr_w；rviz 截图→
  vision_inputs；legs 重扫表）[DATA]。

## 5. X5 场景-通过率地图（参数精扫；X4 全绿后正式单元）

- 扫描轴（非红线参数；禁碰 acc_n/gyr_w/ext 等定案项）：目标点方向×距离网格（现状 5 目标
  集中两个象限）＋巡航速度剖面（0.5/0.75 两档）＋--leg2 组合；每 cell 双口径+分位数。
- 【预填·设计稿就位】`docs/xline_x5_grid_design_v1.md`（T3 v8.3 单元 2.2 产出）：
  基础网格=6 方向×3 距离×2 world 门档=36 位形+leg2 抽样 6=42 轮预算；紧凑模式 1.7G
  磁盘预算；优先级 1=E/S×8m×两 world（穿障对照）。速度剖面维度=到位门两档由 world
  选择承载（max_vel=0.5 红线参数不动）。
- [DATA: cell 矩阵表+通过率地图（fig6）+P3 首飞场景选择建议]

## 6. 统计口径（多轮置信区间）

- 到位指标（min_truth）：n=[DATA]，mean±[DATA]，CI95=[DATA]
- 跳变计数（fj_raw/fj_smj/j0_jump）：n=[DATA]，分布与 CI=[DATA]
- 样本充分性声明：n=5 的 CI 不足以支撑预判时按 T2 U3 统计扩容条款联动（触发判定记录 [DATA]）
- 【预填·对照组基线（U3′ 五轮+历史在线轮，供 §3 差值解读框架）】
  对照表=`docs/t3_xline_u3p_baseline.md`（T3 v8.3 单元 3 产出：ground/hover/obstacles/route×2
  五轮的到位/漂移/规划域画像+X 线差值解读框架）。历史轮到位分布与零翻转回归=
  `sitl_sim/t3_results/xline_histreg/summary.csv`（31 轮，world 全 obstacles→0.75 门）。

## 7. sim2real 差距声明

- 几何/内参链：引 T4-J3 六维基线表（E1 fx/FOV 双侧实测；σ̂=0 注入前实锤；P25 σ̂ 口径）
  ——[DATA: 表引用+差异陈述]
- IMU 噪声域：σ_w=0.069/0.071 两代一致（架构属性；gyr_w 0.0001 已回原仓库值=10× 超设
  修复，在线域定生死/回放域盲的判据分裂事实）
- 慢漂：0.468m/3min（纯视觉无回环架构属性）；10s 窗 SNR 4.6<10 → 0.1m/s 档
  T_detect=60s 泄漏上界 6.0m（Z1.2 验收口径）
- [DATA: 综合差距陈述（P3 首飞前必读）]
  【预填·草稿五条（任务书 v8.3 单元 2.3 素材单；成稿时并 T4-J3 表后定稿）】
  1. **GPS 盲区条**：SITL GPS 喂 EKF2 不关（X 线口径）；EKF2 无 GPS 行为的证明力归
     T1-E4 G-off 臂——本包差距声明只覆盖 VINS 闭环面，EKF2-GPS-off 域差距引用 T1 证据。
  2. **Z1.2 未接线**：odom_sanity_v2 门双轨已绿（flag-off 在 src/px4ctrl/），翻转权归
     T3-Z1.2（前置=T1-E1/0.5 分叉定案）；接线前 odom 毒输入防线=px4ctrl cmd 超时+D2 odom 门。
  3. **慢漂上界**：0.468m/3min 架构属性+泄漏上界 6.0m@60s（见 R4）；U3′ 实测 route 轮
     为**急性爆漂形态**（PR1 30s 冲 274m/PR2 虚构 42m 高，见 R3 规划域证据包）——
     慢漂上界仅适用于零事件窗，事件窗内上界失效。
  4. **EV 暂定不启用**：用户 Q1 裁决 2026-10-01（SITL/实机同构）；runbook §4 勘误稿
     EV_CTRL=0 参数级实锤；禁用侧残余风险=local_position 参考链无冗余（监控面，不吃控制主环）。
  5. **袋口径**：判读正源=帧包（原始 bag）优先；帧样/紧凑袋仅图像侧与审计面；
     X1final 原袋已删=特征重放永久不可行（T4 勘误在案）——X4 五轮原始袋保全至 X7
     （口径 22），处置按出稿后 @T4 流程。
  6. **【预填 v0.2·2026-10-03】受控失败分层语义条**：tag sitl-v0.4 的证明力语义＝
     "VINS 闭环+事故受控兜底"，**不含"零事故"承诺**；5/5 计数=「零 fail ∪ 受控失败」
     （受控=cost 门触发+reboot 后恢复跟踪双证，判据冻结=prereg v1.1 §2.6；触发-无恢复/
     未拦截/冻型=未受控 FAIL）。**诚实声明**：受控路径在存档中零正样本（U3pp A3=触发真实
     但恢复无证据+物理摔机，见 xline_dryrun_v11_report.md S1）——若 X4 五连飞全零触发，
     则"受控兜底"语义的证据力=空集，声明须降格为"受控路径已部署未实战"
     （判读器就位=干跑四样本全链验证，语义声明如实分层）。

## 8. 已知残余风险清单（模板；逐项：风险|证据|缓解/看门|状态）

| # | 风险 | 证据 | 缓解/看门 | 状态 |
|---|---|---|---|---|
| R1 | EKF2-EV 融合从未启用（EV_CTRL=0 全历史） | T1 E1-E1 三合一考古（v7_2026-09-30） | E-4 复现对（T1 P0-C.3 设计文档过审后排飞） | 开放 |
| R2 | Z1.2 odom_sanity_v2 未接线（v2 门双轨已绿未入 build） | docs/t3_z1_failsafe_design.md+odom_sanity_v2.{h,test} | X 线后 catkin 窗接线（与 T1-F3 通道 B 合并） | 计划中 |
| R3 | 环境脆弱（NUC 整机死亡模式；09-30 4 死） | T2 v5.0 卡点 6.2/T4-E 线归档 | runbook §4 ENV-FAIL 决策树+df 门+setsid+nohup | 开放 |
| R4 | VINS 慢漂泄漏（上界 6.0m@60s 检测窗） | E6 慢漂定标（σ_w 两代一致） | 到位判据用 min(窗口)（非末值）+E4 悬停预算重算（T1 P0-C2） | 开放 |
| R5 | WAOL5R 型单次 2.45m 跳变瞬态（T1-D1 域） | T2 C 线在线轮+U0 ulog 存活（层 2 取证可径行） | T1 P0-A 修复链+E2 发布侧防线（在线 PASS 已证） | 修复中 |
| R6 | 【预填 2026-10-02】failureDetection 无 P/V 量域检查（只查 bias/外参/td）→ 大发散零 fail 盲区 | T2 U3′ 五轮（22:08）：PR1 漂 274m/PR2 虚构 42m 全程零 fail | X 线判读 vins 域层加 Bas/ATE 面板交叉（wa_gate 已含）；修复面=用户裁定域（T2 v7.3 序） | 开放 |
| R7 | 【预填 2026-10-02】ego 主节点死亡后 traj_server 独活续发旧轨迹终点悬停（planner 无自检/无心跳面） | T3 R3 证据包（PR1：84.3s 后 traj_id 冻结+344.9s 新 goal 无反应；上游 #57/#85 同形态） | poscmd traj_id 冻结>60s=planner 死签名入判读注记（正源 round_result 频率门可捕获部分形态） | 开放 |
| R8 | 【预填 v0.2·2026-10-03】急冻族载体未隔离+cost 门对其零证据：T2 配对实验未发生（两臂抽两味=在线非确定性，inconclusive-for-pairing）；route 域在线爆率 4/4 跨夜跨栈而 cost 门 route 触发 0 次 | T2 U3pp 终判（c7a4750）+R2F 判别格（回放域不可判=红线 11 最强实例） | X 线 route 轮按 prereg v1.1 §2.6-e 冻结型边界条款执行（只能零 fail 段过门，受控路径不适用）；载体隔离回挖挂 R3 线 | 开放 |
| R9 | 【预填 v0.2·2026-10-03】受控路径（触发+恢复）存档零正样本+数据面三限（failure 后日志静默/紧凑袋 odom 结构性截断/prop 流不可作恢复证据） | xline_dryrun_v11_report.md S1/S3/S4/S5（A3=触发真实+恢复无证据+物理摔机三重取证；A1/A4 同族） | 判读器 L2 落袋侧求解器流+X 线全程袋（prereg §2.6/seam 三条冻结）；首个带触发的 X 线轮=首次实证，阈值不适配=新版本号 | 开放 |
| R10 | [DATA: 新增风险（X 线轮回挖中发现时追加，逐项带证据）] | | | |

## 9. 图表再生（全部脚本可再生；数据源=各轮 wa_gate_online.json+汇总 CSV）

- 生成器：`analysis/t3_xline_report_figs.py --csv <xline_wa_gate.csv> [--out-dir docs/figs]`
  （CSV 由 `t3_wa_gate.py --online --csv <csv> <run_dir>...` 批量产出）
- fig1 X 线逐轮判决面板（四指标+j0+vins 域行）；fig2 ATE 出生点对齐时间线；
  fig3 Bas/Bgs 时间线；fig4 帧跳变双口径分布；fig5 特征数（track_med）分布；
  fig6 X5 场景-通过率地图
- [DATA: 各 fig 插入+生成命令行记录]
  【预填·管线活性凭据 2026-10-02】历史 47 轮 dry-run 全链通：
  `t3_wa_gate.py --online --csv xline_hist_wagate_dryrun.csv run_*`（47 轮判读 47 非 PASS=历史
  基线符合预期）→ `t3_xline_report_figs.py --csv … --out-dir docs/figs_dryrun`（fig1/fig4 产出；
  fig2/3/5/6 依赖 X 线轮回填数据，生成器已标注回填期）。产物在 sitl_sim/docs/figs_dryrun/。

## 附：骨架→成稿检查单

- [ ] 所有 [DATA:*] 槽已替换为实测+证据路径（零预填）
- [ ] fig1-fig6 全部由脚本再生成功（命令行留档）
- [ ] 统计口径 n 与 CI 数字与 legs 框架输出一致
- [ ] 残余风险表逐项有证据链接；新增风险已编号
- [ ] 交叉引用刷新：runbook §/台账节号/STATUS 时戳（任务书守则：交叉引用同夜刷新）

## 10. [DATA:] 槽位审计注记（2026-10-03 02:0x；T3 v8.7 池件⑤；15 槽全分型）

| 分型 | 槽位 | 可预填判定 |
|---|---|---|
| 飞行依赖（X 轮产物） | §2/§3 四指标行·判决表·t1d1 清单·环境重试·§5 cell 矩阵/fig6·§6 n/CI 统计·§9 fig 插入记录 | 不可（防跳步红线） |
| 解锁依赖（U4/跳变修复时点） | §1 栈代快照·U2 双签时戳·T1-E2 提交链·tag 前查验时戳 | 不可（解锁时即填） |
| 收稿合成 | §7 综合差距陈述·表引用+差异陈述（J3 表在 docs/t4_j3_e1e2_evidence.md 可随时引,差异陈述半槽留收稿） | 半可（引用面留收稿并稿） |
| 发现驱动 | R10 新增风险 | 不可（回挖时追加） |

- **审计结论：当前无可合规预填项**——15 槽全部落在飞行/解锁/收稿/发现四类时点后；
本审计的作用=X7 回填期开局即有分型地图，防漏填（漏填检查=成稿检查单增一条「对照 §10 分型逐槽销号」）。

- **R9 风险状态更新（2026-10-03 03:3x）**：受控路径零正样本 → **一正（R5 机器验证 controlled，v1.2 判读器 4cb6acc7）**；数据面三限中日志静默已被 T2 A1 修复栈消除（diag_after_fire=True 实测）；其余两限（紧凑袋截断/prop 不可作恢复证据）维持。

### 槽位审计（2026-10-04 10:1x;池件 P10;零数字预填纪律核对=17/17 槽空置合规）

- 槽→数据源映射核对（v1.3-anchor2/x4judge v1.1 链下）：§1 凭据=prereg 头部栈槽已填 fixface-3（U4 03:48 值,起飞时 §0.5 实读复核）;§2/§5 逐轮槽=wa_gate_online.json 字段（含 controlled_state/counting_pass 两新列,03:0x 已增）;§4 5/5 表=x4judge v1.1 输出。
- **§1 X4 tag 前置③跳变修复面注解更新（2026-10-04）**：2.45m 级跳变族的修复面经 T1 04:36 判读+X 线暂停定案=T2 odometry 重锚面（2.6m 恒量族,家族 6 例在册;X1prime 2.594 为最新例）——原"T1-E2 跳变修复落地凭据"槽的填报时点=T2 重锚修复验证通告（X 线重启触发器①）。
- §6 X5 槽=X5 设计稿 v1.1（紧凑主模式+串行带图,池件 P4）。
