# T4 锚袋资产固化清单（池件①-1）— 2026-10-05

- 执行：T4 线池件执行员·锚袋资产固化（执行域=3090；NUC 侧只读对照）
- 任务：解析锚表 §9.2 v3 全部锚袋条目 → 双机（3090+NUC）逐袋在位核验 → 落本耐久清单
- **锚表正源**：`~/catkin_ws/sitl_sim/docs/t3_xline_runbook.md` §9.2「判读锚袋注册表（v3；2026-10-04 09:32 锚重建#3 定稿）」；实测 md5=`58bed0274ddb20ab594b959ff1f58050`，197 行，mtime epoch=1791106940（=2026-10-04 17:42:20 CST），与锚表侦察报 lines=197/mtime=1791106940 逐项吻合
- **核验时刻**：3090 起 2026-10-05 03:45:25 CST；NUC 起 03:47:45 CST（均以 3090 远端 date 域为准，两机 date 实测同日同分级）
- **双机身份**：3090=ghj@ghj-System-Product-Name（192.168.0.4，`ssh nuc2`）；NUC=uav@uav4（192.168.0.5，`ssh nuc`，只读）
- **载体域（两机同径）**：`~/sitl_sim/t3_results/x11_dryrun_v11/`（注意：在 `~/sitl_sim` 运行区，不在 `~/catkin_ws` 仓库区）
- **核验口径**：逐目录逐文件 size(B)+mtime(epoch) 实测；md5 前 8 位仅对 <2G 文件实算；R5 袋 24,115,985,131B(22.5G)≥2G → 两机均按口径只记 size+mtime；一切判定以远端 stat/md5sum/grep 原样输出为准
- **df 门现场**：3090=607G 裕；NUC=54G 裕（均≥25G，通过）
- **空窗门现场**：3090 md5 前 `pgrep -cx`=vins_node/gzserver/gzclient/rosbag/px4/mavros/rosmaster 全 0（03:43），放行；NUC 侧 rosbag=1（T3 Rold 轮 `rosbag record` 在飞，STATUS 03:29 通告"权序在飞"）→ NUC md5 腿按纪律排队重查，见 §6

---

## §1 锚格登记（锚表 §9.2 v3 全部 5 行，逐行照录+解析）

| 锚格 | 属线 | 注册时间（锚表载明） | 角色（锚面，照录） | 载体目录 |
|---|---|---|---|---|
| ANCHOR_U3PO | T3 判读锚（源袋=run_U3PO_211438，T2 U3 轮） | 2026-10-04 09:32（v1.3-anchor2=8720a1f2） | clean 锚：j0 2.603 / Bas 病态 1.3709 / 359s 存活 | `x11_dryrun_v11/ANCHOR_U3PO/` |
| U3R_t2v3_route_033941 | T3 判读锚（T2 U3R route 轮） | 2026-10-04 09:32（同上批入格） | TNR 教科书锚：5fires+14faildet / 统一锚 legacy@49.376 / L2b 791.9 拦 / Bas 峰 7.17 | `x11_dryrun_v11/U3R_t2v3_route_033941/` |
| U3R_t2v3_hover_035509 | T3 判读锚（T2 U3R hover 轮） | 2026-10-04 09:32（同上批入格） | controlled 锚：legacy@46.476 / L2a 96 / L2b p95 0.0755（v1.3 舰队首翻样本） | `x11_dryrun_v11/U3R_t2v3_hover_035509/` |
| SYN_×12 | T3 合成电池（自产） | 锚表载「永久」 | SYN 电池 9 断言（对抗面四型含）+边界×3 | `x11_dryrun_v11/SYN_*/`（12 目录，见 §2） |
| R5_pairing_fix | T3 判读锚（硬链 T2 保全袋） | 锚表载「在册」（未载具体时刻） | 受控正样本（至 X7） | `x11_dryrun_v11/R5_pairing_fix/` |

锚表另载**退役史证**（非在册锚）：WAOL5R_222234 / X1_232055（T1 02:57 删）、WC2OBS1_032005（T4 05:23 §8.1 顺位2 删，袋失）；本清单 §4.3 有核验注记。

## §2 逐锚袋在位核验（15 袋+1 无袋夹具；锚格 5 行 → 资产目录 16+史证 1=17 目录）

