# T2 任务书 v9.9 — VINS 域深挖主战版·完成清账版（2026-10-06 晨；用户指令款；v9.8 全单元清账）

> 你是 **T2（VINS 质量线）**。执行域=3090（`ssh nuc2`）。
> 本册=v9.8 七单元全部清账后的**完成清账版**（A 完成清账/B 剩余/C 卡点/D 资产/E 等待登记/F 新坑）。
> v9.8 弃读。Windows 权威=本文件;3090 备份=sitl_sim/plans_T2_v9.9.md（md5 双端一致）。

## A. 完成清账（七单元全绿;commit 链 623202c→122d7e5→0fd9bac→c3795f3→1c6ba5a→c51628f）

### A1. 单元 1 — VRFY1 -nan 交互链解剖（C.1 核心）→ 定案
- **五环交互链组件级全定位**: ①根因=臂 sed `cauchy 4.0→0.0`×`vision_loss=1` → `ceres::CauchyLoss(0)` → ρ(s)=0·log(∞)=**NaN 代数炸弹**（与 T1 boot_diff §5 独立推导互证）②INITIAL **111/111 次 cost=-nan 仍被后置门 111/111 放行**（门只查状态有限性,NaN 求解 iters=1 状态不动=sane 假象;VRG1 同位 11115.9→495.2 健康）③marg prior 被 loss-NaN jacobian 污染 → **1051 FAILURE 帧**（iters=0 term=2 init_cost=-1）与 ceres eval-error dump **1051=1051 一一对应**（13/14blk×76/82res=prior 形状）④**cost gate 假触发代数**: NaN 帧清零 streak（IEEE）,但 median 退化 -1 时 `-1>10×(-1)` 恒真 → 连续 5 FAILURE 帧即 reboot——**110 次 reboot 风暴全此形态**（init→reboot gap p50=1.64s）⑤reboot→重 init 自持循环; staged 键结构性哑火（需 NON_LINEAR>80s grace,段活不过 3s,rej=0 全程）。
- **"-nan×1066"口径勘定**=T2slv -nan 955（phase1 844+phase0 111）+T2OPT -nan 111。
- **三歧全判死**: ①staged 拒→饥饿 否（rej=0/深度面与干净轮同脏 35.7% vs 28.5%）②cost 触发→reboot 竞态 因果倒置 ③cauchy 缺失厚尾 否（反向:delta=0 直接 NaN,非厚尾路径）。实因=第四条毒配置半键。
- **机器态降级**: boot-0"同键干净"支柱不成立（RA13/14 带 cauchy=4 非同键）;机器态残线=never-init 线→已销案（见 A2）。
- **修复设计预案四件挂起待用户过目**（参数域断言/init 后置门加 cost 检查/cost-median 退化守卫/prior NaN 防线;①臂装载守卫 T1 v2 已做）。
- 数据: t2_results/nan_dissect_vrfy1/（events 1624/slv 2006/gate 3157 CSV+解析器）。

### A2. 单元 3 — init 分布审计（A1 疑点）→ 定案
- 全库去重 144 轮: init=**确定性 ~10.6s 事件**（p50=10.6,带宽 9.4-12.2,零 >30s 轮）;任务书 3s/53s/102s 引例均非 init finish 口径。
- never-init 3/3=环境级（config 路径 FATAL/无图像 IMU 流/节点未起）——**全库零估计器 init 逻辑失败**。
- multi-init 59=毒配置风暴 6/6（与 C.1 一一对应,init_n=35-216）+环境型 53（route 空中重 init p50=2 常态;BL never-flew 2-15;F3 瞬态 2-19）。
- **cauchy 拖慢收敛假说否证**（loss=0 vs loss=1+c4 init p50 差 0.1s,n=63/29）。
- 地面视差/IMU 激励非 init 障碍（gnd/hov 全一次过;stereo 深度独立于运动视差）。
- **勘误 @T1: DIAGCAUCHY 非 never-init**——init@9.55s 健康+求解器全程净（cost 2906→70,0NaN/0reboot）,死因=中途 34.289m 帧跳变（瞬态发散类）;boot_diff §6 该行待更正,§7 栈代×cauchy4×boot confound 随之不存在。
- 数据: t2_results/init_census/（双机 TSV+普查脚本）。

