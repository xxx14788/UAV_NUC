# X 线判读预注册 v1.1（T3 任务书 v8.7 单元 1.1；2026-10-03 冻结）

> **现行版本 v1.4**（2026-10-05 晚；v1.1-v1.3 谱系见 §7。v1.4 增量=§2.8 双锚取稳+栈槽换代行）。

> **预注册声明**：本文件在任何 X 线验收轮（X1'/X2/X3/X4 五连飞）起飞前冻结。
> 执行中不得改判据/阈值/脚本参数；若客观需要修改=新版本号（v1.2…）+理由入台账，
> 已飞轮不追溯重判。**v1.0（2026-10-02 冻结）从未被任何已飞 X 轮消费**——
> v1.1 在首飞前取代 v1.0 成为唯一在用预注册（v1.0 留存作谱系，勿删）。
> 版本动因=用户 2026-10-02 傍晚裁定②（受控失败分层）+总设计师 10-02 夜审边界条款
> +T3 单元 1 对 U3pp 存档证据的三重取证（见 §6 样本案卷，2026-10-03 01:3x @T2 通告）。
> 正源依赖：round_result.sh（场景名正源，e7120e0+hypot 修复 605bd26，v1.1 增 COSTGATE/FAILDET
> 标注行）+ t3_wa_gate.py --online（判读继承+受控失败层 v1.1）。
> 凭据栈：**fixface-3 = lib e704431948c865cfe33f810f4a409f03 + vins_node 08a46d0adaa97b05886db782b3ff0405**(NUC 时代存档参照;zetafix-1 8574a00f/9b88345b 追认为其等价正源,D-1004-T2-01)
> **3090 执行域栈槽(v9.6 授权更新,2026-10-05)**:起始=build-2 系 **lib 8c3453c0 + node 2ad9676e**(含 W2BB src 诊断打印超集,行为≡zetafix-1 族,Designer 00:31 登记);后续代随 T2 换代填,X 线每轮起飞前 §0.5 实读双 md5 记台账(判据面零变动)
> **栈槽换代 2026-10-05（v11.7 单元 2 授权,T2 v9.5 终局交付,streamguard v4 正源追认随 DECISION_LOG D-1004-T2-01 同型流程[代持 T2 域]）**:现行=**streamguard v4 node b7de133d + lib 59548c6a**(存档 stack_archive/streamguard-1/,f1b1639;guard 臂=gates+guard,cauchy 不入正源维持;X 线/供给轮每轮起飞前 §0.5 实读双 md5 **+ [T2SGCFG] banner 自证**入凭据列,不符禁起飞;前置 build-2 系 8c3453c0/2ad9676e 系谱保留,判据面零变动)
> （**槽已填 2026-10-04 04:0x**：T2 U4 通告 03:48 值;X1prime 起飞时 §0.5 实读复核+台账;
> 分水岭链=285278cc(10-01 20:35)→fixface-2 1d7d2302/47d4308e→fixface-3[案A staged=1 n=80
> 默认入栈,[T2RFIXCFG] banner 自证]）。
> U3pp 在测栈=lib 5dde4d7e+node 86c5c6a3，X 线轮起飞前 §0.5 实读双 md5 记台账——lib+node 双件）。

## 1. 轮次位形表与 5/5 计数集（承 v1.0，零变动）

| 轮 | 命令 | world（实际生效） | 到位门 | 计入 5/5 |
|---|---|---|---|---|
| X1' | `vins_smoke.sh --tag X1final` | sitl_world_obstacles（默认） | **0.75** | ✓ |
| X2① | `vins_smoke.sh --tag X2g1 --goal 7 -4 1` | sitl_world_obstacles | 0.75 | ✓ |
| X2③ | `vins_smoke.sh --tag X2g3 --goal 8 -1 1` | sitl_world_obstacles | 0.75 | ✓ |
| X2④ | `vins_smoke.sh --tag X2g4 --world sitl_world_obstacles_v2 --goal 8 -1 1` | sitl_world_obstacles_v2 | 0.75 | **附加对照轮**（全绿要求同判，不入分母） |
| X3② | `vins_smoke.sh --tag X3l2a --goal 7 -4 1 --leg2 1 0 1` | sitl_world_obstacles | 0.75 | ✓ |
| X3⑤ | `vins_smoke.sh --tag X3l2b --goal 7 -4 1 --leg2 0 0 1` | sitl_world_obstacles | 0.75 | ✓ |

