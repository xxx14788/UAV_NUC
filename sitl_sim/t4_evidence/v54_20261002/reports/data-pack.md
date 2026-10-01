# T4 v5.4 池内深挖数据包（data-pack）

- 生成：2026-10-02，汇总员（B4，attempt=1）。素材根 `D:/drone_VINS/t4_work_20261002/`（raw/ 盘点+素材、derived/ 深挖产物）。
- 纪律声明：本文件为**纯数据面**——只登记数字、表格索引与溯源路径；不含判语/PASS/FAIL/因果断语/修复建议；判据预注册与判读文定稿在主会话。
- 数字纪律：本文每个数字均可在标注的落盘文件中逐一找到；扩展池数据行一律带「扩展池」标注；爆止窗（WC2OBS1_030927/032005）一切引用带窗长注记（§2.3）。
- 锚点交叉核对：见 `D:/drone_VINS/t4_work_20261002/reports/anchor_check.md`；DoD 对照：`reports/dod_map.md`；md5：`reports/manifest.md5`。

---

## 1. 三域总账摘要

域归属口径源：`raw/inventory_runs.md` L6（主池=X1img_015950/WC2OBS1_030927/WC2OBS1_032005/U3PG_210307/U3PO_211438/U3PR2_213717；扩展池=X1img2_020706/U3PH_210708/U3PR1_212450/X1final_173345；其余=域外）。采集均为 2026-10-02 `ssh nuc` 实测。

### 1.1 run_* 目录总账（源：`raw/inventory_runs.md`，47 个 run_*，尺寸=du -sb，flight.bag 在位性=stat）

| 域 | run_* 目录数 | flight.bag 在位 | flight.bag 缺失 | 备注 |
|---|---|---|---|---|
| 主池 | 3（U3PO_211438/WC2OBS1_030927/WC2OBS1_032005） | 3 | 0 | 其余 3 袋（X1img/U3PG/U3PR2）无 run_* 目录：X1img run 目录已删（挂账禁重试），U3PG/U3PR2 经 stage_u3p 软链→bags/ 原袋（inventory_runs.md L59-69） |
| 扩展池 | 1（run_U3PH_210708 仅日志，bag 缺） | 0 | 1 | 其余 3 袋无 run_* 目录：X1img2 已删（物理禁重放）、X1final 已删（挂账禁重试）、U3PR1 manifest 源袋缺/compact 替代袋在位（323,613,677 B，话题面未验证） |
| 域外 | 43 | 29 | 14 | 含 E2/E3/E4/WAOL/U7OL/WD1b/X1/X1final 各族（逐行见 inventory_runs.md 表） |
| 合计 | 47 | 32 | 15 | 根目录无散文件（inventory_runs.md L5）；劈分经本机 python 逐行复核（在位 32=域外 29+主池 3，缺失 15=域外 14+扩展池 1） |

主池在位袋 rosbag 实测（源：`raw/inventory_runs.md` 表 + `raw/matrix_5faces.md`）：WC2OBS1_030927=13,570,656,638 B/376.272s/428,059 msgs；WC2OBS1_032005=13,505,040,084 B/375.704s/444,678 msgs；U3PO_211438=13,193,532,837 B/360.068s/483,186 msgs；U3PG（软链）=1,614,336,882 B/45.1s/35,004 msgs；U3PR2（软链）=22,700,525,381 B/613s/482,911 msgs。

### 1.2 vision_inputs 产物总账（源：`raw/inventory_artifacts.md`，目录内文件总数 1,791）

| 产物类 | 数量 | 明细要点 |
|---|---|---|
| manifest.json | 13 | 池内 10（帧数 len=139–149，t_rec 范围逐份见 inventory_artifacts.md §1）+ ext_proxy 3（fr_d435i_color len=70、fr_stairs_color len=69、fr_stairs_depth len=70） |
| metrics/fb/density/supply 匹配集 json | 48 | 逐份顶层键+md5 见 inventory_artifacts.md §2 与 `raw/json_inventory.txt` |
| metrics json（池内） | 10 | 8 份标准命名 + 2 份 _sim 命名异（X1img/X1img2）+ WC2×2 另有 _w3 变体（补 supply_frac/grid4x4 两键） |
| fb json | 10 | fb_X1img_sim + fbres_×9（B0 时点 7 份=fb_X1img_sim+fbres_×6；B1 补算回填 +3=fbres_WC2OBS1_030927/032005.json、fbres_X1img2_020706.json，见 §2.4） |
| density json | 6 | WC2OBS1_030927/032005、U3PG、U3PO、U3PR2、X1img_015950（后三份为 B1 补算回填，见 §2.4） |
| jr3_replay_*/features.bag | 7 | U3PG 1,285 条/45.082s；U3PO 10,552/359.981；U3PR2 18,218/613.923；WC2OBS1_030927 1,354/46.136；WC2OBS1_032005 3,029/109.343；X1img2 187/18.169；X1img 5,994/207.823（源：inventory_artifacts.md §3） |

### 1.3 数据字典要点（源：`raw/data_dictionary.md`）

- metrics json 顶层 7 键（bag/camera_info/frames_dir/metrics/n_primary/per_frame/sensor_property）；metrics 12 子键同构 `{by_seg_median{0,1,2}, med_ci, n, p10, p50, p90, p90_ci}`；per_frame 为逐帧数组（样例袋 U3PR1 长度 140，每元素 16 键=4 描述+13 数值读数）。
- features.bag 两话题：`/vins_estimator/odometry`（nav_msgs/Odometry，world 系，pose+twist 各 36 项协方差）；`/vins_estimator/point_cloud`（**sensor_msgs/PointCloud 非 PointCloud2**，points=Point32 列表，channels 实测空）。
- 双机环境（python -c 实测）：本机 python 3.12.7/numpy 2.4.4/pandas 3.0.2/scipy 1.17.1/PIL 12.2.0/cv2 4.10.0；NUC python3 3.8.10/numpy 1.17.4/pandas 0.25.3/scipy 1.3.3/PIL 7.0.0/cv2 4.2.0；rosbag 需 source /opt/ros/noetic/setup.bash。

## 2. 五面齐全矩阵（十袋×六格）

源：`raw/matrix_5faces.md`（2026-10-02 ssh nuc 逐项实测）。图例：✓=在位；✗可补=缺失可补（入缺口）；N-A=物理不可补（源袋已删类，不入缺口）；△✓=在位但命名异。任务面枚举 6 项（任务文本称"五面"，按枚举全列）。

### 2.1 主池 6 袋