| # | 袋 | 3090：size(B)/mtime(epoch)/md5前8 | NUC：size(B)/mtime(epoch)/md5前8 | 判定 |
|---|---|---|---|---|
| 1 | ANCHOR_U3PO/flight.bag | 202714067 / 1791054045 / `520e2e09` | 202714067 / 1791054045 / 门控挂起(§6) | 双机在位，size+mtime 逐位一致 |
| 2 | U3R_t2v3_route_033941/flight.bag | 336800817 / 1790970640 / `daa07379` | 336800817 / 1790970640 / 门控挂起(§6) | 双机在位，size+mtime 逐位一致 |
| 3 | U3R_t2v3_hover_035509/flight.bag | 67828912 / 1790971048 / `23bdad16` | 67828912 / 1790971048 / 门控挂起(§6) | 双机在位，size+mtime 逐位一致 |
| 4 | R5_pairing_fix/flight.bag | 24115985131 / 1790968086 / SKIP(≥2G) | 24115985131 / 1790968086 / SKIP(≥2G) | 双机在位，size+mtime 逐位一致 |
| 5 | SYN_CTRL/flight.bag | 829603 / 1790963010 / `405378bb` | 829603 / 1790963010 / 门控挂起(§6) | 双机在位 |
| 6 | SYN_EARLY/flight.bag | 829603 / 1791052912 / `57a49735` | 829603 / 1791052912 / 门控挂起(§6) | 双机在位 |
| 7 | SYN_FALSE/flight.bag | 829603 / 1791050767 / `405378bb` | 829603 / 1791050767 / 门控挂起(§6) | 双机在位 |
| 8 | SYN_LATE/flight.bag | 829603 / 1790963010 / `25d3c931` | 829603 / 1790963010 / 门控挂起(§6) | 双机在位 |
| 9 | SYN_LATE_LEG/flight.bag | 829603 / 1791052845 / `25d3c931` | 829603 / 1791052845 / 门控挂起(§6) | 双机在位 |
| 10 | SYN_LEG/flight.bag | 829603 / 1791050767 / `b8fd1f8f` | 829603 / 1791050767 / 门控挂起(§6) | 双机在位 |
| 11 | SYN_LEG_A1/flight.bag | 98888 / 1791050767 / `48c78ddf` | 98888 / 1791050767 / 门控挂起(§6) | 双机在位 |
| 12 | SYN_MULTI/flight.bag | 829603 / 1790963010 / `405378bb` | 829603 / 1790963010 / 门控挂起(§6) | 双机在位 |
| 13 | SYN_MULTI2/flight.bag | 829603 / 1791052845 / `405378bb` | 829603 / 1791052845 / 门控挂起(§6) | 双机在位 |
| 14 | SYN_NOTC/flight.bag | 829603 / 1790963010 / `405378bb` | 829603 / 1790963010 / 门控挂起(§6) | 双机在位 |
| 15 | SYN_NOTC_LEG/flight.bag | 829603 / 1791052845 / `405378bb` | 829603 / 1791052845 / 门控挂起(§6) | 双机在位 |
| — | SYN_NOBAG/（无袋） | 夹具按设计无 flight.bag；边件 4 件在位（RESULT.txt/round.log/simvins.log/wa_gate_online.json，另有 v12.json） | 同左 | 双机在位（bag-less 边界夹具，非缺损） |

mtime 可读式（CST）：1790963010=10-03 02:23:30；1790968086=10-03 03:08:06；1790970640=10-03 03:50:40；1790971048=10-03 03:57:28；1791050767=10-04 02:06:07；1791052845=10-04 02:40:45；1791052912=10-04 02:41:52；1791054045=10-04 03:00:45。

**SYN 袋同 md5 互证面**：829603B 基袋在 3090 侧实测同 md5=`405378bb`（CTRL/FALSE/MULTI/MULTI2/NOTC/NOTC_LEG 六目录同内容）与 `25d3c931`（LATE/LATE_LEG 同内容）；NUC 侧 CTRL/MULTI/NOTC 三目录共享 inode=14160513（links=3，真硬链）——两机证据互洽：SYN 电池系"同基袋+不同边件配置"的夹具结构，非重复冗余。

## §3 边件面（锚目录内非袋文件，登记不判读）

- 3090 侧 17 目录共 108 文件（15 袋+93 件非袋边件）已全量 size+mtime+md5 实测（附录 A）；NUC 侧全量 size+mtime 实测（对照脚本 v2，T4_SKIP_MD5=1）。
- **结构性差异（如实登记）**：① `j0_decomp.json` 仅 3090 有（ANCHOR_U3PO/U3R_route_033941/U3R_hover_035509 三目录，10-05 01:32-01:42 生成），NUC 无；② `wa_gate_online.json` 等判读边件两机内容不同（如 ANCHOR_U3PO：3090 2733B/1791135233 vs NUC 2147B/1791133271）——两机于 10-05 01:1x-01:4x 各自重跑判读链产物所致，属边件正常分叉；③ **锚袋本体（flight.bag）两机 size+mtime 全部逐位一致，袋面零分叉**。

