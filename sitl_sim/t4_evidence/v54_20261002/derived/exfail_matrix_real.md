# EXF · 判读工具稳健性自测·真实子集 2×3 格（2026-10-02）

- key=EXF；执行位=本机编排 + `ssh nuc` 逐格实跑；六要素口径同合成用例线（退出码 / stdout 摘要 / stderr 摘要 / 输出 json 可解析性(严格+宽松) / NaN·除零行为 / 失败模式分类〔干净通过·干净拒绝·带病输出·挂死〕）。
- 三件工具=NUC 原件 `~/catkin_ws/sitl_sim/analysis/j3_image_metrics.py`、`j3_fb_residual.py`、`j3_feature_density.py`，md5 与本地 work_selftest/ 副本逐一相同（证据 raw/exfail_real_cells/nuc_env_gate.txt）：`abcc5fc811007b6ad16b8000d96f3022` / `c23d42879e9ba6fa722df36f8871003f` / `9e45f9817d8a5370363f8b59e4bb125e`。禁修工具：未改任何工具文件。
- 卫生门禁：`ps -eo comm= | grep -cx rosbag` 间隔 5s 两次全 0（开工前 + 证据落盘时各一次，nuc_env_gate.txt 同文件 0/0）；df 可用 32G→31G（>25G 线）；全程零 rosbag 写操作、零回放、零提帧，仅只读既有帧目录与既有 features.bag（2.1M/19M）。
- 本格主输入只读性：11 用例直接读 `~/sitl_sim/vision_inputs/WC2OBS1_032005_j3/`（139 manifest 条/138 png）；10 用例切片产物落 `/tmp/t4_v54_selftest_real/`（png 用符号链接，源目录零改动）。

## 0) 用例 10 输入裁定

- `run_WAOL5R_222234`（NUC:~/sitl_sim/vins_smoke_runs/，域外，flight.bag 148,204,649B 在位，inventory_runs.md L31）**无帧目录**：目录内仅 flight.bag+日志（arrive_watch/forensics_v2/goal/mavros/planner/poscmd_hz/record/RESULT/round/simvins/sitl/takeoff/wa_gate_online 等），无 *_j3/。→ 按任务书 fallback：**PR2 前后半段对比**。
- 切片操作定义（scripts/exfail_real_make_slices.py，落盘 raw/exfail_real_cells/slice_stats.json）：对 `U3PR2_213717_j3/manifest.json` 全部帧 t_rec 取中点 t_mid=325.716s（t_range 18.720–632.712）；主帧(tag='') t<t_mid → 前半切片，t≥t_mid → 后半切片=**挂旗段切片**（"挂旗"依据=raw/docs/t4_verdicts_v2.md L195-200 该袋密度面挂全域不可判读旗 + L226"PR2 挂旗例外"；切片时段与旗的对应为操作定义，未做独立验证）。主帧的 `_next` 配对帧随基帧入切片。
- 切片实况（slice_stats.json）：front 36 主帧+34 next=70 文件，t=18.720–316.464，seg{0:24,1:12}；back 36 主帧+33 next=69 文件，t=334.960–632.712，seg{1:12,2:24}。
- 用例 11 输入=WC2OBS1_032005_j3 全量（"爆止窗短袋帧目录"），只读直跑。

## 1) 2×3 主矩阵（六要素）

