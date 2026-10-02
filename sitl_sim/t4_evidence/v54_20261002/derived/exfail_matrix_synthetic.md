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

## 修复后复跑登记（2026-10-03，C-14）

- 执行机：NUC uav4，`ssh nuc`；python3 3.8.10 / cv2 4.2.0 / numpy 1.17.4（2026-10-03 本轮实测，与文首同源）；各格执行前 `source /opt/ros/noetic/setup.bash`。
- 四笔修复（仓库 ~/catkin_ws，branch main，作者 rick，未 push）：
  - C14-FIX-1 `3a2722f13982f5079b1d535e639715d7ccfa7d75`（零可读帧拒绝，image+fb）
  - C14-FIX-2 `d2bb538bc2cefc0ac94ff942b5b9d905a64fb29a`（NaN 字面量清洗 null + allow_nan=False 兜底，image）
  - C14-FIX-3 `282a707287b42b91407c7b8d9629b7721861cbe6`（density shift 来源单一化 explicit/legacy/shift-file）
  - C14-FIX-4 `ea4d12b54133a5b031d54891613005930bd96dd8`（schema_version 键集代际 + manifest 版本分支，image+fb 对称）
- 被测工具（修复后，NUC 端 `sitl_sim/analysis/` HEAD 实测，与本机 c14_fix/ 副本一致）：
  - `j3_image_metrics.py` md5 `3721399e7a78e42f6e1cd81a2680286e`
  - `j3_fb_residual.py` md5 `08cb8829d180dad91445f1d436d547a2`
  - `j3_feature_density.py` md5 `7f45974b3a2a81e60c6293865ac3eb5e`
- 执行方式：合并终回归单次跑批 45 行 = 原 33 行（v57 跑批原样）+ 新增 12 行扩展格（C-14 夜审要求：每处修复 ≥2 格 edge case）。runner `~/sitl_sim/t4_selftest/build_and_run_v58_audit.py`（= v57 正本 md5 239b89f0… 逐字节保留 + 审计扩展块），独立审计 checker `check_audit_ext.py`，驱动 `regress_audit_v58.sh`（守卫：SITL.lock 原子取锁 t4wf＋df≥20G＋gzserver/rosbag 双 0；批次 timeout 900 nice -n 10）。原 33 行由修复工程师 expected_fix4.json 判绿（check_fix4.py，含 FIX-3 探针 P1-P7、FIX-4 探针 Q1-Q4），扩展 12 行由审计员期望表判绿，两 checker 互不依赖。实测最长格 0.75 s，无格触达 timeout（无挂死行）。尾行 `MATRIX-GREEN=绿 (merged 45 rows)`，双 checker rc=0。
- 本轮证据留档：本机 `work_selftest/audit_v58_evidence/`（results.jsonl 45 行、双 checker 日志、verdict 文件）；NUC /tmp/t4_v58_audit_*.log、/tmp/t4_v57_selftest/{results.jsonl,logs/}。
- 分类词在原四词基础上扩注一类：**零可读拒绝**＝rc=2、out 顶层恰为 `{schema_version, error, frames_dir}`、stderr 含 ERROR 行（属"干净拒绝"的带产出变体，由 FIX-1 引入）。

### 0a) 修复后期望分类表（原 30 格/33 行）

| 用例 | metrics | fb | density_offset |
|---|---|---|---|
| U1 空帧窗（1a 空目录＋1b 仅manifest） | 1a 干净拒绝 / 1b 零可读拒绝 | 1a 干净拒绝 / 1b 零可读拒绝 | 干净拒绝×2 行 |
| U2 单帧窗 | 干净通过 | 干净拒绝 | 干净拒绝 |
| U3 全白帧 | 干净通过（NaN 已清洗 null，非有限字面量 0） | 带病输出（空 pool） | 干净拒绝 |
| U4 全黑帧 | 干净通过（同 U3） | 带病输出（空 pool） | 干净拒绝 |
| U5 恒定噪声帧 | 干净通过 | 干净通过 | 干净拒绝 |
| U6 截断损坏 PNG | 零可读拒绝（rc=2） | 零可读拒绝（rc=2） | 干净拒绝 |
| U7 manifest 时刻重复 | 带病输出（重复计入） | 干净通过 | 干净拒绝 |
| U8 manifest 缺必填字段 | 干净通过（legacy 兼容读，n_primary=17，legacy_keys=true） | 干净通过（legacy 兼容读） | 干净拒绝 |
| U9 尾随空格文件名 | 零可读拒绝（rc=2） | 零可读拒绝（rc=2） | 干净拒绝 |
| U12 非常规位深/尺寸帧 | 干净通过 | 干净拒绝 | 干净拒绝 |