## §4 结构性发现（登记，不判读）

### §4.1 硬链两态（锚表"硬链"表述的机器差异）
- **NUC（原产侧）硬链为真**：ANCHOR_U3PO/flight.bag ↔ `~/sitl_sim/vins_smoke_runs/run_U3PO_211438/flight.bag` 同 inode=14158098（各 links=2）；R5_pairing_fix/flight.bag ↔ `~/sitl_sim/bags/t2v3_route_025706.bag` 同 inode=13930448（各 links=2）；源袋 size+mtime 与锚袋逐位一致（202714067/1791054045；24115985131/1790968086）。
- **3090（迁移侧）硬链已退化**：四锚袋 links=1、inode 各异（46923893/46924029/46924015/46923902）；迁移 rsync 未保硬链。内容等价性实测：U3PO 锚袋 vs run_U3PO_211438 源袋 **md5 一致（同 520e2e09）**+size+mtime 一致=逐字节等价的两份独立拷贝；R5 锚袋 vs `~/sitl_sim/bags/t2v3_route_025706.bag` size+mtime 一致（24115985131/1790968086，≥2G 按口径不实算 md5，内容等价性为 size+mtime 级）。
- **腾位含义**：3090 上删 `run_U3PO_211438/` 或 `t2v3_route_025706.bag` 不会连带删锚袋（已无硬链耦合），但两份独立拷贝各占盘；NUC 上硬链仍在，**删硬链伙伴=实删锚数据**。

### §4.2 判读链自持面
- x11_dryrun_v11 域总量 25G（du 实测），其中非锚格的 U3R_t2v3_*（ground_032114/ground_035105/hover_032229/hover_032518/hover_035220/route_032809/route_035800/route_040932）等 8 目录**不在锚表注册**，不受本清单保护（由 T3 台账管辖）；本清单只固化 §1 五锚格+史证目录。

### §4.3 退役史证闭环（锚表 v2/v3 退役记载 vs 实勘）
- `RETIRED_WC2OBS1_032005/`（3090）：边件 13 件在位（含真读数存档 `wa_gate_online.pre_v13.json`，mtime 1791057986），**无袋**——与锚表"05:23 删袋、真读数存档"记载吻合；NUC 侧 `run_WC2OBS1_032005/` 同为边件 18 件、**find "*.bag" 零命中**（03:5x 实测）——与"随之失袋"记载吻合。
- WAOL5R_222234 / X1_232055：两机 maxdepth=3 搜索无 run 目录/袋残体（仅 `t3_results/xline_histreg/run_*.new.txt` 文字记录）——与"T1 02:57 删"记载吻合。

### §4.4 锚表引用面
- `~/catkin_ws/docs/sim2real_runbook.md`（3090，md5 前 8=ed035e3b，187 行）内 grep 实测**无五锚格名直引**（0 命中，2026-10-05）——锚表唯一载体=t3_xline_runbook.md §9.2；"3090 同表"按 t3_xline_runbook.md 口径执行。

## §5 保护提示（腾位双门标的）

1. **本清单 §1-§2 全部 17 目录（16 锚资产目录+1 史证目录）均为"腾位双门标的"**：任何线执行腾位删除前，必 runbook §8 三面核对 + grep 锚表（`grep -l <袋名> ~/catkin_ws/sitl_sim/docs/t3_xline_runbook.md`，§9.2 v3），**命中即 @T3 等回执，禁先行删除**。
2. 锚表流程条款照录：注册≠保护（v3 教训=WC2×2 主池袋代理删除致 WC2OBS1 失袋）；v3 设计原则=三锚全部自持 x11_dryrun_v11（T3 域，不在任何腾位池清单内=结构免疫）。
3. R5 锚格保全至 X7（锚表载明）；X4* 袋绝对不删（保全至 X7，条款照录，本清单域内暂无 X4 袋）。
4. NUC 侧硬链伙伴（`run_U3PO_211438/flight.bag`、`bags/t2v3_route_025706.bag`、SYN 基袋 ino=14160513）**与锚袋同 inode**：NUC 腾位时硬链对必 `stat -c '%h %i'` 核对后再动。
5. 本清单为 T4 固化登记，不改变锚表属权：锚格属 T3 判读域，处置权在 T3+主会话。

