# ②b 层①窗内偏差度量注记 v1.0（2026-10-11 收官册单元 7 末件）

- 工具=t2_window_bias_metric.py（[T2diag] |Bas|/|Bgs| 窗内 start/end/Δ/max；C.2-W 写侧截断面只作带误差量化）。
- 实跑=②b BX 批 4 轮（E12P A/B+E8P A/B_r2；第 5 轮 BX_E8P_B_054025=env 壳无 diag 面如实计 miss 外）：**|Bas| 窗内漂移 Δ+0.127~+1.006（中位 +0.537）**，max 达 0.53~7.12；|Bgs| Δ 全部 |·|≤0.009（加速度计偏置主导）。
- 数值面结论：**bias 漂移确实在场且量级可观**——为 v10.10 终判「漂移可治但绿率对 bias 约束零响应（②a 过紧自伤/②b 锁未 ENGAGE=两案夹逼）」补齐逐轮数值证据；bias 路线证伪定案不翻案。
- CSV=window_bias_metric_2b_v1.csv（4 行）。
