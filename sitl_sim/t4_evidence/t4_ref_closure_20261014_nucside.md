# T4 池件①-2 引用闭环报告（20261014，v2 脚本）

- 生成时间（3090 本机）：2026-10-14 19:20:21 
- 脚本：`sitl_sim/analysis/t4_ref_closure_v2.py`（本报告由该脚本产出；脚本自报 md5 前 8 位 = `c3d233c5`）
- v2 脚本源流：带病 v1=f17ebfcd（git 9c5f129，NUC 腿 ~/ 引号内不展开致实存判缺）→ T1 代持原位修复 e850bf42（commit 2f67d89）→ 本 v2（残余修正+--probe-tokens）。
- 性质：登记性质清单（只列不修）。缺失引用不代建不代改；他域缺失项供主会话催办。
- 机器快照：df 可用 27G；pgrep -cx → rosbag=0 gzserver=0 px4=0

## 扫描源

| 源 | 说明 | mtime |
|---|---|---|
| `docs/t4_verdicts_v2.md` | 固定源（verdicts 3090 正源 / runbook） | 2026-10-14 19:20:02 |
| `docs/sim2real_runbook.md` | 固定源（verdicts 3090 正源 / runbook） | 2026-10-05 20:45:40 |
| `docs/coding-style.md` | docs/ 近 30 天判读文 | 2026-09-26 16:40:03 |
| `docs/flight_log.md` | docs/ 近 30 天判读文 | 2026-10-01 19:40:05 |
| `docs/p3_gap_decision_pack.md` | docs/ 近 30 天判读文 | 2026-10-03 06:22:40 |
| `docs/px4ctrl_control_budget.md` | docs/ 近 30 天判读文 | 2026-10-01 02:43:36 |
| `docs/realflight_checklist.md` | docs/ 近 30 天判读文 | 2026-09-28 22:56:44 |
| `docs/t1_vins_odom_contract.md` | docs/ 近 30 天判读文 | 2026-09-28 21:22:50 |
| `docs/t2_a2_xtdrone_audit.md` | docs/ 近 30 天判读文 | 2026-10-01 02:31:11 |
| `docs/t2_bias_observability.md` | docs/ 近 30 天判读文 | 2026-09-30 04:49:47 |
| `docs/t2_experiments.md` | docs/ 近 30 天判读文 | 2026-10-02 14:41:35 |
| `docs/t2_marginalization_anatomy.md` | docs/ 近 30 天判读文 | 2026-09-30 03:42:44 |
| `docs/t2_u5_drift_mitigation.md` | docs/ 近 30 天判读文 | 2026-10-01 02:32:06 |
| `docs/t2_wa_fullregression.md` | docs/ 近 30 天判读文 | 2026-10-01 02:54:49 |
| `docs/t2_wa_prophecy.md` | docs/ 近 30 天判读文 | 2026-10-01 02:32:40 |
| `docs/t3_experiments.md` | docs/ 近 30 天判读文 | 2026-09-29 01:10:15 |
| `docs/t3_handoff_040932_decomp.md` | docs/ 近 30 天判读文 | 2026-10-03 09:39:41 |
| `docs/t3_r3_planner_domain_evidence.md` | docs/ 近 30 天判读文 | 2026-10-02 01:13:03 |
| `docs/t3_u35_autodisarm_verdict.md` | docs/ 近 30 天判读文 | 2026-10-04 09:47:20 |
| `docs/t3_xline_u3p_baseline.md` | docs/ 近 30 天判读文 | 2026-10-02 14:17:11 |
| `docs/t3_z12_prewire_pack.md` | docs/ 近 30 天判读文 | 2026-10-02 14:17:11 |
| `docs/t4_e4_bimodal_prereg.md` | docs/ 近 30 天判读文 | 2026-10-02 01:35:54 |
| `docs/t4_e4_scenario_appendix_draft.md` | docs/ 近 30 天判读文 | 2026-10-04 04:58:08 |
| `docs/t4_exfail5_consumption_audit.md` | docs/ 近 30 天判读文 | 2026-10-05 09:07:48 |
| `docs/t4_exfail5_track_20261006.md` | docs/ 近 30 天判读文 | 2026-10-08 02:27:24 |
| `docs/t4_exfail_consumption_audit.md` | docs/ 近 30 天判读文 | 2026-10-03 11:03:49 |
| `docs/t4_j2_scenario_appendix_draft.md` | docs/ 近 30 天判读文 | 2026-10-04 04:27:35 |
| `docs/t4_j2_seg_judgment_prereg_v1.md` | docs/ 近 30 天判读文 | 2026-10-04 06:46:07 |
| `docs/t4_j2_threshold_prep.md` | docs/ 近 30 天判读文 | 2026-10-03 06:14:36 |
| `docs/t4_j3_e1e2_evidence.md` | docs/ 近 30 天判读文 | 2026-09-30 03:01:47 |
| `docs/t4_jr3_pipeline_dryrun.md` | docs/ 近 30 天判读文 | 2026-10-01 03:24:03 |
| `docs/t4_smooth_lie_prereg.md` | docs/ 近 30 天判读文 | 2026-10-03 01:00:27 |
| `docs/t4_t2_handoff_tracking.md` | docs/ 近 30 天判读文 | 2026-10-04 06:50:50 |
| `docs/t4_v519_verdicts_draft_20261006.md` | docs/ 近 30 天判读文 | 2026-10-08 02:27:24 |
| `docs/t4_w1_reception_20261004.md` | docs/ 近 30 天判读文 | 2026-10-04 22:02:17 |
| `docs/t4_w1_reception_3090_20261005.md` | docs/ 近 30 天判读文 | 2026-10-05 09:07:48 |
| `docs/t4_w1_u3pp_reception.md` | docs/ 近 30 天判读文 | 2026-10-03 07:47:54 |
| `docs/vision_acceptance_protocol.md` | docs/ 近 30 天判读文 | 2026-09-28 23:31:49 |
| `docs/vision_materials.md` | docs/ 近 30 天判读文 | 2026-09-29 02:15:26 |
| `docs/workflow.md` | docs/ 近 30 天判读文 | 2026-09-26 17:02:08 |
| `docs/xline_dryrun_v11_report.md` | docs/ 近 30 天判读文 | 2026-10-03 02:27:57 |
| `docs/xline_histreg_verdict_v1.md` | docs/ 近 30 天判读文 | 2026-10-03 01:42:00 |
| `docs/xline_opcard_v1.md` | docs/ 近 30 天判读文 | 2026-10-04 02:44:12 |
| `docs/xline_prereg_v1.md` | docs/ 近 30 天判读文 | 2026-10-02 01:22:40 |
| `docs/xline_prereg_v1_1.md` | docs/ 近 30 天判读文 | 2026-10-08 02:27:24 |
| `docs/xline_x5_grid_design_v1.md` | docs/ 近 30 天判读文 | 2026-10-06 09:43:43 |

