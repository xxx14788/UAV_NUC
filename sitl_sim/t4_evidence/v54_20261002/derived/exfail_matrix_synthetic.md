# 判读工具稳健性自测·合成用例矩阵（2026-10-02，NUC 实测登记）

- 执行机：NUC uav4，`ssh nuc`；python3 3.8.10 / cv2 4.2.0 / numpy 1.17.4 / PIL 7.0.0（raw/data_dictionary.md §3 同源实测）；j3_feature_density.py 各格执行前 `source /opt/ros/noetic/setup.bash`。
- 被测工具（未修改，两端 md5 一致：NUC 实测与本机 scp 副本相同）：
  - `/home/uav/catkin_ws/sitl_sim/analysis/j3_image_metrics.py` md5 `abcc5fc811007b6ad16b8000d96f3022`
  - `/home/uav/catkin_ws/sitl_sim/analysis/j3_fb_residual.py` md5 `c23d42879e9ba6fa722df36f8871003f`
  - `/home/uav/catkin_ws/sitl_sim/analysis/j3_feature_density.py` md5 `9e45f9817d8a5370363f8b59e4bb125e`
- 合成输入：NUC:/tmp/t4_v54_selftest/cases/（构造脚本 NUC:/tmp/build_and_run_selftest.py，本机留档 work_selftest/build_and_run.py；帧 640×480 uint8 PNG，恒定噪声图=RandomState(7) 同图复用；manifest 仿 U3PG_210307_j3/manifest.json 字段）。/tmp/t4_v54_selftest 实测 26M。
- 执行方式：每格 `bash -lc "source /opt/ros/noetic/setup.bash; timeout 90 <工具命令>"`，逐格捕获退出码/stdout/stderr/产出文件；30 s 内全部自行落定，实测最长 1.02 s，无格触达 timeout（无挂死行）。
- density_offset 格输入统一为 `--bag <该用例帧目录路径>`（任务指定 --mode offset 错误路径；offset 模式只吃 bag，帧类用例无对应 bag 形态）。
- 行=格记录；用例 1 含两个子变体（1a 空目录 / 1b 仅 manifest），故 30 格共 33 行登记。逐格原始记录（rc/耗时/字节数/非有限字面量计数/stdout-stderr 摘要全文截断）落盘本机 `work_selftest/results.jsonl`，stdout/stderr 原文在 NUC:/tmp/t4_v54_selftest/logs/。
- 分类词只有四个：干净通过（rc=0、产出 JSON 可解析、无非有限字面量、统计非空）/ 带病输出（rc=0 但空统计、NaN 字面量、pool 键缺失或重复计入）/ 干净拒绝（rc≠0、无产出文件、stderr 为明确异常）/ 挂死。

## 0) 总矩阵（30 格）

| 用例 | metrics | fb | density_offset |
|---|---|---|---|
| U1 空帧窗（1a 空目录＋1b 仅manifest） | 1a 干净拒绝 / 1b 带病输出 | 1a 干净拒绝 / 1b 干净拒绝 | 干净拒绝×2 行 |
| U2 单帧窗 | 干净通过 | 干净拒绝 | 干净拒绝 |
| U3 全白帧 | 带病输出（NaN×34） | 带病输出（空 pool） | 干净拒绝 |
| U4 全黑帧 | 带病输出（NaN×34） | 带病输出（空 pool） | 干净拒绝 |
| U5 恒定噪声帧 | 干净通过 | 干净通过 | 干净拒绝 |
| U6 截断损坏 PNG | 带病输出（n=0+libpng） | 带病输出（空 pool+libpng） | 干净拒绝 |
| U7 manifest 时刻重复 | 带病输出（重复计入） | 干净通过 | 干净拒绝 |
| U8 manifest 缺必填字段 | 干净拒绝 | 干净拒绝 | 干净拒绝 |
| U9 尾随空格文件名 | 带病输出（n=0 零警告） | 带病输出（空 pool 零警告） | 干净拒绝 |
| U12 非常规位深/尺寸帧 | 干净通过 | 干净拒绝 | 干净拒绝 |