| 袋 | 原始袋 | 帧目录+manifest | metrics json | fb json | density json | features.bag |
|---|---|---|---|---|---|---|
| X1img_015950 | ✗ run 目录已删（**挂账禁重试**） | ✓ X1img_j3/ 139png len=139 t=27.204–301.136 | △✓ metrics_X1img_sim.json | △✓ fb_X1img_sim.json | ✗→✓ B1 补算 metrics_X1img_015950_density.json（§2.4） | ✓ 5,994 条/207.823s |
| WC2OBS1_030927（**爆止窗 46.120s**/袋 376.272s，§2.3） | ✓ 13,570,656,638 B | ✓ 139png len=139 | ✓ base+_w3 | ✗→✓ B1 补算 fbres_WC2OBS1_030927.json | ✓ metrics_WC2OBS1_030927_density.json | ✓ 1,354 条/46.136s |
| WC2OBS1_032005（**爆止窗 109.364s**/袋 375.704s，§2.3） | ✓ 13,505,040,084 B | ✓ 138png len=139 | ✓ base+_w3 | ✗→✓ B1 补算 fbres_WC2OBS1_032005.json | ✓ metrics_WC2OBS1_032005_density.json | ✓ 3,029 条/109.343s |
| U3PG_210307 | ✓ 软链→bags/t2v3_ground_210307.bag（1,614,336,882 B） | ✓ 140png len=141 | ✓ | ✓ fbres_U3PG_210307.json | ✗→✓ B1 补算 metrics_U3PG_210307_density.json | ✓ 1,285 条/45.082s |
| U3PO_211438 | ✓ 13,193,532,837 B | ✓ 139png len=141 | ✓ | ✓ fbres_U3PO_211438.json | ✗→✓ B1 补算 metrics_U3PO_211438_density.json | ✓ 10,552 条/359.981s |
| U3PR2_213717 | ✓ 软链→bags/t2v3_route_213717.bag（22,700,525,381 B） | ✓ 139png len=139 | ✓ | ✓ fbres_U3PR2_213717.json | ✓ metrics_U3PR2_213717_density.json | ✓ 18,218 条/613.923s |

### 2.2 扩展池 4 袋（允许 N-A，一律带「扩展池」标注）

| 袋（扩展池） | 原始袋 | 帧目录+manifest | metrics json | fb json | density json | features.bag |
|---|---|---|---|---|---|---|
| X1img2_020706（扩展池） | ✗ 已删（**跨域 dt segv 物理性禁重放**） | ✓ X1img2_j3/ 140png len=149 t=25.388–172.832 | △✓ metrics_X1img2_sim.json | ✗→✓ B1 补算 fbres_X1img2_020706.json | ✗ 缺（features.bag 在位但仅 10 条全空云） | ✓ 187 条/18.169s（重放 18.2s 段错误窗） |
| U3PH_210708（扩展池） | ✗ run 目录仅日志，flight.bag 缺→**N-A(袋已删类)** | ✓ 140png len=140 | ✓ | ✓ fbres_U3PH_210708.json | ✗ **N-A**（源袋已删无从再算） | ✗ **N-A(袋已删类)** |
| U3PR1_212450（扩展池） | ✗ manifest 源袋缺；替代袋 compact_U3PR1_212450.bag（323,613,677 B）在位但**话题面未验证**→待验证 | ✓ 140png len=140 | ✓ | ✓ fbres_U3PR1_212450.json | ✗ 缺（视 compact 袋验证） | ✗ 缺（唯一可能补法=compact 袋重放，可行性未验证） |
| X1final_173345（扩展池） | ✗ 已删（**挂账禁重试**） | ✓ 140png len=140 | ✓ | ✓ fbres_X1final_173345.json | ✗ **N-A**（源袋已删） | ✗ **N-A(袋已删类)** |

### 2.3 爆止窗窗长注记（WC2 两袋一切引用适用；源：`derived/d3_truncation.md` §1 三方对照）

| 袋 | ①odom 首–末时距（工作口径） | ②features.bag 时距（rosbag info） | ③verdicts L204-205 记载 |
|---|---|---|---|
| WC2OBS1_030927 | **46.120s**（t=[25.820,71.940]） | 46.136s | 43.7s 窗 |
| WC2OBS1_032005 | **109.364s**（t=[25.348,134.712]） | 109.343s | 102.0s 窗 |

三口径差异（① vs ③ 差 2.4s/7.4s）本机数据无法进一步裁决，如实并列（d3_truncation.md §1，该节无占比记载）。占袋时长比两套口径并列：**odom 工作口径 46.120/376.272=12.26%、109.364/375.704=29.11%**（本机算术，分母=rosbag info 袋时长）；**D1 §1c pc 面口径记 45.9s/103.1s 即 12%/27%**（45.900/376.272=12.20%、103.060/375.704=27.43%，源 derived/d1_supply_model.md §1c 窗长注记列）。D3 截断档位即以工作口径 ±20% 六档：W1x0.8=36.896s/W1x1.0=46.120s/W1x1.2=55.344s；W2x0.8=87.491s/W2x1.0=109.364s/W2x1.2=131.237s。

### 2.4 面计数汇总（60 格）与 B1 补算增量

盘点时点计数（源：`raw/matrix_5faces.md` §面计数汇总）：

| 面 | ✓ | ✗可补(入缺口) | N-A |
|---|---|---|---|
| 原始袋 | 5 | 3（X1img/X1img2 已删=实为不可补；U3PR1 视 compact 验证） | 3 类不可补（X1img/X1img2/X1final）+ U3PH 袋缺失 |
| 帧目录+manifest | 10/10 | 0 | 0 |
| metrics json | 10/10（含 2 份 _sim 命名异） | 0 | 0 |
| fb json | 7 | 3（WC2OBS1_030927/032005、X1img2） | 0 |
| density json | 3 | 4 可立即补（U3PG/U3PO/X1img/X1img2）+1 视重放（U3PR1） | 2（U3PH/X1final 源袋已删） |
| features.bag | 7 | 1（U3PR1，视 compact 袋验证） | 2（U3PH/X1final 源袋已删） |

B1 补算后本地 raw/ 实有增量（本机 ls 实测 2026-10-02 + `derived/d2_ndim_corr.md` §6、`derived/d6_time_profiles.md` §5⑤、`derived/d7_stack_era.md` §6④ 登记）：fb json 本地 10/10（+fbres_WC2OBS1_030927/032005.json、fbres_X1img2_020706.json）；density json 本地 6（+metrics_U3PG_210307_density.json、metrics_U3PO_211438_density.json、metrics_X1img_015950_density.json）。其中 4 份补算件无在册 md5 参照（素材集晚于盘点账，d7_stack_era.md §6④）：metrics_X1img_015950_density.json（D7 本机算得 md5 fddcc049a021f77e7ef20f521e51afc8）、fbres_WC2OBS1_030927.json、fbres_WC2OBS1_032005.json、fbres_X1img2_020706.json。X1img2 density 未补（其 features.bag 仅 10 条全空云，D1 §1c）。矩阵注2（软链袋 rosbag info 在空窗判定未过时执行的只读批，已登记偏差）照录（matrix_5faces.md 注2）。

## 3. D1 供给率解释模型（单元5.1）

产物：`derived/d1_supply_model.md` + `derived/d1_episodes.csv`（img 50 条 + pc 54 条 episode）+ `derived/d1_frames_covariates.csv`（逐帧协变量面板；scripts/d1_supply_model.py:3 头注列名）；计算脚本 `scripts/d1_supply_model.py`。

### 3.1 口径与阈值（源：d1_supply_model.md §0）

