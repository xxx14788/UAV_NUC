# 1c 预热对照批·格级前后绿率对比表（T3 统计面 batch1_v1131）

> 生成器 t3_warmup_greenrate_table_v1.0 (T3 v10.9 单元2; OUT=repo 正源) | 输入=/home/ghj/sitl_sim/t1_evidence/v11_31_2026-10-08/unit1_greenrate/warmup_pairs.csv | 生成 2026-10-09 04:00:09
> 判据正源=1b_bias_three_prereg_v1.md §2.3 冻结逐字: **预热臂绿率提升 ≥15pp 且配对方向一致 ≥6/8 → 有效**; 副=bias 收敛(末2s |d(Ba)/dt| 均值 < 初2s 均值 20% 判已收敛, 口径冻结, 收敛器=t1_warmup_bias_convergence.py 复用)。
> 口径: 绿=RESULT PASS; A=预热臂, B=无预热对照。

| cell | A(verdict/jump/arrive/bias收敛) | B(verdict/jump/arrive) | 对方向 |
|---|---|---|---|
| E12O | FAIL  j=0.168 arr=14.047 bc=NOT-CONVERGED | PASS  j=0.119 arr=0.393 | B优 |
| E12P | FAIL  j=0.160 arr=13.024 bc=NOT-CONVERGED | FAIL  j=NA arr=NA | 同 |
| E8P | FAIL  j=3.575 arr=8.898 bc=NOT-CONVERGED | FAIL  j=NA arr=NA | 同 |
| N8P | FAIL  j=0.096 arr=9.216 bc=NOT-CONVERGED | PASS  j=0.097 arr=0.099 | B优 |
| NE8O | FAIL  j=2.866 arr=9.495 bc=NOT-CONVERGED | PASS  j=0.144 arr=0.120 | B优 |
| S12P | FAIL  j=0.037 arr=10.945 bc=NOT-CONVERGED | FAIL  j=2.466 arr=9.713 | 同 |
| S8O | FAIL  j=0.050 arr=7.058 bc=NOT-CONVERGED | FAIL  j=2.246 arr=0.227 | 同 |
| S8P | FAIL  j=0.222 arr=7.209 bc=NOT-CONVERGED | PASS  j=0.081 arr=0.096 | B优 |

## 判据应用（冻结口径逐字套用）

- A(预热)绿率 **0/8=0.0%** vs B(无预热) **4/8=50.0%** → 提升 **-50.0pp**（判据 ≥+15pp: **不满足**）
- 配对方向（A 优向）**0/8**（判据 ≥6/8: **不满足**; 方向分化对合计 4, 其中 B 单绿 4）
- 副指标 jump: A<B 3 对 / A>B 3 对（登记不判 PASS/FAIL）
- **判决: NOT-EFFECTIVE(如实登记)**
- 新病面预案触发登记: **预热自伤面**（-50.0pp ≤ −15pp; 预注册 §2.3 分型登记条款兑现）
