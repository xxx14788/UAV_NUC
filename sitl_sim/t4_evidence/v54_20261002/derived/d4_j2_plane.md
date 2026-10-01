# d4_j2_plane.md — 单元2 数据面（D4，2026-10-02）

八袋 × 十指标：a) 相关矩阵（Pearson+Spearman 双列）；b) 跨袋一致性（逐指标 CV、Kendall W、离群袋点名）；c) 饱和三例去饱和双列（CSV）。
判据预注册在主会话：本文件只给数，不含判语。计算脚本：`scripts/d4_calc.py`（本机 python 3.12.7 / numpy 2.4.4 / pandas 3.0.2 / scipy 1.17.1，data_dictionary §3）。

## 0. 袋集合口径（两口径冲突登记）

- **主面板（Set A，按任务'为准'条款）**：`raw/vision_inputs/j2_threshold_table_v1.json` 的 `bags` 字段 8 袋 = U3PG_210307, U3PO_211438, U3PR2_213717, U3PH_210708, U3PR1_212450, X1final_173345, WC2OBS1_030927, WC2OBS1_032005。
- **附录面板（Set B，任务括号字面）**：主池6+扩展池X1img2/U3PR1 = X1img_015950, WC2OBS1_030927, WC2OBS1_032005, U3PG_210307, U3PO_211438, U3PR2_213717, X1img2_020706, U3PR1_212450。
- 两口径差 2 袋：Set A 含 U3PH_210708/X1final_173345（扩展池），Set B 含 X1img_015950/X1img2_020706（扩展池）。
- 扩展池判定依据 `raw/matrix_5faces.md`（扩展池 4 袋=X1img2/U3PH/U3PR1/X1final；X1img 属主池 6 袋）。

## 0.1 数据源与字段（逐数字溯源基底）

| 项 | 源文件（raw/vision_inputs/ 下） | 字段/口径 |
|---|---|---|
| 袋级 p50（10 指标） | metrics_<bag>.json（各袋映射见 §1 脚注） | `metrics.<metric>.p50`（tag==''主帧口径，n 见表） |
| WC2×2 的 supply_frac/grid4x4 | metrics_WC2OBS1_030927_w3.json / _032005_w3.json | 同上（base json 无此两键，仅 _w3 变体有；两版 d12_sigma_p25.p50 逐位一致=1.0289948230251014 / 1.0297822525958304） |
| X1img/X1img2 的 supply_frac | 派生 | `per_frame.corners_gFT/150`（M1 定义=角点数/max_cnt，max_cnt=150，t4_verdicts_v2.md L209；表中标'派生'） |
| 帧级读数（§4、口径验证） | 同上 json | `per_frame[].<metric>`（tag==''为主帧；WC2 base 有 5 帧整组缺 d12_sigma_*/p_sat 键，帧级计算按键存在性过滤） |
| 饱和三例名单 | raw/anchors.json | `m1_saturation_three_bags`=U3PH/U3PR1/X1final（源 t4_verdicts_v2.md L221-223） |
| 十指标清单 | raw/vision_inputs/j2_threshold_table_v1.json | `threshold_table_v1` 10 键（=data_dictionary §1 十二键去掉 d12_sigma_flat/gamma_pair） |

**口径验证（本次实测运行，非转录）：**
- 验证1：10 份 json（含 2 份 _w3）全部 metrics 键，由 per_frame(tag=='') 重算 P10/P50/P90 与 `metrics.<m>.p10/p50/p90` 比对：124 组，不一致 0 组；帧数与 metrics.n 不一致的组：0 组；跳过 12 组=gamma_pair（无逐帧列，帧间统计指标，不在十指标内）。
- 验证2：Set A 袋级 p50 跨袋 P10/P50/P90 vs j2_threshold_table_v1.json（容差 rel≤0.5%）：30 组，超容差 0 组。
- WC2 袋名映射验证：metrics_WC2OBS1_030927(.json/_w3).metrics.d12_sigma_p25.p50=1.0289948=verdicts L218 WC2#1；032005=1.0297823=WC2#2——anchors.json 中'依顺序推断'的对应经 json 逐位证实。
- 饱和帧≡corners_gFT==150 等价性（帧级逐一核验）：U3PH_210708=True；U3PR1_212450=True；X1final_173345=True。

