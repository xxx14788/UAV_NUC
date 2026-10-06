# T2 任务书 v9.9 — VINS 域深挖主战版·完成清账版（2026-10-06 晨重写稿；用户指令款：完成/未做/卡点客观无方案）

> 你是 **T2（VINS 质量线）**。执行域=3090（`ssh nuc2`）。本册=v9.8 七单元执行完毕后的完成清账版（重写稿，替代同日 04:35 初稿）。
> v9.8 弃读。Windows 权威=本文件；3090 备份=sitl_sim/plans_T2_v9.9.md（md5 双端一致）。
> 沿用红线：红线 1-24+banner 契约+双 md5+预注册先行+单机一路回放（与 T1 飞行批错峰）；等待协议 v2/自主推进/DECISION_LOG。

## A. 完成了什么（七单元清账；commit 链 623202c→122d7e5→0fd9bac→c3795f3→1c6ba5a→c51628f→f00d3bb，全部已推 origin/main）

### A1. 单元 1 — VRFY1 -nan 交互链解剖（C.1 核心）→ 已定案
- **五环交互链定位到组件级**（素材 run_VRFY1_023908 全量解析 164927 行 log）：
  ①根因=臂装载 sed `t2_cauchy_delta: 4.0→0.0` 静默未生效（arm_xline v1 无源值守卫）×`t2_vision_loss: 1` 保留 → estimator.cpp:1337-1339 `ceres::CauchyLoss(0)` → ρ(s)=0²·log(1+s/0²)=NaN（IEEE 0×∞）。与 T1 boot_diff_report §5 独立推导互证。
  ②INITIAL 求解 **111/111 次 init_cost=-nan 且 111/111 被后置门放行**（后置门只查 Ps/Vs/Rs 有限性；NaN 求解 iters=1 不更新状态=sane 假象；对照 VRG1 同位 11115.9→495.2 iters=9 健康）。
  ③marg prior 被视觉因子 loss-NaN jacobian 污染 → **1051 FAILURE 帧**（iters=0 term=2 init_cost=-1）与 ceres "Error in evaluating the ResidualBlock" dump **1051=1051 一一对应**（块形 13/14blk×76/82res=prior 形状）。
  ④**cost gate 假触发代数**：NaN 比较 false 使 streak 清零（IEEE），喂 streak 的是 -1 帧；t2_cost_hist 全 -1/-nan 时 median=-1，判据 `-1 > 10×(-1)=-10` 恒真 → 连续 5 个 FAILURE 帧即 reboot。**110/110 次 reboot 全此形态**（init→reboot gap p50=1.64s/min 0.10/max 5.97s）。
  ⑤reboot→重 init 自持循环 110 次；guard 侧 [T2RESUME] 恢复链（gap 1.9-63s）持续工作但不触及求解器层；staged 键结构性哑火（需 NON_LINEAR∧过 80s grace，段活不过 ~3s，rej=0 全程）。
- **口径勘定**：任务书"-nan×1066 行"=[T2slv] 含 -nan 955（phase1 844+phase0 111）+[T2OPT] -nan 111；两形态=`iters=1 term=0`×1066（NaN 求解）与 `iters=0 term=2`×1051（FAILURE）。
- **任务书三歧判决**：①staged 拒→饥饿→退化=否（rej=0；深度面与干净轮同脏 35.7% vs 28.5%，init_neg 非判别面）②cost 触发→reboot 竞态=因果倒置（cost 触发是假触发的果）③cauchy 缺失厚尾=否（反向：delta=0 直接 NaN，不经厚尾路径；RA13/14 cauchy=4.00 干净）。实因=第四条：毒配置半键 loss=1∧cauchy=0。
- **机器态降级**：boot-0"同键干净"支柱不成立（RA13/14 带 cauchy=4.0 非同键，T1 boot_diff §2 发现②）；全库 6/6 风暴轮=毒配置轮一一对应，无散例。
- **修复设计预案四件已写**（C1_verdict.md §5：参数域断言/init 后置门加 cost 检查/cost-median 退化守卫/prior NaN 防线）——**预案在册，本体未实施**（状态见 C-1）。
- 数据：t2_results/nan_dissect_vrfy1/（events 1624/slv 2006/gate 3157/diag/depth_sec CSV+summary+解析器+C1_verdict.md）。

