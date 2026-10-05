# T4 池件台账续核账（poolledger_20261006）

- 执行：T4 线池件执行员·锚袋资产固化续核账（执行域=3090 ghj@ghj-System-Product-Name；旧 NUC=uav@uav4 只读，经 ssh nuc 免密腿）
- 时刻：2026-10-06 晨（3090 远端 date 实测起点 06:07:37 CST）
- 性质声明：纯清点/核对/登记面，零判读语义，零 PASS/FAIL 判读行；未触碰 verdicts 正本（~/catkin_ws/docs/t4_verdicts_v2.md）；他线文件只读引用；本次无删袋动作（腾位双门无涉）。
- 前册正源：~/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived/pn1_deleted_bag_asset_md5.csv（289 数据行）+ 同名 .md 说明件（pn1=2026-10-05 晨批固化台账）。

## ① pn1 台账抽验复核（抽 6/289）

### 版本固定（3090 原样输出）

- `md5sum` CSV = `9e5c68a9a18f64acb57d82eef5158b96`；`stat -c '%s %Y'` = `33229 1791163366`；`awk 'END{print NR}'` = `290`（=表头 `path,bytes,md5` + 289 数据行）。
- 与 pn1 .md 首部登记（md5=9e5c68a9a18f64acb57d82eef5158b96 / 33229 B / 数据行 289 行）逐项一致 → 所核版本即前册固化版本，无漂移。

### 抽样法（确定性，可复算）

- 等距+面覆盖：数据行 1/70/140/210/280/289 = 文件行 2/71/141/211/281/290（`sed -n '2p;71p;141p;211p;281p;290p'`），覆盖 pn1 三面：面①提帧目录（030927_j3 L0/R1 帧+manifest、032005_j3 R1 帧）、面②metrics json、面③jr3_replay features.bag。

### 结果表（现值经 nuc 腿 uav4 实测：`ssh nuc 'md5sum ...; du -b ...'`）

| # | 文件行 | 资产路径（/home/uav/sitl_sim/vision_inputs/） | CSV md5 | 现值 md5 | 一致 | CSV B | 现值 B |
|---|---|---|---|---|---|---|---|
| 1 | 2 | WC2OBS1_030927_j3/flight_L0_s0_0001.png | 2ed6b89d1c991a9f0ae7a9555ec78568 | 2ed6b89d1c991a9f0ae7a9555ec78568 | 是 | 124624 | 124624 |
| 2 | 71 | WC2OBS1_030927_j3/flight_R1_s0_0001.png | 437ae6912fba55f50f57164d44d3dc01 | 437ae6912fba55f50f57164d44d3dc01 | 是 | 124500 | 124500 |
| 3 | 141 | WC2OBS1_030927_j3/manifest.json | 412d448e573640f28c103371b83b33f3 | 412d448e573640f28c103371b83b33f3 | 是 | 26763 | 26763 |
| 4 | 211 | WC2OBS1_032005_j3/flight_R1_s0_0001.png | 35e0589d1b18576c895b99ca1c7dc76a | 35e0589d1b18576c895b99ca1c7dc76a | 是 | 124469 | 124469 |
| 5 | 281 | metrics_WC2OBS1_030927.json | ad1fb70b7e2bc124af574793f34468e9 | ad1fb70b7e2bc124af574793f34468e9 | 是 | 69671 | 69671 |
| 6 | 290 | jr3_replay_WC2OBS1_032005/features.bag | 19b4036548458d6447900806d9fd4e96 | 19b4036548458d6447900806d9fd4e96 | 是 | 2107784 | 2107784 |

- 结果（数据面）：抽验 **6/6** 现值 md5 与 bytes 逐件一致，漂移 0。
- 边界如实注记：全量 289 件未重算（任务书=抽 6）；3090 域 ~/sitl_sim/bags/（64 袋）未逐袋 md5（非本任务，且大 IO 须走互斥空窗，本次未申请）。

## ② 3090 域腾位删除事件核查

### 本域界定（实测）

- `stat -c '%d %i'`：/home/ghj/sitl_sim 与 /home/ghj/catkin_ws 同 device **66306**（3090 本地 /dev/nvme0n1p2，915G）；`mount` 无 nfs/sshfs/业务 fuse 挂载 → ~/sitl_sim 即本域实体，与旧 NUC（/home/uav，独立盘）为两套文件系统。
- df 门现值：`df -h /home` = **590G 裕**（≥25G 门通过，无腾位压力）。

