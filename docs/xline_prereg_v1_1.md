# X 线判读预注册 v1.1（T3 任务书 v8.7 单元 1.1；2026-10-03 冻结）

> **预注册声明**：本文件在任何 X 线验收轮（X1'/X2/X3/X4 五连飞）起飞前冻结。
> 执行中不得改判据/阈值/脚本参数；若客观需要修改=新版本号（v1.2…）+理由入台账，
> 已飞轮不追溯重判。**v1.0（2026-10-02 冻结）从未被任何已飞 X 轮消费**——
> v1.1 在首飞前取代 v1.0 成为唯一在用预注册（v1.0 留存作谱系，勿删）。
> 版本动因=用户 2026-10-02 傍晚裁定②（受控失败分层）+总设计师 10-02 夜审边界条款
> +T3 单元 1 对 U3pp 存档证据的三重取证（见 §6 样本案卷，2026-10-03 01:3x @T2 通告）。
> 正源依赖：round_result.sh（场景名正源，e7120e0+hypot 修复 605bd26，v1.1 增 COSTGATE/FAILDET
> 标注行）+ t3_wa_gate.py --online（判读继承+受控失败层 v1.1）。
> 凭据栈：vins_node md5=____（**栈号留槽**：T2 U4 定稿通告即填；分水岭 10-01 20:35=285278cc，
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

**消费记录**：T2 R2F 判别格终局（2026-10-02 02:26：echo 污染修复后 G6 健康/G5 实害→视差门
撤出在线/gates 臂=纯 cost 门/死亡袋回放不可判）+U3pp 终判（04:10：gate 3/5、U4 未通告、
route 域 cost 门 0 触发、配对未发生=inconclusive-for-pairing）+T3 三重取证（本节）。
**结论链**：cost 门=触发面已证（A3）、恢复面存档零正样本、route/急冻域零触发
→ §2.6-e 边界条款与 §2.6-f 覆盖均有实证支点；受控路径在 X 线轮=首次真实检验。

## 7. 修正记录（冻结前并入，尚无 X 轮消费本预注册）

- **2026-10-03 02:0x（T2 01:45 预检格结论吸收；早于任何 X 线起飞）**：并入 §2.6-g
  起点窗约束 L1b。T2 预检格新证据：①PR2（route 急冻族袋）门判据保真回放 **FIRES
  @t=48.63s（ic=1728=26×med，连 9 帧>5 需求）早于 |P|>10m 爆窗标记（52.2s）3.6s**
  =门阈值对急冻族可达（回放域），配对实验 6 轮照跑；②A3 回放触发 t=46.96/ic=2026
  与在线逐位一致（门行为回放可达，形态判读仍在线独占）；③边界输入=门是**起点捕获者**，
  冻结尾 cost 平静（平滑谎言）→触发必落起点窗内才算受控。§2.6-e 边界条款的"急冻族
  受控路径不适用"维持（在线 route 触发仍为 0；回放可达≠在线已证，解冻权在配对实验
  结果+新版本号）。
