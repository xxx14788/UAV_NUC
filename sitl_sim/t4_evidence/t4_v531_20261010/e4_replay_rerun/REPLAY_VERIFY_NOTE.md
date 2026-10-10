# E4 cv2 像素级重放重跑验证（T4 v5.31 单元 3 件②，2026-10-10 夜）

- **执行**：六袋帧目录（~/sitl_sim/vision_inputs/{U3PG_210307,U3PH_210708,U3PO_211438,U3PR1_212450,U3PR2_213717,X1final_173345}_j3）× j3_fb_residual.py（3090 analysis/ 在役版）串行重放，每袋 rc=0（耗时 0.47-0.51s/袋）；侧锁=/tmp/t4_side_e4replay.lock（flock 侧文件序列化，主 SITL 锁零触碰——锁测试侧锁铁律遵守）。
- **对账**：重跑产物 fbres_<bag>.json vs 在册 v55 正源 e4_framelevel_fbres_<bag>.json（NUC 原产）逐叶结构对账：

| 袋 | 叶数 | 数值差 | 键差 | 结论 |
|---|---|---|---|---|
| U3PG_210307 | 671 | 1 | 0 | 差=仅 /frames_dir |
| U3PH_210708 | 662 | 1 | 0 | 同上 |
| U3PO_211438 | 680 | 1 | 0 | 同上 |
| U3PR1_212450 | 662 | 1 | 0 | 同上 |
| U3PR2_213717 | 671 | 1 | 0 | 同上 |
| X1final_173345 | 644 | 1 | 0 | 同上 |

- **判读**：合计 3990 叶，3984 叶逐位一致，6 叶差异全为 `/frames_dir` 路径凭据字段（本机 3090 `/home/ghj/...` vs 在册 NUC `/home/uav/...`——机器来源字段，按 C-14 抽样对照先例属排除项：error/schema/path 类元数据不计入数值口径）；键集零代差（schema_version/manifest_schema_version/legacy_keys 双侧一致）。**cv2 像素级逐帧重放环节 bitIdentical 成立（路径凭据叶除外）**。
- **台账联动**：e4_framelevel_recheck_v526.md（5aed12a1）§8.1 登记之"cv2 像素级逐帧重放本次未重跑"局限，就此以本验证**正式闭合**；md5 全件不同属预期（frames_dir 叶差异），数值面零漂移——在册 fbres 六件 JSON 采信面维持，无需改判。
- 产物：rerun JSON 六件+逐袋运行日志+本注记，落 `~/sitl_sim/t4_evidence/t4_v531_20261010/e4_replay_rerun/`；在册正源（v55 derived/）零写入零触碰。
- IO 纪律：STATUS 预告 00:08 在案；纯 CPU 小 IO（每袋 ~0.5s）；主锁未触碰。
