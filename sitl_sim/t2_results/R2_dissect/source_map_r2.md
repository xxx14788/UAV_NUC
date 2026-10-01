# R2-0 源码行号图：三角化初始化路径与 estimated_depth 生命周期（任务书 v7.2 第 0 刀）

- 写表时刻：2026-10-01 晚（T2 R2 战役）
- 版本锚：NUC `~/catkin_ws/src/VINS-Fusion` @ catkin HEAD 04d7686；feature_manager.cpp md5 `66d53568b0c06ac18bea35fca5de6b18`；estimator.cpp md5 `abbab94dfa55476b68d53ab2d9ca1201`；INIT_DEPTH=5.0（parameters.cpp:274）
- 性质：纯读源码 + R1 既有日志复分析（dis0/g_depth vins.log），零新试验、零锁、零代码改动
- 验证法：源码图每条"实测计数"列均与 R1G_dis0/R1G_g_depth 的 vins.log census 互证（命令附后）

## A. estimated_depth 全部写点（11 处）

| # | 写点 | 文件:行 | 触发条件 | t2 开关门控 | dis0 实测计数 |
|---|---|---|---|---|---|
| W1 | stereo 初始化正深度 | feature_manager.cpp:436-437 | 双目分支，depth>0 | gate on 时 L428-435 仅量程内放行 | stereo ok=15792 |
| W2 | **stereo 负深度→INIT_DEPTH(5.0)** | feature_manager.cpp:442-444 | depth≤0 | gate on 时 L430 拒并 erase | stereo init_neg=4906（打印值恒 5.0000） |
| W3 | motion2 初始化正深度 | feature_manager.cpp:505-506 | 非立体首帧+≥2 帧，depth>0 | gate on 时 L494-501 | motion2 ok=10848 |
| W4 | **motion2 负深度→INIT_DEPTH** | feature_manager.cpp:508-511 | 同上 depth≤0 | gate on 拒 | motion2 init_neg=9256 |
| W5 | SVD 分支无条件写 svd_V[2]/svd_V[3] | feature_manager.cpp:558 | —— | —— | **0（分支不可达，见 C）** |
| W6 | SVD <0.1→INIT_DEPTH | feature_manager.cpp:583-586 | 同上 | gate on 时 L571-578 拒 | 0（同上） |
| W7 | **solver 回写 setDepth：est=1/x** | feature_manager.cpp:153-162（estimator.cpp:1046 double2vector，:1518 optimization 内每帧调用） | used_num≥4 全体特征 | **无任何门控**；负→solve_flag=2（fm:164-170），removeFailures（fm:173-181，est:745）帧末删除 | 无逐帧 dump（工具债③） |
| W8 | clearDepth 全置 -1 | feature_manager.cpp:184-188 | 仅 initialStructure 尾（est:960-961） | —— | 初始化一次性 |
| W9 | **滑移深度转移** | feature_manager.cpp:622-663 removeBackShiftDepth | 稳态每次 MARGIN_OLD 滑移（est:1859-1875 slideWindowOld，solver_flag==NON_LINEAR 恒真）；start_frame==0 特征 | dep_j≤0 时：printf L649-651（flag=init_neg, u=v=-1）+ **L661-662 INIT_DEPTH 再注入（无计数器！）**；gate on 时 L654-658 量程外 erase | shift init_neg=118（100% 打印者皆负） |
| W10 | gate 拒绝 erase | feature_manager.cpp:590-600 | t2_gate_reject 集 | —— | dis0 无（gate 关） |
| W11 | t2SvdDepth 探针 | feature_manager.cpp:319-350 | dump-only | 不写 estimated_depth | [T2xcross] 另计 |

**init_replace 计数口径漏洞（新发现，工具债级）**：`[T2gate] init_replace` 计数器只累计 W2/W4/W6 三处；W9 滑移再注入从不进计数。dis0 census 14280 = 9256+4906+118 恰含 118 条 shift（judge init_neg_n=14280 旁证 R1 census 口径含 shift）。

## B. 解算入场、存量与出场阀

- **入场门**：solve 因子循环 estimator.cpp:1323-1325 `used_num<4 → continue`；marg 先验构造 estimator.cpp:1601-1656 同阈值+start_frame==0+非 chi2 拒。**INIT_DEPTH 特征须存活≥4 帧才以 inv_dep=1/est（fm:191-203 getDepthVector，est:1039 vector2double）入解算**。
- **主循环序**（estimator.cpp，每帧）：L700 triangulate → L701 optimization（内含 W7 回写）→ L702-703 outliersRejection → L716 removeOutlier → L725-743 failureDetection→[T2fail]/clearState 重启 → L744 slideWindow（W9 在此）→ L745 removeFailures。**注意 slideWindow 先于 removeFailures：solver 写负（W7）的特征可先经 W9 再注入 INIT_DEPTH 后才被删除。**
- **出场阀**：outliersRejection（est:1940-2001）3px 轨平均（注释自认"长轨稀释"），t2_outlier_px 可调；solve_flag==2（fm:173-181）；丢跟踪 removeBack（fm:675）/removeFront（fm:693）。
- **边际化先验**：t2_prior_gate 族（est:1528-1567）：触发式（cost 尖峰/dBAS/份额），strategy 1=弃先验+跳过本次 marg，**2=弃旧先验+重建新先验（est:1572 t2_drop_prior_only）**，3=冻结；cooldown 默认 5 解算。