### A2. 单元 3 — init 分布审计（A1 疑点）→ 已定案
- 双机全库普查（3090 143 轮+NUC 78 轮，去重 144 轮）：**init=确定性 ~10.6s 事件**（p50=10.6s，带宽 9.4-12.2s，零 >30s 轮）。任务书引例"3s[T2M0]/53s[手工]/102s[VRFY1]"三数均非 init finish 时间（T2M0 实测 1 次 init 正常）。
- **never-init 仅 3 轮且 3/3 环境级**：T2ZETACTRL（config 路径 FATAL）/WD1（无图像 IMU 输入流）/X1_223836（vins_node 未起）——全库零估计器 init 逻辑失败。
- multi-init 59 轮二分：毒配置风暴 6（init_n=35-216，与 C.1 一一对应）+环境型 53（route 空中重 init p50=2；BL never-flew 2-15；F3 瞬态 2-19）。
- **cauchy 拖慢收敛假说否证**：单次 init 轮 loss=0 vs loss=1+cauchy4 的 p50 差 0.1s（n=63/29）。
- 场景关联：gnd/hov 全部单次 init（地面视差不足/IMU 激励≈0 均不阻塞 stereo+IMU init）。
- **勘误 @T1（STATUS 04:16 已发，回执未收）**：DIAGCAUCHY_231757 非 never-init——init@9.55s 健康、求解器全程净（cost 2906→70，0NaN/0reboot），死因=中途 34.289m 帧跳变（瞬态发散类到位 FAIL）。T1 boot_diff_report §6 该行需更正，§7"栈代×cauchy4×boot confound"随之不存在（never-init 残线销案）。
- 数据：t2_results/init_census/（双机 TSV+普查脚本 init_census.sh+verdict）。

### A3. 单元 4+5 — transit 剂量定量化（B3）+ 92% 恒定之谜（A3 疑点）→ 已定案
- **92% 不复现**：全库去重 112 j0 轮，j0≥0.5 大漂移率 3090-native 48/57=**84%** vs NUC-native 44/55=**80%**（storm 排除 83%/79%；全库口径 81-82%）。机器×storm×阈值扫描无任何子口径到 92%。
- **机器改形态不改率定量支持**：extreme(≥10m) NUC 21/55=38% vs 3090 7/57=12%（3 倍）；large(2-10m) 反转 24% vs 53%；storm 8 轮跨双机=毒配置正交件。
- 臂维度：loss=0+c4 73% vs loss=1+c4 89%（16pp）——组间场景构成不均衡，**只登记 confound 面，不作因果结论**。
- 三角定论：率=任务结构定（gnd/hov→route 场景跳变 ~0%→80%）/形态=机器层定/臂键次级调制/毒配置=正交灾难件。
- **B3 剂量定量版**：Spearman 回归（非风暴轮）——gyr_peak 全轮 rho=+0.679、带内(j0<2) **+0.709**；acc_peak 0.599/0.366；goal 航程 0.249/0.349；时长 0.274/0.272。**剂量定义=gyr_peak 主成分+acc_peak 副成分**。
- **a=0.05-0.10 标度律重审**：带内 transit/goal 比值 p50=0.114/p10=0.016/p90=0.822（散布 50 倍），goal 归一拟合 R²=0.049——**判定为比值分布质心，非因果斜率**。
- 数据：t2_results/corpus_j0/（双机 corpus TSV+origin_map（config 路径判原生机）+goal_map+抽取器+verdict）。