行计（33 行）：干净通过 5、带病输出 10、干净拒绝 18、挂死 0。

## 1) 逐格登记

### U1 空帧窗（case1a_emptydir＝空目录无 manifest；case1b_manifestonly＝仅 manifest frames=[]）

| 工具/变体 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics / 1a | 1 | 0.46 | 无 | - | - | 空 | `FileNotFoundError: ... case1a_emptydir/manifest.json`（j3_image_metrics.py:167 open） | 干净拒绝 |
| metrics / 1b | 0 | 0.36 | out_metrics.json 652B | 是 | 0 | 聚合面 12 键全部 `{"n": 0}`；n_primary=0、per_frame=[] | 空 | 带病输出（全零统计面退出 0） |
| fb / 1a | 1 | 0.45 | 无 | - | - | 空 | `FileNotFoundError: ... manifest.json`（j3_fb_residual.py:94） | 干净拒绝 |
| fb / 1b | 1 | 0.47 | 无 | - | - | 空 | `AssertionError: need >=2 stereo pairs, got L=0 R=0`（j3_fb_residual.py:114） | 干净拒绝 |
| density / 1a | 1 | 0.65 | 无 | - | - | 空 | `IsADirectoryError: [Errno 21] Is a directory`（rosbag/bag.py:1450 open） | 干净拒绝 |
| density / 1b | 1 | 0.64 | 无 | - | - | 空 | 同上 IsADirectoryError | 干净拒绝 |