## 1. 输入数据面：袋级 p50（§2/§3 的唯一输入）

n 列 = 该袋各指标 `metrics.<m>.n`（同一取值时单值，否则逐指标列出）。p_sat 原始量级 1e-5（U3PH/X1final 袋级 p50=0）。

| 袋 | 池 | n | p_sat | hist_range_p1_p99 | med_gray | corners_gFT | grad_med | grad_dir_maxbin_frac | grad_dir_entropy_norm | d12_sigma_p25 | supply_frac | grid4x4_occupancy_frac |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U3PG_210307 | 主池 | 73(多数指标)；68(d12系) | 1.63e-05 | 149.00000 | 83.00000 | 90.00000 | 8.24621 | 0.24622 | 0.82456 | 1.03078 | 0.60000 | 0.62500 |
| U3PO_211438 | 主池 | 74(多数指标)；67(d12系) | 2.60e-05 | 152.00000 | 155.00000 | 121.00000 | 8.48528 | 0.27869 | 0.78054 | 1.02891 | 0.80667 | 0.75000 |
| U3PR2_213717 | 主池 | 72(多数指标)；67(d12系) | 9.77e-06 | 154.00000 | 80.00000 | 71.00000 | 8.48528 | 0.25259 | 0.82899 | 1.03009 | 0.47333 | 0.68750 |
| U3PH_210708 | 扩展池 | 72(多数指标)；68(d12系) | 0.00000 | 4.00000 | 178.00000 | 150.00000 | 4.47214 | 0.07968 | 0.99096 | 1.02185 | 1.00000 | 1.00000 |
| U3PR1_212450 | 扩展池 | 72(多数指标)；68(d12系) | 1.63e-05 | 148.00000 | 167.00000 | 126.00000 | 8.24621 | 0.27589 | 0.78981 | 1.03111 | 0.84000 | 0.93750 |
| X1final_173345 | 扩展池 | 72(多数指标)；68(d12系) | 0.00000 | 61.00000 | 44.00000 | 143.50000 | 5.09902 | 0.15467 | 0.94716 | 1.02270 | 0.95667 | 1.00000 |
| WC2OBS1_030927 | 主池 | 72(多数指标)；67(d12系) | 6.51e-06 | 148.00000 | 175.00000 | 102.00000 | 7.61577 | 0.23158 | 0.84747 | 1.02899 | 0.68000 | 0.50000 |
| WC2OBS1_032005 | 主池 | 73(多数指标)；66(d12系) | 1.63e-05 | 149.00000 | 175.00000 | 130.00000 | 8.24621 | 0.28010 | 0.78785 | 1.02978 | 0.86667 | 0.93750 |
| X1img_015950 | 扩展池 | 72(多数指标)；67(d12系) | 0.00000 | 139.00000 | 39.00000 | 37.00000 | 0.00000 | 0.20041 | 0.86947 | 0.00000 | 0.24667 | N-A(旧schema缺) |
| X1img2_020706 | 扩展池 | 79(多数指标)；68(d12系) | 0.00000 | 139.00000 | 87.00000 | 87.00000 | 0.00000 | 0.27093 | 0.84280 | 0.00000 | 0.58000 | N-A(旧schema缺) |

（前 8 行=Set A 主面板输入；后 2 行仅入 Set B 附录面板。N-A=该袋 json 无该指标键。）

## 2. a) 十指标相关矩阵（Pearson + Spearman 双列）

### 2.1 Set A（阈值表 v1 袋集合，8 袋）

