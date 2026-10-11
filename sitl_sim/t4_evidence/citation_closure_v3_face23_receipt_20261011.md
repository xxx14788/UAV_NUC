# 引用闭环 v3 面②③收口凭据（T4 v5.37 单元 3；2026-10-11 夜）

> 面①基线=closure_v3_scan_20261011.txt（46 源 287 refs，16:21 生成，missing 89=both 48+nuc_only 41+skip 0）；本件=面② NUC 真对账（41 件逐件归位）+面③ missing_both 48 三族分账终版。性质=存在性对账登记，零三态判定，零文档改动（只列不修红线维持；verdicts 正本零触碰复核 4f34d500→转录后 f8ef65ba 本夜在册）。
> 探针凭据=本会话本地脚本 t4v537_u2_nuc_probe.sh（ssh stdin 注入旧机执行，41 行 stat+size+真载体复核，23:4x）；旧机 df=28G 空闲（88% 用量，高于 20G 红线但在收窄带）。

## 面② nuc_only 41 件逐件归位（处置三类）

**A. 注记（双侧同物在位/path-style 引用）——38 件**：
- 32 件=工具备注已证 3090 镜像 basename 在位（/home/ghj 镜像路径随行）+本探针 NUC 侧 PRESENT 带 size 实锤：1b_bias_route 族 5（bias_constraint2_design/bias_route_final_verdict/box_arm/box_pairs_v1010/tlock_pairs_v1010）+1c_runs 族 6（bc_recovery/delta_fine_scan_judge/delta_fine_scan_verdict/three_arm_final_verdict/warmup_pairs_v107/x7_convergence_material）+_j3/manifest.json+fast_drone_250.yaml+e2_debug_smooth.yaml×2（catkin 位+WA5C_a6_c4 位同 size 3288）+derived 族 9（c15_wc2obs1_bitchk/d1_supply_model/d2_ndim_corr/d3_truncation/d4_j2_plane/d4_saturation_dual/exfail_matrix_synthetic/j2_seg_judgment_v1/pool_m1m2_byseg）+replay_frames.csv（221KB）+queue_state.json+m3p_results.md+last_verdict_audit_v58.txt（真载体非备份位双在位）+build_pool_m1m2_byseg.py+c15_wc2obs1_bitchk.py+c1_verdict_v1.md(v112 精确相对位)+xline_histreg/summary.csv。
- 2 件=EV/RESULT.txt（87B）+EV/simvins.log（3.6MB）：真载体=旧机 run_T2BL6_203956 run 目录在位；"EV/"为当时工作别名，目录本位不存在——引用属实、路径风格注记。
- 4 件=R1G_g_chi2/depth/reprop/smooth 四配置：**工具的 E15_acc050_gyr001 命中=basename 噪声，本探针真载体实锤**——旧机 /home/uav/sitl_sim/t2_configs/R1G_g_{chi2,depth,reprop,smooth}/sim_stereo_imu_config.yaml 四目录全在位（各 2535B）；3090 无=域资产分布现状（T2 域判读毕，复现凭据留旧机），应同步=否。

**B. 应同步候选（登记，本窗不搬运）——2 件**：
- t2v3_ground_205302.bag：旧机 bags/ 在位 **1.6GB**（1599853275B）——W1 收货证据袋；搬运=窗内 IO 预告件（目标目录未预注册），本窗只登记。
- v1_ground_salvage_211520.bag：旧机 catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28/ 在位 29.9MB；3090 同名目录已在（未跟踪态）但无此袋——随 T1 v1 证据归集窗搬运。

**C. 瞬态已清——1 件**：EV/sitl.log（工具 16:21 报在位 t3_runs/R3090_3_222740/，本探针 23:4x 复测 ABSENT——运行日志当窗被清；引用=历史运行凭证，缺失属预期态）。

**汇总**：41=注记 38+应同步候选 2+瞬态已清 1；零除名、零同步执行、零文档改动。

## 面③ missing_both 48 三族分账终版（实勘五族）

