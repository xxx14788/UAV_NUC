# 1c 预热对照批·格级前后绿率对比表（T3 统计面 batch2_goalfix_v107）

> 生成器 t3_warmup_greenrate_table_v1.0 (T3 v10.9 单元2; OUT=repo 正源) | 输入=/home/ghj/sitl_sim/t2_results/INPUTFACE/1c_runs/warmup_pairs_v107.csv | 生成 2026-10-09 15:11:00
> 判据正源=1b_bias_three_prereg_v1.md §2.3 冻结逐字: **预热臂绿率提升 ≥15pp 且配对方向一致 ≥6/8 → 有效**; 副=bias 收敛(末2s |d(Ba)/dt| 均值 < 初2s 均值 20% 判已收敛, 口径冻结, 收敛器=t1_warmup_bias_convergence.py 复用)。
> 口径: 绿=RESULT PASS; A=预热臂, B=无预热对照。

| cell | A(verdict/jump/arrive/bias收敛) | B(verdict/jump/arrive) | 对方向 |
|---|---|---|---|
| E12O | FAIL  j=0.294 arr=13.202 bc=NOT-CONVERGED | PASS  j=0.095 arr=0.307 | B优 |
| E12P | FAIL  j=NA arr=NA bc=NOT-CONVERGED | FAIL  j=NA arr=NA | 同 |
| E8P | FAIL  j=NA arr=NA bc=NOT-CONVERGED | FAIL  j=NA arr=NA | 同 |
| N8P | FAIL  j=1.308 arr=0.295 bc=NOT-CONVERGED | PASS  j=0.076 arr=0.111 | B优 |
| NE8O | PASS  j=0.168 arr=0.140 bc=NOT-CONVERGED | PASS  j=0.145 arr=0.227 | 同 |
| S12P | FAIL  j=4.781 arr=0.101 bc=NOT-CONVERGED | FAIL  j=7.162 arr=11.377 | 同 |
| S8O | FAIL  j=1.400 arr=0.064 bc=NOT-CONVERGED | FAIL  j=0.333 arr=6.981 | 同 |
| S8P | FAIL  j=1.002 arr=8.388 bc=NOT-CONVERGED | PASS  j=0.142 arr=0.083 | B优 |

## 判据应用（冻结口径逐字套用）

- A(预热)绿率 **1/8=12.5%** vs B(无预热) **4/8=50.0%** → 提升 **-37.5pp**（判据 ≥+15pp: **不满足**）
- 配对方向（A 优向）**0/8**（判据 ≥6/8: **不满足**; 方向分化对合计 3, 其中 B 单绿 3）
- 副指标 jump: A<B 1 对 / A>B 5 对（登记不判 PASS/FAIL）
- **判决: NOT-EFFECTIVE(如实登记)**
- 新病面预案触发登记: **预热自伤面**（-37.5pp ≤ −15pp; 预注册 §2.3 分型登记条款兑现）
