# T4-J2 判读阈值标定：外部文献与口径准备（等待池③，2026-10-01）

> 目的：≥5 轮带图素材到货前，把 J2（像素侧特征密度/分布判读）的指标定义、参数锚点、阈值标定
> 协议备齐。方向裁决 C12 口径强制：报分位+n_eff+CI、禁单帧/标题条、**阈值=新袋产额分位**（不从
> 文献硬搬判线；文献锚点只用于"参数含义"与"合理范围"）。素材到货后 24h SLA 内按本口径出正式判读。

## 1. 参数锚点表（全部 repo 内可核查，一级证据）

| 参数 | 值 | 用途（代码实证） | 出处 |
|---|---|---|---|
| max_cnt | 150 | 每帧目标角点数上限；增量补点 `goodFeaturesToTrack(cur_img, n_pts, MAX_CNT-cur_pts.size(), 0.01, MIN_DIST, mask)` | sim_stereo/fast_drone_250/realsense_d435 三配置同值；feature_tracker.cpp:190 |
| qualityLevel | **0.01 硬编码** | Shi-Tomasi 角点质量门，非配置面 | feature_tracker.cpp:190 |
| min_dist | 30px | 相邻特征最小间距（掩膜圆半径） | 三配置同值；feature_tracker.cpp:82 |
| F_THRESHOLD | 1.0（默认，三配置均未显式写） | **F 矩阵 RANSAC 外点判像素阈**（非角点质量）：`findFundamentalMat(..., FM_RANSAC, F_THRESHOLD, 0.99, status)` | feature_tracker.cpp:347 |
| freq | 10（三配置同值） | VINS 有效处理帧率上限——**两域同口径 10Hz**，J2 判读按"每处理帧"归一 | sim_stereo/e2_debug_smooth、realsense_d435、fast_drone_250 |

J2 含义注：J3 六维表纹理行「sim 37 角点/帧 vs 样张 117-150/帧」的对照基准=max_cnt 150——
sim 供给率 0.25 / 样张 0.78-1.0（1080p 口径换算待样本），供给饥饿是 R3 pyrLK 奇异根因的像素侧镜像。

## 2. J2 指标草案（帧级像素统计域，与 T2 插桩域/J1.3 三维点域三域划界）

| # | 指标 | 定义 | 分位口径 | 工具现状 |
|---|---|---|---|---|
| M1 | 供给率 | 每处理帧角点数 / max_cnt | P10/P50/P90 + n_eff | j3_image_metrics.py 已出角点数，补归一 |
| M2 | 空间分布 | 4×4 网格占用格数/16；最大格占比 | P50/P90 | 需补（现仅方向集中度 0.200） |
| M3 | 平坦梯度 | 平坦区梯度 P50（flat-band 口径） | P50 + 零梯度帧占比 | 已有（X1img 双袋 P50=0.0 双证） |
| M4 | 模糊代理 | Laplacian 方差 + 方向能量 | P50/P90 | 部分有（方向能量 0.200=纹理本底口径已立） |
| M5 | 外点率 | F-RANSAC 剔除比例 | P50/P90 | **归 T2 插桩域**（划界已握手），J2 不做 |
| M6 | track 寿命 | 同 ID 帧间存活长度 | P50/P90 | **归 T2 插桩域**，J2 不做 |

三域划界（复述防漂移）：J1.3=3D 特征点分区密度（点/m²，重放特征袋）；J2=像素侧帧统计（本册）；
T2=插桩域（track/FB/深度内状态）。三域判读互不重做、交叉引用。

## 3. 阈值标定协议（正式轮执行步骤）

1. **候选嫌疑线（待数据标定，非判线）**：M1 供给率 P10<0.2=供给饥饿嫌疑；M2 占用格 P50<8/16=分布
   退化嫌疑；M3 零梯度帧占比 >0.3=平坦区主导嫌疑——三条均标注"嫌疑触发→转 T2 插桩域复核"，
   J2 单域不下死判（单帧/单域禁判红线）。
2. **产额分位法**（C12 强制）：正式阈值=≥5 轮新袋各指标合并分布的分位（P10 为运营门，P50 为基线），
   标定后回填本册 §4 表并写 verdicts 台账行；改阈值必须给数据分布依据。
3. **统计口径**：n_eff=独立轮数×段数（段间不独立按轮计）；CI=bootstrap 95%（重采样单元=轮）；
   禁单帧结论；素材>50KB 有效性门。
4. **曝光耦合**：γ 帧间统计仅近静止段纯净（X1img2 γ_pair P90=2.105 goal 视角剧变伪影教训），
   M4 判读限定悬停/匀速段，段判定用 odometry 速度门（|v|<0.3m/s）。
5. **饱和处理双列（C-5 裁定落地；2026-10-02 预注册，先于判读数据包 commit）**：每指标同报双列=
   原值分位（P10/P25/P50/P90，全部帧样本）+ 去饱和分位（剔除该帧饱和样本后重算，同分位族，
   附剔除率列）；每指标饱和判据预声明：M1 供给率=角点数触 max_cnt 150（配额顶格帧）；曝光类
   （hist_range/med_gray）=位深顶格（0/255 主导帧）；其余指标不设饱和剔除。两列各自对照产额
   分位门，**判读门取两列中更不利者（严侧）**——禁单选美化（总设计师 10-02 跨线裁）。