- **族 A 瞬态/运行期工件——13**：/home/uav/sitl_sim/SITL.lock（锁 symlink 瞬态，报告原注）+/tmp/* 11 件（audit_queue_driver.sh、e4_scenario_byseg_out.json、e4_scenario_byseg_tables.md、t4_hbloop_test_v533.lock、t4_locktest.lock、t4_w1_work/t4_w1_replay.sh、t4w1_reception/bags_md5.txt、t4wf_pool4_scan.py、t4wf_pool4_scan_out.txt、t4wf_pool5_scan.py、t4wf_pool5_scan_out.txt——扫描中间产物/测试侧锁/收货清单，凭据在各凭据文档）+EV/wa_online.txt（运行期输出）——**缺失属预期态，注记销号**。
- **族 B 已删凭据型——18**：袋 17（_shift.bag×3occ、e7_ctrl2_125hz.bag×2occ、flight_2026-09-26_220814/224815/230126.bag、t2_A_173156、t2_A_60hz320、t2_A_60hz640、t2_A_clean、t2_C_60hz320、t2_C_60hz640、t2v3_ground_202520、t2v3_hover_203248、t2v3_route_112652、t2v3_route_112652_125hz、t2v3_route_203830、t2v3_route_212450、t2v3_route_215016、t2w5_p2_215545×3occ）——**本探针独立实锤**：旧机 bags/ 目录 63 袋中上述 15 个原始袋名 raw=0（在册 57 个"匹配"均系 compact_* δ 精简衍生变体，非引用对象）；删除=判读毕磁盘纪律（W-0 三袋删凭据在 verdicts 等 lineage），袋名引用=历史凭证——**凭据型注记销号**。+rootfs/etc/logging/logger_topics.txt——3090 全域深搜（maxdepth 6）无=毒文件依根除链"禁用该路径"移除（月报 A 系首条+v112 close F#1），引用=取证记录——销号。
- **族 C Windows 侧载体——15**：plans/ 7（2026-09-27_t4_report ✓现役/2026-09-28_vision_acceptance_v2 ✗双侧未检得/2026-10-01_prompt_disk_chain ✗/2026-10-03_T4_v57_night_workflow ✓/v5.17 ✗/v5.24 ✗/2026-10-09_v5.26 ✓现名 2026-10-09_T4_v526_workflow.dwf.ts 改名载体）+/drone_VINS/t4_v526_out/verdicts_draft_v526.md（草稿本夜已转录归档改名 transcribed_20261011——引用时点载体成立，现退役）+scan_exfail.py/scan_exfail5.py ✓（t4/work_20261002/pool4|5_audit/）+bag75_indep_recount_v533.sh ✓（t4/v533_out/）+t4_v57_night_report.md ✓（t4/work_20261002/reports/）+pool5_audit_increment.md ✓+t4_v517_night_report.md ✓（t4/work_3090_20261005/）+c14_commit_msg.txt ✓（t4/work_20261002/c14_fix/）——**11 现役 Windows 载体本会话逐一 ls 实锤+4 退役未检得（2026-09-28_v2/2026-10-01_prompt/v5.17/v5.24；3090 plans_T4_v5.x 族无对应、archive 翻查无果——内容谱系由月报/台账承继，不判缺失事故）**。
- **族 D typo 型——1**：`/~/catkin_ws/sitl_sim/STATUS.md`（草稿 L247 双前缀 "/~/"）——typo 确认；载体=已转录归档草稿（bd042be6 凭据 md5 冻结不可改），**正本不含此 typo**（转录节=L314-339，L247 不在转录面）——注记销号，不修（红线）。
- **族 E 系统/框架路径——1**：rosbag/bag.py——真载体=/opt/ros/noetic/lib/python3/dist-packages/rosbag/bag.py（3090 本探针实锤 ROSBAG_MODULE_OK）；引用系以相对路径书写的系统模块指称——**收窄为在位（path-style）**。

**汇总**：48=预期缺失 13+已删凭据销号 18+Windows 载体 15（现役 11/退役 4）+typo 冻结注记 1+系统路径收窄在位 1；**零 typo 可修面（唯一 typo 载体冻结）、零凭据型未销号、零新工程**——面③收窄闭环，48 项全部落三态处置（预期缺失/凭据销号/载体注记）。

## 对账捕获（非计划发现）

- **v5.37 册 3090 侧未部署**：单元 1 转录凭据引用 3090 正源时核出 RC=2——当场补部署（Windows plans/2026-10-11_T4_v5.37.md → 3090 ~/sitl_sim/plans_T4_v5.37.md+repo 树镜像，md5 **7e87e2a6** 双端一致）；缺陷=册下发未随双端部署（v5.34 三处一致口径未延续）——已录本周期 T4 新坑（月报同周期追加小节收口）。
- 旧机 df=28G（88%）：高于 20G 红线，5h 窗巡检（单元 6b）留意识别。