证据总文件：raw/exfail_real_cells/results_real.jsonl（10 行，逐格六要素全量）；格产物 raw/exfail_real_cells/out/*.json。分类判据=跑批器机械规则（results_real.jsonl 同行 class 字段）。

### 用例 10 跑飞段真实子集（拆 10a 前半 / 10b 挂旗段切片两行）

| 格 | ①退出码 | ②stdout 摘要 | ③stderr 摘要 | ④json 可解析 | ⑤NaN/除零 | ⑥失败模式分类 |
|---|---|---|---|---|---|---|
| 10a×image_metrics | 0 | 2,456B（12 指标聚合表）；3.08s | 0B，无模式命中 | 严格+宽松双过 | per_frame 0 个 NaN；0 NaN/Infinity token | 干净通过 |
| 10a×fb_residual | 0 | 704B（双池+h6）；0.66s | 0B | 严格+宽松双过 | 0 NaN token | 干净通过 |
| 10b×image_metrics | 0 | 2,471B；3.02s | 0B | 严格+宽松双过 | 0 NaN；n_primary=36 全入选，metrics 无 n=0 项 | 干净通过 |
| 10b×fb_residual | 0 | 709B；0.65s | 0B | 严格+宽松双过 | 0 NaN | 干净通过 |
| 10a×feature_density | —（density 不吃帧目录，见 §2 ③a 格） | | | | | |
| 10b×feature_density | 1 | 0B；0.63s | 887B，Traceback，末行 `IsADirectoryError: [Errno 21] Is a directory: '…/U3PR2_back_j3slice'`（out/10b_dens_dirasbag.stderr.txt） | 无输出 | 无 | 干净拒绝（裸 traceback 通道，见坑位 E5） |

### 用例 11 爆止窗短袋帧目录（WC2OBS1_032005_j3 全量）

| 格 | ①退出码 | ②stdout 摘要 | ③stderr 摘要 | ④json 可解析 | ⑤NaN/除零 | ⑥失败模式分类 |
|---|---|---|---|---|---|---|
| 11×image_metrics | 0 | 2,409B；5.94s | 0B | 严格+宽松双过（out/11_img.json 77.3K） | per_frame 0 NaN；n_primary=73 全入选 | 干净通过 |
| 11×fb_residual | 0 | 703B；1.11s | 0B | 严格+宽松双过 | 0 NaN | 干净通过 |
| 11×feature_density | 1 | 0B；0.64s | 893B，同上 IsADirectoryError（out/11_dens_dirasbag.stderr.txt） | 无输出 | 无 | 干净拒绝（同 E5） |

注：feature_density 对帧目录输入无 `--frames-dir` 接口（工具头注释与 argparse 仅 `--bag`，j3_feature_density.py L166-178），三件中唯有它无法以帧目录为正输入；其在真实子集的正输入格（③b）与错误路径格（③a）见 §2。

## 2) feature_density 补充格

③a 错误路径（帧目录当 `--bag`，与合成用例线同款）＝上表两格：rc=1、IsADirectoryError 裸 traceback、stdout 0B → 干净拒绝。工具自带的两处 FAIL 消息通道（话题缺失 L48、无点云 L99）未触发——错误路径走的是未捕获异常而非 FAIL 通道。

③b 真实袋正输入格（既有 jr3_replay features.bag 只读，`source /opt/ros/noetic/setup.bash` 后 python3；默认三盒+默认 shift，全量 stdout 存档 out/*_dens_realbag.stdout.txt）：

| 格 | ①退出码 | ②stdout=json 本体 | ③stderr | ④严格 json | ⑤NaN/除零 | ⑥分类 |
|---|---|---|---|---|---|---|
| 11_dens_realbag（jr3_replay_WC2OBS1_032005/features.bag 2.1M） | 0 | 768B；0.73s | 0B | 过 | 0 NaN/Infinity | 干净通过 |
| 10_dens_realbag（jr3_replay_U3PR2_213717/features.bag 19M） | 0 | 771B；2.41s | 0B | 过 | 0 NaN/Infinity | 干净通过 |

读数：11 格 points_total=36,037 / msgs=609 / odom 2,036 / duration_s=102.0 / per_msg p50=51,p90=128,max=157；zones obstacle 4,097·ground 27,296·air 4,644；ground 分母 107,206.21 m²→per_m2=0.25，air 分母 315,710,340.73 m³→**per_m3 打印 0.0**（分母淹没）。10 格 points_total=781,230 / msgs=6,066 / odom 12,142 / duration_s=612.9 / per_msg p50=130,p90=149,max=167；zones obstacle 54,060·ground 724,461·air 2,709；ground 16.19 m²→per_m2=44,759.66。

与在册对账（现象登记，不作判言）：
- 10 格 points_total=781,230、odom 12,142、per_msg 130/149/167 与 raw/docs/t4_verdicts_v2.md L196/L199 原文逐位同；msgs 6,066 vs L196"6076 云"差 10（工具计非空 point_cloud，n==0 跳过，j3_feature_density.py L87-88）。
- fresh vs 在册 density json（metrics_U3PR2_213717_density.json、metrics_WC2OBS1_032005_density.json，md5 见 raw/raw_manifest.md5）：总点数逐位同（781,230 / 36,037）；zone 计数不同——WC2 ground 27,296 vs 27,324（−28）、air 4,644 vs 4,614（+30）、obstacle 4,097 vs 4,099（−2）；PR2 obstacle 54,060 vs 54,110（−50）、ground 724,461 vs 724,419（+42）、air 2,709 vs 2,701（+8）。两次运行的 `shift` 输入字段不同：fresh=工具默认 `[1.01,0.98,0.104]`（ground_top_vins=−0.004），在册=逐袋实测（PR2 `[1.0198,1.0126,0.1085]`、WC2 `[1.0094,0.9812,0.1036]`，见各 density json shift 字段）；boxes_gazebo 双方同（默认三盒）。

## 3) 前后半段对比（工具读数并列，不做因果判语）

读数源 out/10a_img.json、10b_img.json、11_img.json、10a_fb.json、10b_fb.json、11_fb.json：

| 读数 | 10a 前半(t18.7–316.5) | 10b 挂旗段切片(t335.0–632.7) | 11 全量短窗 |
|---|---|---|---|
| img n_primary | 36 | 36 | 73 |
| supply_frac p50 | 0.48 | 0.4667 | 0.8667 |
| corners_gFT p50 | 72 | 70 | 130 |
| d12_sigma_p25 p50 | 1.03(n=34) | 1.03(n=33) | 1.02978(n=66) |
| gamma_pair n | 34 | 33 | 67 |
| fb nf(立体对数) | 18 | 18 | 34 |
| fb temporal_pool n/p50/p90 | 1062 / 0.076px / 76.725px | 1099 / 0.009px / 29.408px | 3747 / 0.015px / 3.502px |
| fb stereo_pool n/p50/p90 | 1051 / 46.193px / 121.668px | 1003 / 42.881px / 123.458px | 3117 / 27.011px / 112.338px |
| h6 p90_ratio(stereo/temporal) | 1.586 | 4.198 | 32.082 |

对照在册：PR2 全程袋 metrics（raw/docs/t4_verdicts_v2.md L200 行原文 σ̂P25=1.03009 n=67、corners p50=71、M1 p50=0.473）——前后半切片读数 0.48/0.4667、72/70、1.03 落在全程读数近旁；11 全量与在册 metrics_WC2OBS1_032005.json 十个公共键 p50 **逐位相同**（见 §4）。

## 4) 复现性比对（fresh 工具 vs 在册产物，同输入）

- **image_metrics**：11 格 fresh 重跑 WC2OBS1_032005_j3 vs 在册 raw/vision_inputs/metrics_WC2OBS1_032005.json（md5 467f8a13c1a614bf8e5f52d7e305701e）：n_primary=73、per_frame=139 双同；公共 10 键 p50 逐位 SAME（corners 130 / d12_flat 1.0677 / d12_p25 1.02978 / gamma 1 / 方向熵 0.787851 / maxbin 0.280103 / grad_med 8.24621 / hist_range 149 / med_gray 175 / p_sat 1.6276e-05）。**键集不同**：fresh 12 键，在册 base 10 键（缺 supply_frac、grid4x4_occupancy_frac；现工具 L215-228 恒输出 12 键）——在册 base 为 W3 供给面增量前代工具产物（数据字典 §1"v5.0-W3 增量"注记同源）。
- **feature_density**：总点数逐位同、zone 计数随 shift 输入不同而异（§2，差 2–50 点，占该区计数 0.006%–0.65%）。

## 5) EX-FAIL 候选坑位表（格位 × 现象 × 一句话预案）

| # | 格位 | 现象 | 一句话预案 |
|---|---|---|---|
| E1 | 10/11×feature_density ③b | 同袋同工具重跑，总点数逐位同但 zone 计数差 2–50 点：fresh 用默认 shift 先验，在册 json 为逐袋实测 shift（shift/ground_top 字段在档可查） | density 复算对账前先核对本方 shift 与在册 json shift 字段一致，不一致格只比 points_total/per_msg，不比 zones |
| E2 | 11×image_metrics | 同目录重跑 10 公共键 p50 逐位同，但键集 12 vs 在册 base 10（在册无 supply_frac/grid4x4_occupancy_frac，代差产物） | 以在册 base json 对账时按"公共键交集"比对并注记键集代差，勿因缺 2 键登记缺面 |
| E3 | 10_dens_realbag | msgs=6,066（非空云计数）vs verdicts L196"6076 云"（全量口径），差 10=空云 | 云数引用带"非空/全量"口径注记，对账前统一口径 |
| E4 | 10a/10b/11×fb_residual | nf=min(L,R)=18/18/34，仅消费主帧的 47%–50%（73 主帧→34 对），时序池仅 17/17/33 帧 FB 残差 | 引用 fb 分布必带 nf/n 与主帧数比值，防按"139 帧目录全帧"误读样本覆盖 |
| E5 | 10b/11×feature_density ③a | 帧目录误当 --bag 时走裸 IsADirectoryError traceback（rc=1，stderr 887/893B），不经过工具自带 FAIL 消息通道，且 rc=1 与"话题缺失"FAIL 的 rc=1 同码 | 包装器按 stderr 末行异常名分类失败种别，勿按 rc 或 stdout 的 FAIL: 前缀 |
| E6 | 11_dens_realbag | air 区分母 3.16e8 m³ → per_m3 打印 0.0（分母淹没，n=4,644 仍在） | air/ground per_* 读到 0 时回读 zones.n 与分母原值字段再引用 |
| E7 | 全部 image_metrics/fb 格（机制在库、本轮 0 触发） | 工具存在两处静默机制：img 不可读静默 continue（j3_image_metrics.py:174-175）、梯度能量≤100 时 NaN 直写 json（L126-127，json.dump 出非严格 JSON）；本轮真实帧 0 丢帧 0 NaN（严格解析全过） | 下游解析固定走 parse_constant 严格通道，并核 n_primary+per_frame 长度与 manifest 条数差，切片/损伤帧场景必查 |
| E8 | 10a/10b 切片上游 | 切片 manifest 继承原 bag 字段、工具输出 frames_dir 指向 /tmp 切片路径——溯源字段两套并存 | 切片产物强制带 slice_note（已做），对账溯源以 manifest bag 字段+slice_stats.json 为准，frames_dir 字段不作同族判据 |

## 6) 证据文件清单（绝对路径）

- 格级六要素全量：D:/drone_VINS/t4_work_20261002/raw/exfail_real_cells/results_real.jsonl（10+4 行，含 4 行 _stdoutcap 修正行）
- 切片定义与实况：D:/drone_VINS/t4_work_20261002/raw/exfail_real_cells/slice_stats.json；切片器 D:/drone_VINS/t4_work_20261002/scripts/exfail_real_make_slices.py；跑批器 scripts/exfail_real_run_cells.py；density 二遍采集 scripts/exfail_real_density_capture.py
- NUC 环境与门禁：D:/drone_VINS/t4_work_20261002/raw/exfail_real_cells/nuc_env_gate.txt
- 格产物（NUC 原件 scp 回）：D:/drone_VINS/t4_work_20261002/raw/exfail_real_cells/out/{10a,10b,11}_{img,fb}.json、out/{10b,11}_dens_dirasbag.stderr.txt、out/{10,11}_dens_realbag.stdout.txt
- 对账基准（既有在册件，未改动）：D:/drone_VINS/t4_work_20261002/raw/vision_inputs/metrics_WC2OBS1_032005.json、metrics_U3PR2_213717_density.json、metrics_WC2OBS1_032005_density.json、raw/docs/t4_verdicts_v2.md、raw/inventory_runs.md、raw/raw_manifest.md5