单元=袋级 p50（§1 表）。n=8/对（10 指标 8 袋齐，无缺失）。注：supply_frac≡corners_gFT/150 为定义恒等式（M1 口径，已帧级验证零例外），故凡涉这两指标的对，Pearson/Spearman 数值成对相同（corners×supply 恒为 1.000）。

| 指标对 | n | Pearson r | Spearman ρ | 注 |
|---|---|---|---|---|
| p_sat × hist_range_p1_p99 | 8 | 0.752 | 0.696 |  |
| p_sat × med_gray | 8 | 0.243 | -0.049 |  |
| p_sat × corners_gFT | 8 | -0.289 | -0.405 |  |
| p_sat × grad_med | 8 | 0.829 | 0.797 |  |
| p_sat × grad_dir_maxbin_frac | 8 | 0.837 | 0.872 |  |
| p_sat × grad_dir_entropy_norm | 8 | -0.891 | -0.970 |  |
| p_sat × d12_sigma_p25 | 8 | 0.751 | 0.552 |  |
| p_sat × supply_frac | 8 | -0.289 | -0.405 |  |
| p_sat × grid4x4_occupancy_frac | 8 | -0.262 | -0.360 |  |
| hist_range_p1_p99 × med_gray | 8 | 0.039 | -0.376 |  |
| hist_range_p1_p99 × corners_gFT | 8 | -0.691 | -0.771 |  |
| hist_range_p1_p99 × grad_med | 8 | 0.976 | 0.957 |  |
| hist_range_p1_p99 × grad_dir_maxbin_frac | 8 | 0.971 | 0.711 |  |
| hist_range_p1_p99 × grad_dir_entropy_norm | 8 | -0.948 | -0.687 |  |
| hist_range_p1_p99 × d12_sigma_p25 | 8 | 0.954 | 0.482 |  |
| hist_range_p1_p99 × supply_frac | 8 | -0.691 | -0.771 |  |
| hist_range_p1_p99 × grid4x4_occupancy_frac | 8 | -0.612 | -0.573 |  |
| med_gray × corners_gFT | 8 | 0.315 | 0.395 |  |
| med_gray × grad_med | 8 | 0.114 | -0.370 |  |
| med_gray × grad_dir_maxbin_frac | 8 | 0.100 | -0.012 |  |
| med_gray × grad_dir_entropy_norm | 8 | -0.210 | 0.048 |  |
| med_gray × d12_sigma_p25 | 8 | 0.136 | -0.204 |  |
| med_gray × supply_frac | 8 | 0.315 | 0.395 |  |
| med_gray × grid4x4_occupancy_frac | 8 | 0.037 | 0.079 |  |
| corners_gFT × grad_med | 8 | -0.686 | -0.700 |  |
| corners_gFT × grad_dir_maxbin_frac | 8 | -0.532 | -0.286 |  |
| corners_gFT × grad_dir_entropy_norm | 8 | 0.493 | 0.310 |  |
| corners_gFT × d12_sigma_p25 | 8 | -0.689 | -0.619 |  |
| corners_gFT × supply_frac | 8 | 1.000 | 1.000 |  |
| corners_gFT × grid4x4_occupancy_frac | 8 | 0.808 | 0.892 |  |
| grad_med × grad_dir_maxbin_frac | 8 | 0.966 | 0.786 |  |
| grad_med × grad_dir_entropy_norm | 8 | -0.970 | -0.786 |  |
| grad_med × d12_sigma_p25 | 8 | 0.973 | 0.552 |  |
| grad_med × supply_frac | 8 | -0.686 | -0.700 |  |
| grad_med × grid4x4_occupancy_frac | 8 | -0.556 | -0.472 |  |
| grad_dir_maxbin_frac × grad_dir_entropy_norm | 8 | -0.989 | -0.952 |  |
| grad_dir_maxbin_frac × d12_sigma_p25 | 8 | 0.930 | 0.524 |  |
| grad_dir_maxbin_frac × supply_frac | 8 | -0.532 | -0.286 |  |
| grad_dir_maxbin_frac × grid4x4_occupancy_frac | 8 | -0.420 | -0.205 |  |
| grad_dir_entropy_norm × d12_sigma_p25 | 8 | -0.935 | -0.500 |  |
| grad_dir_entropy_norm × supply_frac | 8 | 0.493 | 0.310 |  |
| grad_dir_entropy_norm × grid4x4_occupancy_frac | 8 | 0.402 | 0.265 |  |
| d12_sigma_p25 × supply_frac | 8 | -0.689 | -0.619 |  |
| d12_sigma_p25 × grid4x4_occupancy_frac | 8 | -0.554 | -0.482 |  |
| supply_frac × grid4x4_occupancy_frac | 8 | 0.808 | 0.892 |  |