| 项 | 值 | 溯源 |
|---|---|---|
| 图像侧 M1 | supply_frac = corners_gFT/150 | raw/docs/t4_j2_threshold_prep.md L24/L11 |
| 图像侧塌陷阈 thr_img | 0.562 | raw/vision_inputs/j2_threshold_table_v1.json supply_frac.P10 |
| 敏感阈（逐帧池 P10） | 0.4133（10 袋 per_frame 合并 n=1407） | 本机自算（d1_supply_model.md §0） |
| 云侧塌陷阈 thr_pc | 43 点/云 | raw/vision_inputs/j13_supply_pooled.json pooled."10"（n=12950） |
| \|v\| | odom 位置中心差分，>20m/s 判跳变剔除 | csv 无 twist 列——方法降级（§3.6） |

### 3.2 逐袋双口径供给剖面（源：d1_supply_model.md §1 表；sup=supply_frac 全帧分位）

| 袋 | 池 | n帧 | sup_P50 | sup_P90 | <0.562 帧占比 | corners_P50 | grid_P50 |
|---|---|---|---|---|---|---|---|
| X1img_015950 | 主池 | 139 | 0.247 | 0.455 | 0.950 | 37.0 | NA(旧schema) |
| X1img2_020706 | **扩展池** | 149 | 0.587 | 0.640 | 0.295 | 88.0 | NA(旧schema) |
| WC2OBS1_030927 | 主池（**爆止窗 46.120s**） | 139 | 0.680 | 0.733 | 0.079 | 102.0 | 0.500 |
| WC2OBS1_032005 | 主池（**爆止窗 109.364s**） | 139 | 0.880 | 1.000 | 0.094 | 132.0 | 0.938 |
| U3PG_210307 | 主池 | 141 | 0.580 | 0.640 | 0.496 | 87.0 | 0.625 |
| U3PH_210708 | **扩展池** | 140 | 1.000 | 1.000 | 0.043 | 150.0 | 1.000 |
| U3PO_211438 | 主池 | 141 | 0.813 | 1.000 | 0.078 | 122.0 | 0.750 |
| U3PR1_212450 | **扩展池** | 140 | 0.840 | 0.954 | 0.086 | 126.0 | 0.875 |
| U3PR2_213717 | 主池 | 139 | 0.473 | 0.533 | 0.957 | 71.0 | 0.688 |
| X1final_173345 | **扩展池** | 140 | 0.957 | 1.000 | 0.057 | 142.5 | 1.000 |

主帧口径交叉验证（d1_supply_model.md §1 括注）：sup_P50主帧 U3PO 0.807/U3PR2 0.473/U3PR1 0.840/X1final 0.957/WC2#1 0.680/WC2#2 0.867 与 t4_verdicts_v2.md L163/L194/L200/L222 逐值一致；grid_P50 六袋序列 0.625/0.750/0.688/1.000/0.938/1.000 与 verdicts L222 逐值一致。

### 3.3 特征云侧（源：d1_supply_model.md §1c）

| 袋 | 池 | n云 | 云Hz | 非空率 | 点数P10/P50/P90 | 窗长注记 |
|---|---|---|---|---|---|---|
| X1img_015950 | 主池 | 2001 | 9.630 | 0.995 | 41/45/90 | 全程 207.7s（袋 273.9s 的 77%） |
| X1img2_020706 | **扩展池** | 10 | 5.560 | 0.000 | 0/0/0（10 云全空） | 仅 1.8s/10 云（重放 18.2s 段错误前） |
| WC2OBS1_030927 | 主池 | 454 | 9.890 | 0.866 | 0/65/140 | **爆止窗 45.9s/袋 376.2s(12%)**，61 空云 |
| WC2OBS1_032005 | 主池 | 993 | 9.630 | 0.613 | 0/4/126 | **爆止窗 103.1s/袋 375.7s(27%, T2fail t=128.5)**，384 空云 |
| U3PG_210307 | 主池 | 432 | 9.590 | 0.977 | 83/83/119 | 全程 45.1s |
| U3PH_210708 | **扩展池** | 0 | NA | NA | NA | features.bag 不在位（源袋已删），云侧 N-A |
| U3PO_211438 | 主池 | 3521 | 9.780 | 0.985 | 80/118/133 | 全程 360.0s |
| U3PR1_212450 | **扩展池** | 0 | NA | NA | NA | features.bag 不在位，云侧 N-A |
| U3PR2_213717 | 主池 | 6076 | 9.900 | 0.998 | 120/130/149 | 全程 613.9s |
| X1final_173345 | **扩展池** | 0 | NA | NA | NA | features.bag 不在位（源袋已删），云侧 N-A |

非空云 P50 与 j13 per_round p50 逐袋一致：45/97/51/83/119/130（6/6 对上，d1_supply_model.md §1c 括注）。

### 3.4 相关与分箱要点（源：d1_supply_model.md §2/§3/§4）

- Spearman（全帧 POOLED 行，n=1407 或标注）：z −0.655（n=602）、med_gray +0.484（n=1407）、hist_range −0.346、init 后时龄 +0.178（n=987）、|v| +0.179（n=574）、M3 +0.082、M4 −0.120。逐袋符号不一（如 M3：U3PG +0.398/WC2#1 +0.544/X1final −0.338/X1img2 +0.200；时龄：X1img −0.688/U3PO +0.322/U3PR2 −0.263）。
- |v| 八分位×supply：仅顶箱（|v|>0.2m/s）sup_P50 抬至 0.693，底 6 箱 0.467–0.520（n=574，2–5 袋/箱混杂）。
- z 四分位×supply：最低箱（z≤−0.032）0.827 最高、最高箱（z>0.74）0.453 最低（n=602；两箱各混 3–4 袋且为漂移帧，原表注记属袋间差异非高度效应——照录）。
- 塌陷 vs 正常（thr=0.562，全帧 n=1407，塌陷 440 帧）：med_gray 中位 80 vs 167；M3 7.659 vs 7.616；hist_range 149 vs 147；|v| 0.009 vs 0.018（n=574 子集）。

### 3.5 塌陷 episode 注册表（源：d1_supply_model.md §6；全量 `derived/d1_episodes.csv`）

img 口径逐袋窗数：U3PG 16、U3PH(扩展池) 1、U3PO 2、U3PR1(扩展池) 3、U3PR2 4、WC2OBS1_030927 3、WC2OBS1_032005 3、X1final(扩展池) 3、X1img2(扩展池) 12、X1img 3（合计 50）。最长窗：U3PR2 557.860s（t=74.852–632.712，127 帧，sup 中位 0.473）、X1img 249.270s（t=51.864–301.136，125 帧，sup 中位 0.247）。pc 口径 54 窗集中 WC2#2（9 窗/累计 67.31s）与 WC2#1（3 窗/14.55s）。

### 3.6 证据清单与降级登记（源：d1_supply_model.md §7/§8，摘要）