## 抽取与核对规则

- bag 引用：token 以 `.bag` 结尾（含带路径形态）；袋名前缀引用 = token 为在册袋 stem 全名或其前缀（len≥8、含 `_` 与数字；stem 集 = 3090 盘上全部 *.bag 去扩展名）。
- 路径引用：`~/`、`/`、`./` 锚定 token，或不带斜杠但带已知扩展名 token；相对路径按 ~/catkin_ws、~/catkin_ws/sitl_sim、~/sitl_sim、docs/、analysis/、t4_evidence/、~ 依次试探；裸文件名按全盘索引 basename 兜底。
- URL（含 `://`）剔除；去重后按 token 记账，出处最多记 5 条。
- 3090 存在性 = 本机实测（os.path.exists，悬空 symlink 单列）；缺失项再做 NUC 只读 ssh 存在性（超时/失败 → skip，如实注记）。
- NUC 侧配对策略（v2）：未锚定 token 缺失但 basename 兜底命中 → present(basename hit)（与 3090 腿同策略）；`~/` 锚定 token 缺失但 basename 命中 → absent(basename hint)（严格路径语义，只出证据不翻案）。
- 边界：docs/ 仅顶层 *.md（figs/ 子目录不在判读文面）；裸目录名引用（无扩展名、非袋前缀）不在抽取面，见注记；占位符 `<...>`、`${VAR:-/x}` 与 prose 枚举粘连形态已过滤，不计数不判缺。

## 汇总

| 项 | 数值 |
|---|---|
| 引用总数（去重 token） | 275 |
| 引用总出现次数 | 425 |
| bag 引用（bag-file） | 73 |
| 袋名前缀引用（bag-prefix） | 21 |
| 路径引用（path） | 181 |
| 在位（3090） | 202 |
| 悬空 symlink | 0 |
| 缺失（3090）合计 | 73 |
| — missing-both | 0 |
| — nuc-only | 0 |
| — nuc-check-skip | 73 |

## 缺失清单（只列不修）

