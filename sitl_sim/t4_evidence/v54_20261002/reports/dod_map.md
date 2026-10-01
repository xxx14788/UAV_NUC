# DoD 对照表（任务书 10 单元 → 本批产物指针）

生成：2026-10-02，汇总员 attempt=1。任务书原文不在本工作流素材内，按任务书给汇总员的 10 单元名称逐条映射；"主会话定稿件/不在本工作流范围"=本批无产物、按判读禁区或范围边界如实标注。所有指针为绝对路径。

| # | 单元 | 本批状态 | 指针 |
|---|---|---|---|
| 1 | C-9 补推 | **不在本工作流范围**：铁律禁 push（NUC WAN 瘫，remote=UAV_NUC）。本批仅完成 NUC 侧本地 commit（见 §附注），push 维持阻塞 | commit 登记见 §附注；仓库 NUC:~/catkin_ws |
| 2 | J2 判读文 | **主会话定稿件**（判读禁区，本批不下判据）。数据面已备：十指标相关/跨袋一致性/饱和三例去饱和双列 | `D:/drone_VINS/t4_work_20261002/derived/d4_j2_plane.md`（Set A/B 双面板+§4 饱和双列+`derived/d4_saturation_dual.csv`）；阈值表 v1 全量重算 `derived/d7_stack_era.md` §2.4 |
| 3 | E4 双峰 | **主会话定稿件**（"双峰成立/不成立"判语禁区，本批只给统计量）。数据面已备：ΔBIC/BC±CI/切点扫描/55-64s 覆盖/60s 时序 | `derived/d5_bimodal.md` + `derived/d5_overlap.csv` + `derived/d5_compute.py` |
| 4 | J3 正源四项 | **主会话定稿件/不在本工作流范围**（单元内容未在本工作流任务面展开）。可供数据面指针：features.bag 七袋在位性与消息数、fresh 工具复现比对 | `raw/inventory_artifacts.md` §3；`raw/matrix_5faces.md`；复现比对 `derived/exfail_matrix_real.md` §3-§4 |
| 5 | 池内深挖 5.1-5.3 | **已完成** | 5.1 供给解释：`derived/d1_supply_model.md` + `derived/d1_episodes.csv`；5.2 N 维相关：`derived/d2_ndim_corr.md` + `derived/d2_matrix.csv` + `derived/d2_pairs.csv`；5.3 爆止窗漂移：`derived/d3_truncation.md` + `derived/d3_sensitivity.csv` |
| 6 | P3 预填充 | **主会话定稿件/不在本工作流范围**（禁区）。参考件：`D:/drone_VINS/t4_work_20261002/docs/p3_gap_decision_pack.md`（随素材落盘，本批未改动） | 同左 |
| 7 | 工具自测 | **已完成**：合成 10×3 格（33 行：干净通过 5/带病输出 10/干净拒绝 18/挂死 0）+ 真实子集 2×3 格+补充格 + 坑位表 E1-E8 | `derived/exfail_matrix_synthetic.md`；`derived/exfail_matrix_real.md`；逐格留档 `work_selftest/results.jsonl` 与 `raw/exfail_real_cells/`（results_real.jsonl、slice_stats.json、nuc_env_gate.txt、out/*.json/txt） |
| 8 | 磁盘预签 | **不在本工作流范围**（跨线预签属主会话）。本批仅登记当轮 df 读数：EXF real 当轮 df 32G→31G（exfail_matrix_real.md §卫生门禁）；打包时刻 df 可用 31G | `raw/exfail_real_cells/nuc_env_gate.txt`；`reports/data-pack.md` §12 |
| 9 | 素材池监视 | **本批=时点快照**（2026-10-02 盘点）；持续监视不在本工作流范围 | `raw/inventory_runs.md`、`raw/inventory_artifacts.md`、`raw/matrix_5faces.md`、`raw/data_dictionary.md`、`raw/json_inventory.txt`、`raw/raw_manifest.md5`、`raw/nuc_tree_raw.txt` |
| 10 | W6 持续 | **不在本工作流范围** | — |

## 附注（回传与提交登记，已完成）

- scp 两段式：本地 `reports/`+`derived/` → NUC:/tmp/t4_v54_b4_stage/ → 远端 cp 落位 `~/catkin_ws/sitl_sim/t4_evidence/v54_20261002/`；/tmp/t4_v54_tools/ 临时脚本（extract_odom_pc.py、probe_point32.py、rosbag_info_features.txt、out/ 共 18 件）cp 入同目录 tools/（与源逐件 md5 相同，18/18 实测）。远端 md5sum 对账（find derived reports | xargs md5sum vs `reports/manifest.md5` 对应行）：传输集 34/34 文件逐位一致、mismatch=0（34=derived 31+reports 3）；远端另含 manifest.md5 自身（本地清单除外项）；raw/ 108 件不属传输集（素材原件在 NUC 源路径）。
- git：`cd ~/catkin_ws && git add sitl_sim/t4_evidence/v54_20261002 && git commit -F /tmp/t4_v54_commit_msg.txt`（中文信息经 scp 文件通道）。提交链（amend 前史，8 位前缀；被取代 hash 已退出分支 log 可达历史、reflog 可考）：初版 51d83a4 → 复核修正1 fe54559 → 复核修正2 a490c5d → 本节修正；**最终 hash 以 `git -C ~/catkin_ws log -- sitl_sim/t4_evidence/v54_20261002` 最新一条为准**（52 files changed 口径；derived/__pycache__/*.pyc 被 NUC .gitignore L37 `__pycache__/` 排除未入库）。只 add 自有路径；禁 push。
- 打包时刻运行登记：rosbag 门禁读数 1/1（rosbag 进程在飞，非本工作流所启；本批零 rosbag/回放/提帧操作）；df 31G。
