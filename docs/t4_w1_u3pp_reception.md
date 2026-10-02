# T4-W1 U3PP 素材收货回执（2026-10-03）

> 执行：T4 线 W1 素材收货执行员（动态工作流子代理）；目标机 NUC uav4（`ssh nuc`）。
> 性质：素材收货回执（素材面事实登记+图像侧可行性裁定），非判读件；判读红线遵守：
> 全文无 PASS/FAIL 判读语、无单帧结论、无预拍阈值；本文无判读行草稿产出（原因见 §6）。

## 0. 结论速览

六袋（任务书五袋+素材面多报 1 袋）`rosbag info` 全量话题表实测：图像类话题全部为 0，
compact 图像侧**不可行**，链在提帧之前即停。按 U3PR1 先例口径（compact 零图像袋注记挂账）
六袋全部挂账，不硬凑提帧/metrics/重放。重放三门（锁空/进程空窗/df≥25G）实测全过，
但图像侧前提不成立，重放未执行（replayRan=false）。无 metrics 袋 → 无判读行草稿可产出。

## 1. 前置门实测（本会话逐项执行）

| 门 | 命令 | 实测 | 裁定 |
|---|---|---|---|
| df≥25G（<20G 全线停） | `df -h /` | `/dev/nvme0n1p2 234G 171G 51G 78% /` | 过（51G） |
| rosbag 空窗 | `pgrep -a rosbag` | 无输出（rc=1，0 进程） | 过 |
| gzserver 空窗 | `pgrep -a gzserver` | 无输出（rc=1，0 进程） | 过 |
| 锁空 | `ls ~/sitl_sim/SITL.lock` | `No such file or directory` | 锁空 |

md5 批量 IO 前空窗复验：`pgrep -c rosbag`=0、`pgrep -c gzserver`=0（2026-10-03 本会话）。

## 2. 工具版本对账（C14-FIX 后新版，双端 md5 一致）

任务书在册旧版 md5（image=abcc5fc8…/fb=c23d4287…/density=9e45f981…）为 C14-FIX 前版本；
本会话按"修复后按新版走"，实测双端一致（本机 `t4_work_20261002/c14_fix/` 副本 vs
NUC `~/catkin_ws/sitl_sim/analysis/`）：

| 工具 | md5（双端一致） |
|---|---|
| j3_extract_frames.py | `18a71153f9020b86d6237a93369906a6` |
| j3_feature_density.py | `7f45974b3a2a81e60c6293865ac3eb5e` |
| j3_image_metrics.py | `3721399e7a78e42f6e1cd81a2680286e` |
| j3_fb_residual.py | `08cb8829d180dad91445f1d436d547a2` |

对齐 STATUS 在册：C14-FIX-3 后 density=`7f45974b…`、C14-FIX-4 后 image=`3721399e…`/fb=`08cb8829…`（04:52/04:58 两行）。
本批素材零图像，新版工具实际未被调用（见 §3/§5）。

## 3. 六袋裁定表（rosbag info 实测，2026-10-03）

执行命令（逐袋，NUC）：
`timeout 90 bash -lc "source /opt/ros/noetic/setup.bash; rosbag info <袋>.bag"`，
六袋 rc 全部=0，原始输出留档 NUC `/tmp/t4w1_reception/<袋>.info`。
图像面判定命令：对 info 全量输出 `grep -icE 'image|camera|infra'`（防截断，全表 grep）。

| 袋名（~/sitl_sim/bags/） | 时长 | 大小 | 话题数 | img grep | 图像侧可行 | 链走到哪一步 |
|---|---|---|---|---|---|---|
| t2v3_ground_030355 | 44.7s | 20.1MB | 8 | 0 | 不可行 | 提帧前即停 |
| t2v3_hover_033544 | 137s | 47.2MB | 9 | 0 | 不可行 | 提帧前即停 |
| t2v3_hover_033842 | 137s | 45.2MB | 9 | 0 | 不可行 | 提帧前即停 |
| t2v3_route_034144 | 654s | 226.6MB | 11 | 0 | 不可行 | 提帧前即停 |
| t2v3_route_035325 | 649s | 192.0MB | 10 | 0 | 不可行 | 提帧前即停 |
| t2v3_hover_031337（素材面多报第 6 只） | 25.0s | 11.2MB | 8 | 0 | 不可行 | 提帧前即停 |

话题面事实（与侦察员报告逐项吻合）：
- 六袋话题面全部为 gazebo/mavros/vins 状态-里程计-控制面，无任何传感器图像流。
- t2v3_route_034144 含 `/position_cmd` 58659 msgs+`/px4ctrl/takeoff_land` 58 msgs（正常起飞 route）。
- t2v3_route_035325 无 `/position_cmd`（与侦察员"疑 A1 未起飞臂"观察一致，本件仅转记事实）。
- 两 hover 袋（033544/033842）各含 `/px4ctrl/takeoff_land` 58 msgs。