6. **判读映射（预注册三态）**：正常（指标 ≥P50 基线）/ 中间观察带（P10–P50 之间，@T2 注记
   不作判）/ 饥饿嫌疑（<P10 运营门 → 转 T2 插桩域复核）。J2 单域不下死判（红线复述）；
   爆止窗袋入样必带窗长注记。
7. **解释性附录（预注册）**：十指标相关矩阵（Pearson+Spearman 双列）+ 跨袋一致性表（袋间 CV、
   Kendall W、离群袋点名）为判读文附录；|ρ|>0.8 冗余对在判读文降权表述、数据全保留
   （减面不减信息）。
8. **口径锁定**：判读对象=8 注入代袋合并分布（袋集合以 j2_threshold_table_v1.json 为准）；
   重采样单元=轮；bootstrap 95% CI 1000 次；本预注册（§3.5–3.8）先于判读数据包 commit
   （提交时间戳即预注册凭证），判读文随后依此出。

## 4. 阈值表（素材到货后回填）

| 指标 | 基线 P50（标定值） | 运营门 P10 | 数据分布依据 | 标定日 |
|---|---|---|---|---|
| M1 供给率·原值列 | 0.823 | 0.562 | verdicts v2 L302 产额分位门（Set A 八袋袋级 p50 跨袋）；j2_threshold_table_v1.json supply_frac 全精度 P50=0.8233/P10=0.562/P90=0.9697 | 2026-10-02 |
| M1 供给率·去饱和列 | —（不构成阈值面） | —（不构成阈值面） | verdicts v2 L321：U3PH 去饱和后 n=4，其去饱和分位不构成阈值面（d4 §5.5）；严侧判不翻转主池结论→判读门取原值列；扩展池剔除率 U3PH 0.9444/U3PR1 0.0694/X1final 0.2917（d4_saturation_dual.csv 120 行，d4_j2_plane.md §4） | 2026-10-02 |
| M2 占用格·原值列 | 0.844 | 0.588 | verdicts v2 L302 产额分位门；j2_threshold_table_v1.json grid4x4_occupancy_frac 全精度 P50=0.8438/P10=0.5875/P90=1.0 | 2026-10-02 |
| M2 占用格·去饱和列 | 同原值列（双列=单列） | 同原值列（双列=单列） | 预注册 §3.5 M2 不设饱和剔除；verdicts v2 L321 主池五袋无饱和剔除需求（双列=单列） | 2026-10-02 |
| M3 零梯度占比 | 待标定 | 待标定 | verdicts v2 十指标面（L302）无零梯度帧占比门值行，不回填数字（待主会话定稿）；最近关联 grad_med 门值 P50/P10=8.246/4.91（L302）系平坦梯度中位数，非同指标，映射未裁定 | — |
| M4 Laplacian | 待标定 | 待标定 | verdicts v2 十指标面（L302）无 Laplacian 指标与门值，不回填数字（待主会话定稿） | — |

回填口径=§3 第 5 条双列（原值+去饱和各一行，附剔除率与严侧标记）。
回填记录（2026-10-03，T4 工作流 §4 回填员）：M1/M2 门值按 verdicts v2 正源回填（数字逐位=L302/L321 与
j2_threshold_table_v1.json 互证）；M3/M4 在 verdicts v2 无对应门值行，维持待标定并注记实况，不编数；
改动格=M1/M2 原值+去饱和共 4 行新增值+M3/M4 依据列注记。数据面转抄，判读待主会话定稿。

## 5. 文献锚点（二级，仅含义与范围，不搬判线）

- Qin, Li, Shen — **VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator**,
  IEEE T-RO 2018：前端 KLT+均匀化（min_dist）+F 验外点架构的原始出处口径。
- Qin, Shen 等 — **VINS-Fusion**（repo 自带上游默认值即为本文 §1 锚点源）。
- Jianbo Shi, Carlo Tomasi — **Good Features to Track**, CVPR 1994：qualityLevel/min_dist 语义。
- Jean-Yves Bouguet — **Pyramidal Implementation of the Lucas Kanade Feature Tracker**（Intel 技术报告，
  2001）：pyramid LK 与失败模式（R3 平坦区奇异的历史实锤=T2-R3 已闭环）。
- OpenCV 文档：goodFeaturesToTrack/findFundamentalMat 参数语义（qualityLevel≠RANSAC 阈值，本册 §1 已代码实证）。
- 运动模糊与可跟踪性：六维表运动模糊行 sinc² 拐点 ±40px（H9）+ t_exp=8ms 样张锚，M4 代理口径承袭。

## 6. 与素材管线的接口

- 输入=vision_inputs/queue_j3/（J-R3① 排队器产物）+ j3_extract_frames --pairs 帧；
- J2 判读脚本=j3_image_metrics.py 增量（M1 归一+M2 网格），改动入库前过 dry-run 校准（J-R3② 同法）；
- 素材到货（STATUS 通告）→ 24h 内按本册口径出正式 J2 判读 → verdicts 台账行 + @T2/T3 采信。