- **5/5 计数集 = {X1', X2①, X2③, X3②, X3⑤}**；X4 打 tag sitl-v0.4 前置：
  ①5/5 全绿（**零 fail ∪ 受控失败**，判定语义见 §2.6）②T1 跳变落地凭据或重估销案通告（K-2）。
  允许 1 环境性重试（ENV-FAIL 三签名，§2.4）。
- tag sitl-v0.4 证明力语义（X7 声明同步）＝"VINS 闭环+事故受控兜底"，不含"零事故"承诺。

## 2. 判据冻结（四指标双口径 + J0 + 出生点对齐 + 场景名到位门 + **受控失败分层**）

### 2.1-2.5 承 v1.0 全文有效（四指标/到位场景门 0.75(obstacles)/0.5(无障碍)/避障 0.349/poscmd≥50Hz/auto_disarm/J0 锚差恒门 0.5/J0 修订 raw==0 且 smj≤10/ENV 三签名/wa_gate 调用参数冻结），仅两处增注：
- J0 修订口径在**受控失败轮**的适配见 §2.6-c（中毒窗豁免，仅此一处，其余恒门不动）。
- round_result.sh 输出新增**纯标注行**（COSTGATE-FIRE/FAILDET，§3.2），不改任何判值。

### 2.6 受控失败分层（v1.1 核心；用户 10-02 裁定②落地）

**计数语义**：5/5 的"零 fail"要求由「**零 fail ∪ 受控失败**」满足；受控失败轮与零失败轮
同级计入 5/5。未拦截/未恢复=FAIL。到位门（场景名 0.75/0.5）与 J0 恒门 0.5**维持硬门不变**
（受控豁免仅作用于 VINS 域 fail 计数与 J0 修订的帧跳分母，见 c 项）。ENV 签名轮不算受控
（环境死≠受控失败，承 §2.4）。

**受控=触发+恢复双证（机器可判，签名冻结）**：

- **(a) 触发行 L1**：run 目录 simvins.log 含 ≥1 行匹配
  `cost gate: streak=\d+ over [\d.]+x short-window median, reboot`
  （A3 正型：`cost gate: streak=5 over 10.0x short-window median, reboot`）。
  登记：触发次数、首触发行 sim 时刻（WARN 头第二字段）、streak/倍率值。
- **(b) 恢复判据 L2（毒窗后三查，全部满足）**：
  - L2a **odom 复流**：/vins_estimator/odometry（求解器输出流，非 imu_propagate——后者
    无视觉也自由积分，不作跟踪证据）在 `[t_fire, t_fire+中毒窗上界]` 之后仍有消息：
    `[t_fire+pw, t_fire+pw+10s]` 窗内 ≥ **50** 条；
  - L2b **误差有界**：出生点对齐后，`[t_fire+pw, 轮末]` 段 odom-truth 误差 p95 ≤ **0.5 m**
    （J0 恒门同尺度；健康域实测 p50 0.03-0.05/p95 0.09-0.12）；
  - L2c **诊断复流**：simvins.log 在首触发行之后有 [T2diag] 行（求解器恢复出解）——
    **报告项不入判**（观测到 t2gates 栈 failure 后日志静默模式，见 §6- seam-1；入判面=L2a+L2b）。
- **(c) 中毒窗上界 pw = 10.0 s（冻结）**：自首触发行起算。窗内 odom 帧跳（|ΔP|>0.5）计为
  **reboot 对号跳变**（受控豁免）；**窗外帧跳必须 raw==0** 且全程 smj≤10（J0 修订的中毒窗适配，
  唯一豁免点）。pw 依据=门自身 streak 窗（W=20 帧≈2s）×5 裕量；存档零恢复正样本（§6），
  上界首版从严冻结，若 X 线轮出现恢复事件且 10s 不够=新版本号+理由，不追溯。
- **(d) 判定输出四态**（wa_gate --online `controlled` 块）：
  `controlled`（L1∧L2a∧L2b）/ `triggered-no-recovery`（L1∧¬(L2a∧L2b)）/ 
  `uncontrolled-fail`（无 L1 且有 [T2fail]/failure detection!/急性发散/流死任一）/
  `clean`（零 fail 零触发）。
- **(e) 冻结型边界条款（总设计师 10-02 夜审，写死防判读扯皮）**：**爆窗 cost 门未触发
  且无恢复证据的轮＝未受控 FAIL**。急冻/平滑谎言型（T2 R2F 格+U3pp 结论：route 域在线
  4/4 爆、cost 门 route 触发 0 次、判别格证实回放域不可判）在 v1.1 下**只能靠
  「零 fail 段+到位+J0」过门，受控路径不适用**。本条款与 T2 配对实验结果联动：
  配对若未来证明 cost 门对急冻族有效，仍需新版本号解冻。
- **(f) 触发-无再 init 型（v1.1 新增覆盖，源自 §6 A3/A1 取证）**：触发成立但 reboot 后
  无 motion/无视差→VINS 不再 init→流死（A1/A3 同型）→ L2 不满足 → **未受控 FAIL**。
  即：触发是必要条件不是充分条件，恢复证据不可省。
- **(g) 起点窗约束 L1b（修正记录 2026-10-03 02:0x 并入；T2 01:45 预检格输入吸收，
  见 §7 修正记录）**：**t_fire 必须落在起点窗内**——起点标记 t_onset=袋侧爆窗首证
  （首个 |ΔP|>0.5 帧跳 或 出生对齐 |odom-truth|>10m 急窗标记，取更早者）；判据=
  `t_fire ≤ t_onset + 5.0 s`（早于起点=早检好案，PR2 门回放实测 fire 早于 |P|>10m 3.6s；
  晚于起点 5s 以上=迟触发，按 triggered-no-recovery 处理不入受控）。无起点标记
  （无爆窗）时 L1b 空真。机理依据=T2 预检格：门=起点捕获者，冻结尾 cost 平静
  （平滑谎言）——迟触发不构成"事故兜底"证据。

### 2.7 判读禁吃清单（承 v1.0 §2.5/§5）
判读禁吃 /mavros/local_position（EKF2 融合链）；正源=truth+imu_propagate（到位双口径）+
odometry（受控层）。GPS 口径：SITL GPS 喂 EKF2 不关（EKF2 无 GPS 行为证明力归 T1-E4，X7 声明）。

### 2.8 双锚取稳到位锚（v1.4；2026-10-05 用户裁定案③落地；[T1 代持 T3 域]）

- **动因**：anchor 污染定案 22/22（goal+5s 动态窗 z 污染 +0.18~+0.71，BL5/BL2 xy 污染在 cauchy 栈）；X2g3 三口径 0.849/0.036/1.015——到位 FAIL 为量测伪影，物理到位已达成（ARRIVE_WATCH 0.099 佐证）。
- **双锚候选**（窗口与均值构造逐字沿用现行，保 bit-exact 复现）：
  - C_dyn = goal_ts→+5s 窗（round_result.sh:44-49 现行口径）；
  - C_sta = goal_ts−15s→−5s 窗（t3_anchor_batch_probe.py:31 口径，静态窗锚=库出生偏移带 22/22 位等价在册）；
  - F 兜底 = 首 truth@prop[0]−prop[0]（出生锚）。
- **稳态判据**（窗口级，xy+z 全维，评窗内配对差 truth_i−prop_i 的离散度；锚值构造仍用前 50 样本，评估窗预算 150）：逐轴 std≤0.03 ∧ IQR≤0.06；可用性 n≥50 ∧ 跨度≥0.4s。
- **取稳规则**：R1 双稳且 3D 锚差 gap≤0.15 → C_sta(AGREE)；R2 双稳且 gap>0.15 → C_sta+旗 DUAL-ANCHOR-DIVERGENT（低散系统性分歧=动态窗污染形态，X2g3 族）；R3 sta 稳 dyn 不稳/不可用 → C_sta；R4 仅 dyn 稳 → C_dyn+旗 STA-UNSTABLE；R5 双不稳 → F+旗 DUAL-ANCHOR-UNSTABLE（风暴轮；jump 面另行判 FAIL，定性不变）。
- **J0 末端锚=不同规**（按任务书 v11.7 授权由本预注册定）：末端无静止窗类比物+j0 为冻结净轮门构造成员+末端帧不稳已由 jump>0.5 覆盖；若出现“末端锚污染∧jump<0.5”实例回本条重开（待用户过目）。
- **门值零改动**：0.5/0.75/0.349/50Hz/jump0.5/j0<0.5 全部维持。历史全面重算=22 轮 survey+X 五轮+U3′/MACH/BL/RA 全库新旧双列；**预注册预期=唯一翻绿 X2g3**，其他任何 PASS/FAIL 翻转=停机复核。
- 定标与 selftest 三层（L1 R1-R5 合成用例含压线样本/L2 X 五轮 C_sta 与探针在册值逐位等/L3 全库重算回归）详见冻结底稿 t1_evidence/v11_7_2026-10-05/prereg_v14_dual_anchor_draft.md（NUC 袋定标：净窗 std≤0.007 vs 污染≥0.072；同意带 gap≤0.12 vs 分歧带≥0.18）。

## 3. 判读流水（每轮，锁窗内；v1.1 增 3.2/3.3）

1. 轮毕 vins_smoke.sh 自动跑 round_result.sh（参数与 §1 表逐字核对）；RESULT.txt 双源判读。
2. **新增标注行（round_result v1.1，纯标注不入判）**：扫描 `$EV/simvins.log` 输出
   `COSTGATE-FIRE n=<次数> first_t=<sim时刻> streak=<> ratio=<>`（无触发=不输出该行）
   与 `FAILDET n=<次数>`（[T2fail]/failure detection! 计数）；RESULT 判值逻辑零变动。
3. `python3 analysis/t3_wa_gate.py --online <run_dir>` → xline_pass/`controlled` 块/
   计数判定（§2.6）入台账；--leg2 轮附 --leg2 锚差漂移读数。
4. df 检查点：起飞前 >15G、轮毕记录 df；每轮重放登记 vins_node+lib 双 md5（T4 红线）。

## 4. 连败 2 轮回挖分支（承 v1.0 §4 + 受控轮新分支）

同型定义/触发后动作序列承 v1.0（冻结素材/tar 索引/md5/跳变型交 T1-D1/规划型跑
t3_r3_planner_domain.py/到位型分解规划段 vs 执行段/回挖不改 5/5 计数）。**新增**：
- **受控失败轮的回挖分支=查未受控分量**：①毒窗外帧跳清单（>0 项逐条定位）；
  ②触发前中毒预窗（px4ctrl D2 拒帧起 vs t_fire 差=A3 型 0.77s，与 prop 流 |p| 峰值）；
  ③reboot 后再 init 失败归因（无 motion 无视差=场景性；有 motion 仍不 init=栈域，@T2）。
- **triggered-no-recovery 型连败 2**（§2.6-f 型）：回挖主查"reboot 路径是否吞掉了可恢复性"
  （对照毒窗内 truth 运动幅——机体动而 VINS 不再 init=栈域问题移交 @T2）。

## 5. 已知坑对照（承 v1.0 §5 + v1.1 新增四条）

承 v1.0：vins_smoke 默认 goal/world/BUDGET 三坑/mavros 50Hz 顶/pkill 自匹配/goal 竞态/
判读禁吃 local_position/降采样硬链接/Aborted core 红线 29/每轮双 md5。新增：
- **seam-1 日志静默模式**：t2gates 栈 failureDetection 后 vins 节点 stdout 静默（A1/A3 实证，
  再 init 不打印、[T2gate] 不复现）——触发后恢复判读**只能走袋侧 odom 流**（L2a/L2b），
  勿依赖日志复流；L2c 降级为报告项的根因。
- **seam-2 紧凑袋证据边界**：U3pp 紧凑袋的 odom 流在故障点附近结构性终止（A1/A3/A4 皆
  ~30s 止，A4 健康 causing 亦然）——紧凑袋不可判"恢复"，X 线轮 flight.bag 全程录制无此问题，
  但受控层判读必须在**轮仍在飞**的窗口内取 L2a 样本（毒窗后 ≥50 条线在 X 线轮长=可满足）。
- **seam-3 两流分工**：px4ctrl 吃 imu_propagate（A3 拒帧证据在 prop 流），受控层恢复证据
  必须用 /vins_estimator/odometry（求解器流）；勿用 prop 判恢复（prop 无视觉自由积分）。
- **seam-4 栈号绑定**：cost 门打印格式属 t2gates 栈（lib 5dde4d7e 系）；若 X 线起飞时栈
  定稿≠该系（L1 行不存在），受控路径对该轮自动不适用（=零 fail 或 FAIL 二选一），
  判读器不得因缺行报错。

## 6. 样本案卷（v1.1 冻结前消费的预检格结论+三重取证；判读器 selftest 锚）

| 样本 | 任务书预期 | 存档证据机器判 | 判读器预期输出 | 备注 |
|---|---|---|---|---|
| U3pp A3（hover/gates, t2v3_hover_033842+u3pp_logs/A3） | 受控正样本 | 触发✓（sim47.024, streak5/10.0x）；恢复✗：odom 46.9 终止（触发前 0.1s，末 0.5s 五连跳 0.36-0.54m）、prop 毒至 99m 于 52.9 死、truth z 冲 2.47m→~60s 落地、armed 终 True、px4ctrl D2 46.25 起拒帧 851+（|p|至 67m+） | `triggered-no-recovery` | **T2 原判"reboot 恢复健康"证据不支持**（"err p95=0.094"实为触发前主导的全流统计）；触发面成立=cost 门真实检测实锤 |
| U3pp A1（route/gates, t2v3_route_035325+u3pp_logs/A1） | 未受控负样本 | 无 cost 行；legacy Bas 门 49.16s 拦（Bas=3.17）；odom 净但流 +29s 死；机体未起飞 | `uncontrolled-fail` | 与 T2 原判一致；§2.6-f 同型（无 motion 无视差不再 init） |
| U3pp A2（route/base, t2v3_route_034144, log 丢失） | 未受控负样本 | log 缺失（被覆盖）；袋侧 573 跳>0.5m、误差 max 546m、流 145.9s | `uncontrolled-fail`（log 缺失路径） | seam：log 同名覆盖债（T2 已登记编排教训）；X 线轮每轮独立 run 目录无此问题 |
| U3PO（vins_smoke_runs/run_U3PO_211438） | 零 fail 正样本 | 全程存活 359s/零 fail（T2/T4 双判） | `clean` + xline 原判不变 | 零漂移回归锚：v1.1 判读器对其 four/J0/vins 各判值必须与 v1.0 逐位一致 |
| **R5（T2 配对实验旗舰袋,t2v3_route_025706.bag,A1 修复栈,2026-10-03）** | （任务书后新增） | **controlled（v1.2）**=史上首个真受控正样本 | 触发@104.5 streak5/10x;onset 98.69;L2a 99 条;L2b p95 0.229m;diag 复流;毒窗 19/0;xline=FAIL(硬门不豁免实弹) | 首真样本驱动 v1.2 窗锚修正（§7）;T2 修复的恢复面获独立机器量化确认 |

**消费记录**：T2 R2F 判别格终局（2026-10-02 02:26：echo 污染修复后 G6 健康/G5 实害→视差门
撤出在线/gates 臂=纯 cost 门/死亡袋回放不可判）+U3pp 终判（04:10：gate 3/5、U4 未通告、
route 域 cost 门 0 触发、配对未发生=inconclusive-for-pairing）+T3 三重取证（本节）。
**结论链**：cost 门=触发面已证（A3）、恢复面存档零正样本、route/急冻域零触发
→ §2.6-e 边界条款与 §2.6-f 覆盖均有实证支点；受控路径在 X 线轮=首次真实检验。

## 7. 修正记录（冻结前并入，尚无 X 轮消费本预注册）

### v1.4（2026-10-05 晚冻结；[T1 代持 T3 域] 单元 3）
- 增 §2.8 双锚取稳到位锚（用户裁定案③落地）；栈槽换代行已由 v11.7 单元 2 增补（streamguard v4 b7de133d/59548c6a）。
- 判读器实施待 round_result.sh v1.4 改造（红线 24 全流程）+历史全面重算；本版冻结先于实施（判据未预注册不出 PASS-FAIL）。


- **2026-10-03 02:0x（T2 01:45 预检格结论吸收；早于任何 X 线起飞）**：并入 §2.6-g
  起点窗约束 L1b。T2 预检格新证据：①PR2（route 急冻族袋）门判据保真回放 **FIRES
  @t=48.63s（ic=1728=26×med，连 9 帧>5 需求）早于 |P|>10m 爆窗标记（52.2s）3.6s**
  =门阈值对急冻族可达（回放域），配对实验 6 轮照跑；②A3 回放触发 t=46.96/ic=2026
  与在线逐位一致（门行为回放可达，形态判读仍在线独占）；③边界输入=门是**起点捕获者**，
  冻结尾 cost 平静（平滑谎言）→触发必落起点窗内才算受控。§2.6-e 边界条款的"急冻族
  受控路径不适用"维持（在线 route 触发仍为 0；回放可达≠在线已证，解冻权在配对实验
  结果+新版本号）。

- **2026-10-03（X3 两段式轮与受控层互操作语义澄清；判据值零变动）**：①毒窗为**流级全局窗**
  （自首触发行起 [tf-1, tf+10]s，不分腿）——fire 落 leg1 或 leg2 均按全流计窗内外帧跳；
  ②fire 落 leg2 时：leg2 的腿末 3s 锚差漂移读数若落在毒窗内=对号豁免面（与 j0 修订 raw 同口径），
  窗外锚差漂移照判（X7 §3 表锚差漂移列加注毒窗标记）；③--leg2 轮的 counting 语义不变：
  受控豁免仅 VINS 域 fail 计数+J0 修订 raw 分账，leg2 到位门与 J0 锚差恒门不豁免；
  ④腿切分正源=goal 时戳（PR1 预演校准：leg1/leg2 切分与史实逐段对上，见
  analysis/t3_pr1_legs_preview_output.txt）。

- **2026-10-03 03:3x（v1.2 修正;R5 首真受控样本驱动;早于任何 X 线起飞）**:
  ①**毒窗锚点修正**:窗左界 fire-1.0 → **min(onset,fire)-1.0**——v1.1 的 fire-1 起窗
  隐含零检测延迟假设,R5 实测症状首跳 98.69s 先于触发 104.5s 达 5.8s(门自身 W20+N5
  streak+短窗中值构建的固有捕捉延迟),捕捉前症状跳 3 个被误计毒窗外;修正后窗内 19 跳
  (含捕捉前症状+4 次 reboot churn)/窗外 0=事件对号语义成立。
  ②**L1b 上界 5.0→10.0s**(对齐毒窗尺度):R5 捕捉延迟 5.81s 证伪 5.0s;SYN_LATE 反例
  (迟 50s)仍被拦=迟触发防线不变。
  ③**R5 终判(v1.2)**:state=**controlled**(L2a 复流 99≥50/L2b 恢复段自对齐 p95=0.229m/
  diag_after_fire=True=修复栈 failure 后诊断复流,旧栈静默模式已被 A1 修复消除);
  xline verdict=FAIL(four=0/1/1/0,到位真值 4.264m+J0 4.682m)=**硬门不豁免语义实弹验证**
  (受控只免 VINS 域 fail 计数)。R5=T2 配对实验旗舰袋(t2v3_route_025706.bag 23G,保全),
  判读产物=x11_dryrun_v11/R5_pairing_fix/。
  ④v1.1 判读器(ac1df603)对 R5 的 triggered-no-recovery 误判记录在案不抹除(过程账);
  v1.2 判读器=4cb6acc7,全套电池绿(在线 selftest 三格/SYN 正反例×5/边界例×3)。

- **2026-10-04 02:2x（v1.3 修正;用户 10-03 12:09 裁定②落地;早于任何 X 线起飞）**:
  ①**L1 触发面扩至任一门拦截**:cost 门行之外,legacy `failure detection!` 行同等作 L1
  触发行（裁定②"legacy 与 cost 同等"）;锚=任一门首触发时刻（033941 实证 legacy 49.376
  早于 cost 51.872 达 2.5s——v1.2 仅认 cost 首发会把毒窗整体右移）;毒窗/L1b/L2a/L2b
  全链以统一锚起算;`first_fire_t` 键保留=cost 首发口径（v1.2 兼容）。
  ②**§2.6-h 误触发排除（裁定②"误触发不算"的机器签名）**:触发取得 L1 资格须有真实事故
  证据,三面任一——(h-i)位姿面 onset 标记存在;(h-ii)首触发前 2s 内 [T2diag] |Bas|>1.0
  或 |Bgs|>0.5（A1 正型:fire@49.212 前 0.048s |Bas|=3.17;健康域锚=WAOL5R 0.981<1.0;
  Bgs 线=W4 前置门 0.5）;（h-iii)cost 行自带 ratio≥10x 门阈证据（§2.6-a 正型 10.0x）。
  三面皆无=误触发处置:不入受控,按 §2.6-d 既有映射（门行在=fail 面→uncontrolled-fail）。
  残余面如实登记:飞行中 spurious 触发若自造 >0.5m 再锚跳会伪造 (h-i)——防线=fixface-2
  门复位已根除 55.432 型（T2 V1:21 banner 零误触发）+L2a/L2b 仍须全过;X 线轮若现此
  形态=新版本号,不追溯。
  ③**U3″ 舰队表 v1.3 重跑（逐臂核对;ps_u3r_fleet_table_v13.txt;判值面 18 样本零漂移）**:
  6 clean 不变+035509 **controlled**（legacy@46.476 真触发双面证据[onset@51.36+diag 越线]/
  L2a 复流 96≥50/L2b p95=0.0755m/帧跳 3 个全部改判窗内）+032809/035800 →
  triggered-no-recovery（复流 100/98 过但 post_p95 68.3m/95.4m 被 L2b 拦=「落地恢复型」
  恢复到错处的机器量化;T2 12:09 ④"032809 留复跑轮统一裁不回溯"口径下受控路径机器答案
  =否）+033941 维持 TNR（锚前移 49.376,post_p95 791.9m 仍拦）+A1 → triggered-no-recovery
  （§2.6-f"触发-无再 init"原型态:v1.2 的 uncontrolled-fail 仅因 L1 限 cost 所致）。
  **预期核对=任务书 v9.3"仅 035509 翻 controlled"精确命中**。
  ④判读器 v1.3=**6fb9ccb4**（v1.2=4cb6acc7→.bak_v13_20261004 双备份;红线 24 全流程:
  补丁 8 处唯一命中+py_compile+三层验证=离线 selftest 绿+在线 4 格绿[含 X1_232055 期望
  合法更新 uncontrolled-fail→triggered-no-recovery:v1.3 下 legacy fire@134.332 为真触发
  →机器路径→L2 无恢复]+18 样本 re-regression 判值面逐位一致+SYN 电池 8 夹具 5 断言全绿
  [新增 SYN_LEG=任一门正型/SYN_FALSE=误触发负型/SYN_LEG_A1=触发-无恢复原型]）。