## 4. 素材 manifest（md5+字节数，本会话实测登记）

`md5sum`（NUC，bags/ 原位）+`stat -c '%n %s'`，留档 `/tmp/t4w1_reception/bags_md5.txt`：

| 袋 | 字节数 | md5 |
|---|---|---|
| t2v3_ground_030355.bag | 21084958 | `eab5d1f54833cfdc45db135a87755471` |
| t2v3_hover_033544.bag | 49463547 | `a24c7d0c5629d9289d97a5ef42fa7a2a` |
| t2v3_hover_033842.bag | 47374230 | `c58445f8ec82bad925fde0c11534b9d9` |
| t2v3_route_034144.bag | 237652534 | `35c8b6789ec5ffa8298632ad50c5b44b` |
| t2v3_route_035325.bag | 201362561 | `8a77e1ba158ca3f6d444c163455abeb6` |
| t2v3_hover_031337.bag | 11730569 | `43bd00ed2c2e115c5a8dbd5a8ba1e2b1` |

manifest 前置（既往提帧核查）：`ls ~/sitl_sim/vision_inputs/` 中 t2v3 相关条目
`grep -c t2v3` = **0**——无 `t2v3*_j3` 提帧目录、无 t2v3 metrics_*.json（在册 18 份 metrics
全部属 U3P*/WC2/X1 各袋），无既往提帧可复用。

## 5. 链走向与重放级判定

- **提帧**：j3_extract_frames 输入前提=袋内有图像流；六袋零图像话题，无帧可提，
  提帧不执行（staging 符号链接步骤因无下游而无意义，未建）。禁区"不硬凑"适用。
- **offset/metrics/fb**：均为帧目录下游，前置不成立，未执行；无 metrics 产出
  （/tmp 工作区无落盘物，vision_inputs 正本未触碰）。
- **重放级（每袋独立判定）**：三门实测——锁空 ✓（§1）、rosbag/gzserver 双 0 ✓（§1）、
  df=51G≥25G ✓（§1）。三门全过，但重放对象前提（vins_node 需图像流输入）六袋全部不成立
  → 不做重放； devel vins_node/lib 双 md5 登记（重放前置步骤）随重放一并未执行。
  按 U3PR1 先例口径挂账：在册先例=compact_U3PR1_212450.bag（NUC `/home/uav/sitl_sim/bags/`
  在位，323613677 字节）零图像话题、verdicts v2 L206"帧样-only（不可重放，图像侧已出）"同族口径。

## 6. 判读行草稿：无

依预注册判据链（commit 682dc3a：docs/t4_j2_threshold_prep.md"J2（像素侧特征密度/分布判读）"
+"≥5 轮**带图**素材到货前把判读备齐"+阈值=新袋产额分位，禁预拍；verdicts v2 L251-258 判据链
与单域三态口径；供给嫌疑门 P10<0.2 见 verdicts v2 L209）机械映射的输入=metrics（分位+CI+n）。
本批六袋均无 metrics（§5），**判读行草稿产出=0 行**，故亦无"草稿·待主会话定稿"行待定稿。
素材到货条件（带图）未满足，J2 正式判读 24h SLA 未被触发。

## 7. 挂账清单与诚实注记

挂账（U3PR1 先例口径，compact 零图像袋）：六袋全部挂账"图像侧不可行，待带图重录或改状态面消费"。
诚实注记：
1. 任务书称"五袋"，素材面列 6 袋且第 6 袋（t2v3_hover_031337，25s）自标注"多余第6只，疑试飞"；
   裁定表按 6 袋全列（5+1 标注），未擅自丢弃素材面事实。
2. 重放三门全过但未做重放——挂起原因是素材图像侧前提不成立，非门不满足；与"任何门不满足就
   地挂起"不同源，如实区分。
3. 侦察员报告与本会话实测逐项一致（六袋零图像、034144 position_cmd=58659、035325 无
   position_cmd、两 hover takeoff_land=58、U3PR1 先例袋 309M）；独立复验未发现矛盾。
4. "五袋 vs 6 袋"的差异按素材面原样转记，范围归属留主会话定夺。
5. 本件只 add `docs/t4_w1_u3pp_reception.md`；不 push；commit 作者 rick <rick@nuc.local>。

## 8. 留档位置

- 本文档：NUC `~/catkin_ws/docs/t4_w1_u3pp_reception.md`（scp 通道落盘，中文零内联）。
- rosbag info 原始输出×6：NUC `/tmp/t4w1_reception/<袋>.info`。
- 袋 manifest md5：NUC `/tmp/t4w1_reception/bags_md5.txt`。
- 收货回执：`~/sitl_sim/STATUS.md` 尾行追加（scp 通道）。
