# 实机域估计质量画像 v1(五袋判读原始面;报告 v2 主体素材)

## scen0_static (static) — IN-EXPECT
- 预期: 零位移(<0.05m)+零跳变
- n: 2766
- dur_s: 184.5
- rate_hz: 15.0
- pathlen_m: 0.292
- maxjump_m: 0.001
- jumps_gt_05cm: 0
- jumps_gt_10cm: 0
- end_drift_m: 0.003
- drift_rate_m_per_min: 0.001
- env_x_m: 0.0017
- env_y_m: 0.0033
- env_z_m: 0.0022
- lindrift_x_m: -0.0015
- lindrift_y_m: -0.0029
- lindrift_z_m: 0.0019

## scen1_microshake (static) — IN-EXPECT
- 预期: 零位移(<0.05m)+零跳变
- n: 2240
- dur_s: 149.4
- rate_hz: 15.0
- pathlen_m: 0.115
- maxjump_m: 0.0003
- jumps_gt_05cm: 0
- jumps_gt_10cm: 0
- end_drift_m: 0.0007
- drift_rate_m_per_min: 0.0003
- env_x_m: 0.0004
- env_y_m: 0.0007
- env_z_m: 0.0009
- lindrift_x_m: 0.0001
- lindrift_y_m: -0.0005
- lindrift_z_m: 0.0009

## scen2_slowmove (slowmove) — IN-EXPECT
- 预期: 平滑轨迹+端点漂移量化(观测值入表)
- n: 3589
- dur_s: 239.4
- rate_hz: 15.0
- pathlen_m: 4.883
- maxjump_m: 0.0246
- jumps_gt_05cm: 0
- jumps_gt_10cm: 0
- end_drift_m: 0.8554
- drift_rate_m_per_min: 0.2144
- env_x_m: 1.021
- env_y_m: 0.8439
- env_z_m: 0.3121
- lindrift_x_m: -0.348
- lindrift_y_m: 0.1795
- lindrift_z_m: 0.1906

## scen3_walk (walk) — IN-EXPECT
- 预期: 米级位移+往返漂移量化(观测值入表)
- n: 3590
- dur_s: 239.4
- rate_hz: 15.0
- pathlen_m: 30.012
- maxjump_m: 0.0523
- jumps_gt_05cm: 2
- jumps_gt_10cm: 0
- end_drift_m: 0.0579
- drift_rate_m_per_min: 0.0145
- env_x_m: 3.5424
- env_y_m: 4.7339
- env_z_m: 0.2196
- trips: 4
- trip_peak_spread_m: 2.3765
- peak_pair_dists: 3.0891/2.5056/2.6043

## scen4_slide (slide) — IN-EXPECT
- 预期: 往返重复性(观测值入表)
- n: 2691
- dur_s: 179.5
- rate_hz: 15.0
- pathlen_m: 2.163
- maxjump_m: 0.0029
- jumps_gt_05cm: 0
- jumps_gt_10cm: 0
- end_drift_m: 0.392
- drift_rate_m_per_min: 0.1311
- env_x_m: 0.3537
- env_y_m: 0.7466
- env_z_m: 0.0069
- trips: 2
- trip_peak_spread_m: 0.0705
- peak_pair_dists: 0.7998

