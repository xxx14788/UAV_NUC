# goal_adopted 归因面注记 v1.0（T3 v11.1 单元 5 尾件；材料支持型注记，@T2 消费）

> 素材正源：`t2_results/INPUTFACE/1c_runs/warmup_pairs_v107.csv`（goal_adopted 列，WU2 复验批
> 8 对 16 轮）+ `t2_results/INPUTFACE/1b_bias_route/bias_constraint2_design_v1.md`（W4-ADOPTED
> 7/7 语义源）。T3 判读侧材料整理，供 T2 ②a 臂批（bias 约束②独立验证线）设计消费。

## 1. 两层分离（归因纯净度）

| 层 | 证据 | 状态 |
|---|---|---|
| 协议层（goal 切换） | **W4-ADOPTED 7/7**——goal 面修复验证全过（mission goal 被 FSM 采纳 7/7；warmup_pairs_v107 goal_adopted 列 8/8 A 臂=W2-RESTART 标记，E12P_A_r2 带 W4-ADOPTED(stoploss) 双标记） | **修复闭环** |
| 激励层（warmup 预热） | WU2 复验 A 臂 **1/8=12.5%** vs B 4/8=50%（−37.5pp，两批 32 轮同向） | **NOT-EFFECTIVE 维持** |

**归因分离结论**：goal 协议缺陷（第一批 −50.0pp 的 harness 层主因）修复验证通过后，复验批
仍 −37.5pp——NOT-EFFECTIVE 的归因不再有协议残留混杂，**纯净归因于激励形态本身**。

## 2. 材料支持面（@T2 约束②设计）

- A 臂 transit jump **4/7 数值对劣于 B 臂**（S8O 1.400 vs 0.333 / S8P 1.002 vs 0.142 /
  N8P 1.308 vs 0.076 / E12O 0.294 vs 0.095；仅 S12P 反向）——与「激励把 bias 状态推入
  大瞬态、任务段带着未平复瞬态」机理自洽（bias_constraint2_design_v1 §1 本夜新证据）。
- 该材料支持 1b 路线裁决「**约束漂移优先于先收敛**」：激励先收敛路线（①FEED 载体
  NO_VALID_CARRIER+③预热 NOT-EFFECTIVE）双证伪后，约束②（transit 窗 bias 强先验/
  物理域界阻断漂移吸收）为独立验证线。

## 3. T3 注记口径

- goal_adopted 7/7 与绿率 1/8 的分离=「协议修复成功」≠「激励有效」——两判读面分栏，
  禁以 adopted 通过推断绿率改善（材料方向相反）。
- X7 注记二/补记②（预热终态）与本注记衔接：NOT-EFFECTIVE 维持的归因基座从「goal 协议
  缺陷混淆面」升级为「纯净激励归因面」——X7 §7 消费时引用本注记为支持材料。