行计（33 行）：干净通过 9、零可读拒绝 6、带病输出 3、干净拒绝 15、挂死 0。对照修复前（§3：干净通过 5、带病输出 10、干净拒绝 18）：FIX-1 翻转 6 行（U1b/U6/U9 × metrics/fb → rc=2 零可读拒绝）、FIX-2 翻转 2 行（U3/U4 × metrics：NaN 字面量 34→0，转干净通过）、FIX-4 翻转 2 行（U8 × metrics/fb：KeyError → legacy 兼容读转干净通过）；其余 23 行分类保持。

### 0b) 扩展格期望分类表（新增 12 行，逐格）

| 格（case\|tool） | rc | 产出 | 分类 | 覆盖面 |
|---|---|---|---|---|
| case13_partread \| metrics | 0 | 完整统计 json，n_primary=15（17 帧仅 L_s000 截断不可读），legacy_keys=true | 干净通过 | FIX-1 新退出码误杀面：部分可读帧不触发零可读拒绝，正常出值 |
| case13_partread \| fb | 0 | pool 双非空＋h6_tail_compare 在位 | 干净通过 | FIX-1 同上（fb 侧） |
| case14_allgone \| metrics | 2 | out 顶层恰 [error, frames_dir, schema_version]，error 字段以 "no readable frames" 开头，严格 JSON 0 非有限 | 零可读拒绝 | FIX-1 error 字段旧消费者兼容面（缺文件型触发，区别于 U6 截断型） |
| case14_allgone \| fb | 2 | 同上 | 零可读拒绝 | FIX-1 同上（fb 侧） |
| case15_mixed_nanwhite \| metrics | 0 | 白/噪声混排：per_frame 清洗 null ≥8 处，grad_dir_maxbin_frac n≥8 仍可算，非有限字面量 0 | 干净通过 | FIX-2 NaN 上游清洗后统计仍可算 |
| case18_infreject_case3dir \| metrics_infreject | 1 | 绕过 _sanitize 注入非有限值：allow_nan=False 兜底抛 ValueError（Traceback），产出文件截断为不可解析空壳，无非有限字面量落盘 | 干净拒绝（rc=1） | FIX-2 合法 inf 序列化拒绝路径 |
| case19_shiftconflict \| density_shiftconflict | 3 | stderr 含 `SHIFT-CONFLICT` ASCII 标签，无产出 | 干净拒绝（rc=3） | FIX-3 --shift 与 --shift-file 并给报错 |
| case20_legacyshift \| density_legacy | 0 | stdout json：shift=[1.01,0.98,0.104]、shift_source="legacy"（探针袋 2×PointCloud×8点+odometry） | 干净通过 | FIX-3 --allow-legacy-shift 复现旧轮（shift 精确值另由 check_fix4 P3 探针全量断言） |
| case16_legacykeys \| metrics | 0 | 旧键集（无 tag/seg、无 schema_version）兼容读，n_primary=17，legacy_keys=true | 干净通过 | FIX-4 旧键集输入兼容读 |
| case16_legacykeys \| fb | 0 | pool 双非空，legacy_keys=true | 干净通过 | FIX-4 同上（fb 侧） |
| case17_schemavers9 \| metrics | 3 | stderr 含 `MANIFEST-SCHEMA-UNKNOWN`，无产出 | 干净拒绝（rc=3） | FIX-4 未知 schema_version 拒绝 |
| case17_schemavers9 \| fb | 3 | 同上 | 干净拒绝（rc=3） | FIX-4 同上（fb 侧） |

行计（12 行）：干净通过 6、零可读拒绝 2、干净拒绝 4、挂死 0。合计 45 行：干净通过 15、零可读拒绝 8、带病输出 3、干净拒绝 19、挂死 0。

### 0c) 本轮复跑说明与审计备注

- 审计件两处缺陷在首跑暴露并修正后才有终回归（均系审计 harness 自身，与被测工具无关）：case18 探针 wrapper 误将模块 spec 指向目录（漏拼文件名）；case20 忘记 `--world-boxes` 有三盒默认值致 stdout_head 240 字符窗口盖不住 shift_source（改为单盒显式声明）。
- 已知边界（本轮登记，不属四笔修复范围）：fb 时序残差分支对"前帧可读＋相邻帧不可读"的组合会以 cv2.error 崩溃退出（j3_fb_residual.py 主循环 `if i+1 < nf` 无 None 守卫，calcOpticalFlowPyrLK 不接受空帧）；原 33 格未覆盖该面，扩展格 case13 特意只截首帧 L_s000（pts=None 全短路）以隔离 FIX-1 判定面。该组合面的行为归类留待后续轮。
- 判读红线遵守：本节为复跑登记与分类对照，不出 PASS/FAIL 判读语；绿/红仅指"实测行为与期望分类表逐格一致"。