### A4. 单元 2 — MACH8 带图袋回放+发作窗解剖（A4 疑点）→ 已定案
- 原轮求解器全程净（3765 帧 0NaN/0err/0reboot，track p50=122，init 1 次）——"静默"实证。
- **发作窗时间线**（T2diag 逐帧）：t=31.5-33 起飞 Bas 瞬态 0.005→0.570→回落；t=47-50 二次爬至 **0.72 锁死**；t=91-173 transit 积累（j0 分解 transit 3.67m=88% dominant）；t=173-383 **P 冻结 210s** 于错稳态 (7.18,-3.70,0.95)。
- **三候选判决**：窗口退化=否；偏置爆炸=**修正为偏置固化**（锁定 0.724 后零漂，爆炸路径与锁定后 P 冻结矛盾）；**transit 慢漂主导=定案**——bias-lock×transit 位移积分=稳态偏差，连续一致但错误（sane 发布门结构性盲，与"走爬带"同族）。
- **回放复现**：t=0-112.964/361 段（vins_node md5=b7de133d v4 栈登记，cfg=当轮臂），772 帧对齐 dP p50=0.218m/max=0.380m（多线程非确定带内），Bas 爬升+transit 轨迹同型——**输入确定性，非时序彩票**。
- **回放中断事实**：04:26 被 T1 X3l2a 起轮清残留杀于 t=112.964（STATUS 04:30 让路通告在案；私有 master 11312 隔离有效，双方轮/录制无损）。**冻结段（t=113-383）未回放**，本线以原轮 log 210s 冻结实证作等价豁免——该豁免是本线单方判断（状态见 C-3）。
- 修复面仅登记未动手：BAS-LOCK 读数入 j0d 扩展（T3 队列域）/transit 前 bias 约束（需预注册）。
- 数据：t2_results/mach8_onset/（verdict+原轮解析 CSV+回放 log+回放 odom bag force-add）。

### A5. 单元 7 — 归还件消费 → 已落账
- **BL7/MACH6 双列注记**：旧到位 0.467/0.673（轮正本 RESULT.txt，保全不改）vs L3 新口径 1.810/0.960（正源=T1 l3_recompute_v14_summary.md）；两轴均红，双列并存不静默改判；两轮同是 64-65m 帧中途跳变轮。
- **13 边缘轮红转绿裁定=登记注记，不追溯改判**（判据变更不追溯改判历史轮的预注册纪律）。
- **B2 时序彩票**：27 轮 probe_r3x 聚合（imu_jit/stampage×形态×机器）——同机器内各形态 p50/p99/max/age 全重叠不可分（clean/3090 max 21ms vs extreme/3090 20ms vs storm/3090 15ms）；机器差（NUC max 107ms）不与形态共变。**lockstep/回调顺序候选降级**；剩余候选=VINS 进程内非确定性（与 T1 v11.2 敌对态判决同向）。X7 §8 素材在册（unit27_verdict.md B4 节表）；**X7 文件本体未改**（跨线件，避免代改）。
- **B1 敌对态物理载体**：3090↔NUC 免密腿验证可用；BL 系轮目录无现成硬件遥测文件——**如实 open**（排除面=无现成文件；数据包=verdict；X7 条目素材=open+腿已建三件齐）。
- 悬停 8.5m 证据包：t2_results 未检索到实物，@T4 求指针（STATUS 04:32，回执未收）。W2 僵尸核对 PASS（04:29 快照仅 T1 飞行进程）。
- **池=3 在位**：MACH8 补全段回放（如索要）/B1 遥测考古/X5 网格剂量轴设计件。
- 狂飙占比并入单元 4（A3 已含 extreme 段）；A1 场景移植维持"X 线后"（X 线冻结中）。

### A6. 单元 6 — V2/净轮扩充与画像 → 已交付
- 净轮清单（j0<0.5∧0NaN）全库 20 轮，3090 原生 11（T2M0 0.090/MACH3 0.008 全库最低/VRG1 0.137/X2g3 0.092/VRFY2 0.100/RA5hover/RA12hov/RA14 0.493/DIAGGUARD2 0.418 等）。**V2 判定状态依 prereg 冻结口径维持"未过"（1/2）不变**，清单=候选池交付。
- **3090 敌对窗口存在性=排除**：storm 4/4 集中于 22-23 时段（毒配置飞行窗）；clean 轮散布 6/10 时段——无独立于配置/任务的敌对窗口（V2 前置降级件假设否证）。
- guard 画像：T2RESUME 全库仅 3 轮（恢复事件罕见）/E2uls 捕获数百-数千次常态/sane 门全库零触发（MACH8 型盲区再证）。
- 数据：t2_results/net_pool_v2/（verdict+guard_scan.tsv）。