### 核查面（五面，命令与命中如实录）

1. **STATUS.md（942 行）grep '腾位|删袋|删除'**：命中集中 10-04——L673/L676 磁盘危机章（df 22→68G 量级=NUC 域刻度）；L712/L713/L714/L721 T4 WC2×2 腾位令执行与回执（run_WC2OBS1_030927/flight.bag 13.6G + run_WC2OBS1_032005/flight.bag 13.5G）=**已由 pn1 289 件固化入账，非新增**；L726/L727 锚袋事故#2 定案与 T4 双门机制吸收；L845 T1 单元8 E-4 袋释放=**袋身份未定挂账请求件，未执行**（DECISION_LOG D-1006-T1-08："E-4 袋身份=跨线指认请求件…维持挂起"）；L926 T3 04:24 批窗申报明示"无 pkill/无清场/无轮删除"。**pn1 固化时点（2026-10-05 08:33）之后零删袋命中。**
2. **DECISION_LOG.md grep '腾位|删袋'**：命中 L65（WC2×2 执行依据）/L80（#10 锚事故定案）/L82-L87（D-2026-10-04-08 双门扩充）/L121/L123（轮转复核通过），全部 10-04 在册项，其后无新增。
3. **run 区普查**：~/sitl_sim/vins_smoke_runs 共 **151** run 目录；无 flight.bag 者 **28** 个（实列清单在案），与今日 T4 recept 批 05:48 STATUS 登记行"登记 47（28 无袋+19 T1 轮次袋判读权归 T1）"的"28 无袋"同集——其中 WC2×2 为已入账删除，其余为无袋型 run（gnd/probe/E2FAIL/早期 X1 等），无"曾有袋后失袋"新面孔。
4. **trash/attic/deleted 目录**：`find ~/sitl_sim -maxdepth 3 \( -iname '*trash*' -o -iname '*attic*' -o -iname '*deleted*' \)` = **0 命中**。
5. **锚资产今日在位（3090 侧）**：x11_dryrun_v11 下 ANCHOR_U3PO / U3R_t2v3_route_033941 / U3R_t2v3_hover_035509 / R5_pairing_fix 四格 `ls -d` 全 OK，SYN_* 计 **12** 目录；R5 袋 `stat` = **24115985131 B**（mtime 10-03 03:08），与 anchor_assets_manifest_20261005.md 登记 24,115,985,131 B 一致 → 锚面零缺损。runbook 正源在位：~/catkin_ws/sitl_sim/docs/t3_xline_runbook.md（16016 B，mtime 10-04 17:42，与锚清单所录锚表 mtime 吻合）。

### 结论（登记面，非判读行）

- **本域（ghj@3090，/home/ghj/sitl_sim）自 pn1 固化（2026-10-05 08:33）以来：删袋事件 = 0，已删袋资产台账（pn1_deleted_bag_asset_md5.csv，289 件）增补 = 0 条**——如实零增补登记。
- 域外/批前史证不增补、不代记，如实注记：①10-04 危机章删除均属 NUC 域刻度（T3 U3PO 蒸馏+删原袋 +12.7G=df 22→28G、T2 自清 024434+030207≈43G、退役史证锚 WAOL5R_222234/X1_232055=T1 02:57 删，见 STATUS L666/L673/L676 与锚清单退役史证节），其资产固化属 NUC 侧账面责任域；②E-4 袋释放请求（L845）维持挂起，未构成删除事件，后续如执行须按双门（§8 三面核对+§9.2 锚表 grep）另起通告并届时增补本账。
- IO 互斥合规注记：本次仅小件 md5（6 件合计 ≈2.7MB）+元数据清点，无重放/提帧/大 IO；T1 批态核查 `find t1_evidence -name 'x4_batch_report.md' -mmin -30` = 0 命中（无运行窗）。

## ③ 本件落盘与 git

- 落盘：~/catkin_ws/sitl_sim/t4_evidence/poolledger_20261006.md（中文经 scp 通道两段式：本地写→scp nuc2:/tmp/→cp 归位，双端 md5sum 对账一致后为准）。
- git：cd ~/catkin_ws，只 add 本件路径，commit --author='rick <rick@nuc.local>'（前缀 T4-poolled），工作单元内**不 push**（收口统一推）。
- keyStats：抽验 6/6 一致；增补 0 条。
- 附：本件为登记/数据面草稿性质，如后续主会话需引用入 verdicts，由主会话定稿；本执行员未改任何判据与判读行。