### A3. 单元 4+5 — transit 剂量定量版（B3）+ 92% 恒定之谜（A3 疑点）→ 定案
- **92% 不复现**: 真恒定量=**80-84% 带**（3090-native 84% vs NUC-native 80%,storm 排除 83/79;全库口径 81-82%）。
- **机器改形态不改率定量支持**: extreme≥10m NUC 38% vs 3090 12%（3 倍）,large 2-10m 反转 24%/53%;storm 8 轮=毒配置正交件。
- 臂维度: loss=0+c4 73% vs loss=1+c4 89%（16pp）——**confound 面如实注记,不作因果结论**。
- **三角定论: 率=任务结构定（场景跳变~0→80%）/形态=机器层定/臂键次级调制/毒配置=正交灾难件**。
- **B3 剂量定量版: gyr_peak 主导**（带内 rho=+0.709,全轮 0.679;acc_peak 副之 0.60/0.37;goal 航程/时长弱 0.25-0.35）——**X5 网格/温和剖面轮剂量轴建议换 gyr_peak**。
- **a=0.05-0.10 标度律重审=比值分布质心非因果斜率**（p50=0.114,散布 50 倍 p10-p90=0.016-0.822,goal 拟合 R²=0.049）。
- 数据: t2_results/corpus_j0/（双机 145 轮+origin/goal map+抽取器）。