### U2 单帧窗（case2_singleframe：1 帧 L_s000.png，manifest frames len=1）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.38 | out_metrics.json 2315B | 是 | 0 | n_primary=1；12 键 n=1（p10=p50=p90 同值）；d12_sigma_flat/d12_sigma_p25/gamma_pair n=0；n<8 无 CI 键 | 空 | 干净通过 |
| fb | 1 | 0.46 | 无 | - | - | 空 | `AssertionError: need >=2 stereo pairs, got L=1 R=0`（j3_fb_residual.py:114） | 干净拒绝 |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U3 全白帧（case3_allwhite：17 张 255 灰阶模板帧）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.64 | out_metrics.json 7925B | 是（json.loads 宽容） | **34**（grep -c "NaN" 实测 34，留档 work_selftest/case3_out_metrics.json） | stdout 聚合面：p_sat p50=1.0（n=16，含 p90_ci/med_ci）、hist_range 0、med_gray 255；grad_dir_maxbin_frac/grad_dir_entropy_norm 两键 `{"n": 0}`（per_frame 的 NaN 在聚合侧被 isnan 过滤，j3_image_metrics.py:202-203） | 空 | 带病输出（退出 0＋产出文件 34 处 NaN 字面量＝17 帧×grad_dir 两键，j3_image_metrics.py:126-127 写入；JSON 非严格合法，Python json.load 之外解析器拒收） |
| fb | 0 | 0.43 | out_fb.json 298B | 是 | 0 | stdout=`{}`；产出键仅 frames_dir/lk_params/method_note/stereo/temporal，temporal=[]、stereo=[]，temporal_pool/stereo_pool/h6_tail_compare 三键缺失（j3_fb_residual.py:143-151 仅在有残差时写入） | 空 | 带病输出（退出 0＋空 pool＋stdout 空对象） |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U4 全黑帧（case4_allblack：17 张 0 灰阶模板帧）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.63 | out_metrics.json 7756B | 是 | **34**（同 U3 机制，results.jsonl out_nonfinite_hits=34） | p_sat p50=1.0、med_gray 0、hist_range 0（n=16）；grad_dir 两键 n=0；gamma_pair n=0（med_gray=0 不满足 >5 配对条件，j3_image_metrics.py:239） | 空 | 带病输出（同 U3：NaN 字面量进产出文件） |
| fb | 0 | 0.43 | out_fb.json 298B | 是 | 0 | stdout=`{}`；pool 三键缺失、temporal/stereo 空数组 | 空 | 带病输出（同 U3/fb） |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U5 恒定噪声帧（case5_constnoise：17 张同一 RandomState(7) 噪声图）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.97 | out_metrics.json 9673B | 是 | 0 | n_primary=16；12 键全 n=16（d12 两键 n=1）；无 NaN；D12 帧间差分同图→σ̂=0；gamma_pair n=1 | 空 | 干净通过 |
| fb | 0 | 0.49 | out_fb.json 3272B | 是 | 0 | temporal_pool n=1050、p50=p90=p95=p99=0.0（同图 LK 恒等映射）；stereo_pool 同构；h6_tail_compare 键在位；未触发除零（p90_ratio 分母 `max(p90,1e-9)`，j3_fb_residual.py:149） | 空 | 干净通过 |
| density | 1 | 0.64 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U6 截断损坏 PNG（case6_truncpng：模板 17 张各截留前 60% 字节）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.35 | out_metrics.json 647B | 是 | 0 | 全键 n=0、n_primary=0、per_frame=[]（cv2.imread 全部返回 None 后静默 continue，j3_image_metrics.py:174-175） | `libpng error: Read Error`×17 行（wc -l=17） | 带病输出（退出 0＋全零统计面；libpng 报错仅上 stderr） |
| fb | 0 | 0.35 | out_fb.json 298B | 是 | 0 | stdout=`{}`；pool 三键缺失（imread None→goodFeaturesToTrack(None) 在 cv2 4.2 绑定下返回 None 不抛错，pts is None 走 fb_residual 短路，j3_fb_residual.py:54-56） | `libpng error: Read Error`×23 行（wc -l=23） | 带病输出（退出 0＋空 pool＋stderr 23 行 libpng） |
| density | 1 | 0.63 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U7 manifest 时刻重复（case7_dupts：L_s000 记录原样复制 1 条，同 file 同 t_rec）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 1.02 | out_metrics.json 10037B | 是 | 0 | n_primary=17（16 主帧＋重复记录 1 条直接计入）；gamma_pair n=2（重复记录使同 file 主帧命中两次，j3_image_metrics.py:232-242）；其余键 n=17 | 空 | 带病输出（重复记录无去重、无告警进入分位统计） |
| fb | 0 | 0.50 | out_fb.json 3267B | 是 | 0 | temporal_pool/stereo_pool n=1050、p50=p90=0.0；t_rec 重复仅进 sorted 稳定排序（j3_fb_residual.py:96-99），产出结构与 U5/fb 同 | 空 | 干净通过 |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U8 manifest 缺必填字段（case8_missingfield：frames 每条目删除 tag 键）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 1 | 0.45 | 无 | - | - | 空 | `KeyError: 'tag'`（j3_image_metrics.py:169 列表推导 `fr['tag'] in ('','next')`） | 干净拒绝 |
| fb | 1 | 0.45 | 无 | - | - | 空 | `KeyError: 'tag'`（j3_fb_residual.py:98 列表推导） | 干净拒绝 |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U9 尾随空格文件名（case9_trailspace：manifest file 全部带尾随空格，磁盘文件名干净）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.32 | out_metrics.json 649B | 是 | 0 | 全键 n=0、n_primary=0、per_frame=[]（imread 带空格路径全部 None→静默跳过）；stdout 亦为全 n=0 JSON | **空（零告警）**（留档 work_selftest/case9_out_metrics.json） | 带病输出（退出 0＋全零统计面＋stderr 无任何提示） |
| fb | 0 | 0.34 | out_fb.json 300B | 是 | 0 | stdout=`{}`；pool 三键缺失（manifest 命中带空格 file→imread None→gFT 返 None→无残差，全程无异常抛出） | **空（零告警）** | 带病输出（退出 0＋空 pool＋零告警） |
| density | 1 | 0.65 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

### U12 非常规位深/尺寸帧（case12_odddepth：L_s000 8bit 640×480；L_s001 16bit PNG 640×480；R_s001 72×48；L_s000_next 320×240）