证据清单 9 条（低照度暗帧 4 个强窗、X1 双袋 M3≡0 全程塌、U3PR2 图像/云侧背离、时龄符号不一、|v| 无一致方向、z 袋间混杂、纹理符号不一、γ 恒 1.0 无区分度、云侧塌陷集中 WC2 两袋）——原文为仅关联非因果形式。降级登记 10 条：|v| 位置差分；U3PR2 剔 4559 条(37.7%)/WC2#2 575 条(28.3%) 跳变；U3PH/U3PR1/X1final 无云侧与 |v|/z/age；X1img/X1img2 supply 为派生（corners/150，恒等式在原生袋 0 失配）；POOLED 行袋间混杂；per_frame 13 行重复文件名按原样保留等。

## 4. D2 N 维同批相关表（单元5.2）

产物：`derived/d2_ndim_corr.md` + `derived/d2_matrix.csv`（30 行×14 指标）+ `derived/d2_pairs.csv`（91 对）+ `derived/d2_stats.json`（scripts/d2_corr.py:3 头注列名产出件）；脚本 `scripts/d2_corr.py`、`scripts/d2_md.py`。

- 行=10 袋（主池 6+扩展池 4，扩展池行带标注）×3 段=30 段行；列=14 指标（M1/M2/M3/M4/γ/云·非空率/云·Hz/云·供给/σ̂袋级/FB temp·stereo p90 袋级/三区密度袋级）。
- 相关：C(14,2)=91 对，Pearson+Spearman 双列，置换 p=1999 次（种子 20261002）；85 对可算、6 对 γ 零方差置空。scipy 交叉验证：max|Δpearson|=6.7e-16、max|Δspearman|=1.1e-16（d2_ndim_corr.md §0）。
- 伪复制警示：袋级列在 3 段行重复，含袋级列的段级对有效独立单元≈袋数（d2_ndim_corr.md §1）。

|ρ_s|>0.8 高相关边 6 条（源：d2_ndim_corr.md §4.1）：

| 对 | ρ_s | ρ_p | n | 分类 |
|---|---|---|---|---|
| M1 supply_frac ~ M2 grid4x4 | +0.865 | +0.813 | 24 | 冗余 |
| M1 supply_frac ~ 密度·ground/m²(袋) | −0.840 | −0.700 | 15 | 对立 |
| M2 grid4x4 ~ 密度·air/m³(袋) | −0.848 | −0.711 | 15 | 对立 |
| M3 grad_med ~ 云·供给率(P50/150) | +0.907 | +0.824 | 11 | 冗余 |
| M4 dir_maxbin ~ 云·供给率(P50/150) | +0.813 | +0.810 | 11 | 冗余 |
| 云·供给率(P50/150) ~ FB stereo p90(袋) | +0.974 | +0.922 | 11 | 冗余 |

聚簇 8 个（§4.2）：簇1={M1,M2,密度ground,密度air}、簇2={M3,M4,云供给,FB stereo p90}、其余 6 列各自成簇（γ/云非空率/云Hz/σ̂/FB temporal/密度obstacle）。形态补记照录：σ̂~密度·air 段级 ρ_p=−1.0000 而 ρ_s=−0.3189（X1img σ̂=0 单点支配 Pearson，§3 注）。

袋级 6 列（每袋 1 值；源：d2_ndim_corr.md §2 袋级表）：σ̂P50 X1img=0(67)/U3PH=1.022(68)/X1final=1.023(68)/U3PO=1.029(67)/WC2#1=1.029(67)/WC2#2=1.03(66)/U3PG=1.031(68)/U3PR1=1.031(68)/U3PR2=1.03(67)；FB stereo p90 px：X1img 0.7119(1293)/WC2#1 57.29/WC2#2 112.3/U3PG 92.96/U3PO 104.4/U3PR2 122.6/X1img2 61.8/U3PH 2.905/U3PR1 109/X1final 99.56；三区密度仅主池 6 袋有值且 6 份 density json 全部 dry_run=True（verdicts L197-198 挂旗状态照录）。

缺失登记（§6 摘要）：M1/M2 缺 3 袋（X1img/X1img2 旧 schema，WC2×2 用 _w3 补齐）；三区密度缺 4 袋；云侧三率缺 4 袋 + X1img seg2/WC2×2 全段门控剔除（回放覆盖 <90%）。M4 降级=方向能量单半边代理（metrics json 无 Laplacian 字段）；FB p90 降级=袋级 pool（条目无绝对时刻）。

## 5. D3 爆止窗漂移量化（单元5.3）

产物：`derived/d3_truncation.md` + `derived/d3_sensitivity.csv`（156 行）+ 中间量 `derived/_d3_mid.json`；脚本 `scripts/d3_unit5_3_calc.py`、`scripts/d3_unit5_3_gen_md.py`。bootstrap B=1000（单元=段），种子 20261002。本单元 4 袋全部主池（d3_truncation.md §0）。

- 窗长三方对照：见 §2.3 表（46.120s/109.364s 工作口径 vs features.bag 46.136s/109.343s vs verdicts 43.7s/102.0s）。
- 管线自检：4 袋×12 指标×P10/P50/P90 重算 vs metrics json 存值 max|Δ|=2.84e-14；n 逐袋一致（67/66/68/67）（d3_truncation.md §3）。

part a 窗池(n=31) vs 全程池(n=147) 逐指标分位差（源：d3_truncation.md §4.1，img 面；CI=bootstrap 95%）：

| 指标 | ΔP50 [CI] | ΔP90 [CI] |
|---|---|---|
| supply_frac | −0.02 [−0.2533, 0.0335] | +0.1333 [−0.132, 0.308] |
| corners_gFT | −3 [−38, 5] | +20 [−19.8, 33.13] |
| grid4x4_occupancy_frac | +0.125 [−0.03125, 0.375] | +0.0375 [−0.225, 0.3125] |
| grad_med | −1.922 [−4.013, −1.175] | −0.3561 [−0.3561, 2.285] |
| grad_dir_maxbin_frac | −0.06056 [−0.09094, −0.04672] | −0.03756 [−0.04, −0.001858] |
| grad_dir_entropy_norm | +0.1034 [0.0821, 0.1454] | +0.1654 [0.06497, 0.1664] |
| hist_range_p1_p99 | −17 [−40, −3] | −3 [−5, 2] |
| med_gray | −2 [−74, −1] | +22 [15, 44.45] |
| d12_sigma_p25 | −0.002894 [−0.005946, −0.000674] | −0.003364 [−0.004825, −0.001623] |
| p_sat | −2.6e-05 [−3.58e-05, −1.3e-05] | −6.18e-05 [−7.06e-05, −4.46e-05] |

pc 供给面（n_WIN=1447/n_FULL=3953）：ΔP10=−83 [−99,−19]；ΔP50=−97 [−117, 0.025]；ΔP90=+3 [−69.05, 12]；窗池 P50=21 点/云 vs 全程池 118 点/云（d3_truncation.md §4.3）。WIN 池 31 帧=WC2OBS1_030927（爆止窗 46.120s）10 帧 + WC2OBS1_032005（爆止窗 109.364s）21 帧；段级重采样单元仅 2 个，CI 偏宽属口径固有（§4.1 注）。