| 引用 | 类别 | kind | 出现次数 | 出处（file:line） | NUC | 备注 |
|---|---|---|---|---|---|---|
| `/drone_VINS/t4_work_20261002/pool4_audit/scan_exfail.py` | nuc-check-skip | path | 1 | docs/t4_exfail_consumption_audit.md:71 | skip: nuc check disabled |  |
| `/drone_VINS/t4_work_20261002/pool5_audit/scan_exfail5.py` | nuc-check-skip | path | 1 | docs/t4_exfail5_consumption_audit.md:70 | skip: nuc check disabled |  |
| `/home/uav/sitl_sim/SITL.lock` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:503 | skip: nuc check disabled | 锁 symlink 为瞬态结构，缺失属预期态 |
| `/tmp/audit_queue_driver.sh` | nuc-check-skip | path | 2 | docs/t4_verdicts_v2.md:504；docs/t4_verdicts_v2.md:551 | skip: nuc check disabled |  |
| `/tmp/e4_scenario_byseg_out.json` | nuc-check-skip | path | 1 | docs/t4_e4_scenario_appendix_draft.md:151 | skip: nuc check disabled |  |
| `/tmp/e4_scenario_byseg_tables.md` | nuc-check-skip | path | 1 | docs/t4_e4_scenario_appendix_draft.md:152 | skip: nuc check disabled |  |
| `/tmp/t4_locktest.lock` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:504 | skip: nuc check disabled |  |
| `/tmp/t4_w1_work/t4_w1_replay.sh` | nuc-check-skip | path | 1 | docs/t4_w1_reception_20261004.md:78 | skip: nuc check disabled |  |
| `/tmp/t4w1_reception/bags_md5.txt` | nuc-check-skip | path | 2 | docs/t4_w1_u3pp_reception.md:65；docs/t4_w1_u3pp_reception.md:117 | skip: nuc check disabled |  |
| `/tmp/t4wf_pool4_scan.py` | nuc-check-skip | path | 1 | docs/t4_exfail_consumption_audit.md:13 | skip: nuc check disabled |  |
| `/tmp/t4wf_pool4_scan_out.txt` | nuc-check-skip | path | 2 | docs/t4_exfail_consumption_audit.md:13；docs/t4_exfail_consumption_audit.md:71 | skip: nuc check disabled |  |
| `/tmp/t4wf_pool5_scan.py` | nuc-check-skip | path | 2 | docs/t4_exfail5_consumption_audit.md:15；docs/t4_exfail5_consumption_audit.md:70 | skip: nuc check disabled |  |
| `/tmp/t4wf_pool5_scan_out.txt` | nuc-check-skip | path | 2 | docs/t4_exfail5_consumption_audit.md:15；docs/t4_exfail5_consumption_audit.md:70 | skip: nuc check disabled |  |
| `/tmp/w9/replay_summary.csv` | nuc-check-skip | path | 1 | docs/t3_experiments.md:169 | skip: nuc check disabled |  |
| `EV/RESULT.txt` | nuc-check-skip | path | 2 | docs/t4_verdicts_v2.md:553；docs/xline_opcard_v1.md:24 | skip: nuc check disabled | basename 'RESULT.txt' exists at /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/RESULT.txt (parent path absent) |
| `EV/simvins.log` | nuc-check-skip | path | 1 | docs/xline_prereg_v1_1.md:126 | skip: nuc check disabled | basename 'simvins.log' exists at /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/simvins.log (parent path absent) |
| `EV/sitl.log` | nuc-check-skip | path | 1 | docs/xline_opcard_v1.md:19 | skip: nuc check disabled | basename 'sitl.log' exists at /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/sitl.log (parent path absent) |
| `EV/wa_online.txt` | nuc-check-skip | path | 1 | docs/xline_opcard_v1.md:25 | skip: nuc check disabled |  |
| `R1G_g_chi2/sim_stereo_imu_config.yaml` | nuc-check-skip | path | 1 | docs/t2_experiments.md:1733 | skip: nuc check disabled | basename 'sim_stereo_imu_config.yaml' exists at /home/uav/sitl_sim/t2_configs/E15_acc050_gyr001/sim_stereo_imu_config.yaml (parent path absent) |
| `R1G_g_depth/sim_stereo_imu_config.yaml` | nuc-check-skip | path | 1 | docs/t2_experiments.md:1732 | skip: nuc check disabled | basename 'sim_stereo_imu_config.yaml' exists at /home/uav/sitl_sim/t2_configs/E15_acc050_gyr001/sim_stereo_imu_config.yaml (parent path absent) |
| `R1G_g_reprop/sim_stereo_imu_config.yaml` | nuc-check-skip | path | 1 | docs/t2_experiments.md:1734 | skip: nuc check disabled | basename 'sim_stereo_imu_config.yaml' exists at /home/uav/sitl_sim/t2_configs/E15_acc050_gyr001/sim_stereo_imu_config.yaml (parent path absent) |
| `R1G_g_smooth/sim_stereo_imu_config.yaml` | nuc-check-skip | path | 2 | docs/t2_experiments.md:1735；docs/t2_experiments.md:1736 | skip: nuc check disabled | basename 'sim_stereo_imu_config.yaml' exists at /home/uav/sitl_sim/t2_configs/E15_acc050_gyr001/sim_stereo_imu_config.yaml (parent path absent) |
| `_j3/manifest.json` | nuc-check-skip | path | 1 | docs/t4_e4_scenario_appendix_draft.md:153 | skip: nuc check disabled | basename 'manifest.json' exists at /home/uav/sitl_sim/vision_inputs/U3PR1_212450_j3/manifest.json (parent path absent) |
| `_shift.bag` | nuc-check-skip | bag-file | 3 | docs/t2_experiments.md:139；docs/t2_experiments.md:166；docs/t4_exfail_consumption_audit.md:31 | skip: nuc check disabled |  |
| `c14_fix/c14_commit_msg.txt` | nuc-check-skip | path | 1 | docs/t4_t2_handoff_tracking.md:68 | skip: nuc check disabled |  |
| `config/fast_drone_250.yaml` | nuc-check-skip | path | 1 | docs/t2_experiments.md:1544 | skip: nuc check disabled | basename 'fast_drone_250.yaml' exists at /home/uav/catkin_ws/src/VINS-Fusion/config/fast_drone_250.yaml (parent path absent) |
| `config/sim_stereo/e2_debug_smooth.yaml` | nuc-check-skip | path | 1 | docs/t4_jr3_pipeline_dryrun.md:29 | skip: nuc check disabled | basename 'e2_debug_smooth.yaml' exists at /home/uav/sitl_sim/t3_configs/WA5C_a6_c4/e2_debug_smooth.yaml (parent path absent) |
| `derived/c15_wc2obs1_bitchk.md` | nuc-check-skip | path | 1 | docs/t4_t2_handoff_tracking.md:76 | skip: nuc check disabled | basename 'c15_wc2obs1_bitchk.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/c15_wc2obs1_bitchk.md (parent path absent) |
| `derived/d1_supply_model.md` | nuc-check-skip | path | 1 | docs/p3_gap_decision_pack.md:18 | skip: nuc check disabled | basename 'd1_supply_model.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d1_supply_model.md (parent path absent) |
| `derived/d2_ndim_corr.md` | nuc-check-skip | path | 1 | docs/p3_gap_decision_pack.md:18 | skip: nuc check disabled | basename 'd2_ndim_corr.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d2_ndim_corr.md (parent path absent) |
| `derived/d3_truncation.md` | nuc-check-skip | path | 1 | docs/p3_gap_decision_pack.md:18 | skip: nuc check disabled | basename 'd3_truncation.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d3_truncation.md (parent path absent) |
| `derived/d4_j2_plane.md` | nuc-check-skip | path | 2 | docs/t4_verdicts_v2.md:300；docs/t4_verdicts_v2.md:324 | skip: nuc check disabled | basename 'd4_j2_plane.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d4_j2_plane.md (parent path absent) |
| `derived/d4_saturation_dual.csv` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:323 | skip: nuc check disabled | basename 'd4_saturation_dual.csv' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d4_saturation_dual.csv (parent path absent) |
| `derived/exfail_matrix_synthetic.md` | nuc-check-skip | path | 1 | docs/t4_exfail_consumption_audit.md:41 | skip: nuc check disabled | basename 'exfail_matrix_synthetic.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/exfail_matrix_synthetic.md (parent path absent) |
| `derived/j2_seg_judgment_v1.csv` | nuc-check-skip | path | 1 | docs/t4_j2_seg_judgment_prereg_v1.md:37 | skip: nuc check disabled | basename 'j2_seg_judgment_v1.csv' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/j2_seg_judgment_v1.csv (parent path absent) |
| `derived/pool_m1m2_byseg.md` | nuc-check-skip | path | 1 | docs/t4_e4_scenario_appendix_draft.md:7 | skip: nuc check disabled | basename 'pool_m1m2_byseg.md' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/pool_m1m2_byseg.md (parent path absent) |
| `e7_ctrl2_125hz.bag` | nuc-check-skip | bag-file | 2 | docs/sim2real_runbook.md:164；docs/sim2real_runbook.md:165 | skip: nuc check disabled |  |
| `flight_2026-09-26_220814/224815/230126.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:15 | skip: nuc check disabled |  |
| `online/replay_frames.csv` | nuc-check-skip | path | 1 | docs/t2_experiments.md:1736 | skip: nuc check disabled | basename 'replay_frames.csv' exists at /home/uav/sitl_sim/t2_results/R1_dissect/replay_frames.csv (parent path absent) |
| `out-root/queue_state.json` | nuc-check-skip | path | 1 | docs/t4_jr3_pipeline_dryrun.md:14 | skip: nuc check disabled | basename 'queue_state.json' exists at /home/uav/sitl_sim/vision_inputs/queue_state.json (parent path absent) |
| `plans/2026-09-27_T3_planner_quality.md` | nuc-check-skip | path | 1 | docs/t3_experiments.md:3 | skip: nuc check disabled |  |
| `plans/2026-09-27_t4_report.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:4 | skip: nuc check disabled |  |
| `plans/2026-09-28_T4_vision_acceptance_v2.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:3 | skip: nuc check disabled |  |
| `plans/2026-10-01_prompt_disk_chain.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:159 | skip: nuc check disabled |  |
| `plans/2026-10-05_T4_vision_acceptance_v5.17.md` | nuc-check-skip | path | 1 | docs/t4_exfail5_consumption_audit.md:139 | skip: nuc check disabled |  |
| `plans/directions/C09_sim2real-vision-sixdim-baseline/DOSSIER.md` | nuc-check-skip | path | 1 | docs/t4_j3_e1e2_evidence.md:3 | skip: nuc check disabled |  |
| `realsense_d435/left.yaml` | nuc-check-skip | path | 1 | docs/t4_j3_e1e2_evidence.md:14 | skip: nuc check disabled | basename 'left.yaml' exists at /home/uav/sitl_sim/t2_configs/E15_acc050_gyr001/left.yaml (parent path absent) |
| `rosbag/bag.py` | nuc-check-skip | path | 1 | docs/t4_exfail_consumption_audit.md:9 | skip: nuc check disabled |  |
| `sim_stereo/e2_debug_smooth.yaml` | nuc-check-skip | path | 1 | docs/t4_w1_reception_3090_20261005.md:74 | skip: nuc check disabled | basename 'e2_debug_smooth.yaml' exists at /home/uav/sitl_sim/t3_configs/WA5C_a6_c4/e2_debug_smooth.yaml (parent path absent) |
| `t2_A_173156.bag` | nuc-check-skip | bag-file | 1 | docs/t2_experiments.md:15 | skip: nuc check disabled |  |
| `t2_A_60hz320.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:35 | skip: nuc check disabled |  |
| `t2_A_60hz640.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:37 | skip: nuc check disabled |  |
| `t2_A_clean.bag` | nuc-check-skip | bag-file | 1 | docs/t2_experiments.md:379 | skip: nuc check disabled |  |
| `t2_C_60hz320.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:36 | skip: nuc check disabled |  |
| `t2_C_60hz640.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:38 | skip: nuc check disabled |  |
| `t2v3_ground_202520.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:39 | skip: nuc check disabled |  |
| `t2v3_hover_203248.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:40 | skip: nuc check disabled |  |
| `t2v3_route_112652.bag` | nuc-check-skip | bag-file | 1 | docs/sim2real_runbook.md:165 | skip: nuc check disabled |  |
| `t2v3_route_112652_125hz.bag` | nuc-check-skip | bag-file | 2 | docs/sim2real_runbook.md:164；docs/sim2real_runbook.md:164 | skip: nuc check disabled |  |
| `t2v3_route_203830.bag` | nuc-check-skip | bag-file | 1 | docs/flight_log.md:41 | skip: nuc check disabled |  |
| `t2v3_route_212450.bag` | nuc-check-skip | bag-file | 1 | docs/t2_experiments.md:1745 | skip: nuc check disabled |  |
| `t2v3_route_215016.bag` | nuc-check-skip | bag-file | 1 | docs/t2_experiments.md:1729 | skip: nuc check disabled |  |
| `t2w5_p2_215545.bag` | nuc-check-skip | bag-file | 3 | docs/t2_experiments.md:76；docs/t2_experiments.md:199；docs/t2_experiments.md:264 | skip: nuc check disabled |  |
| `t4_work_20261002/work_selftest/audit_v58_evidence/last_verdict_audit_v58.txt` | nuc-check-skip | path | 1 | docs/t4_t2_handoff_tracking.md:68 | skip: nuc check disabled | basename 'last_verdict_audit_v58.txt' exists at /home/uav/sitl_sim/t4_selftest/last_verdict_audit_v58.txt (parent path absent) |
| `tools/build_pool_m1m2_byseg.py` | nuc-check-skip | path | 1 | docs/t4_j2_scenario_appendix_draft.md:32 | skip: nuc check disabled | basename 'build_pool_m1m2_byseg.py' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/tools/build_pool_m1m2_byseg.py (parent path absent) |
| `tools/c15_wc2obs1_bitchk.py` | nuc-check-skip | path | 1 | docs/t4_t2_handoff_tracking.md:52 | skip: nuc check disabled | basename 'c15_wc2obs1_bitchk.py' exists at /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/tools/c15_wc2obs1_bitchk.py (parent path absent) |
| `xline_histreg/summary.csv` | nuc-check-skip | path | 1 | docs/xline_histreg_verdict_v1.md:54 | skip: nuc check disabled | basename 'summary.csv' exists at /home/uav/sitl_sim/t3_results/xline_histreg/summary.csv (parent path absent) |
| `~/sitl_sim/SITL.lock` | nuc-check-skip | path | 1 | docs/t4_w1_u3pp_reception.md:21 | skip: nuc check disabled | 锁 symlink 为瞬态结构，缺失属预期态 |
| `~/sitl_sim/bags/t2w5_p1_092335.bag` | nuc-check-skip | bag-file | 1 | docs/t1_vins_odom_contract.md:5 | skip: nuc check disabled |  |
| `~/sitl_sim/plans_T4_v5.22.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:576 | skip: nuc check disabled |  |
| `~/sitl_sim/plans_T4_v5.37.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:597 | skip: nuc check disabled | basename 'plans_T4_v5.37.md' exists at /home/uav/catkin_ws/sitl_sim/plans_T4_v5.37.md (parent path absent) |
| `~/sitl_sim/t4_evidence/t4_v526_20261010/verdicts_draft_v526.md` | nuc-check-skip | path | 1 | docs/t4_verdicts_v2.md:598 | skip: nuc check disabled |  |
| `~/sitl_sim/vins_smoke_runs/run_T2BL5_203404/j0_decomp.json` | nuc-check-skip | path | 1 | docs/t4_w1_reception_3090_20261005.md:128 | skip: nuc check disabled |  |

