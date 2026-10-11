# 内存泄漏 L2 符号级归属判决 v1.0（2026-10-11；工程合并 v1.6 单元2）

> 执行域=3090 回放源实例（t2v3_hover_134845.bag 137s 循环，私有 master :11312，话题零重映射直配）。
> 判据预注册=t1_memleak_l2.sh 头注（40KB/帧量子分配点归属到代码面+RSS 斜率复核）。
> 本判决取代路线：heaptrack 长窗（因插桩致停摆而废）→ 自研轻探针 t1_mtrace.so v4 + gdb 条件断点全帧 → 本件。

## 1. 执行链与三事故翻案（全部实证在案）

| 阶段 | 结果 | 判 |
|---|---|---|
| heaptrack 包 rosrun | 4K 空文件 | LD_PRELOAD 被 ROS 工具链剥离（月报 37） |
| heaptrack 直包二进制（supp 137s 单遍） | 符号级管线全通（trackImage:190 全栈行号） | 单遍无泄漏积累面（top=临时分配 8.6MB） |
| heaptrack 直包+loop（smoke/loopmain/包装轮 13 实例） | **VINS 一律 init 后停摆**（track 行冻结 693-1499，RSS 平） | heaptrack 插桩本身致停摆——baretest 对照：裸 VINS 200s 处理 20236 行+RSS 实涨 |
| slowmain（0.019× 单遍） | init 后输入饿死停摆 | 极端慢率下配对/探针交互路径，弃 |
| **自研 t1_mtrace.so v4 + 裸 VINS + loop（探针窗 55min，13 实例随机 SIGBUS 自动重启）** | **主窗成立** | 累计处理 track 行 21-23k/实例（≈裸速），mtrace 30-56 万行/实例 |

探针 v4 演进四坑（dlsym 启动段错误→__libc_ 直连；__thread 早期 TLS 段错误→全局守卫；fopen 重入爆栈→opening 守卫；`grep -f` 先匹配包装进程→`pgrep -x`）+ bag --loop 时戳回归 SIGBUS 边界死亡（飞行域时钟单调无此路径）——全部入月报 37/38/40。

## 2. 泄漏速率（RSS 斜率，7 实例 180-240s 窗合并）

- **回放域探针实测=0.95GB/h**（0.85-1.11 GB/h 带内，n=7，1620s 合并）。
- 对照：旧机实机统一模型 2.18GB/h（5h 窗第四数据点 2.09GB/h 同带）——回放域泄漏与实机同数量级（回放域无 T2 探针/健康占比差），**泄漏为 VINS 进程内在行为、非传感器/驱动域**，上周期 L1 段级结论（malloc 堆路径+纯匿名无文件映射）获符号级确认。

## 3. 符号级归属（两大独立证据面交叉定桩）

### 3.1 gdb 条件断点全帧（实例 12 上 20 hit，size∈(9.5,13.5)KB，零 unwind 歧义）

- **量子链 A（10512B，高频）**：`operator new` ← **`Estimator::processImage` estimator.cpp:666**（每帧特征容器 vector 分配）与 **`Estimator::slideWindow` estimator.cpp:2188**（滑窗容器）——VINS 自身代码。
- **量子链 B（11488-12192B，每轮求解）**：`operator new` ← `std::vector<ceres::internal::CompressedList>::_M_default_append` ← **`ceres::BlockJacobianWriter::CreateJacobian`** ← `TrustRegionPreprocessor::Preprocess` ← **`Estimator::optimization` estimator.cpp:1736**——Ceres 求解器每轮新建 Jacobian 结构。

### 3.2 探针 still-live 时序（实例 1，free 配对后按 caller 聚合）

- 主增长组：573→1177→1406 次（120s，**线性不封顶=真泄漏非 plateau**），单次 ~10.3KB —— 与链 A 对齐（bt3 落 libvins_lib PLT 帧垃圾化，gdb 面定桩）。
- 跨 13 实例合并 live top（相对排序面，绝对值受实例死亡尾差高估）：vins_node 内 ~900KB/次（=640×480×3 图像 buffer 家族）、libopencv_core ~156KB/次、libvins_lib 10.3KB×8994 次——三大家族=图像 buffer/estimator 容器/求解器结构。
- 单实例 ≥8KB live 增速 ≈0.7GB/h + <8KB 未记部分 → 与 RSS 0.95GB/h 自洽。✓

### 3.3 归属结论

**40KB/帧量子的构成（19Hz 双目回放）**：链 A（processImage:666 容器）+链 B（ceres CreateJacobian 每轮求解结构）为主量子（各 ~10-12KB/次、高频线性不归还）；图像 buffer（900KB 家族）与 OpenCV 内部（156KB 家族）为次级滞留面。**分配点已归属到代码面（行号级）**，判据达成。

## 4. 处置（终局制出口）

- 修复面评估：泄漏横跨 **VINS 源码（estimator.cpp:666/2188/1736 容器生命周期）+ Ceres（每轮求解结构不还）+ OpenCV（内部滞留）** 三层的复合源码级生命周期工程（重审 feature_buf/滑窗/marginalization 所有权链+上游 cherry-pick 对照+回归+泄漏复测）——**多日量级 → 归升级路线图冻结域（W12 独立排障线域）**，禁悬挂态。
- 当周期核心增量（已做完）：归属判决（本件）+速率模型（0.95GB/h 回放域/2.09GB/h 实机第四点）+工具资产（t1_mtrace.so v4 探针+聚合器+gdb 条件断点法——升级路线图 W12 可直接复用）。
- 运维缓解维持：旧机 5h 窗重启制（本周期已执行到窗，watch2 连续在册）。

## 5. 证据索引

- 探针窗：memleak_l2/probe_window_211030/{window.log, inst1..13/{mtrace.log,msum.log,rss.csv,vins.log,play.log}, maps_*.txt(9), gdb_bt4.txt(20 全帧)}
- 阶段件：l2_smoke_200420 / l2_loopmain_201130(SIGBUS 现场+heaptrack 4K 空文件) / l2_supp_202539(heaptrack 符号管线通+PEAK 面) / baretest_*(对照定案) / l2_slowmain_*(慢率停摆)
- 工具：t1_mtrace.c(v4)+t1_memleak_l2.sh+t1_memleak_l2_wrapper.sh+t1_l2_probe_window.sh+t1_l2_gdb2.cmd+t1_mtrace_liveagg2.py+t1_l2_final_agg.py+t1_nmnear.py+t1_mtrace_sym_samples.py
- 上游：unit4_memleak_forensics_design_v1.md（L0/L1 设计）；vins_mem_watch_v1139.csv（实机连续面）