part b 截断敏感度（阈值 10%；源：d3_truncation.md §5.2）：

| 清单 | 指标（max|ΔP50|%） |
|---|---|
| 窗稳（img 面） | hist_range_p1_p99 6.58%；d12_sigma_flat 0.07%；d12_sigma_p25 0.28%；d12_flat_frac 0.00% |
| 窗敏（img 面） | p_sat 100.00%；med_gray 47.74%；corners_gFT 34.30%；supply_frac 34.30%；grad_dir_maxbin_frac 30.30%；grad_dir_entropy_norm 17.95%；grid4x4_occupancy_frac 16.67%；grad_med 16.67% |
| pc 供给面 | n_points max|ΔP50|% = 59.7%（U3PO, W1x1.2）→窗敏列 |

档位与退化：U3PG_210307（span=45.004s）除 W1x0.8 外 5 档全部退化不入分类；U3PO 全 6 档有效（d3_truncation.md §5）。pc 面 |ΔP50|% 非单调（W1 三档 3.4→36.0→59.7，W2 三档 10.2→1.7→3.4，§5.1 注记窗内场景相位主导——照录）。

odom 数据质量异常登记（§6，未入统计表）：U3PO_211438 自 t≈79.5s 起两条位置轨迹交替（实测行 1055–1061，交替步距 ~55m）；WC2OBS1_032005 983/2035 步 dt≤0 同型交错；WC2OBS1_030927 末步 71.836→71.940 跳 91.689m；U3PG 双轨近重合（dp P50=0.012m）。逐样本 odom 速度/漂移分位全部不入 part a/b。

## 6. D4 J2 数据面（单元2 数据面）

产物：`derived/d4_j2_plane.md` + `derived/d4_saturation_dual.csv`（120 行）；脚本 `scripts/d4_calc.py`。

- 袋集合两口径（§0）：主面板 Set A=j2_threshold_table_v1.json `bags` 8 袋（U3PG/U3PO/U3PR2/U3PH/U3PR1/X1final/WC2×2）；附录 Set B=任务括号口径（主池6+X1img2/U3PR1）。两口径差 2 袋（U3PH/X1final ↔ X1img/X1img2）。
- 口径验证（本次实测运行，d4_j2_plane.md §0.1）：验证1 重算 vs 存值 124 组不一致 0 组（跳过 gamma_pair 12 组）；验证2 Set A 跨袋分位 vs j2 阈值表 30 组超容差 0 组；WC2 袋名对应经 json 逐位证实（030927=1.0289948=WC2#1、032005=1.0297823=WC2#2——anchors.json 中"依顺序推断"的对应获逐位证实）；饱和帧≡corners_gFT==150 帧级等价三袋全 True。
- 输入面=袋级 p50（d4_j2_plane.md §1 表，10 袋全量在案；扩展池 4 行带标注）。X1img/X1img2 旧 schema：无 supply_frac/grid4x4 键，supply 派生 corners/150，grad_med 与 d12_sigma_p25 袋级 p50=0.0 为 json 原值（§5.2）。
- 相关矩阵（§2.1 Set A，n=8/对）极值：|r| 最大 grad_dir_maxbin_frac×grad_dir_entropy_norm=−0.989（ρ_s=−0.952）；grad_med×hist_range r=+0.976；corners×supply r=1.000（定义恒等式）。Set B 附录 45 对全量在案（§2.2）。
- 跨袋一致性（§3.1 Set A）：CV 最小 d12_sigma_p25=0.004、最大 p_sat=0.794；离群袋（Tukey 1.5×IQR）：U3PH_210708 入 5 指标栅栏外（hist_range/grad_med/maxbin/d12_sigma_p25 及 X1final 同列 hist_range/d12 栅栏外）；W_seg(k=3) 0.759–0.984；W_overall（10 指标×8 袋）W=0.0783，χ²=5.481(df=7)。Set B：W_overall=0.3366（9 指标，§3.2）。
- 饱和三例去饱和双列（§4，三袋均**扩展池**）：

| 袋（扩展池） | n_orig | n_sat | 剔除率 | n_desat | 受影响指标（|relΔ|>1% 数） |
|---|---|---|---|---|---|
| U3PH_210708 | 72 | 68 | 0.9444 | 4 | 10/10（p_sat 为 inf；hist_range max|relΔ|=36.250） |
| U3PR1_212450 | 72 | 5 | 0.0694 | 67 | 5/10 |
| X1final_173345 | 72 | 21 | 0.2917 | 51 | 7/10 |

- 登记（§5 摘要）：U3PH 去饱和后仅 n=4（其分位仅按算式给出）；p_sat 量级 1e-5；X1img corners_gFT 袋级 p50=37.0（json 原值）与 anchors.json era 记载的 45 属**不同指标**（45=特征云每云点数 p50，见 D7 §2.1；37=角点数/帧，=verdicts L72"37/帧"）——两值并存不冲突，出处均登记（d4_j2_plane.md §5.7）。

## 7. D5 立体残差双峰统计量（单元3 数据面）

产物：`derived/d5_bimodal.md` + `derived/d5_overlap.csv` + 可复现脚本 `derived/d5_compute.py`（片段 `derived/_d5_tables.md`）；另 `derived/_d5_report.npy`（136B，numpy int64 数组 [0]；全树 grep 无生成脚本引用——孤立中间量，如实登记）。六袋=E4 FB 残差六袋（主池 U3PG/U3PO/U3PR2 + 扩展池 U3PR1/U3PH/X1final，行带标注）。

粒度降级（d5_bimodal.md §1，读数前提）：无逐帧原始残差数组（fb json stereo=33–37 箱分位摘要）→全部统计目标=**箱级 p50/p90 序列**（n=35–37 箱/袋），非原始分布统计；箱→时间映射为推断假设（§2，不可本地核验）。

池化参考（源：d5_bimodal.md §6 首表，fbres_*.json stereo_pool）：

| bag | 池 | n | p50 px | p90 px |
|---|---|---|---|---|
| U3PG_210307 | 主池 | 2517 | 43.13 | 92.96 |
| U3PO_211438 | 主池 | 3519 | 26 | 104.4 |
| U3PR2_213717 | 主池 | 2054 | 44.44 | 122.6 |
| U3PR1_212450 | **扩展池** | 3172 | 35.66 | 109 |
| U3PH_210708 | **扩展池** | 4056 | 0.5632 | 2.905 |
| X1final_173345 | **扩展池** | 3770 | 2.047 | 99.56 |

a) ΔBIC=BIC(2分量)−BIC(1分量)（负=偏 2 分量；p50 序列，d5_bimodal.md §6a）：U3PG +3.4042；U3PO −49.9484；U3PR2 +5.8233；U3PR1 −47.7269；U3PH −278.0038（σ 触地板旗标）；X1final −161.6918。p90 序列：U3PG −22.0877/U3PO −54.7232/U3PR2 +0.1769/U3PR1 −54.4594/U3PH −223.3237/X1final −22.8134（U3PH/X1final 触地板）。