## 在位引用（202 条）

| 引用 | kind | 次数 | 3090 解析 |
|---|---|---|---|
| `/opt/ros/noetic/setup.bash` | path | 2 | /opt/ros/noetic/setup.bash |
| `021949/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `023658/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `RESULT/wa_online/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `analysis/bag_extract_moments.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/bag_extract_moments.py |
| `analysis/bag_extract_stereo.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/bag_extract_stereo.py |
| `analysis/ekf2_burst_analysis.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/ekf2_burst_analysis.py |
| `analysis/t2_bias_observability.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t2_bias_observability.py |
| `analysis/t2_depth_census.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t2_depth_census.py |
| `analysis/t2_wa_night1_third_party_verdicts.csv` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t2_wa_night1_third_party_verdicts.csv |
| `analysis/t3_e6_drift_budget.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_e6_drift_budget.py |
| `analysis/t3_pr1_legs_preview_output.txt` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_pr1_legs_preview_output.txt |
| `analysis/t3_r3_planner_domain.py` | path | 2 | /home/uav/catkin_ws/sitl_sim/analysis/t3_r3_planner_domain.py |
| `analysis/t3_synth_controlled_test.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_synth_controlled_test.py |
| `analysis/t3_trichotomy.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_trichotomy.py |
| `analysis/t3_wa_gate.py` | path | 5 | /home/uav/catkin_ws/sitl_sim/analysis/t3_wa_gate.py |
| `analysis/t3_z12_stampage_eval.py` | path | 2 | /home/uav/catkin_ws/sitl_sim/analysis/t3_z12_stampage_eval.py |
| `bags/t2v3_hover_134845.bag` | bag-file | 3 | /home/uav/sitl_sim/bags/t2v3_hover_134845.bag |
| `canonical_route_out.bag` | bag-file | 1 | /home/uav/sitl_sim/xtdrone_ref_exp/canonical_route_out.bag |
| `catkin_ws/sitl_sim/analysis/t3_r3_planner_domain.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_r3_planner_domain.py |
| `compact_T2pairR3` | bag-prefix | 1 | compact_T2pairR3_023852 |
| `compact_U3PH_210708.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/compact_U3PH_210708.bag |
| `compact_U3PR1_212450` | bag-prefix | 2 | compact_U3PR1_212450 |
| `compact_U3PR1_212450.bag` | bag-file | 3 | /home/uav/sitl_sim/bags/compact_U3PR1_212450.bag |
| `compact_t2v3_route_024434` | bag-prefix | 1 | compact_t2v3_route_024434 |
| `compact_t2v3_route_024434.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/compact_t2v3_route_024434.bag |
| `d435i_walk_around` | bag-prefix | 2 | d435i_walk_around |
| `d435i_walk_around.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/ext_proxy/d435i_walk_around.bag |
| `d435i_walking.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/ext_proxy/d435i_walking.bag |
| `devel/lib/libvins_lib.so` | path | 1 | /home/uav/catkin_ws/devel/lib/libvins_lib.so |
| `devel/setup.bash` | path | 1 | /home/uav/catkin_ws/devel/setup.bash |
| `docs/analysis/flight.png` | path | 1 | /home/uav/catkin_ws/docs/analysis/flight.png |
| `docs/analysis/flight_2026-09-26_202121.png` | path | 1 | /home/uav/catkin_ws/docs/analysis/flight_2026-09-26_202121.png |
| `docs/analysis/legs.csv` | path | 1 | /home/uav/catkin_ws/docs/analysis/legs.csv |
| `docs/p3_gap_decision_pack.md` | path | 1 | /home/uav/catkin_ws/docs/p3_gap_decision_pack.md |
| `docs/sim2real_runbook.md` | path | 3 | /home/uav/catkin_ws/docs/sim2real_runbook.md |
| `docs/t2_a2_xtdrone_audit.md` | path | 2 | /home/uav/catkin_ws/docs/t2_a2_xtdrone_audit.md |
| `docs/t2_bias_observability.md` | path | 1 | /home/uav/catkin_ws/docs/t2_bias_observability.md |
| `docs/t2_experiments.md` | path | 4 | /home/uav/catkin_ws/docs/t2_experiments.md |
| `docs/t2_u5_drift_mitigation.md` | path | 1 | /home/uav/catkin_ws/docs/t2_u5_drift_mitigation.md |
| `docs/t2_wa_fullregression.md` | path | 3 | /home/uav/catkin_ws/docs/t2_wa_fullregression.md |
| `docs/t2_wa_prophecy.md` | path | 1 | /home/uav/catkin_ws/docs/t2_wa_prophecy.md |
| `docs/t3_r3_planner_domain_evidence.md` | path | 1 | /home/uav/catkin_ws/docs/t3_r3_planner_domain_evidence.md |
| `docs/t3_z12_prewire_pack.md` | path | 1 | /home/uav/catkin_ws/docs/t3_z12_prewire_pack.md |
| `docs/t4_e4_bimodal_prereg.md` | path | 5 | /home/uav/catkin_ws/docs/t4_e4_bimodal_prereg.md |
| `docs/t4_e4_scenario_appendix_draft.md` | path | 1 | /home/uav/catkin_ws/docs/t4_e4_scenario_appendix_draft.md |
| `docs/t4_exfail5_consumption_audit.md` | path | 3 | /home/uav/catkin_ws/docs/t4_exfail5_consumption_audit.md |
| `docs/t4_exfail_consumption_audit.md` | path | 1 | /home/uav/catkin_ws/docs/t4_exfail_consumption_audit.md |
| `docs/t4_j2_scenario_appendix_draft.md` | path | 1 | /home/uav/catkin_ws/docs/t4_j2_scenario_appendix_draft.md |
| `docs/t4_j2_seg_judgment_prereg_v1.md` | path | 1 | /home/uav/catkin_ws/docs/t4_j2_seg_judgment_prereg_v1.md |
| `docs/t4_j2_threshold_prep.md` | path | 4 | /home/uav/catkin_ws/docs/t4_j2_threshold_prep.md |
| `docs/t4_j3_e1e2_evidence.md` | path | 3 | /home/uav/catkin_ws/docs/t4_j3_e1e2_evidence.md |
| `docs/t4_jr3_pipeline_dryrun.md` | path | 1 | /home/uav/catkin_ws/docs/t4_jr3_pipeline_dryrun.md |
| `docs/t4_smooth_lie_prereg.md` | path | 1 | /home/uav/catkin_ws/docs/t4_smooth_lie_prereg.md |
| `docs/t4_t2_handoff_tracking.md` | path | 5 | /home/uav/catkin_ws/docs/t4_t2_handoff_tracking.md |
| `docs/t4_verdicts_v2.md` | path | 17 | /home/uav/catkin_ws/docs/t4_verdicts_v2.md |
| `docs/t4_w1_reception_20261004.md` | path | 4 | /home/uav/catkin_ws/docs/t4_w1_reception_20261004.md |
| `docs/t4_w1_u3pp_reception.md` | path | 2 | /home/uav/catkin_ws/docs/t4_w1_u3pp_reception.md |
| `docs/vision_materials.md` | path | 1 | /home/uav/catkin_ws/docs/vision_materials.md |
| `docs/xline_opcard_v1.md` | path | 1 | /home/uav/catkin_ws/docs/xline_opcard_v1.md |
| `docs/xline_prereg_v1.md` | path | 1 | /home/uav/catkin_ws/docs/xline_prereg_v1.md |
| `docs/xline_prereg_v1_1.md` | path | 2 | /home/uav/catkin_ws/docs/xline_prereg_v1_1.md |
| `docs/xline_x5_grid_design_v1.md` | path | 1 | /home/uav/catkin_ws/docs/xline_x5_grid_design_v1.md |
| `features.bag` | bag-file | 20 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_030927/features.bag |
| `flight.bag` | bag-file | 7 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `flight_2026-09-23_212510.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-23_212510.bag |
| `flight_2026-09-23_214433.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-23_214433.bag |
| `flight_2026-09-23_221002.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-23_221002.bag |
| `flight_2026-09-26_` | bag-prefix | 1 | flight_2026-09-26_175942 |
| `flight_2026-09-26_175942.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-26_175942.bag |
| `flight_2026-09-26_195352.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-26_195352.bag |
| `flight_2026-09-26_202121.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-26_202121.bag |
| `flight_2026-09-26_224815.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/flight_2026-09-26_224815.bag |
| `jr3_replay_T2MACH3_011804/features.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_030927/features.bag |
| `jr3_replay_T2MACH8_015411/features.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_030927/features.bag |
| `jr3_replay_T2V3HOVER_134845/features.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_030927/features.bag |
| `run_T2MACH3_011804/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_T2MACH8_015411/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_U3PH_210708/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_U3PO_211438/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_WC2OBS1_032005/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_WD1b_032925/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `run_WD1b_033751/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `sitl_sim/analysis/analyze_takeoff_divergence.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/analyze_takeoff_divergence.py |
| `sitl_sim/analysis/controller_replay.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/controller_replay.py |
| `sitl_sim/analysis/j3_extract_queue.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/j3_extract_queue.py |
| `sitl_sim/analysis/j3_image_metrics.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/j3_image_metrics.py |
| `sitl_sim/analysis/stoppage_analysis.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/stoppage_analysis.py |
| `sitl_sim/analysis/t2_domain_guard.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t2_domain_guard.py |
| `sitl_sim/analysis/t3_legs_rescan.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_legs_rescan.py |
| `sitl_sim/analysis/t3_wa_gate.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_wa_gate.py |
| `sitl_sim/analysis/t3_xline_report_figs.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_xline_report_figs.py |
| `sitl_sim/analysis/t4_ref_closure.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t4_ref_closure.py |
| `sitl_sim/analysis/ulog_ekf2_reanchor.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/ulog_ekf2_reanchor.py |
| `sitl_sim/analysis/vins_divergence_forensics.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/vins_divergence_forensics.py |
| `sitl_sim/analysis/wa_scene_contrast.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/wa_scene_contrast.py |
| `sitl_sim/env_health_check.sh` | path | 1 | /home/uav/catkin_ws/sitl_sim/env_health_check.sh |
| `sitl_sim/round_result.sh` | path | 1 | /home/uav/catkin_ws/sitl_sim/round_result.sh |
| `sitl_sim/t1_evidence/v1_flight_results.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v1_flight_results.md |
| `sitl_sim/t1_evidence/v7_2026-09-30/F2_closure.md` | path | 3 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v7_2026-09-30/F2_closure.md |
| `sitl_sim/t2_results/R2_dissect/prereg_signatures_R2.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t2_results/R2_dissect/prereg_signatures_R2.md |
| `sitl_sim/t2_results/R2_dissect/source_map_r2.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t2_results/R2_dissect/source_map_r2.md |
| `sitl_sim/t4_evidence/t4_ref_closure_20261005.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/t4_ref_closure_20261005.md |
| `sitl_sim/t4_evidence/v54_20261002/derived/exfail_matrix_synthetic.md` | path | 3 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/exfail_matrix_synthetic.md |
| `sitl_sim/t4_evidence/v55_20261003/derived/pool_m1m2_byseg.csv` | path | 2 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/pool_m1m2_byseg.csv |
| `sitl_sim/t4_evidence/v55_20261003/tools/build_e4_scenario_byseg.py` | path | 2 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/tools/build_e4_scenario_byseg.py |
| `smoke_runs/run_2026-09-28_021048/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `src/VINS-Fusion/config/realsense_d435/rs_camera_vins.launch` | path | 1 | /home/uav/catkin_ws/src/VINS-Fusion/config/realsense_d435/rs_camera_vins.launch |
| `src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml` | path | 1 | /home/uav/catkin_ws/src/VINS-Fusion/config/sim_stereo/sim_stereo_imu_config.yaml |
| `src/launch/sim_vins.launch` | path | 1 | /home/uav/catkin_ws/src/launch/sim_vins.launch |
| `stairs` | bag-prefix | 3 | stairs |
| `stairs.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/ext_proxy/stairs.bag |
| `t1_evidence/v11_7_2026-10-05/prereg_v14_dual_anchor_draft.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/prereg_v14_dual_anchor_draft.md |
| `t1_evidence/v4_imu_freq_assessment.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v4_imu_freq_assessment.md |
| `t1_evidence/v7_2026-09-30/F2_closure.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v7_2026-09-30/F2_closure.md |
| `t1_evidence/w4_cert_runbook.md` | path | 1 | /home/uav/sitl_sim/t1_evidence/w4_cert_runbook.md |
| `t2_results/R1_dissect/prereg_signatures.md` | path | 1 | /home/uav/sitl_sim/t2_results/R1_dissect/prereg_signatures.md |
| `t2_results/R2_dissect/judge_dis0_baseline_r2tool.json` | path | 1 | /home/uav/sitl_sim/t2_results/R2_dissect/judge_dis0_baseline_r2tool.json |
| `t2_results/R2_dissect/prereg_r2_addendum.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t2_results/R2_dissect/prereg_r2_addendum.md |
| `t2_results/R2_dissect/r2_judge.py` | path | 1 | /home/uav/sitl_sim/t2_results/R2_dissect/r2_judge.py |
| `t2_results/R2_dissect/source_map_r2.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t2_results/R2_dissect/source_map_r2.md |
| `t2v3_ground_030355` | bag-prefix | 1 | t2v3_ground_030355 |
| `t2v3_ground_030355.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_ground_030355.bag |
| `t2v3_ground_205302` | bag-prefix | 2 | t2v3_ground_205302 |
| `t2v3_ground_205302.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_ground_205302.bag |
| `t2v3_ground_210307` | bag-prefix | 1 | t2v3_ground_210307 |
| `t2v3_ground_210307.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_ground_210307.bag |
| `t2v3_hover_031337` | bag-prefix | 2 | t2v3_hover_031337 |
| `t2v3_hover_031337.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_hover_031337.bag |
| `t2v3_hover_033544` | bag-prefix | 1 | t2v3_hover_033544 |
| `t2v3_hover_033544.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_hover_033544.bag |
| `t2v3_hover_033842` | bag-prefix | 2 | t2v3_hover_033842 |
| `t2v3_hover_033842.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_hover_033842.bag |
| `t2v3_hover_134845` | bag-prefix | 1 | t2v3_hover_134845 |
| `t2v3_hover_134845.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_hover_134845.bag |
| `t2v3_route_024006` | bag-prefix | 2 | t2v3_route_024006 |
| `t2v3_route_024006.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_route_024006.bag |
| `t2v3_route_025706` | bag-prefix | 1 | t2v3_route_025706 |
| `t2v3_route_025706.bag` | bag-file | 2 | /home/uav/sitl_sim/bags/t2v3_route_025706.bag |
| `t2v3_route_025808` | bag-prefix | 2 | t2v3_route_025808 |
| `t2v3_route_025808.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_route_025808.bag |
| `t2v3_route_034144` | bag-prefix | 3 | t2v3_route_034144 |
| `t2v3_route_034144.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_route_034144.bag |
| `t2v3_route_035325` | bag-prefix | 3 | t2v3_route_035325 |
| `t2v3_route_035325.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_route_035325.bag |
| `t2v3_route_213717` | bag-prefix | 4 | t2v3_route_213717 |
| `t2v3_route_213717.bag` | bag-file | 1 | /home/uav/sitl_sim/bags/t2v3_route_213717.bag |
| `t2v3_w2b` | bag-prefix | 1 | t2v3_w2b_121141 |
| `t3_results/y4_full_verdicts.csv` | path | 1 | /home/uav/sitl_sim/t3_results/y4_full_verdicts.csv |
| `t4_evidence/disk_manifest_20260929.md` | path | 1 | /home/uav/sitl_sim/t4_evidence/disk_manifest_20260929.md |
| `t4_evidence/e1_lock_tests_0250.log` | path | 1 | /home/uav/sitl_sim/t4_evidence/e1_lock_tests_0250.log |
| `t4_evidence/t4_migration_3090_20261005.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/t4_migration_3090_20261005.md |
| `t4_evidence/v54_20261002/derived/d5_compute.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/derived/d5_compute.py |
| `t4_evidence/v54_20261002/tools/out/jr3_replay_U3PR2_213717_odom.csv` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/tools/out/jr3_replay_U3PR2_213717_odom.csv |
| `t4_evidence/v55_20261003/derived/c15_wc2obs1_bitchk.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/c15_wc2obs1_bitchk.md |
| `t4_recept_20261006/judging_draft.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/t4_recept_20261006/judging_draft.md |
| `t4_w1_x4_20261006/x4_recept_register.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/t4_w1_x4_20261006/x4_recept_register.md |
| `v1_ground_salvage_211520.bag` | bag-file | 1 | /home/uav/catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28/v1_ground_salvage_211520.bag |
| `vins_out` | bag-prefix | 1 | vins_out |
| `vins_out.bag` | bag-file | 16 | /home/uav/sitl_sim/t2_results/R2F_G5_po_flight/vins_out.bag |
| `vision_inputs/WC2OBS1_030927_j3/manifest.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/WC2OBS1_030927_j3/manifest.json |
| `vision_inputs/WC2OBS1_032005_j3/manifest.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/WC2OBS1_032005_j3/manifest.json |
| `vision_inputs/j2_threshold_table_v1.json` | path | 2 | /home/uav/sitl_sim/vision_inputs/j2_threshold_table_v1.json |
| `vision_inputs/jr3_replay_WC2OBS1_030927/features.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_030927/features.bag |
| `vision_inputs/jr3_replay_WC2OBS1_032005/features.bag` | bag-file | 1 | /home/uav/sitl_sim/vision_inputs/jr3_replay_WC2OBS1_032005/features.bag |
| `vision_inputs/metrics_WC2OBS1_030927.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/metrics_WC2OBS1_030927.json |
| `vision_inputs/metrics_WC2OBS1_030927_density.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/metrics_WC2OBS1_030927_density.json |
| `vision_inputs/metrics_WC2OBS1_030927_w3.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/metrics_WC2OBS1_030927_w3.json |
| `vision_inputs/metrics_WC2OBS1_032005_density.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/metrics_WC2OBS1_032005_density.json |
| `worlds_fix/sitl_north.world` | path | 1 | /home/uav/sitl_sim/worlds_fix/sitl_north.world |
| `~/catkin_ws/docs/t2_experiments.md` | path | 1 | /home/uav/catkin_ws/docs/t2_experiments.md |
| `~/catkin_ws/docs/t2_wa_fullregression.md` | path | 1 | /home/uav/catkin_ws/docs/t2_wa_fullregression.md |
| `~/catkin_ws/docs/t2_wa_prophecy.md` | path | 1 | /home/uav/catkin_ws/docs/t2_wa_prophecy.md |
| `~/catkin_ws/docs/t4_smooth_lie_prereg.md` | path | 1 | /home/uav/catkin_ws/docs/t4_smooth_lie_prereg.md |
| `~/catkin_ws/docs/t4_t2_handoff_tracking.md` | path | 1 | /home/uav/catkin_ws/docs/t4_t2_handoff_tracking.md |
| `~/catkin_ws/docs/t4_verdicts_v2.md` | path | 1 | /home/uav/catkin_ws/docs/t4_verdicts_v2.md |
| `~/catkin_ws/docs/t4_w1_u3pp_reception.md` | path | 1 | /home/uav/catkin_ws/docs/t4_w1_u3pp_reception.md |
| `~/catkin_ws/sitl_sim/analysis/t3_anchor_survey_v1.csv` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_anchor_survey_v1.csv |
| `~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/analysis/t3_wa_gate.py |
| `~/catkin_ws/sitl_sim/round_result.sh` | path | 1 | /home/uav/catkin_ws/sitl_sim/round_result.sh |
| `~/catkin_ws/sitl_sim/t4_evidence/anchor_assets_manifest_20261005.md` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/anchor_assets_manifest_20261005.md |
| `~/catkin_ws/sitl_sim/t4_evidence/v55_20261003/tools/build_e4_scenario_byseg.py` | path | 1 | /home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/tools/build_e4_scenario_byseg.py |
| `~/sitl_sim/DECISION_LOG.md` | path | 1 | /home/uav/sitl_sim/DECISION_LOG.md |
| `~/sitl_sim/STATUS.md` | path | 15 | /home/uav/sitl_sim/STATUS.md |
| `~/sitl_sim/plans_T1_v11.2.md` | path | 1 | /home/uav/sitl_sim/plans_T1_v11.2.md |
| `~/sitl_sim/sitl_lock.sh` | path | 1 | /home/uav/sitl_sim/sitl_lock.sh |
| `~/sitl_sim/smoke_runs/run_2026-09-27_165340/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_171440/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_181440/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_182104/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_193052/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_193748/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/smoke_runs/run_2026-09-27_194855/flight.bag` | bag-file | 1 | /home/uav/sitl_sim/vins_smoke_runs/run_T2BL6_203956/flight.bag |
| `~/sitl_sim/t2_configs/E01_baseline/sim_stereo_imu_config.yaml` | path | 1 | /home/uav/sitl_sim/t2_configs/E01_baseline/sim_stereo_imu_config.yaml |
| `~/sitl_sim/t2_experiments.md` | path | 3 | /home/uav/sitl_sim/t2_experiments.md |
| `~/sitl_sim/t2_results/wb4_real_projection.json` | path | 1 | /home/uav/sitl_sim/t2_results/wb4_real_projection.json |
| `~/sitl_sim/t2_u2_forensics.json` | path | 1 | /home/uav/sitl_sim/t2_u2_forensics.json |
| `~/sitl_sim/t2_u2_freeze.txt` | path | 2 | /home/uav/sitl_sim/t2_u2_freeze.txt |
| `~/sitl_sim/t2_u2_queue.sh` | path | 1 | /home/uav/sitl_sim/t2_u2_queue.sh |
| `~/sitl_sim/t2_u2_replay_queue.log` | path | 1 | /home/uav/sitl_sim/t2_u2_replay_queue.log |
| `~/sitl_sim/vins_smoke.sh` | path | 1 | /home/uav/sitl_sim/vins_smoke.sh |
| `~/sitl_sim/vision_inputs/j2_threshold_table_v1.json` | path | 1 | /home/uav/sitl_sim/vision_inputs/j2_threshold_table_v1.json |

## 注记

- NUC 查证口径：未执行（--no-nuc）
- `/home/uav/...` 形态引用为旧 NUC 时代绝对路径（NUC 用户 uav；3090 用户 ghj），3090 侧按路径原文判缺，由 NUC 查证给出归宿。
- `run_*` staging 目录为重放期临时 ln -s 结构，其引用判缺属预期态（原始袋在位即闭环），已在备注列标注 basename 归宿。
- 本报告不产 PASS/FAIL 判读，不含任何判据阈值；缺失清单不触发任何修复动作。