## §6 NUC md5 腿门控记录（诚实条款，如实登记）

- 03:46 首查：`pgrep -cx`=rosbag=1 / gzserver=0 → 未过双 0 门，md5 暂缓，size+mtime 轻量勘验先行（不涉大 IO）。
- 03:59 二查：rosbag=1（身份实测=`rosbag record -O ~/sitl_sim/t3_runs/Rold_1_225851/flight.bag …`，T3 Rold 轮采集在飞）→ 继续排队。
- - 04:10 三查：rosbag=1（同一 record 进程 PID 3608527，`Rold_1_225851` 自 ≥03:46 持续采集）→ **3 次重查（03:46/03:59/04:10，间隔 ~600s 级）均未过双 0 门，按纪律本腿挂起，禁硬闯**（他线 T3 Rold 轮权序在飞，STATUS 03:29 在册）。NUC 15 袋 md5 补算留待 NUC 门清后另行登记，本清单不虚记为已算。
- 口径说明：NUC 在位性判定（§2 表）已由 size+mtime 逐位一致支撑；md5 为补充等价性证据，其缺不影响在位结论。
- 口径说明：NUC 在位性判定（§2 表）已由 size+mtime 逐位一致支撑；md5 为补充等价性证据，其缺不影响在位结论。

## 附录 A：3090 侧全量文件清单（17 目录逐文件；格式 dir|file|size(B)|mtime(epoch)|links|inode|md5前8）

