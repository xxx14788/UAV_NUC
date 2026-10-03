# prereg_gatereset_initshift — 门复位修复+init_replace 分源计数器（v8.3 单元 1；判据先于代码；2026-10-03 12:2x）

## 1a 门复位（规格承台账补遗章）

- 补丁：estimator.cpp clearState() 增 `t2_cost_hist.clear(); t2_cost_streak = 0;`（成员为 estimator.h 既有私有成员，clearState 是唯一复位语义的正确落点——boot/reboot/init 门 reinit 三路径全覆盖）。
- 语义：门随 reboot 重武装，需 20 帧新鲜 NON_LINEAR 窗口才开检=再 init 成熟期保护；根除 55.432 型（陈旧低中值×新鲜 init 高初始 cost→误连击→掐灭成熟中 init→风暴自维持）。
- 行为不变性声明：t2_cost_gate=0 时门逻辑从不读写 hist/streak（est:1521 在 T2_COST_GATE&& 内）→清零对 gate-off 轮逐位不变；gate-on 健康轮（20 帧内无 cost 突增）同样零行为差。

## 1b init_replace 分源计数器（等待池 6②）

- fm.cpp：tri 侧 stereo 负深写点与 motion2 负深写点各增源计数（t2_stat_init_st/t2_stat_init_m2，局部）；尾部 <0.1 兜底维持 t2_stat_init（残余桶=st+m2 之外）。
- shift 侧：FeatureManager 新增成员 `long t2_init_shift_total`（removeBackShiftDepth dep_j≤0→INIT_DEPTH 处递增）+`long t2_init_shift_last`（打印水位）；[T2gate] 行追加 ` ir_st=%d ir_m2=%d ir_shift=%d`（ir_shift=自上次打印的增量，打印后清水位）。旧字段 init_replace=%d（总数）保留向后兼容。
- 消费面：单元 2 空中再 init 画像直接吃分源计数（shift 注入是否在假盆地轮异常）。

## gtest（test_a1_reboot_fix.cpp 增 1 用例 + 新 test_t2_init_shift.cpp）

- test_t2_init_shift：构造 FeatureManager，注入 start_frame==0/双帧特征，removeBackShiftDepth 以 Rx(π) 翻转位姿使 dep_j<0 → 断言 estimated_depth==INIT_DEPTH 且 t2_init_shift_total==1；正转移对照（dep_j>0）→ 计数不动。
- estimator 侧 clearState 复位不可单测（需完整 Estimator 构造）——以代码评审断言+在线验证轮 V1 代偿，如实记。

## 在线验证轮（预算 3 轮：route gates ×2 + hover gates ×1；判据先于飞）

- **V1 重武装（主判，硬性）**：任一 [T2GATECFG] banner 后 2.5s 窗（≈20 帧 NON_LINEAR）内**零 cost 门触发**（55.432 型根除）；判读=log 逐 banner 扫描。
- **V2 风暴缩短（条件判据）**：若验证轮出现爆窗（非必需——急冻族 0/9 成熟在案），任一 10s 窗内 reboot 数 ≤4（033941 型 14 连为对照基线）；无爆窗则记"未检验"如实。
- **V3 健康回归（硬性）**：hover 轮零 [T2fail]+odom 连续+悬停保持正常；route 轮 VINS 域健康（odom 连续/prop 峰米级）。
- 每轮：双 md5+紧凑袋+log 归档（flight.sh 硬化自动）+glitch 计数（四态表口径）。
- 栈纪律：新双 md5 登记+双件存档+STATUS 通告 @T1 @T3（T3 prereg v1.1 只改栈号）。

## 结果落点

- 三判据全过 → 门复位修复定稿入栈（fixface-2 代），单元 2 空中再 init 画像开跑（数据自此不被误触发污染）；
- V1 失败 → 回滚该两行（保留 1b 计数器）如实入账；
- V3 失败 → 栈换代引入回归=停用新栈回 4701bd3a，逐位 diff 审。