## B. 还有什么没做（客观清单；阻塞指针指向 C 节）

1. **C.1 修复本体写码**——预案四件在册，未实施（←C-1）。
2. **T1 对照批 -nan 新样本并案扩行**——C.1 §6 矩阵扩行（预期 loss=1∧cauchy=0 必风暴）待新轮到货（←C-2）。
3. **MACH8 补全段回放（t=113-383）**——豁免在案但属本线单方判断，未经用户/对线复核；执行受回放互斥约束（←C-3）。
4. **B1 硬件遥测考古**——NUC 侧 bag 内 mavros/state 或系统日志扫描未做（←C-6）。
5. **X5 网格/温和剖面轮的剂量轴设计件**——未起草（应消费 A3"剂量=gyr_peak"结论；属预注册件，起草后待用户过目才能排飞）（←C-2/C-5 同类约束）。
6. **剂量面补检**——truth_z_max（爬升比候选）与方向变化率候选未检（←C-4）。
7. **A3 臂差 16pp 因果化**——不可达闭环（←C-5）。
8. **悬停 8.5m 证据包定位**——等 T4 指针回执（←C-7）。
9. **X7 §8 本体条目更新**——素材在册，文件未改（跨线件归属，未与本线确认改权）（←C-7）。
10. **V2 推进面其余要件**（ground 回归 RA18gnd 补测等，v9.6 册在案）——未消费（判读/飞轮依赖与 X 线冻结面交叠，←C-2/C-8）。

## C. 卡点与阻塞（客观描述面临的问题；不含方案）

**C-1 修复本体依赖用户过目裁决（流程性阻塞）**。客观状态：根因与五环链已定案（623202c），修复设计预案四件写在 C1_verdict.md §5；按挂起件纪律（任务书 v9.8 原文"修复本体等三歧定案+用户过目"），三歧定案文书已出但用户尚未过目/未裁定。另：预案 1（臂装载守卫）已由 T1 在 arm_xline.sh v2 实施（sed 源值守卫+loss=0 路径），但该守卫只覆盖 arm_xline 装载路径——canonical 直改/手工 yaml/其他装载路径下 `t2_vision_loss:1 ∧ t2_cauchy_delta:0` 组合仍可进入运行时（本册未对该面做穷尽审计）。

**C-2 上游依赖链未解锁**。三歧并案扩行材料=T1 F3 对照批新轮；T1 X4/对照批处于用户臂重裁冻结（W-X4arm-recheck，T1 v11.10/v11.13 在案）。依赖链=用户臂裁定→T1 批执行→新样本到货→本线扩行。本线无法单方面推进。同因波及：X5 网格设计件（排飞面同属用户过目+批互斥）、V2 推进要件中的飞轮项。

**C-3 回放与 T1 飞行批结构性互斥（技术性阻塞）**。本夜实锤：T1 轮脚本起轮时以 pgrep -f 'devel/lib/vins/vins_node' 全匹配清残留，**不区分 ROS master**，杀掉本线私有 master（11312）下合法运行的回放 vins_node（04:26 事故）。现行隔离手段仅流程性（STATUS 预告+错峰+起回放前 pgrep 预检），无双 master 技术隔离；在 T1 批活跃期，本线任何回放都有被杀风险。MACH8 补全段因此未完成（已录段恰好覆盖发作窗是偶然，不是可依赖的属性）。

**C-4 剂量面数据缺口**。①truth_z_max 提取覆盖 0/112——forensics_v2.json 的 end_state 内无该键（或键名与抽取器不符，end_state 实际键集未逐一对账）；爬升比剂量候选因此未检。②gyr/acc 面仅覆盖 42 轮（forensics_v2.json 在盘 45（3090）+29（NUC），非全库；多数老轮无 forensics 文件）。③方向变化率剂量需 bag 级重算，属大 IO 件受 C-3 约束。