| 工具 | rc | 耗时s | 产出 | json 可解析 | 非有限字面量 | stdout 摘要 | stderr 摘要 | 分类 |
|---|---|---|---|---|---|---|---|---|
| metrics | 0 | 0.49 | out_metrics.json 4637B | 是 | 0 | n_primary=4；16bit PNG 经 IMREAD_GRAYSCALE 读回 8bit 未崩（p_sat p50≈0.0235）；72×48 帧 PATCH=16 整除余数被 floor 截断未崩（nh,nw=3,4）；next(320×240) 对 base(640×480) 的 D12 patch 级 16×16 块相减形状兼容未崩，产出 d12_sigma_flat=73.14412112779625（该值来自跨尺寸 pair 并回填 base，j3_image_metrics.py:144-148、186-194；留档 work_selftest/case12_out_metrics.json）；gamma_pair n=1 | 空 | 干净通过 |
| fb | 1 | 0.51 | 无 | - | - | 空 | `cv2.error: OpenCV(4.2.0) lkpyramid.cpp:1391: error: (-215:Assertion failed) prevPyr[...]size() == nextPyr[...]size() in function 'calc'`（640×480 对 72×48 LK，calcOpticalFlowPyrLK 无尺寸前置校验） | 干净拒绝 |
| density | 1 | 0.66 | 无 | - | - | 空 | IsADirectoryError（rosbag/bag.py:1450） | 干净拒绝 |

## 2) NaN 与除零行为登记（跨格汇总）

- NaN 写入产出文件的格：U3/metrics、U4/metrics，各 34 处 NaN 字面量（per_frame 17 帧 × grad_dir_maxbin_frac / grad_dir_entropy_norm 两键；写入点 j3_image_metrics.py:126-127；json.dump 未禁 allow_nan，j3_image_metrics.py:244-245）。产出文件 Python json.load 可解析（宽容 NaN），stdout 聚合面无 NaN（聚合侧 isnan 过滤后 n=0，j3_image_metrics.py:202-203）。
- 除零显式异常：0 格（无任何 ZeroDivisionError token 命中）。U5/fb 的 h6_tail_compare p90_ratio 分母走 `max(p90, 1e-9)` 保护（j3_fb_residual.py:149），残差全 0 时 ratio=0.0，未抛错。
- 汇总 `{"n": 0}` 空统计面格：U1b/metrics、U6/metrics、U9/metrics（三者退出码均为 0，stdout 亦为全 n=0 JSON）。

## 3) 失败模式分类汇总（33 行）

| 分类 | 行数 | 行明细 |
|---|---|---|
| 干净通过 | 5 | U2/metrics、U5/metrics、U5/fb、U7/fb、U12/metrics |
| 带病输出 | 10 | U1b/metrics（n=0）、U3/metrics（NaN×34）、U3/fb（空 pool）、U4/metrics（NaN×34）、U4/fb（空 pool）、U6/metrics（n=0+libpng 17 行）、U6/fb（空 pool+libpng 23 行）、U7/metrics（重复计入）、U9/metrics（n=0 零告警）、U9/fb（空 pool 零告警） |
| 干净拒绝 | 18 | 10×density_offset（IsADirectoryError 同型）＋U1a/metrics、U1a/fb（FileNotFoundError）＋U1b/fb、U2/fb（AssertionError）＋U8/metrics、U8/fb（KeyError 'tag'）＋U12/fb（cv2.error 尺寸断言） |
| 挂死 | 0 | 无（最长 1.02 s，timeout 90 未触达） |

## 4) 证据文件与留档位置

- 本机：`D:/drone_VINS/t4_work_20261002/work_selftest/`——results.jsonl（33 行逐格记录）、build_and_run.py（构造+驱动脚本，NUC 副本 /tmp/build_and_run_selftest.py）、j3_*.py 三工具只读副本（md5 与 NUC 端一致）、case3_out_metrics.json（含 34 处 NaN，grep -c "NaN"=34）、case3_out_fb.json、case9_out_metrics.json、case12_out_metrics.json。
- NUC：/tmp/t4_v54_selftest/（cases/ 11 目录＋out_*.json 产出、logs/ 每格 stdout/stderr 原文、results.jsonl），合计 26M。
- 工具零修改：NUC 端 md5sum 与本机 scp 副本 md5sum 逐字节一致（见文首三行 md5）。
