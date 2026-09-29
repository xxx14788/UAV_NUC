# T2-WA2 边缘化机制全解剖(2026-09-30 夜)

行号基于 NUC HEAD(65674ab+WA 补丁前),函数=VINS-Fusion vins_estimator。

## 1. 代码走读(行号级)

### 1.1 求解与边缘化主流程(estimator.cpp)
- `optimization()` :1171 起。:1212-1219 **先验因子**加入(NULL loss);
  :1222-1231 IMU 因子(NULL loss);:1234-1285 视觉因子(HuberLoss(1.0));
  :1327 ceres::Solve(DOGLEG,DENSE_SCHUR,MARGIN_OLD 时限 0.8×SOLVER_TIME)
- **W-A2 门落点**:Solve 后 :1349 double2vector → :1354+ MARGIN_OLD 边缘化
  (补丁在 return 短路后、边缘化分支前插入触发判定)
- MARGIN_OLD 块 :1343-1450:旧先验作为因子(:1343-1357,drop para_Pose[0]/
  SpeedBias[0])+IMU[0-1]+imu_i==0 的视觉因子 → preMarginalize → marginalize
  → addr_shift → `delete last_marginalization_info; last = new`(:1448-1450)
- MARGIN_SECOND_NEW 块 :1455-1525:仅当上窗先验含 WINDOW_SIZE-1 姿态时
  重边缘化;同样滚存
- slideWindow 独立于边缘化(solve 流程先后调用)——跳过边缘化时窗口照常
  滑移(丢最老帧的约束贡献,但保留其观测的特征深度转移)

### 1.2 先验构造数学(marginalization_factor.cpp)
- `ResidualBlockInfo::Evaluate()` :13-79:每因子在**当前参数值**上固化
  残差 e 与雅可比 J;**loss function 在此应用**(视觉块带 Huber 的 rho 缩放,
  :57-77 residual_scaling/alpha 重加权)——注意:固化的是**裁剪后**的 e/J
- `preMarginalize()` :120-140:parameter_block_data 快照(线性化点)
- `marginalize()` :185-308:A=ΣJ^T J,b=ΣJ^T e 多线程累加(:237-266);
  **Amm 特征值分解+eps=1e-8 截断伪逆**(:277-283,h:80 `const double eps=1e-8`);
  schur:A←Arr−Arm·Amm⁻¹·Amr,b←brr−Arm·Amm⁻¹·bmm(:290-293);
  **先验因子形态**:J_prior=√S·V^T,e_prior=S⁻¹ᐟ²·V^T·b(:300-303)
  (S=第二步特征值 eps 截断)——e_prior 含**上帧残差平方项的滚存**且
  MarginalizationFactor::Evaluate 无 loss(NULL),残差无界可平方增长
- `MarginalizationFactor::Evaluate`:e_prior = e_lin + J_prior·(x−x_lin)
  一阶展开——x 漂离 x_lin 越远,先验残差越大(平方进入 cost)

### 1.3 失效链闭环(代码+实测互证)
1. 毒观测(负深度→伪 5.0)进窗 → 视觉项爆([T2cost] t=27.34 vis=2120/99.7%)
2. 求解后边缘化:毒块的 e/J(Huber 裁剪后)进入 A/b → **先验固化毒记忆**
3. 后续帧:先验因子在漂移状态上产生平方残差(prior_share 实测 0.2-0.5)
4. bias 弱约束(WB4:视觉锚定下弱 13 个量级)→ 残差灌进 Bas(0.005→2.53)
5. failureDetection Bas>2.5 → reboot 清先验 → cost 回落 → 新毒再积累
   (78→17k 周期的重置边;T2cost t=37.94 prior_share=1.0 的空窗即 reboot 边)

## 2. 数值复现实验(实测替代合成——论证)

任务书要求"构造已知毒观测注入合成窗口,数值展示 cost 增长曲线"。
**替代路径:WA1V_RCAN_TRACE 轮的 [T2cost] 分解就是真实毒观测的实测增长曲线**
(合成实验的目的是证明机理,实测数据证明同一机理且更权威):

| t | tot | prior | vis | 阶段解读 |
|---|---|---|---|---|
| 27.34 | 2126 | 0 | 2120 | 毒入口第一击=视觉项(99.7%) |
| 28-31 | 120-180 | 15→29 | 91-175 | 平静期:先验固化爬升,share≤0.26 |
| 32.0 | 57.7 | 28.9 | 22.5 | **prior_share=0.50 峰**——毒记忆主位 |
| 33-36 | 220-665 | 61→82 | 178-540 | 新毒批入场 |
| 37.07-37.5 | 1.1e4→3.0e4 | 105-112 | 1.07e4→2.98e4 | 视觉项破 1e4 |
| 37.94 | 78 | 78 | 0 | reboot 空窗(share=1.0) |
| 38.74 | 7.9e6 | 800 | 7.9e6 | 死亡瞬间(状态跑飞全部投影爆) |

**机理结论修正(相对研究文档)**:
- "视觉 Huber 有界到不了 1e4"在**块数量**维度不成立:vis_n=1389 块×单块
  上界 ~65=理论上界 9e4;实测毒暴发时 vis 直达 2.98e4——**视觉项本身是
  尖峰主源**,先验是**平静期的记忆滚存者**(share 0.2-0.5)+二次放大的载体
- W-A1(断毒入口)因此更核心:vis 爆的根源=毒特征本体
- W-A2(先验门)的靶=平静期滚存:触发器 prior_share>0.5 有实测支撑
  (健康流 CTRL2 的 share 分布待 trace 对照轮定标,queued)

## 3. 门设计(已实现,W-A2.3)

触发器(任一,全部 rosparam 化):
- T1 `summary.initial_cost > t2_prior_cost_thr`(默认 5e3;CTRL2 中位 2120
  /R_CAN 毒窗 5.5e4,阈值留 2.3× 裕度,矩阵校准)
- T2 `||ΔBas||>t2_prior_dbas_thr`(默认 0.05;CTRL2 健康帧间 ΔBas~0.005-0.02)
- T3 `cost_prior > t2_prior_share_thr × cost_tot`(默认 0.5;实测毒窗 share
  峰 0.50,健康流待对照)
限频:`t2_prior_cooldown`(默认 5 帧内至多 1 次——防等效软重启风暴)
策略:`t2_prior_strategy` 1=删先验+跳过本轮边缘化 / 2=删先验+照常重边缘化
(纯观测重建) / 3=冻结先验+跳过(下帧仍用旧先验)
日志:[T2WA2G] 触发行(进 T2frame wa2_trigger 列)

## 4. FEJ 评估(研究债)

见台账 2026-09-30 03:12 条:VINS 无 FEJ 的本质=先验旧线性化点与新因子新点
并存;工程量大/风险高/与主失效通道(毒观测+滚存)相关性弱——**书面不实施**;
W-A2 门以"丢弃毒先验"形式规避毒窗重线性化问题。