**C-5 观察性数据的因果不可分**。臂维度 16pp 差（loss=0+c4 73% vs loss=1+c4 89%）与场景构成混杂：全库轮的臂键分配由历史战役决定，非随机化；带内/全轮任何分层都无法把臂键效应从场景效应中分离。因果化需要臂键随机化对照批——属 X 线判别轮域，且受 C-2 同类阻塞。

**C-6 B1 无现成数据源**。BL 系轮目录（3090+NUC）逐查无硬件遥测文件（无 CPU 温度/频率/负载类落盘）；硬件面对表的唯一可能来源=bag 内 mavros 主题或 NUC 系统日志（/var/log 类）考古——大 IO+只读考古性质，未执行。疑点状态如实=open。

**C-7 跨线回执未收（三件挂起）**。①@T1 DIAGCAUCHY 勘误（boot_diff §6/§7 需更正）——STATUS 04:16 已发，T1 未回（T1 批活跃中）；②@T4 悬停 8.5m 指针——STATUS 04:32 已求，未回；③@用户 过目三件（C.1 修复预案/对审 v1.4/X4 臂重裁材料归因修正）——全部未过目。X7 §8 条目更新也属此列（素材在册、改权未确认）。

**C-8 V2 判定推进的结构约束**。prereg 冻结口径下净轮池扩充不自动改变 V2 主判状态；V2 剩余要件（ground 回归补测等）需飞轮/判读窗，与 X 线冻结面（C-2）和回放互斥（C-3）交叠。

**C-9 判读素材的覆盖不均（历史性）**。全库 145 去重轮中：j0_decomp 覆盖 112、forensics 74、banner 键可读 ~135、无 log（NOLOG）17、config_file 行缺失 11。单元 4/5 的统计基数为覆盖子集（112/74），非全库普查——结论在覆盖子集内成立，子集外（老轮/短轮）无外推保证。

## D. 资产与等待登记

- **commit 链**（全部已推）：623202c（U1 C.1）/122d7e5（U3 init census）/0fd9bac（U4+5）/c3795f3（U2+7）/1c6ba5a（回放 bag force-add）/c51628f（U6）/f00d3bb（v9.9 初稿）。数据目录：t2_results/{nan_dissect_vrfy1, init_census, corpus_j0, mach8_onset, net_pool_v2}。
- **vins_node md5**：回放轮登记 b7de133d（devel v4 栈）；canonical config 飞行期被 T1 运行时覆写（现状 T1 域管理）。
- **等待登记**：W-T1 对照批样本（←C-2）/W-用户过目三件（←C-7）/W-T4 悬停 8.5m 指针（←C-7）/W-T1 DIAGCAUCHY 勘误回执（←C-7）/W-臂重裁（T1 域材料面含本册新增证：VRG1 干净归因=loss=0 臂非机器态）。
- **池（≥3 履行，当前 3）**：MACH8 补全段回放/B1 遥测考古/X5 剂量轴设计件。

## E. 新坑（本夜新增六条）

1. **回放起前必查 T1 批+被杀风险常在**：T1 起轮清残留=pgrep 全匹配杀 vins_node 不分 master（04:26 实锤）；错峰=STATUS 预告+pgrep 预检双保险，但批活跃期回放风险不可消除（技术性，见 C-3）。
2. **pkill -f 自匹配**：复合命令行含匹配串会杀自身 shell（后续命令全丢）——pkill 单独成行。
3. **forensics_v2.json 键名=小写**（imu/end_state，非 txt 报告的中文/大写）；end_state 内键集与直觉不符（truth_z_max 缺失，C-4）——抽取前先 dump 键。
4. **goal.txt 解析**：tr -d 去空白会粘连数字吞科学计数；必须 sed 前缀+空白 split。
5. **轮正本 RESULT.txt 不随 L3 重算更新**（正本保全）——到位新口径读数正源=T1 l3_recompute_v14_summary.md，消费走双列注记。
6. **census/抽取脚本参数约定**：NUC 侧跨机传参位置差异致输出文件名错乱——固定"无参=本机全库、末参=输出路径"约定（corpus_extract2.py 已按此）。