## C. ①「第二注入路径」的源码级判定（R2-1 切分之上半）

- **SVD 分支（W5/W6）在此构建不可达**：到达需「非立体首帧 且 size≤1」（否则被 stereo L394 / motion2 L461 截胡），此时 used_num=1<4 被 L519-520 跳过。实测 dis0/g_depth census `src=svd` 行数=0（互证）。
- gate-on 模式下 estimated_depth 写点全集 = {量程内 stereo/motion2 正深度（W1/W3），solver 回写（W7）}。**不存在隐藏第三注入口。**
- 操作化证据链（既有，不重跑）：g_depth（gate_rej=25481、init_replace=0）仍爆@135.212s + U3R1_M2OFF（t2_motion2_min_base=999 全禁 motion2，同袋）仍爆 → 窄义①**证伪**。
- 剩余入口嫌疑 = **stereo 量程内垃圾**（见 D-2 深度分布）经解算耦合放大——与②在 solver 环内不可分，须用存量必要性切分（R2-2 预注册）。

## D. R2 分析轮新增实测事实（R1 口径未覆盖；数据源=既有 vins.log，命令见 F）

1. **三源 initneg 分解（dis0，5s bin census）**：motion2 负深率 46.0%（9256/20104，25s 起即 40-53% 持续）；stereo 负深率 23.7%（4906/20712），其中 55-80s 窗升至 30-41%；shift 再注入 118 全负。R1 的 initneg_frac 口径混合三源。
2. **深度值分布（dis0，分位）**：motion2 ok 在 55-80s 窗 p50=6.9m/p75=48.8m/**p95=487m**（零基线噪声，量程门 [0.15,30] 拦不住 30m 内正值）；stereo ok 同窗 p50=5.9/p75=24.0/p95=39.5m（立体基线物理有界）。
3. **vis_n 坍塌（两轮同型）**：55-60s bin 视觉因子数从 700-1300/帧 塌至 50-100/帧（10-25×），早于 cost 爆（120s+）60s 以上；vis_cost 于 50s bin 已 5.8e3（40s bin 421）= 55-58s 尖峰。canonical 死亡链精化为：42.6s initneg 起搏 → 55-58s vis_cost 尖峰 → **55-60s 特征池大失血（出场阀屠杀）** → 60-120s 饥饿带（vis_n 50-100, tri churn 3×） → 134s 终爆。
4. **g_depth 无饥饿**：接受率全程 0.90-0.98（tri 45K/10s 级 vs rej ≤4.5K/10s）→ 排除"gate 拒绝饿死"替代解释。
5. ~~canonical 自证存量可活~~ **勘误（R2G_a58 判读时自纠，2026-10-01 18:50）**：dis0 无爆后存续——n_diag=1036 ≈ 25-134s 帧数，进程死于 134s 爆点（vins_node Aborted，试验台既定死法，R1G 五格同）。爆前 25-134s 墙内容对干净状态从未测过=R2G_a58 格的存在理由（该格实测结果：fresh init 死于 61.4s，见台账 R2G_a58 行）。

## E. 干预面地图（全部现有开关/基建，0 新代码）

| 干预 | 锚点 | 状态 |
|---|---|---|
| t2_motion2_min_base | fm:469-471（WA9） | M2OFF 已证伪载体 |
| t2_depth_gate/min/max | fm:428/494/571/654 | g_depth 已证伪 |
| **t2_prior_gate strategy=2** | est:1528-1567 | **未跑过本袋 → R2G_pr 格** |
| t2_outlier_px | est:1994-1999 | 出场阀松紧（修复面候选） |
| **T2_PLAY_EXTRA="-s N"** | t2_replay.sh:62-63 | **换起点重放 → R2G_a58 格** |

## F. 复验命令（证据三件套之"命令"）

```bash
# src census（dis0/g_depth 同式）
awk '/T2depth/{src="";flag="";for(i=1;i<=NF;i++){if($i~/^src=/)src=substr($i,5);if($i~/^flag=/)flag=substr($i,6)}print src,flag}' <vins.log> | sort | uniq -c
# tri/rej/init 时间线
awk '/T2gate/{t=-1;tri=-1;rej=-1;init=-1;for(i=1;i<=NF;i++){if($i~/^t=/)t=substr($i,3)+0;if($i~/^tri=/)tri=substr($i,5)+0;if($i~/^rej=/)rej=substr($i,5)+0;if($i~/^init_replace=/)init=substr($i,14)+0}if(t>0){b=int(t/10)*10;T[b]+=tri;R[b]+=rej;I[b]+=init;N[b]++}}END{for(k in T)printf "%ds tri=%d rej=%d init=%d n=%d\n",k,T[k],R[k],I[k],N[k]}' <vins.log> | sort -n
# vis_n 坍塌
awk '/T2cost/{t=-1;vn=-1;for(i=1;i<=NF;i++){if($i~/^t=/)t=substr($i,3)+0;if($i~/^vis_n=/)vn=substr($i,7)+0}if(t>0){b=int(t/10)*10;V[b]+=vn;N[b]++}}END{for(k in V)printf "%ds vis_n/f=%.1f\n",k,V[k]/N[k]}' <vins.log> | sort -n
```

## 增补章:failureDetection 源码取证 + 上游对照 + P/V 挂点裁定(2026-10-02 01:5x,任务书单元2)

### 1. 现行实现全文取证(estimator.cpp:1134-1206,T2-W4 版)
| 检查项 | 量域/条件 | 触发动作 | 状态 |
|---|---|---|---|
| insane states(有限性+量域) | !Ps/Vs/Rs.allFinite() 或 |P|>1e3 或 |V|>50 | return true→reboot(clearState+重 init) | **本项目 T2-W4 新增**(2026-09-27) |
| little feature | last_track_num<2 | 仅 ROS_INFO(return true 被注释) | 上游注释保留 |
| Bas 量域 | |Bas|>2.5 | return true | 活(上游同款) |
| Bgs 量域 | |Bgs|>1.0 | return true | 活(上游同款) |
| extrinsic | tic(0)>1 | **整块注释** | 上游注释保留 |
| 平移跳变 | (P-last_P).norm()>5 | 打印+return 注释 | 上游注释保留 |
| z 跳变 | |ΔP.z|>1 | 打印+return 注释 | 上游注释保留 |
| 旋转跳变 | delta_angle>50° | 打印+return 注释 | 上游注释保留 |
调用点:estimator.cpp:725(每图像帧 solve 尾,~10Hz 节奏);触发打印 [T2fail] 快照(P/V/Bas/Bgs/tic/td/track,T2-R1.5 插桩)。
复位逻辑:failureDetection true→Estimator::clearState()→solver_flag=INITIAL→滑窗/特征/偏置全清→重新 initialStructure(软重启,进程不死)。
配套发布端防线:estimator.cpp:245(latest_P<1e3/|V|<50 有界性门,125Hz 外送前,T2-v3 W1.3);E2 clamp 钳制(T1-E2 C03-A4,dt 域断裂时 hold 发布)。

### 2. 上游 v1.17 对照(git diff 视角;remote=github.com HKUST-Aerial-Robotics/VINS-Fusion master)
- 上游 failureDetection **首行 `return false;` 使全函数成死代码**(全部检查不可达)——本项目 T2-W4 移除该行并新增 insane states 检查;Bas/Bgs 检查上游原样(本项目可达);little feature/extrinsic/jump×3 上游即注释,本项目保持注释=**无未登记的本地改动残留**(对照结论:干净)。
- 上游 jump 检查(P>5/Δz>1/角度>50)被注释的历史语义=单帧跳变易误杀(上游有意保留打印不触发)——与本项目 R3 实测互证:跳变≠失败(重锚/优化 jump 正常存在,健康轮 E2uls dP 毫米级-米级均活)。

### 3. P/V 量域检查挂点裁定(R3 取证驱动,喂单元4)
- **量域门判死**:R3 实测健康轮 U3PO v_max(尖峰口径)=21.17 vs 病轮 PR1=17.0/PR2=6.6——重叠无判别力;|P| 门与 route 真航程(百米级)冲突;降阈值必误杀健康轮。上游注释的 jump 挂点同理不取。
- **改挂 cost 门(推荐)**:T2slv init_cost>10×滚动基线(100 帧 p50)持续 N=5 帧→failureDetection 新增返回路径(挂在 Bas 检查后、little feature 前,与既有结构同型);R3 实证:route 急冻形态 cost 65→643@t=50.0s 精确起点,量域异常(冻结/零 fail)全程未现——cost 门早于任何可观测状态异常。
- 次选挂点:Bas 平台门(|Bas| 逐位不变持续 M=100 帧→梯度死寂信号;R3 病轮 Bas 冻结 28s 先于爆窗,健康轮冻结率 3.7%)。两门都属"估计器自一致性"类,无需真值。
- 预注册阈值注记:N/M 与 10× 从 U3PO/U3PG 健康轮 cost/Bas 分位取(单元4 附计算过程);防误杀条款=门触发仅当 solver_flag==NON_LINEAR 且非 init 后首 100 帧。

### 4. 与 R2F 的关系
R2F(视差门)在观测入环前(fm.cpp),本节门在解算后(estimator.cpp)——前后两道独立防线,R2 载体(视觉坍塌)归 R2F,R3 载体(在线 IMU/状态域,cost×10 型)归本节 cost 门;两门默认全关=逐位不变,判别格各自独立跑。