紧凑矩阵（上三角=Pearson，下三角=Spearman）：

| | p_sat | hist_range_p1_p99 | med_gray | corners_gFT | grad_med | grad_dir_maxbin_frac | grad_dir_entropy_norm | d12_sigma_p25 | supply_frac | grid4x4_occupancy_frac |
|---|---|---|---|---|---|---|---|---|---|---|
| p_sat | — | 0.75 | 0.24 | -0.29 | 0.83 | 0.84 | -0.89 | 0.75 | -0.29 | -0.26 |
| hist_range_p1_p99 | 0.70 | — | 0.04 | -0.69 | 0.98 | 0.97 | -0.95 | 0.95 | -0.69 | -0.61 |
| med_gray | -0.05 | -0.38 | — | 0.31 | 0.11 | 0.10 | -0.21 | 0.14 | 0.31 | 0.04 |
| corners_gFT | -0.41 | -0.77 | 0.40 | — | -0.69 | -0.53 | 0.49 | -0.69 | 1.00 | 0.81 |
| grad_med | 0.80 | 0.96 | -0.37 | -0.70 | — | 0.97 | -0.97 | 0.97 | -0.69 | -0.56 |
| grad_dir_maxbin_frac | 0.87 | 0.71 | -0.01 | -0.29 | 0.79 | — | -0.99 | 0.93 | -0.53 | -0.42 |
| grad_dir_entropy_norm | -0.97 | -0.69 | 0.05 | 0.31 | -0.79 | -0.95 | — | -0.93 | 0.49 | 0.40 |
| d12_sigma_p25 | 0.55 | 0.48 | -0.20 | -0.62 | 0.55 | 0.52 | -0.50 | — | -0.69 | -0.55 |
| supply_frac | -0.41 | -0.77 | 0.40 | 1.00 | -0.70 | -0.29 | 0.31 | -0.62 | — | 0.81 |
| grid4x4_occupancy_frac | -0.36 | -0.57 | 0.08 | 0.89 | -0.47 | -0.20 | 0.27 | -0.48 | 0.89 | — |

### 2.2 Set B（任务括号口径，附录）

单元=袋级 p50（§1 表）。X1img/X1img2 旧 schema 降级：涉 grid4x4 的对 n=6；X1img/X1img2 的 supply 为派生值（corners/150）。