b) 双峰系数 BC（p50 序列，bootstrap 10000 次 95%CI）：U3PG 0.4798 [0.3784,0.6757]；U3PO 0.6573 [0.4466,0.7823]；U3PR2 0.3704 [0.2868,0.5607]；U3PR1 0.7767 [0.3730,0.8972]；U3PH 0.9997 [0.3349,1.0000]；X1final 0.9753 [0.4040,0.9982]（参考线 0.5556；d5_bimodal.md §6b）。

c) 切点±20% 扫描（§6c）：切点 px U3PG 40.7225/U3PO 1.3555/U3PR2 33.3478/U3PR1 2.1398/U3PH 43.9620/X1final 5.9162；1.0× 阈下量占（≥阈值 Σn/池 n）分别为 0.559/0.8355/0.8866/0.9275/0.01652/0.03687。

d) 高位簇 vs 55–64s 载体窗（§6d，时间=推断映射）：覆盖率 U3PG 0.1982（该袋帧时轴止于 58.152s，上限 0.3502）、U3PR2 1.0000（Jaccard 0.0167）、U3PO/U3PR1/U3PH/X1final 0.0000。

e) 60s 窗时序（§6e，p50\*=窗内各箱 p50 按 n 加权中值）：六袋逐窗表在案（如 U3PO [0,60) 窗 p50\*=0.6672、[120,180) 起 29.6–37.5px；U3PH [0,60) p50\*=0.5637 后各窗 0.5252–0.6202px）。

旗标登记（§5）：U3PH 2-GMM 高分量 σ 触地板且由单一离群箱（p50=46.78px, n=67）驱动、切点独立复算不唯一；X1final p90 序列低分量 σ 触地板；bootstrap CI 普遍偏宽（n=35–37 小样本）。计算内验证 6 项全过（§4：1-GMM 闭式 6/6、scipy BC 6/6、切点复算 5/6+U3PH 例外、质量守恒 6/6 等）。

## 8. D6 时间局部化剖面

产物：`derived/d6_time_profiles.md`、`derived/d6_window_metrics_long.csv`（122 窗×28 指标）、`derived/d6_worst_windows.csv`（20 行）、`derived/d6_collapse_flags.csv`（122 窗×4 族×2 判据）、`derived/d6_bag_anchors.csv`；脚本 `derived/d6_compute.py`、`derived/d6_make_md.py`。

- 覆盖：主池 6 袋 30s 分箱 A/B/C 三表逐窗全指标（76 窗）+ 扩展池 4 袋（46 窗，行带「扩展池」标注；粒度降级见下）。
- 判据命中总览（主池 76 窗，源：d6_time_profiles.md §2.1）：绝对门 M1<0.2 命中 0 窗；M2<0.5 命中 0 窗；纹理零梯>0.3 命中 11 窗（全部 X1img_015950）；残差 p90>30.7px 命中 40 窗（U3PO×11/U3PR2×10/WC2#1×13/WC2#2×4/X1img×2）。相对门（≤袋帧级 P10 / ≥袋 FB 条目 P90）：供给 6、占用 17、纹理 34、残差 15 窗。
- 绝对门 ≥2 族同窗：仅 X1img_015950 的 0-30s 与 30-60s 两窗（纹理零梯+残差尖峰）（§2.2）。
- 相对门 ≥2 族同窗对齐表 31 窗（主池 14+扩展池 17，§2.3；逐窗中位与锚值全列在案）。
- 最差 30s 窗注册（composite 分位秩和，§3；源表逐行在案）：主池 worst1=X1img 210-240s(comp_norm 0.7083)/WC2#1 240-270s(0.6148)/WC2#2 60-90s(0.6327)/U3PG 0-30s(0.5357)/U3PO 30-60s(0.7161)/U3PR2 600-630s(0.7078)；扩展池 worst1=X1img2 150-180s(0.6389)/U3PH 0-30s(0.7636)/U3PR1 60-90s(0.7826)/X1final 30-60s(0.6333)。
- 袋级锚表（§4，官方池化值 10 袋全量在案，含 n_primary/corners/grid/gradmed/maxbin/γ/FB 双池/density points_total/per_msg p50）。
- 降级与缺口登记 9 条（§5 摘要）：①FB 条目无时间戳→stride-2 索引映射（偏差上界≈2 帧间隔）；②|v| 差分副本+双流污染（跳变剔除占比 X1img 0%/U3PG 0%/WC2#1 8.7%/WC2#2 36.2%/U3PO 90.2%/U3PR2 44.9%）；③γ 无逐帧数组（seg 映射）；④M4 方向能量单半边代理；⑤主池 3 份 fb json 为工作流内新增件（不在 raw_manifest.md5）；⑥WC2/X1img 回放覆盖截断（帧面 402/401/301s vs 回放 71.9/134.7/235.0s）；⑦窗级无 CI（未预注册）；⑧绝对门零命中注记；⑨扩展池粒度（X1img2 pc 全零行=无点产出非场景读数；U3PH/U3PR1/X1final 无 odom/pc 面）。

## 9. D7 跨栈与年代可比性核验

产物：`derived/d7_stack_era.md` + `derived/d7_offset_table.csv`（154 行=148 数据行+6 组偏移行；扩展池行 50 行带标注）；脚本 `scripts/d7_build_offset_table.py`。

- 年代效应端点复现（§2.1）：前代 X1img 每云点数 p50=45.0（n=1991 非空云；旁证 metrics_X1img_015950_density.json per_msg_points.p50=45.0/points_total=108995）；注入代池 p50=127.0（n=10959）；归一 0.3000 与 0.8467（127/150，四舍五入 0.85）。n 恒等式：422+3469+6066+393+609=10959 逐位成立；+X1img 1991=12950=pooled.n（全池 P50=124，verdicts L216 仅存档口径）。
- 逐轮表（j13 ↔ 6 density json ↔ verdicts 三层逐位一致，§2.1）：X1img 45/90/154(n=1991)、WC2#2 51/128/157(609)、U3PG 83/119/132(422)、WC2#1 97/141/156(393)、U3PO 119/133/159(3469)、U3PR2 130/149/167(6066)（p50/p90/max）。
- 增量标签算术核验（§2.2）：绝对增量 +82.0 点/云；相对增量 +182.22%（=(127−45)/45）；倍率 2.8222×。**verdicts L214 与任务书所载"+112%"标签与自身端点算术不符**（45→127 算术为 +182.2%；本机素材内未找到 +112% 推导口径）——登记不裁决（进 anchor_check diffs）。
- 同指标跨面（§2.3）：σ̂P25 X1img/X1img2=0.0 vs 注入代 8 袋 1.02185–1.03111；corners X1img=37（=verdicts L72）vs 注入代 71–150；grad_med X1img=0.0 vs 4.47214–8.48528。
- J2 v1 阈值表全量重算（§2.4）：9/10 指标 |diff|≤5e-5 逐位复现；p_sat 行表载 0/0/0 vs 重算 0/1.30e-05/1.92e-05（与 data_dictionary L36"袋级 p50 截断显示"登记一致——照录，进 anchor_check diffs）。
- 栈登记总表（§3）：cf0384 代=X1img/WC2#1/WC2#2（verdicts L172）；285278cc=U3PG/U3PO/U3PR2（L172/L183）；X1img2=cf0384 代【时间线推断，跨午夜歧义已登记】；U3PH/U3PR1/X1final 无 features 面。anchors.json 本体无逐袋栈 md5 字段，登记位置实际在 verdicts L172/L183/L228；canonical 冻结文件 ~/sitl_sim/t2_u2_freeze.txt 在 NUC 本地无副本（§6①）。
- 偏移点名 G1–G6（§4）：G1 年代 +82.0 点/云（+182.22%）；G2 注入代内跨栈 cf0384 轮中位 74.0 vs 285278cc 119.0（+45.0，+60.8%；场景+覆盖窗混杂登记）；G3 同栈年代 +29.0（+64.4%）；G4 σ̂ +1.02185~+1.03111；G5 corners +34~+113；G6 J2 表重算 9/10+ p_sat 行差。注入代内跨栈轮域交叠 [83,97]（2/5 轮）。
- U7 A/B 中性声明（§5）：引文在位（verdicts L173/L228-229）；底层 T2 逐位比对记录不在本地素材，"逐位中性"未在本机复验（降级为引文在位性核对）；本地 run_U7OL1/U7OL2 为 U7 开环飞行轮（域外），不能充当该证据。

