# ②b transit 相对锁臂批预注册 v1.0（批前冻结——2026-10-10 07:0x 落盘，发射前）

上位链：bias_constraint2_design_v1.md（c16f59c1）§2 ②b 备选+W∈{5,10,20} 冻结 →
②a 判负（box_arm_verdict_v1.md 2db067fb）触发本件 → 任务书 v10.10 单元 3 判负分支。
判据沿设计件 §3 冻结口径零变动（≥15pp ∧ 方向一致 ≥6/8）；三层判读预设沿
box_arm_batch_prereg_v1010.md §3 结构（②b 版等价适用：层①=ENGAGE/RELEASE banner
+锁窗内 |Ba-快照| 偏差统计；层②=dbadt 对比；层③=预分类[无效型/过紧型/机理负型]）。

## 1. ②b 写码面（本件冻结的操作化——设计件 §2 未细部分）

- 落码：estimator.cpp NON_LINEAR 求解域+estimator.h 状态机三成员+parameters
  键 `t2_bias_tlock`（默认 0）+`t2_bias_tlock_w`（默认 10）+env 旁路
  T2_BIAS_TLOCK/T2_BIAS_TLOCK_W（②a 同规则）+banner `[T2BIASTLK]`/`[T2TLOCK]`。
- prior=InitialBiasFactor（WA7G 加权构造器复用，weight=W）挂全窗帧
  para_SpeedBias[0..frame_count]——"锚到窗首快照"的滑动窗实现。
- **窗口谓词**（冻结）：V 首过 >0.3 m/s → ENGAGE（快照当帧 Bas/Bgs=窗首值）；
  V 回降 <0.2 m/s → RELEASE+done（单窗语义，release 后不重锁——leg2 不二次锁，
  如实注记）。设计件"前 1s 起"在线不可回溯——快照取越阈当帧=最近未漂值，
  操作化偏差如实注记。
- **W 操作化**（冻结）：W=绝对权重（sqrt_info=W×I₆），基线语境=WA7G 硬锁
  T2_BIAS_WEIGHT=50；W∈{5,10,20} 全梯度冻结在册。**首批 A 臂 W=10**（梯度
  中值）；5/20 扫=判临界时的复验轮（env 可换不重编译）。批 8 对=①样（同夜
  同栈 md5 锁+config 键两臂同文件+臂身份 env 承载+banner 自证）。
- gtest：7/7（②a 4+②b 3：谓词冻结/转移表/默认锁）；邻近回归零漂移。

## 2. 批设计（沿 ①样零改动）

8 格同 ①样（E8P/S12P/S8O/E12O/NE8O/N8P/E12P/S8P，A_first/B_first 交替同表）；
A=env T2_BIAS_TLOCK=1（W=10 默认）；B=无 env。budget 300+stoploss；ENV-FAIL/
NO-RESULT 重试 1 次/轮；同夜同栈硬约束；产物=1b_bias_route/tlock_pairs_v1010.csv
（列结构同 box_pairs_v1010.csv 16 列版+tlock_banner 列替 box_banner）。

## 3. 干测前置门（①样消歧式，补条 B 目的重述版直接沿用）

- 证据链判定：banner 自证（[T2BIASTLK] tlock=1 + [T2TLOCK] ENGAGE/RELEASE 实飞
  出现）∧ 栈健康（流/零重启/零 NaN/config md5）→ 通过。
- 行为面（verdict/jump）今夜跳态语境下不作单轮判定（补条 B 教训）；批内活控
  组绊线同 ①样（B 臂前 4 轮全 FAIL∧jump>7.2m∧栈异常→停批审计）。

## 4. 分支（任务书单元 3 第三分支对接）

- ②b **通过**（≥15pp∧≥6/8）→ ②b=绿率修复主件成立（呈报件：config 默认值
  走向=W 依批数据定稿，用户过目件）。
- ②b **判负** → **bias 路线整体证伪定案文书**（绿率修复面收敛定案：选格收窄
  70.5%+止损件+架构级 transit 地板注记[回环不接入裁定维持]）+X7 收敛声明素材
  增补（@T3）——判负分支亦有实质产出（定案文书），无空手分支。
- ②b 批无窗（凌晨窗耗尽/他线占用）→ ②a 判负中间报告（已落盘 2db067fb）+
  ②b 次窗首件挂起条款（任务书原文）。

## 冻结声明

判据/窗口谓词/W 梯度/臂名册自落盘冻结；批后任何改动=新 prereg 条目。