### A4. 单元 2 — MACH8 静默大发散发作窗解剖（A4 疑点）→ 定案
- 求解器全程净（3765 帧 0NaN/0err/0reboot,track p50=122,init 1 次）——"静默"实证。
- **发作窗时间线**: t=31.5-33 起飞 Bas 瞬态 0.005→0.57→回落;t=47-50 二次爬至 **0.72 锁死**;t=91-173 transit 积累（j0 88%）;t=173-383 **P 冻结 210s** 在错稳态 (7.18,-3.70,0.95)。
- **三候选判决**: 窗口退化 否/偏置爆炸 **修正为偏置固化**（锁定 0.724 后零漂,爆炸路径不成立）/**transit 慢漂主导**——bias-lock×transit 位移积分=稳态偏差,连续一致但错误（sane 门结构性盲,与走爬带同族）。
- **回放复现**（t=0-113 恰覆盖发作窗,772 帧 dP p50=0.218/max 0.380 多线程非确定带内,Bas 爬升+transit 同型）=**输入确定性非时序彩票**;被 T1 X3l2a 起轮清残留杀于 t=112.964（STATUS 04:30 让路通告在案,无互扰）;冻结段以原轮 log 210s 实证等价,补全回放豁免。
- 修复面登记（不动手）: BAS-LOCK 读数进 j0d 扩展（归 T3 队列）/transit 前 bias 约束（需预注册）。
- 数据: t2_results/mach8_onset/（文书+CSV+回放 log+odom bag,md5=b7de133d v4 栈登记）。

### A5. 单元 7 — 归还件消费 → 全件落账
- **BL7/MACH6 双列注记**（旧 0.467/0.673 轮正本 vs L3 新 1.810/0.960,两轴均红,不静默改判;两轮同是 64-65m 帧跳变轮）。
- **13 边缘轮裁定=登记注记不追溯改判**（预注册纪律;§2.8a 修正效应注记"新口径到位=X"）。
- **B2 时序彩票**: 27 轮探针聚合 lockstep/回调顺序候选**降级**（IMU p50/p99/max/age 同机器内与形态不可分;机器差不共变形态）→剩余主候选=VINS 进程内非确定性（与 T1 v11.2 互证）;X7 §8 更新=open+新证据。
- **B1 敌对态物理载体**: 轮目录无现成硬件遥测文件,腿已建,NUC bag/state 考古排队——**如实 open**（排除面+数据包+X7 条目三件齐）。
- 悬停 8.5m 证据包未定位实物（**@T4 求指针**,STATUS 04:32 在案）;W2 僵尸核对 PASS。
- **池=3 在位**: MACH8 补全段回放（如索要）/B1 遥测考古/X5 网格剂量轴设计件。

### A6. 单元 6 — V2/净轮扩充画像 → 交付
- 净轮清单全库 20 轮（3090 原生 11: M0/MACH3/VRG1/X2g3/VRFY2/RA5hover/RA12hov/RA14/DIAGGUARD2 等;最低 MACH3 j0=0.008）。**V2 判定状态维持未过不变**（prereg 冻结口径）,清单=候选池交付。
- **3090 敌对窗口存在性=排除**（storm 4/4 集中 22-23 时段毒配置飞行窗;clean 散布 6/10 时段——无独立于配置/任务的敌对窗口,V2 前置降级件假设否证）。
- guard 画像: T2RESUME 全库仅 3 轮（恢复事件罕见）/E2uls 捕获常态高频/sane 门零触发（MACH8 型盲区再证）。
- 数据: t2_results/net_pool_v2/。

## B. 剩余（下任清单）

1. **W-用户过目三件**: C.1 修复预案四件（A1）/对审 v1.4（T1 域在案）/X4 臂重裁材料新增 VRG1 干净归因修正（boot_diff §2 发现②,本册 A1/A2 补证）。
2. B1 硬件遥测考古（NUC bag/state 主题,需 IO 窗）。
3. X5 网格设计件（gyr_peak 剂量轴,预注册件队列——消费 A3 结论）。
4. MACH8 补全段回放（材料等价豁免已注记,用户索要即执行）。
5. @T4 悬停 8.5m 指针回执。
6. T1 对照批 -nan 新样本到货→C.1 §6 矩阵扩行（预期:loss=1∧cauchy=0 必风暴;已被 5/5+全库 6/6 支持）。

## C. 卡点（客观描述,无阻塞主线索）

1. C.1 修复本体=挂起件纪律（三歧定案文书+用户过目后才写码;预案四件在 A1）。
2. 回放与 T1 飞行批互斥（本轮实测: T1 起轮清残留杀我回放 vins——错峰纪律已验证必要;私有 master 隔离有效,无互扰面）。
3. corpus_j0 的 truth_z_max 提取 0 覆盖（end_state 键名差异）——爬升比剂量候选拖欠,不影响 gyr 主导结论。
4. A3 臂差 16pp confound 不闭环——因果版需臂键随机化批（X 线判别轮域）。

## D. 资产与等待登记

- commit 链: 623202c（C.1）→122d7e5（init census）→0fd9bac（U4+5）→c3795f3（U2+7）→1c6ba5a（bag force-add）→c51628f（U6）。全部已推 origin/main。
- 数据目录: t2_results/{nan_dissect_vrfy1,init_census,corpus_j0,mach8_onset,net_pool_v2}。
- 等待: W-T1 对照批样本（并案扩行）/W-用户过目三件/W-T4 悬停 8.5m 指针/W-臂重裁（T1 域,材料面含本册新增证）。

## E. 新坑（本夜新增）

1. **t2_replay 起前必查 T1 批**: T1 轮脚本起轮清残留会杀私有 master 之外的 vins_node（本夜实锤 04:26）;错峰=STATUS 预告+pgrep 全机预检双保险。
2. **pkill -f 自匹配**: 复合命令行含匹配串会杀自身 shell（bash -c 内联 pkill 时 STATUS append 等后续命令全丢）——pkill 单独成行。
3. **corpus forensics 键名**: json=小写（imu/end_state）,txt 报告=中文/大写——抽取器须按 json 键。
4. **goal.txt 解析**: tr -d 粘连数字致科学计数误吞;必须 sed 前缀+空白 split。
5. **轮正本 RESULT 不随 L3 重算更新**（正本保全原则）——到位新口径读数以 T1 l3_recompute_v14_summary.md 为正源,消费走双列注记。
6. **NUC 侧 census 脚本传参**: 参数位置差异致输出文件名错乱——固定"无参=本机全库"约定。