| 指标对 | n | Pearson r | Spearman ρ | 注 |
|---|---|---|---|---|
| p_sat × hist_range_p1_p99 | 8 | 0.758 | 0.700 |  |
| p_sat × med_gray | 8 | 0.568 | 0.370 |  |
| p_sat × corners_gFT | 8 | 0.720 | 0.712 |  |
| p_sat × grad_med | 8 | 0.804 | 0.803 |  |
| p_sat × grad_dir_maxbin_frac | 8 | 0.613 | 0.663 |  |
| p_sat × grad_dir_entropy_norm | 8 | -0.896 | -0.933 |  |
| p_sat × d12_sigma_p25 | 8 | 0.778 | 0.556 |  |
| p_sat × supply_frac | 8 | 0.720 | 0.712 |  |
| p_sat × grid4x4_occupancy_frac | 6 | 0.475 | 0.585 | grid4x4 缺2袋(旧schema) |
| hist_range_p1_p99 × med_gray | 8 | 0.458 | 0.037 |  |
| hist_range_p1_p99 × corners_gFT | 8 | 0.485 | 0.242 |  |
| hist_range_p1_p99 × grad_med | 8 | 0.942 | 0.956 |  |
| hist_range_p1_p99 × grad_dir_maxbin_frac | 8 | 0.410 | 0.400 |  |
| hist_range_p1_p99 × grad_dir_entropy_norm | 8 | -0.622 | -0.630 |  |
| hist_range_p1_p99 × d12_sigma_p25 | 8 | 0.926 | 0.476 |  |
| hist_range_p1_p99 × supply_frac | 8 | 0.485 | 0.242 |  |
| hist_range_p1_p99 × grid4x4_occupancy_frac | 6 | -0.088 | 0.030 | grid4x4 缺2袋(旧schema) |
| med_gray × corners_gFT | 8 | 0.913 | 0.874 |  |
| med_gray × grad_med | 8 | 0.633 | 0.075 |  |
| med_gray × grad_dir_maxbin_frac | 8 | 0.592 | 0.527 |  |
| med_gray × grad_dir_entropy_norm | 8 | -0.689 | -0.419 |  |
| med_gray × d12_sigma_p25 | 8 | 0.657 | 0.217 |  |
| med_gray × supply_frac | 8 | 0.913 | 0.874 |  |
| med_gray × grid4x4_occupancy_frac | 6 | 0.347 | 0.191 | grid4x4 缺2袋(旧schema) |
| corners_gFT × grad_med | 8 | 0.653 | 0.346 |  |
| corners_gFT × grad_dir_maxbin_frac | 8 | 0.830 | 0.762 |  |
| corners_gFT × grad_dir_entropy_norm | 8 | -0.869 | -0.762 |  |
| corners_gFT × d12_sigma_p25 | 8 | 0.657 | 0.431 |  |
| corners_gFT × supply_frac | 8 | 1.000 | 1.000 |  |
| corners_gFT × grid4x4_occupancy_frac | 6 | 0.667 | 0.754 | grid4x4 缺2袋(旧schema) |
| grad_med × grad_dir_maxbin_frac | 8 | 0.443 | 0.507 |  |
| grad_med × grad_dir_entropy_norm | 8 | -0.691 | -0.741 |  |
| grad_med × d12_sigma_p25 | 8 | 0.998 | 0.547 |  |
| grad_med × supply_frac | 8 | 0.653 | 0.346 |  |
| grad_med × grid4x4_occupancy_frac | 6 | 0.508 | 0.313 | grid4x4 缺2袋(旧schema) |
| grad_dir_maxbin_frac × grad_dir_entropy_norm | 8 | -0.854 | -0.881 |  |
| grad_dir_maxbin_frac × d12_sigma_p25 | 8 | 0.416 | 0.216 |  |
| grad_dir_maxbin_frac × supply_frac | 8 | 0.830 | 0.762 |  |
| grad_dir_maxbin_frac × grid4x4_occupancy_frac | 6 | 0.912 | 0.899 | grid4x4 缺2袋(旧schema) |
| grad_dir_entropy_norm × d12_sigma_p25 | 8 | -0.663 | -0.431 |  |
| grad_dir_entropy_norm × supply_frac | 8 | -0.869 | -0.762 |  |
| grad_dir_entropy_norm × grid4x4_occupancy_frac | 6 | -0.853 | -0.754 | grid4x4 缺2袋(旧schema) |
| d12_sigma_p25 × supply_frac | 8 | 0.657 | 0.431 |  |
| d12_sigma_p25 × grid4x4_occupancy_frac | 6 | 0.397 | 0.232 | grid4x4 缺2袋(旧schema) |
| supply_frac × grid4x4_occupancy_frac | 6 | 0.667 | 0.754 | grid4x4 缺2袋(旧schema) |