## 10. D8 双口径记录（图像侧 M1 vs 云侧 supply）

产物：`derived/d8_dualcaliber.md` + `derived/d8_ratio.csv`（1,407 行逐帧配对，扩展池行 pool 列=扩展池）。任务边界：只记现象与形态，不含换算结论。

逐袋并列（判读样本分位，源：d8_dualcaliber.md §3）：

| 袋 | 池 | 口径 | n | M1 p50 | 云 p50 | 点数 p50 | 比值 p50（p10–p90） |
|---|---|---|---|---|---|---|---|
| X1img_015950 | 主池 | primary | 54 | 0.250 | 0.293 | 44.0 | 0.831（0.700–0.975） |
| WC2OBS1_030927 | 主池（爆止窗 46.120s，匹配 20/139 帧） | allmatch(主帧 n=6<8 降级) | 12 | 0.523 | 0.803 | 120.5 | 0.652（0.594–6.213） |
| WC2OBS1_032005 | 主池（爆止窗 109.364s，匹配 21/139 帧） | primary | 8 | 0.517 | 0.597 | 89.5 | 0.581（0.436–4.109） |
| U3PG_210307 | 主池 | primary | 70 | 0.550 | 0.553 | 83.0 | 0.867（0.750–1.145） |
| U3PO_211438 | 主池 | primary | 70 | 0.813 | 0.800 | 120.0 | 1.029（0.865–1.948） |
| U3PR2_213717 | 主池 | primary | 70 | 0.473 | 0.867 | 130.0 | 0.552（0.477–0.620） |
| X1img2_020706 | **扩展池** | — | 0 | — | — | — | —（10 云全空，仅空云事件） |
| U3PH_210708 | **扩展池** | — | 0 | — | — | — | —（仅图像侧） |
| U3PR1_212450 | **扩展池** | — | 0 | — | — | — | —（仅图像侧） |
| X1final_173345 | **扩展池** | — | 0 | — | — | — | —（仅图像侧） |

帧级同向/背离（§4）：X1img 同向 31/48（65%）rho=+0.3732(p=0.0054)；U3PO 同向 22 vs 背离 46 rho=−0.3889(p=0.0009)；U3PG 12:12 rho=−0.2585(p=0.0307)；U3PR2 29:33 rho=−0.0983(p=0.4181)；WC2#2 2:6 rho=−0.4880(n=8,p=0.2199)；WC2#1 6:6 rho=+0.1006(n=12)。形态三簇（§4.3）：恒低于 1 紧簇（X1img、U3PR2）；跨 1 交错（U3PO/U3PG）；重右尾（WC2 两袋 p90=4.109/6.213=图侧高位+近空云样本）。

空云事件（§5）：命中空云比例 WC2#2 13/21(62%)、WC2#1 8/20(40%)、X1img2 4/4(100%)、X1img 2/56、U3PG 3/73、U3PO 4/74、U3PR2 2/72。

对账与发现（§7）：M1 定义式重算 6 袋帧逐位误差 0.0、WC2×2 vs _w3 逐帧误差 0.0；pc 非空云数 vs j13 per_round.n 六袋全等（1991/393/609/422/3469/6066）；帧时刻采样点数 p50 vs j13 全回放 p50：X1img 44 vs 45、U3PO 120 vs 119（差 1 点采样口径）、WC2#1 120.5 vs 97、WC2#2 89.5 vs 51（重放仅覆盖早期段）。**odom 通道双流发现**（§7.3）：6 袋 csv 存在两条交错姿态流（同刻双值或奇偶交替），不分流直算得非物理值（例 U3PO 直算 |v| 中位 973 m/s；分流后主流仅 1/3,855 段无效）；extract_odom_pc.py 只读单一话题，双流出自在位 features.bag 本身（成因不在本记录溯源范围——照录）。

## 11. EX-FAIL 判读工具自测矩阵摘要

### 11.1 合成用例 10×3 格（源：`derived/exfail_matrix_synthetic.md`；执行机 NUC，python3 3.8.10/cv2 4.2.0）

- 被测工具零修改（NUC 与本机副本 md5 一致）：j3_image_metrics.py `abcc5fc811007b6ad16b8000d96f3022`、j3_fb_residual.py `c23d42879e9ba6fa722df36f8871003f`、j3_feature_density.py `9e45f9817d8a5370363f8b59e4bb125e`。
- 用例 U1 空帧窗(1a/1b)、U2 单帧、U3 全白、U4 全黑、U5 恒噪、U6 截断 PNG、U7 manifest 时刻重复、U8 缺必填字段、U9 尾随空格、U12 非常规位深/尺寸；U1 含双子变体→33 行登记。
- 行计（33 行）：**干净通过 5 / 带病输出 10 / 干净拒绝 18 / 挂死 0**（最长 1.02s，timeout 90 未触达）。
- 关键格（§0/§1）：U3/U4 metrics 退出 0 且产出文件含 **34 处 NaN 字面量**（17 帧×grad_dir 两键，写入点 j3_image_metrics.py:126-127）；U1b/U6/U9 metrics 全零统计面退出 0（U9 stderr 零告警）；U6 另伴 libpng error（metrics 17 行/fb 23 行）；U7 重复时刻直接计入（n_primary=17）；U8 双工具 KeyError 'tag' 干净拒绝；U12 metrics 干净通过（跨尺寸 pair 回填 d12_sigma_flat=73.1441…）、fb cv2.error 尺寸断言干净拒绝；density_offset 10 格同型 IsADirectoryError 干净拒绝（工具只吃 bag）。除零显式异常 0 格（fb p90_ratio 分母 max(p90,1e-9) 保护）。
- 留档：本机 `work_selftest/`（results.jsonl 33 行+样例产出+三工具只读副本）；NUC /tmp/t4_v54_selftest/（26M）。

