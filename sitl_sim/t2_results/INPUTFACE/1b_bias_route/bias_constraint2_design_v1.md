# bias 约束②设计件+预注册 v1.0（transit 前/中 bias 约束——①③证伪后独立验证线）

上位框架：1b_bias_route/1b_bias_three_prereg_v1.md §4（件②骨架，冻结）。
触发条款：§5"①③证伪则此件独立验证"——本夜 ①FEED=NO_VALID_CARRIER（10-08 定案）+
③预热段=NOT-EFFECTIVE（本夜 8/8 对干净复验：goal 面已修复[W4-ADOPTED 7/7]前提下
A 12.5% vs B 50%，-37.5pp，方向一致 3/8<6/8）→**双证伪触发，②升独立验证线**。
任务书 v10.7 单元 2 失败分支："当夜出 bias 约束②设计件+预注册[下周期即写码]"。
冻结时刻：2026-10-09 07:1x（写码前冻结）。

## 1. 机理与本夜新证据

- 机理（1b §4 冻结）：transit 段（速度爬坡主毒，j0 主贡献段）bias 可观测性差+
  marg prior 自持 → Ba/Bg 漂移吸收位置误差 → 终态漂移。约束=在 transit 窗内
  给 bias 强先验/物理域界，阻断"漂移吸收"路径。
- **本夜新证据（v10.7 复验批）**：预热激励非但不提升绿率，A 臂 transit jump
  反而劣于 B 臂（4/7 数值对：S8O 1.400 vs 0.333 / S8P 1.002 vs 0.142 /
  N8P 1.308 vs 0.076 / E12O 0.294 vs 0.095；仅 S12P 反向）——与"激励把 bias
  状态推入大瞬态、任务段带着未平复瞬态"机理自洽；v11.31"A 臂帧稳定反优"
  勘误=悬停混杂（不导航=无跳变机会）。**该证据支持"约束漂移"优先于"先收敛"**。

## 2. 设计两子案（默认序=②a 先，判负才开 ②b，不并行开双侵入面）

- **②a 物理域 box 约束（默认首案）**：ceres `SetParameterLowerBound/UpperBound`
  对 para_SpeedBias 的 Ba[3]（±0.5 m/s²）/Bg[3]（±0.05 rad/s）分量加盒界
  （域值沿 1b §1 第 0 步合理性域，上游无暴露=需代码）。作用窗=全程（box 为
  结构性安全域，非窗式）；侵入=estimator.cpp AddParameterBlock 后三行×2 组
  +config 键 t2_bias_box（默认 0=原语义逐位同；T2 补丁模式[config 键+env
  旁路]沿 t2_iqg_observe 先例）。
- **②b transit 相对锁先验（备选）**：prior factor 在 transit 窗（起飞后首帧
  速度>0.3m/s 前 1s 起，至速度回降<0.2m/s 止——窗定义冻结）内将 Ba/Bg 锚到
  窗首值，权重 W 梯度 {5,10,20}×基线；侵入=MarginalizationFactor 外挂 prior
  残差（较深）。
- 判负升级条件：②a 批判负（绿率差 <-10pp 或 jump 面劣化）→②b 设计生效。

## 3. 臂实验预注册（冻结）

- 格名册=复验批同 8 格（E8P/S12P/S8O/E12O/NE8O/N8P/E12P/S8P，plain+obstacles
  混合，毒格健康格同池——与 v10.7 复验批同构可三方对照 A/B/②a）。
- 配对 ≥8 对：②a 臂 vs 当夜基线臂（B 臂须同夜重跑，禁跨夜复用）；
  判据沿 2.3 冻结口径：绿率提升 ≥15pp ∧ 方向一致 ≥6/8 → 有效；
  副指标=transit 窗内 |d(Ba)/dt| 均值（约束生效性验证）+j0 终态/jump 面
  （复验批同判读链）。
- **新病面预案（预注册）**：约束过强压制真 bias 变化 → SITL 域判"有效"但
  实机温漂场景失效——SITL 收益/风险不对称注记强制入终稿；②a 臂劣化 ≥15pp
  =box 域值错或约束自伤，如实收卷转域值审计，不硬推。
- ENV-FAIL 轮=环境性重试 1 次/轮上限（沿 X 线先例）；NO-RESULT 无 RESULT.txt
  判 env 类不入绿率分母。

## 4. 写码面（下周期首件，本件仅设计冻结）

- 落点：vins_estimator/src/estimator/estimator.cpp（~L1429 AddParameterBlock
  para_SpeedBias 处）+parameters.{h,cpp}（config 键解析）；编译窗与 T1 P3
  修复错峰（CPU 互斥在册）。
- 验证序：gtest（box 语义+默认 0 逐位同）→干测（config 键生效 banner）→
  8 对臂批。判据零变动；任何改动=新 prereg 条目。

## 5. 冻结声明

本件判据/域值/窗定义/臂名册自落盘冻结；②b 的 W 梯度冻结 {5,10,20}；
实机适用性声明沿 1b §3.4（SITL 结论边界=工程链正确性+副作用面，有效性终验
在实机台架）。