## 3. b) 跨袋一致性表

定义（预述）：CV=袋级 p50 的 sd(ddof=1)/|mean|；离群袋=Tukey 1.5×IQR 栅栏外者；
W_seg=逐指标 Kendall 一致性系数，评级者=3 个提帧段（metrics.<m>.by_seg_median seg0/1/2 的 p50），主题=n_seg 袋，并列秩修正；
W_overall=评级者=10 指标（袋级 p50），主题=8 袋。χ²=k(n−1)W、df=n−1（大样本近似式，仅列出不解读）。

### 3.1 Set A（阈值表 v1 袋集合）

| 指标 | n_bags | mean(p50) | sd | CV | n_seg | W_seg(k=3) | χ²_seg(df) | 离群袋（Tukey 1.5×IQR） | 栅栏 |
|---|---|---|---|---|---|---|---|---|---|
| p_sat | 8 | 1.14e-05 | 9.04e-06 | 0.794 | 8 | 0.798 | 16.754 (df=7) | 无 | [-1.22e-05, 3.34e-05] |
| hist_range_p1_p99 | 8 | 120.62500 | 56.52291 | 0.469 | 8 | 0.916 | 19.236 (df=7) | U3PH_210708, X1final_173345 | [91.0000, 185.0000] |
| med_gray | 8 | 132.12500 | 54.00645 | 0.409 | 8 | 0.924 | 19.413 (df=7) | 无 | [-56.8750, 314.1250] |
| corners_gFT | 8 | 116.68750 | 27.06202 | 0.232 | 8 | 0.968 | 20.333 (df=7) | 无 | [47.4375, 184.9375] |
| grad_med | 8 | 7.36202 | 1.62154 | 0.220 | 8 | 0.759 | 15.949 (df=7) | U3PH_210708 | [5.0075, 10.2851] |
| grad_dir_maxbin_frac | 8 | 0.22493 | 0.07154 | 0.318 | 8 | 0.778 | 16.333 (df=7) | U3PH_210708 | [0.1160, 0.3729] |
| grad_dir_entropy_norm | 8 | 0.84967 | 0.07812 | 0.092 | 8 | 0.799 | 16.778 (df=7) | 无 | [0.6647, 0.9970] |
| d12_sigma_p25 | 8 | 1.02803 | 0.00364 | 0.004 | 8 | 0.778 | 16.333 (df=7) | U3PH_210708, X1final_173345 | [1.0230, 1.0346] |
| supply_frac | 8 | 0.77792 | 0.18041 | 0.232 | 8 | 0.968 | 20.333 (df=7) | 无 | [0.3163, 1.2329] |
| grid4x4_occupancy_frac | 8 | 0.80469 | 0.19027 | 0.236 | 8 | 0.984 | 20.656 (df=7) | 无 | [0.2500, 1.3750] |

**W_overall**（评级者=10 指标，主题=8 袋）：W=0.0783，χ²=5.481，df=7。

### 3.2 Set B（任务括号口径，附录）

