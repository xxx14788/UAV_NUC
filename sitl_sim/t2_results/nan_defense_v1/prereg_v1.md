# NaN 防线四件 预注册 v1（任务书 v11.17 §2.1；预案正源 nan_dissect_vrfy1/C1_verdict.md §5；写码前冻结）

## 触发判据（冻结；正常路径零行为差=各守卫在健康轮零触发）
- **D2 参数域断言**（C.1 §5.2）：载入处 `t2_vision_loss==1 && t2_cauchy_delta<=0` →
  `[T2NANDEF] FATAL` 打印 + exit(2) 拒启（fail-fast；覆盖一切臂/手工路径）。
- **D3 init 后置门扩展**（C.1 §5.3）：init_sane_post 增加 `isfinite(t2_last_initial_cost)
  ∧ termination_type!=FAILURE ∧ iterations>=1`（成员快照由 optimization() 每解后写入；
  违反=走既有 re-init 路径——VRFY1 111/111 风暴轮改判 never-init FAIL 而非风暴）。
- **D4 cost-median 退化守卫**（C.1 §5.4）：streak feed 处 `median<=0 ∨ !isfinite` →
  streak 清零 + 计数器 + 节流 WARN `[T2NANDEF]`（恢复 gate "cost 暴涨" 设计语义；
  -1 帧不再假触发）。
- **D5 prior NaN 防线**（C.1 §5.5，任务书列④获批）：preMarginalize 后校验 prior 块
  （MarginalizationFactor 构造块）residuals/jacobians 有限性；非有限=丢弃本次
  marginalization（delete 本次 marg info，保留上次干净 prior），计数+WARN——防 prior
  污染跨帧传播（交互链环 3）。

## 通告与凭据
- banner 新行：`[T2NANDEF] def=2/3/4/5 armed`（parameters 载入尾打印，恒开非选配）。
- 栈 md5 换代：build 后 vins_node/libvins_lib 新 md5 入册，x5_batch preflight 引用新凭据。
- 健康轮回归口径：D2 恒过（canonical 臂 loss=0）；D3 快照恒满足；D4 median 恒>0 有限；
  D5 prior 恒有限——四守卫零触发即零行为差；回归轮四指标与预建基线（C1=0.055 到位族）同族。

## 验证序列（批外低峰）
1. catkin build → gtest 全量+新增（守卫谓词单测）；
2. 毒配置注入：临时 arm 文件 loss=1∧cauchy=0 → vins_node 拒启（console [T2NANDEF] FATAL+
   非零退出+轮内 VINS init 门超时=ENV-FAIL 面）；
3. 正常臂回归 1 轮零行为差（build 后栈）。