### 11.2 真实子集 2×3 格 + 补充格（源：`derived/exfail_matrix_real.md`；证据 `raw/exfail_real_cells/`）

- 用例 10=U3PR2_213717 前半(10a, t=18.720–316.464, 36 主帧+34 next)/挂旗段切片(10b, t=334.960–632.712, 36+33)（run_WAOL5R_222234 无帧目录→按任务书 fallback 用 PR2 前后半段）；用例 11=WC2OBS1_032005_j3 全量（爆止窗短袋，139 条/138 png）。
- 六要素结果：10a/10b/11 × image_metrics、fb_residual 六格全部干净通过（rc=0、严格+宽松双解析、0 NaN）；feature_density 对帧目录 2 格干净拒绝（裸 IsADirectoryError traceback，不经过工具 FAIL 通道）；③b 真实袋正输入格 2 格干净通过：11 格 points_total=36,037/msgs=609(非空口径)/odom 2,036/duration_s=102.0/per_msg p50=51,p90=128,max=157/zones obstacle 4,097·ground 27,296·air 4,644；10 格 points_total=781,230/msgs=6,066/odom 12,142/per_msg 130/149/167/zones 54,060·724,461·2,709。
- 复现性比对（§4）：11 格 fresh 重跑 vs 在册 metrics_WC2OBS1_032005.json 公共 10 键 p50 **逐位 SAME**（corners 130/d12_p25 1.02978/grad_med 8.24621/hist 149/med_gray 175/p_sat 1.6276e-05 等）；键集代差 fresh 12 键 vs 在册 base 10 键（缺 supply_frac/grid4x4）。feature_density 总点数逐位同，zone 计数差 2–50 点（0.006%–0.65%）：fresh 用默认 shift [1.01,0.98,0.104]、在册 json 为逐袋实测 shift（PR2 [1.0198,1.0126,0.1085]、WC2 [1.0094,0.9812,0.1036]），两次运行 shift 输入字段不同——两套参数均登记在档（源 derived/exfail_matrix_real.md §2 并列陈述）。
- 与在册对账（§2/§3，现象登记）：10 格 msgs=6,066（非空）vs verdicts L196"6076 云"（全量）差 10=空云；前后半切片读数（supply 0.48/0.4667、corners 72/70、σ̂ 1.03）落在 PR2 全程在册读数（0.473/71/1.03009）近旁。
- EX-FAIL 候选坑位表 E1–E8（§5 全文在案）：E1 shift 两套输入（默认先验/逐袋实测）与 zone 计数差 2–50 点并存；E2 键集代差 12 vs 10；E3 云数非空/全量口径差 10；E4 fb nf 仅消费主帧 47%–50%；E5 帧目录误当 bag 走裸 traceback 且 rc=1 与 FAIL 同码；E6 air 区分母 3.16e8 m³→per_m3 打印 0.0（分母淹没）；E7 img 静默 continue+NaN 直写机制（本轮真实帧 0 触发）；E8 切片产物 frames_dir 溯源双套。
- 卫生门禁（当轮）：空窗双判定 0/0、df 32G→31G（>25G 线）、零 rosbag 写操作（nuc_env_gate.txt）。

## 12. 本批产出、回传与运行登记

- 本批新增 reports/：`data-pack.md`、`dod_map.md`、`anchor_check.md`、`manifest.md5`（python hashlib 全量 raw/+derived/+reports/；唯一除外项=manifest.md5 自身，防自引用）。
- 回传（已完成，复核修正后再传）：reports/+derived/ 全量 scp→NUC:/tmp/t4_v54_b4_stage/→远端 cp 落位 NUC:~/catkin_ws/sitl_sim/t4_evidence/v54_20261002/。远端 md5sum 对账（find derived reports | xargs md5sum vs 本清单对应行）：传输集 **34/34 文件逐位一致，mismatch=0**（34=derived 31+reports 3）；远端多出 1 件=manifest.md5 自身（本地清单除外项）；raw/ 108 件不属本次传输集（素材原件在 NUC 各源路径），不在远端对账范围。/tmp/t4_v54_tools/ 临时脚本（extract_odom_pc.py、probe_point32.py、rosbag_info_features.txt、out/ 共 18 件）cp 入证据目录 tools/，与源逐件 md5 相同（18/18，两侧 md5sum 实测）。
- git（历轮复核修正均 amend）：NUC:~/catkin_ws 仅 add sitl_sim/t4_evidence/v54_20261002。提交链（amend 前史，8 位前缀；历次被 amend 取代的 hash 已不在分支 log 可达历史、reflog 可考，故本文件只记前缀不记全 hash）：初版 51d83a4 → 复核修正1 fe54559 → 复核修正2 a490c5d → 本节修正（**最终 hash 以 `git -C ~/catkin_ws log -- sitl_sim/t4_evidence/v54_20261002` 最新一条为准**）。中文提交信息经 scp 文件通道 git commit -F 传入；52 files changed 口径；derived/__pycache__/d5_compute.cpython-312.pyc 被 NUC .gitignore L37 `__pycache__/` 规则排除未入库（check-ignore 实测）；禁止 push（NUC WAN 瘫）。
- 独立复核修正登记（2026-10-02 第二轮）：①§1.1 在位/缺失劈分更正为 32/15（域外 29/14）——初版 31/16 系统计错误，经 python 逐行复核 raw/inventory_runs.md 更正；②§2.3 占袋时长比更正为工作口径 12.26%/29.11%，D1 §1c pc 面口径 12%/27%（27.43%）两套并列，删除错误出处指针；③补收 derived/ 三件产物索引（d1_frames_covariates.csv、d2_stats.json、_d5_report.npy）；④§11.2 因果连词改并列陈述（L326 复现性比对句当轮已改，L328 坑位表 E1 行第三轮补改）；⑤本节 raw 计数 107→108。
- 独立复核修正登记（2026-10-02 第三轮）：⑥L328 E1 行残留因果连词"致"改为并列陈述（与源 derived/exfail_matrix_real.md §5 E1 行并列口径一致）；⑦本节提交链改记 8 位前缀+reflog 说明——全 hash 随逐轮 amend 退出可达历史，40 位串不可整段复验（复核员实测仅 8 位前缀可考）；⑧tools 18/18 与传输集 34/34 对账随本轮回传重新机械复验（find+md5sum+diff）。
- 打包时刻 NUC 运行登记（2026-10-02，本工作流实测）：`ps -eo comm= | grep -cx rosbag` 间隔读取两次均=1（rosbag 进程在飞，非本工作流所启）；df 可用 31G（>25G 线）。本工作流全程零 rosbag/回放/提帧操作，仅文件传输与 git。
- 本包未覆盖（登记，非本工作流范围）：X1img/X1final 特征重放（原始袋已删，挂账永久不可行）；X1img2 物理性重放；U3PR1 compact 袋重放验证（话题面未验证）；判据预注册/J2 判读文/E4 判决/P3 预填充/跨线预签/素材池持续监视/W6 持续项（主会话或后续批）。