| 指标 | n_bags | mean(p50) | sd | CV | n_seg | W_seg(k=3) | χ²_seg(df) | 离群袋（Tukey 1.5×IQR） | 栅栏 |
|---|---|---|---|---|---|---|---|---|---|
| p_sat | 8 | 1.14e-05 | 9.04e-06 | 0.794 | 8 | 0.798 | 16.754 (df=7) | 无 | [-1.22e-05, 3.34e-05] |
| hist_range_p1_p99 | 8 | 147.25000 | 5.49675 | 0.037 | 8 | 0.810 | 17.004 (df=7) | X1img_015950, X1img2_020706 | [139.7500, 155.7500] |
| med_gray | 8 | 120.12500 | 53.58954 | 0.446 | 8 | 0.893 | 18.763 (df=7) | 无 | [-47.8750, 299.1250] |
| corners_gFT | 8 | 95.50000 | 31.48242 | 0.330 | 8 | 0.958 | 20.111 (df=7) | 无 | [24.1250, 181.1250] |
| grad_med | 8 | 6.16562 | 3.81503 | 0.619 | 8 | 0.850 | 17.843 (df=7) | X1img_015950, X1img2_020706 | [1.8206, 12.1972] |
| grad_dir_maxbin_frac | 8 | 0.25455 | 0.02801 | 0.110 | 8 | 0.603 | 12.667 (df=7) | 无 | [0.1915, 0.3276] |
| grad_dir_entropy_norm | 8 | 0.82144 | 0.03231 | 0.039 | 8 | 0.524 | 11.000 (df=7) | 无 | [0.7073, 0.9259] |
| d12_sigma_p25 | 8 | 0.77246 | 0.47677 | 0.617 | 8 | 0.517 | 10.864 (df=7) | X1img_015950, X1img2_020706 | [0.3838, 1.4181] |
| supply_frac | 8 | 0.63667 | 0.20988 | 0.330 | 6 | 0.924 | 13.857 (df=5) | 无 | [0.1608, 1.2075] |
| grid4x4_occupancy_frac | 6 | 0.73958 | 0.17418 | 0.236 | 6 | 0.987 | 14.806 (df=5) | 无 | [0.2656, 1.2656] |

**W_overall**（评级者=9 指标，主题=8 袋）：W=0.3366，χ²=21.208，df=7。注：n_seg<8 行的 W_seg 仅基于有 by_seg_median 键的袋（X1img/X1img2 无 supply/grid 键）；W=N-A 为全并列（S=0，分母为 0）。

## 4. c) 饱和三例去饱和双列（详表=`d4_saturation_dual.csv`）

定义（预述）：饱和帧≡该帧 per_frame.supply_frac ≥ 1.0−1e-9（角点数达 max_cnt=150 封顶=检测器删失帧）；已核验与 corners_gFT==150 帧级一一等价（§0.1）。
原值分位=tag==''主帧全量 numpy.percentile(linear) 重算（与 json 口径一致，验证1）；去饱和分位=剔除饱和帧后重算。
受影响判据（预述）：该指标 4 个分位任一 |relΔ|>1%（relΔ=Δ/|原值|；原值=0 且去饱和≠0 记 inf→受影响）。
明细=120 行（3 袋×10 指标×4 分位）；列=pool,bag,metric,n_orig,n_sat_removed,removal_rate,n_desat,quantile,orig,desat,delta,rel_delta,affected_1pct。

| 袋 | 池 | n_orig | n_sat | 剔除率 | n_desat | 受影响指标（|relΔ|>1%，括号=最大|relΔ|） |
|---|---|---|---|---|---|---|
| U3PH_210708 | 扩展池 | 72 | 68 | 0.9444 | 4 | p_sat(max|relΔ|=inf)；hist_range_p1_p99(max|relΔ|=36.250)；med_gray(max|relΔ|=0.542)；corners_gFT(max|relΔ|=0.531)；grad_med(max|relΔ|=0.881)；grad_dir_maxbin_frac(max|relΔ|=2.052)；grad_dir_entropy_norm(max|relΔ|=0.168)；d12_sigma_p25(max|relΔ|=0.011)；supply_frac(max|relΔ|=0.531)；grid4x4_occupancy_frac(max|relΔ|=0.438) |
| U3PR1_212450 | 扩展池 | 72 | 5 | 0.0694 | 67 | p_sat(max|relΔ|=0.200)；med_gray(max|relΔ|=0.022)；corners_gFT(max|relΔ|=0.023)；supply_frac(max|relΔ|=0.023)；grid4x4_occupancy_frac(max|relΔ|=0.067) |
| X1final_173345 | 扩展池 | 72 | 21 | 0.2917 | 51 | hist_range_p1_p99(max|relΔ|=0.111)；med_gray(max|relΔ|=0.773)；corners_gFT(max|relΔ|=0.109)；grad_med(max|relΔ|=0.387)；grad_dir_maxbin_frac(max|relΔ|=0.155)；supply_frac(max|relΔ|=0.109)；grid4x4_occupancy_frac(max|relΔ|=0.113) |