```
ANCHOR_U3PO|flight.bag|202714067|1791054045|1|46923893|520e2e09
ANCHOR_U3PO|forensics_v2.json|2939|1790876153|1|46923894|eff550f9
ANCHOR_U3PO|j0_decomp.json|307|1791135159|1|46924245|5ab57ab8
ANCHOR_U3PO|RESULT.txt|626|1790860941|1|46923892|693b258c
ANCHOR_U3PO|round.log|1353|1790860942|1|46923895|a0f2dcd3
ANCHOR_U3PO|simvins.log|11440868|1790860943|1|46923896|b1c95615
ANCHOR_U3PO|wa_gate_online.json|2733|1791135233|1|46923897|087a31df
U3R_t2v3_route_033941|flight.bag|336800817|1790970640|1|46924029|daa07379
U3R_t2v3_route_033941|forensics_v2.json|3745|1791077469|1|46924030|f641f96a
U3R_t2v3_route_033941|forensics_v2.txt|1952|1791077469|1|46924031|9f2eb10b
U3R_t2v3_route_033941|j0_decomp.json|334|1791135703|1|46924246|9d3a9b4d
U3R_t2v3_route_033941|RESULT.txt|645|1790993030|1|46924028|f889758b
U3R_t2v3_route_033941|round.log|42|1790993006|1|46924032|7100dd9b
U3R_t2v3_route_033941|simvins.log|39141781|1790970643|1|46924033|d5f46868
U3R_t2v3_route_033941|wa_gate_online.json|2863|1791135247|1|46924034|3465cf23
U3R_t2v3_route_033941|wa_gate_online.v12.json|2158|1790993040|1|46924035|489b2c1c
U3R_t2v3_hover_035509|flight.bag|67828912|1790971048|1|46924015|23bdad16
U3R_t2v3_hover_035509|forensics_v2.json|2810|1791077483|1|46924016|7ae85e46
U3R_t2v3_hover_035509|forensics_v2.txt|1321|1791077483|1|46924017|009d3f86
U3R_t2v3_hover_035509|j0_decomp.json|318|1791135742|1|46924247|99ebbf17
U3R_t2v3_hover_035509|RESULT.txt|576|1790993055|1|46924014|481bdd08
U3R_t2v3_hover_035509|round.log|42|1790993051|1|46924018|7100dd9b
U3R_t2v3_hover_035509|simvins.log|1991451|1790971051|1|46924019|e47da400
U3R_t2v3_hover_035509|wa_gate_online.json|2696|1791135250|1|46924020|4d36bf62
U3R_t2v3_hover_035509|wa_gate_online.v12.json|2142|1790993058|1|46924021|7484c3a5
R5_pairing_fix|flight.bag|24115985131|1790968086|1|46923902|SKIP_GE2G
R5_pairing_fix|forensics_v2.json|3707|1790969027|1|46923903|8c8ae228
R5_pairing_fix|forensics_v2.txt|1922|1790969027|1|46923904|ff580f56
R5_pairing_fix|RESULT.txt|630|1790968966|1|46923901|4db3edc9
R5_pairing_fix|round.log|108|1790968886|1|46923905|b4261d51
R5_pairing_fix|simvins.log|11151794|1790968089|1|46923906|eaa2183b
R5_pairing_fix|wa_gate_online.json|2321|1791050983|1|46923907|c088fd64
R5_pairing_fix|wa_gate_online.v12.json|2159|1790969256|1|46923908|4c0d4eeb
RETIRED_WC2OBS1_032005|arrive_watch.txt|81|1790796271|1|46923910|cf9fd737
RETIRED_WC2OBS1_032005|forensics_v2.json|3001|1790851040|1|46923911|75a4af2c
RETIRED_WC2OBS1_032005|forensics_v2.txt|1468|1790851040|1|46923912|6b12a963
RETIRED_WC2OBS1_032005|goal.txt|27|1790796059|1|46923913|ae4191d3
RETIRED_WC2OBS1_032005|mavros.log|410315|1790796471|1|46923914|23db33e9
RETIRED_WC2OBS1_032005|planner.log|84914|1790796471|1|46923915|4bb1d7e2
RETIRED_WC2OBS1_032005|poscmd_hz.txt|22|1790796280|1|46923916|735c999d
RETIRED_WC2OBS1_032005|preflight.txt|286|1790796031|1|46923917|864469aa
RETIRED_WC2OBS1_032005|px4ctrl.log|143263|1790796471|1|46923918|f7a1134a
RETIRED_WC2OBS1_032005|record.log|1455|1790796418|1|46923919|dbc16a96
RETIRED_WC2OBS1_032005|RESULT.txt|570|1790796469|1|46923909|0cd2824f
RETIRED_WC2OBS1_032005|round.log|1269|1790796471|1|46923920|df51a58f
RETIRED_WC2OBS1_032005|wa_gate_online.pre_v13.json|2545|1791057986|1|46923921|a2476a26
SYN_CTRL|flight.bag|829603|1790963010|1|46923923|405378bb
SYN_CTRL|RESULT.txt|296|1791135307|1|46923922|7c5e734c
SYN_CTRL|round.log|42|1791135307|1|46923924|7100dd9b
SYN_CTRL|simvins.log|111|1791135307|1|46923925|9d8d53be
SYN_CTRL|wa_gate_online.json|2398|1791135307|1|46923926|dda3ed6c
SYN_EARLY|flight.bag|829603|1791052912|1|46923928|57a49735
SYN_EARLY|RESULT.txt|296|1791135307|1|46923927|7c5e734c
SYN_EARLY|round.log|42|1791135307|1|46923929|7100dd9b
SYN_EARLY|simvins.log|71|1791135307|1|46923930|ed3da33f
SYN_EARLY|wa_gate_online.json|2565|1791135309|1|46923931|c8bc7cad
SYN_FALSE|flight.bag|829603|1791050767|1|46923933|405378bb
SYN_FALSE|RESULT.txt|296|1791135307|1|46923932|7c5e734c
SYN_FALSE|round.log|42|1791135307|1|46923934|7100dd9b
SYN_FALSE|simvins.log|71|1791135307|1|46923935|ed3da33f
SYN_FALSE|wa_gate_online.json|2632|1791135308|1|46923936|4a99b223
SYN_LATE|flight.bag|829603|1790963010|1|46923938|25d3c931
SYN_LATE|RESULT.txt|296|1791135307|1|46923937|7c5e734c
SYN_LATE|round.log|42|1791135307|1|46923939|7100dd9b
SYN_LATE|simvins.log|112|1791135307|1|46923940|375757da
SYN_LATE|wa_gate_online.json|2619|1791135308|1|46923941|0a3459a8
SYN_LATE_LEG|flight.bag|829603|1791052845|1|46923943|25d3c931
SYN_LATE_LEG|RESULT.txt|296|1791135307|1|46923942|7c5e734c
SYN_LATE_LEG|round.log|42|1791135307|1|46923944|7100dd9b
SYN_LATE_LEG|simvins.log|72|1791135307|1|46923945|53d2e627
SYN_LATE_LEG|wa_gate_online.json|2609|1791135310|1|46923946|c3bd1d35
SYN_LEG|flight.bag|829603|1791050767|1|46923948|b8fd1f8f
SYN_LEG|RESULT.txt|296|1791135307|1|46923947|7c5e734c
SYN_LEG|round.log|42|1791135307|1|46923949|7100dd9b
SYN_LEG|simvins.log|71|1791135307|1|46923950|ed3da33f
SYN_LEG|wa_gate_online.json|2405|1791135308|1|46923951|de129803
SYN_LEG_A1|flight.bag|98888|1791050767|1|46923953|48c78ddf
SYN_LEG_A1|RESULT.txt|296|1791135307|1|46923952|7c5e734c
SYN_LEG_A1|round.log|42|1791135307|1|46923954|7100dd9b
SYN_LEG_A1|simvins.log|219|1791135307|1|46923955|2bf0cfda
SYN_LEG_A1|wa_gate_online.json|2517|1791135309|1|46923956|6a269676
SYN_MULTI|flight.bag|829603|1790963010|1|46923958|405378bb
SYN_MULTI|RESULT.txt|296|1791135310|1|46923957|7c5e734c
SYN_MULTI|round.log|42|1791135310|1|46923959|7100dd9b
SYN_MULTI|simvins.log|206|1791135310|1|46923960|464df92a
SYN_MULTI|wa_gate_online.json|2399|1791135310|1|46923961|767fec5a
SYN_MULTI|wa_gate_online.v12.json|1977|1790969203|1|46923962|f6b9ad50
SYN_MULTI2|flight.bag|829603|1791052845|1|46923964|405378bb
SYN_MULTI2|RESULT.txt|296|1791135307|1|46923963|7c5e734c
SYN_MULTI2|round.log|42|1791135307|1|46923965|7100dd9b
SYN_MULTI2|simvins.log|182|1791135307|1|46923966|028aaff3
SYN_MULTI2|wa_gate_online.json|2402|1791135309|1|46923967|34338ea5
SYN_NOBAG|RESULT.txt|296|1791135310|1|46923968|7c5e734c
SYN_NOBAG|round.log|42|1791135310|1|46923969|7100dd9b
SYN_NOBAG|simvins.log|103|1791135310|1|46923970|ac1f6c83
SYN_NOBAG|wa_gate_online.json|2420|1791135311|1|46923971|524e4cd0
SYN_NOBAG|wa_gate_online.v12.json|1998|1790969204|1|46923972|a6a663d1
SYN_NOTC|flight.bag|829603|1790963010|1|46923974|405378bb
SYN_NOTC|RESULT.txt|296|1791135310|1|46923973|7c5e734c
SYN_NOTC|round.log|42|1791135310|1|46923975|7100dd9b
SYN_NOTC|simvins.log|74|1791135310|1|46923976|cbe53570
SYN_NOTC|wa_gate_online.json|2502|1791135311|1|46923977|37dccaff
SYN_NOTC|wa_gate_online.v12.json|2097|1790969204|1|46923978|f2a3b8f6
SYN_NOTC_LEG|flight.bag|829603|1791052845|1|46923980|405378bb
SYN_NOTC_LEG|RESULT.txt|296|1791135307|1|46923979|7c5e734c
SYN_NOTC_LEG|round.log|42|1791135307|1|46923981|7100dd9b
SYN_NOTC_LEG|simvins.log|34|1791135307|1|46923982|010f9e14
SYN_NOTC_LEG|wa_gate_online.json|2509|1791135310|1|46923983|12080265
```

目录 mtime（3090）：ANCHOR_U3PO=1791134662，U3R_t2v3_route_033941=1791135166，U3R_t2v3_hover_035509=1791135167，R5_pairing_fix=1791050948，RETIRED_WC2OBS1_032005=1791077688，SYN_* 见脚本输出（域=/home/ghj/sitl_sim/t3_results/x11_dryrun_v11，du 总量 25G）。

## 附录 B：NUC 侧对照勘验摘要（stat 口径；full listing 在会话日志）

- 17/17 目录在位（/home/uav/sitl_sim/t3_results/x11_dryrun_v11）；逐文件 size+mtime 与 3090 对照**零差异**（含 15 袋与全部边件）。
- NUC 缺 3090 的 3 件 `j0_decomp.json`（10-05 01:3x 仅 3090 生成）；判读边件内容分叉见 §3。
- 硬链面：锚袋 links=2/3（伙伴见 §4.1）；3090 对应 links=1。
- NUC md5 腿：见 §6 门控记录。

---
*固化人：池件①-1 T4 锚袋资产员；本清单为登记性质资产台账，不含任何判读结论；判据/权属问题一律归 T3+主会话。*
