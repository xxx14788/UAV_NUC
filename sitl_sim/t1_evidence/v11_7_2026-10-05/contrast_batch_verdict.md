# 单元 3 对照批汇总（三歧断案器收官；2026-10-06 05:2x）

> 三歧已被静态 diff（boot_diff_report）+T2 独立互证（commit 623202c）+T3 全库矩阵（DECISION_LOG 三歧行）合力定案；本对照批补飞行面三件。

## 1. hover 净轮 ×2（v2 臂，goal 0,0,1，SUPHV 口径）

| 轮 | 判 | 物理到位 | VINS 面 |
|---|---|---|---|
| HVNET1_050936 | FAIL（保守判） | **0.077m** | **跳变 2.985m**（物理净而 VINS 跳标本；与 boot-1 SUPHV3b 3.9m 同型=悬停面跳变跨 boot 在案） |
| HVNET2_0513xx | **PASS 四指标全绿** | 0.115m | jump 0.136 净（净轮序列新样本：DIAGGUARD2 0.418/VRG1 0.137/VRFY2 0.100/HVNET2 0.136） |

## 2. RA13/14 精确复刻轮（cauchy=4.0 全家桶 loss=1 cost_gate=1 staged=1 guard=1）

**RAREP1_051826 = PASS 四指标全绿**（到位 0.095m/jump 0.166/init +3s/disarm=1）。
- v4 栈+boot-2 上 cauchy=4.0 全家桶**全绿**——boot-1 DIAGCAUCHY never-init **未复现**（never-init=boot-1 特有或另有条件，栈代/机器态 confound 线索@T2）。
- 同位形 (8,-1,1) 05:01 v2 臂跳 24.2m vs 05:18 cauchy=4 臂全绿（17 分钟间隔）——臂间对照直接素材（剂量定量化@T2：单样本不定案）。

## 3. 组合矩阵新增行（在线飞行轮终版）

| 臂 | boot-0(v3栈) | boot-1(v4) | boot-2(v4) |
|---|---|---|---|
| loss=1∧cauchy=0（NaN 臂） | – | 风暴 4/4 | VRFY1 风暴 |
| loss=1∧cauchy=4.0（全家桶） | RA13/14 干净 | DIAGCAUCHY never-init | **RAREP1 全绿** |
| loss=0（v2：cg=1/staged=1/guard=1） | – | – | VRFY2 绿+X4 批跳变族 5/悬停 1 跳 1 绿 |
| guard only（VRG1 臂） | – | DIAGGUARD2 净面 | VRG1 全绿 |

**终版三歧**：Z（零成功）=NaN 臂专属已解；M（机器态）=跳变族时间维度（X2g3 同位形 56 分钟绿→巨跳）+ never-init boot 特异性——**收敛为"时间维度/会话面"嫌疑，非 boot 维度**；C（cauchy）=排除（cauchy=4.0 全家桶跨栈绿）。

## 4. 遗留件

①planner starve 修复（T1 harness 域：goal 订阅就绪探测门）②autoattach 扩名补 HVNET|RAREP ③跳变族机理=T2 X1prime/瞬态域主战（时间维度材料全在表）④never-init boot-1 特异性线索@T2。