三袋均为扩展池（matrix_5faces.md 扩展池 4 袋口径）。CSV 绝对路径：`D:/drone_VINS/t4_work_20261002/derived/d4_saturation_dual.csv`。

## 5. 缺失/降级/口径登记（warnings）

1. 袋集合两口径冲突：任务括号（主池6+X1img2/U3PR1）≠ j2_threshold_table_v1.json `bags`（差 U3PH/X1final ↔ X1img/X1img2）。按任务'为准'条款以阈值表袋集合为主面板（Set A），括号口径全量降为附录（Set B）。
2. metrics_X1img_sim.json / metrics_X1img2_sim.json 为旧 schema：`metrics` 无 supply_frac/grid4x4_occupancy_frac 键，`per_frame` 亦无该两列（W3 工具增量前产物，t4_verdicts_v2.md L163）。Set B 降级：涉 grid4x4 的相关/一致性 n=6；X1img/X1img2 的 supply_frac 以 corners_gFT/150 派生（M1 定义恒等式；已在其余 3 袋帧级验证 supply≡corners/150 零例外）。另注：该两袋 grad_med 与 d12_sigma_p25 袋级 p50=0.0 为 json 原值非缺失（实测 X1img2 帧级 grad_med 唯一值={0, 14.142, 16.0}，中位=0），涉该两袋的 Set B 表中相关行受此零值影响。
3. metrics_WC2OBS1_030927.json / _032005.json（base）同样缺 supply/grid 两键：Set A 该两指标取自 _w3 变体；两版 d12_sigma_p25.p50 与 n 逐位一致（67/66）。
4. 全部 10 袋的 per_frame 均有 d12_sigma_flat/d12_sigma_p25/d12_flat_frac 三键缺帧（每袋 4~11 帧，如 WC2 base 030927 有 5 帧 idx 22/45/68/91/114）：metrics 的 d12 n=n_primary−缺帧数（帧级计算按键存在性过滤，验证1 帧数比对 0 组不一致）；p_sat 与其余指标不缺帧；袋级 p50 直接取 json 值不受影响。
5. U3PH_210708 去饱和后仅剩 n=4 帧：其去饱和 P10/P25/P50/P90 为 4 个点上的分位，数值仅按算式给出，不构成任何阈值或策略建议。
6. p_sat 口径注记：Set A 中 U3PH/X1final 袋级 p50=0.000、其余袋 1e-5 量级（data_dictionary §1 引 verdicts L239'p_sat 全零'为袋级截断显示）；其 CV/W 数值对该量级敏感。
7. 口径出入登记（不裁决）：本文件 X1img_015950 corners_gFT 袋级 p50=37.0（主帧 n=72 与全帧 n=139 两基下同为 37，json 原值），而 anchors.json era_effect（源 t4_verdicts_v2.md L213）记 pre_inject_X1img_p50=45（0.30）——37≠45，L213 口径（提帧轮次/窗口）未在本任务复算范围内，仅登记差异。
8. 验证1 不一致 0/124 组（跳过 gamma_pair 12 组）；帧数 vs metrics.n 不一致 0 组；验证2 超容差 0/30 组（明细见 §0.1）。除此之外未做任何显著性或合格性表述。
9. 零 NUC IO：全部输入为 raw/vision_inputs/ 本地副本；未触碰 rosbag/重放/NUC/git。

