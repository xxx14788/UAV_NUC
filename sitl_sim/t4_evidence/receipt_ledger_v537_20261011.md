# T4 v5.37 收货台账（承 receipt_ledger §10 系滚动；2026-10-11 夜；工程合并册 v1.6 收官产物收货=W-T4 回执闭环）

> 口径承 bag_receipt_ledger_v526/receipt_ledger_v531 §0-§10：索引级+md5 锚，零 T4 预注册判据面收货判读（收货≠判读，verdicts 判决权在预注册判据线）。

## §10.10 C-1 系收货（5 ulg+判决书+指纹件）

| 件 | md5（前 8） | 路径（3090 实测） |
|---|---|---|
| 分离轮 round.ulg（=04_44_27.ulg 86.2MB） | f0d32dc5 | t1_evidence/v113_2026-10-11/c1_separation/run_C1se_184008/round.ulg |
| 回归轮 round.ulg | efd5b3fd | 同树 run_C1re_183315/round.ulg |
| 正控 disarm round.ulg | 47c82a70 | 同树 run_C1v3_disarm_185451/round.ulg |
| 正控 term round.ulg | 7568dfcc | 同树 run_C1v3_term_185824/round.ulg |
| **实机原始轮 08_24_40.ulg** | 81a213e9 | **PX4-Autopilot/build/px4_sitl_default/rootfs/log/2026-10-10/08_24_40.ulg** |
| 判决书 c1_separation_final_verdict.md | **f7c87ae5 ✓对账合** | 同树 c1_separation/c1_separation_final_verdict.md |
| 构建指纹件×2（C1se/C1re） | 见注 | 各轮 build_fingerprint.txt：px4_bin_md5=**0bac7286**cf38075f8880880b1eb9c9d2 ✓（=任务书继任基线指纹全串实锚）+patch_md5+commander_patched_md5+note"forensic-build-F1 zero functional change" |

- 注 1：任务书"ulg×5"实测口径=4 SITL 轮+实机原始轮（判决书 §6 证据索引 L81 口径）——5/5 全实物在位逐件 md5 锚；第 5 件初次搜索未检得（t1 树/PX4 build -newermt 10-11 滤窗误排除），扩搜 PX4 rootfs log 2026-10-10 目录定位——**搜索滤窗坑在录**。
- 注 2：附加佐证=v112 c1_verify 两轮 round.ulg（run_C1_122832=9853060d / run_C1_124411=867d7482）——v1 判决（620aa07f，观测有效/定性被取代）证据系一并锚定。
- 注 3：指纹件仅 C1se/C1re 两轮在位（取证构建 F1 轮）；disarm/term 正控轮=修复版构建（89dc2a1 后），无指纹文件——轮日志/判决书承载构建身份，如实注记非缺失事故。

## §10.11 L2 系收货

| 件 | md5（前 8） | 路径 |
|---|---|---|
| memleak_l2_verdict.md | **469e75f2 ✓对账合** | t1_evidence/v113_2026-10-11/memleak_l2/memleak_l2_verdict.md |
| 探针源 t1_mtrace.c | 94fe8c9c | ~/sitl_sim/t1_mtrace.c |
| 探针库 t1_mtrace.so | ccd0baa7 | ~/sitl_sim/t1_mtrace.so |

## §10.12 δ 系收货（批报表+注记面+主袋×8）

- 判决书 delta_a_verdict.md **实物=b51f6172**（3090 双树一致，git 988014d 唯一代，mtime 20:38；轮 8 批报表数值 8.508 已填终版）vs 任务书/收官册 D 表锚 **536fea47**=Windows 镜像时点值（数值填充前占位"(批报表)"态，diff 单格实锚）——**锚换代勘误：正源=b51f6172，Windows 镜像（t1/2026-10-11_工程合并v1.6/）已当场同步至 b51f6172**；@T1ENG 勘误通告（落 STATUS）。
- 批报表：delta_a_batch_report.csv + delta_a_batch_report_r1-4.csv（同目录）+delta_img_state.txt=**图像袋注记面 8×DISCARDED 实物**（ROUND_START/DISCARDED 逐轮行："非绿轮,图像袋删;主 flight.bag 保留"——规格注记实证）。
- 主袋×8（任务书"compact 袋×8"实测=run_DAn8p_1..8 主袋 flight.bag；compact 规格=图像袋已删 8×DISCARDED，非 bags/ 下 compact_* 命名族——命名勘误注记）：run_DAn8p_1_190321=9cdd37e1 / _2_191109=b3538e6d / _3_191851=291b3824 / _4_192636=8026b488 / _5_193135=738e182b / _6_193932=e60e44f5 / _7_194715=8f1082b7 / _8_195511=0d199426（均 vins_smoke_runs/ 下 flight.bag）。

## §10.13 月报收货读数

- 月报 **131 条版**（e6819cc4，本册单元 2 续跑并入后新基线；任务书所记 128 条版 c96e573b=并入前时点值）双树一致 ✓——收官册 E 项"月报 128"按 131 读数收货（增量=本册单元 2 3 新条+A5 复发，算术链 120→128→131 在册）。

## §10.14 收讫声明

- 工程合并册 v1.6 收官册 E 等待项 **"W-T4 收货回执"（C-1 ulg×5+δ 袋×8+L2 判决+月报）就此闭环**——本台账 §10.10-§10.13 即回执；全部收货=索引级 md5 锚，零预注册判据面，零三态判定。
- 勘误两件随收货产出：①δ 判决锚换代（536fea47→b51f6172，镜像时点差）②"compact 袋"命名口径（=主袋 8+图像袋 DISCARDED 规格）。均零内容疑点、零判决值触碰。
