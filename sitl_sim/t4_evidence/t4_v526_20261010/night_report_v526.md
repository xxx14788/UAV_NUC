# T4 夜报 v5.26 — 三周期积压全量清账+新轮收货（2026-10-09）

> 撰写=T4 夜报撰写员（保底④收口单元）。材料来源=本夜各单元返回值与独立审计结论（ask 内嵌），本稿不添写任何单元未报告的事实；不确定处标【待确认】。
> 环境复核（夜报撰写员本机实测，非单元返回值）：nuc2(3090) 09:20 可达 rc=0、nuc(NUC .6) 09:21 可达 rc=0（`ssh date +%H:%M; echo` 探测），与可达预期一致，无降级注记需要。STATUS 落点实测：nuc2 唯一 STATUS=`/home/ghj/sitl_sim/STATUS.md`（写入时点 1109 行、尾行=09:06 T4 心跳），HOME 侧 `~/STATUS.md` 实测不存在——与《可做而未做清单》第 10 条审计时点口径（HOME=1109/repo=1096 分叉）相比现状已变化，分叉收敛机制仍按第 10 条移交裁决。

## ① 双必达裁决

**审计结论：双必达两项达成。**

1. **verdicts 三节草稿=达成**：`verdicts_draft_v526.md` 310 行落盘非占位（三周期三节+§6 八条对账表+异常注记 9 组），但稿内自曝两条未闭环注记（代编稿待主会话认领定稿/'三节'定义两解待裁），不影响"落盘∧非占位"事实。
2. **E4 复核=达成（有果，mode=recalc-done，非阻塞注记）**：预注册判据定位+六袋 216 帧复算+箱级对照 6/6 一致+v55 正源产物逐位一致（bitIdentical）。

双项均经本审计独立抽验（md5/远端实读）吻合。

## ② 单元结果表

| 单元 | 结论 | 产物路径 |
|---|---|---|
| 开工对账 | pull 前 HEAD=9d66a9c2 → pull RC=0…unchanged，六件全符（台账已找到）；df=解析失败，见开工对账员复测 | 台账正源：docs/t4_verdi…【待确认，原文截断】 |
| verdicts 三节草稿 | ok——310 行非占位：节一漏发（v5.24 编排完备零执行）/节二未开工（v5.22+v5.23，三重凭据）/节三单线期避让+§6 八条对账表（7 条未达维持+1 条已闭合 L561 在册）；遗留注记：任务书 L15 明文"主会话直出"而本稿系草稿员代编稿待认领、'三节'两解（(B)旧构有 v5.22 L29 在册祖源优势）待主会话裁 | D:/drone_VINS/t4_v526_out/verdicts_draft_v526.md |
| E4 帧级复核 | ok·有果（recalc-done，非阻塞注记）——prereg 判据定位（md5 fd750919，审计远端 md5sum 实读同值）、六袋三条件复算 4 立 2 不立、verdicts_v2 §3 箱级对照六袋全一致（正本 md5 4f34d500 审计实测未变=零触碰）、三件产物与 v55 正源 cmp 逐位一致；局限 §8 七条如实（cv2 像素重放未重跑/U3PG 切点稳健=否新旗标待主会话裁）。别名件 e4_frame_recheck_v526.md 与正名件 diff 实测 IDENTICAL，双件 md5 5aed12a1 | D:/drone_VINS/t4_v526_out/e4_framelevel_recheck_v526.md（别名件 e4_frame_recheck_v526.md 同目录） |
| 新袋收货+台账 | ok——7 cohort 定义 78/实物 78 全"收讫-待判"零三态（无 T4 预注册收货判据，红线①合规）+7 分册抽读（cohort1-7）均非占位+W-T2 滚动件销记（预热复验 16+三臂今补 12+A1×3=31 袋）+锚袋 A1OBS md5×3 凭据在册（782619d5/06eaaca2/52483365）+臂配对口径 §8；预热对照批 16 定义/15 实物，缺 run_WU_E8P_A_*（昨夜），有补飞链注记（WU_FIX r2+复验 WU2_E8P_A） | D:/drone_VINS/t4_v526_out/bag_receipt_ledger_v526.md + cohort1~7_*_receipt_20261009.md（7 分册） |
| 第五坑月报 | 已落盘（长期件必落项，全增量并入，无外部依赖） | D:/drone_VINS/t4_v526_out/pit_monthly_report_v526.md |
| 悬停 8.5m 镜像 | mirrored——本夜 NUC 实测可达（07:23/08:28/09:13 三探），四点 md5 镜像落定 nuc2 `~/sitl_sim/t4_mirror_hover/`（审计远端 md5 实测 bag 7e3d56f1+判读文 c2350faa 与 MIRROR_RECORD 一致），STATUS L1104/L1105 在册 | D:/drone_VINS/t4_v526_out/staging_hover/MIRROR_RECORD.md（凭据）+nuc2:~/sitl_sim/t4_mirror_hover/ |
| 池（恒 ≥3） | 3/3——引用闭环 NUC 腿 v2 / judging_draft→verdicts 生成器 / 零图像袋月报口径 | D:/drone_VINS/t4_v526_out/pool_citation_v2.md、pool_draft2verdicts.md、pool_zeroimage_criteria.md |
| W-T2 滚动件 | 到货已补收——补收小节追加进台账（销记=复验 16+三臂今补 12+A1×3=31 袋收讫-待判；遗留 DFS 细扫回放增量留下任） | D:/drone_VINS/t4_v526_out/bag_receipt_ledger_v526.md（补收小节） |

## ③ 保底清单④项对照

1. **①草稿=ok** —— `verdicts_draft_v526.md` 实读 310 行非占位：节一漏发（v5.24 编排完备零执行）/节二未开工（v5.22+v5.23，三重凭据）/节三单线期避让+§6 八条对账表（7 条未达维持+1 条已闭合 L561 在册）；遗留注记：任务书 L15 明文"主会话直出"而本稿系草稿员代编稿待认领、'三节'两解（(B)旧构有 v5.22 L29 在册祖源优势）待主会话裁。
2. **②E4 复核=ok·有果（非阻塞注记）** —— e4_framelevel_recheck_v526.md（e4_frame_recheck_v526.md 为同内容别名件，diff 实测 IDENTICAL，双件 md5 5aed12a1）：prereg 判据定位（md5 fd750919，本审计远端 md5sum 实读同值）、六袋三条件复算 4 立 2 不立、verdicts_v2 §3 箱级对照六袋全一致（正本 md5 4f34d500 本审计实测未变=零触碰）、三件产物与 v55 正源 cmp 逐位一致；局限 §8 七条如实（cv2 像素重放未重跑/U3PG 切点稳健=否新旗标待主会话裁）。
3. **③收货+台账=ok** —— bag_receipt_ledger_v526.md 7 cohort 定义 78/实物 78 全"收讫-待判"零三态（无 T4 预注册收货判据，红线①合规）+7 分册抽读（cohort1-7）均非占位+W-T2 滚动件销记（预热复验 16+三臂今补 12+A1×3=31 袋）+锚袋 A1OBS md5×3 凭据在册（782619d5/06eaaca2/52483365）+臂配对口径 §8；预热对照批 16 定义/15 实物缺 run_WU_E8P_A_* 有补飞链注记（WU_FIX r2+复验 WU2_E8P_A）。
4. **④夜报+可做而未做清单=pending→本件即交付** —— 夜报撰写员随后完成：即本文件+下节清单；审计时点现况"无夜报文件、远端 STATUS 无 T4 收官行"由本件与本次 STATUS 收口行闭合；审计 undone 清单（13 项）即其直接输入（下节全量收录）。

## ④ 《可做而未做清单》（13 项，逐条保留）

1. **开工行补登**：04:20/05:16 两版开工行（含重启声明+HEAD 9d66a9c2+五工具 md5 对账）在 nuc2 `~/sitl_sim/STATUS.md` 现况零残留（grep -e '05:16 | T4' -e '04:20 | T4' 零命中，本审计实跑）——按中文 scp 通道重发"开工补登"行至 HOME+repo 双副本。
2. **本夜 T4 产物系镜像 3090**：verdicts 草稿/E4 复核件/台账+7 分册/池三件/月报全部仅存 Windows 本地（find ~ /tmp -name verdicts_draft_v526.md 零命中；~/sitl_sim/t4_evidence/ 末件仍=10-07 12:52 manifest，ls -lt 实测）——两段式 scp 至 nuc2 `~/sitl_sim/t4_evidence/t4_v526_20261009/`+T4-pool 前缀 commit；草稿至少落 /tmp 供主会话执行域消费。
3. **引用闭环 v2 的 3090 权威重跑**：部署 tools/t4_ref_closure_v2.py（c3d233c5）至 nuc2 `~/catkin_ws/sitl_sim/analysis/` 并 T4-poolRef 前缀 commit 后全扫描重跑，替代带病 f17ebfcd 报告——pool_citation_v2 §4-1 以"ssh nuc2 权限=只读"未做，但同夜 08:24 同凭据成功写入 `~/sitl_sim/t4_mirror_hover/`（本审计远端 md5 实测），"只读"判断与实证矛盾，重验权限后大概率可做。
4. **M3′36 袋收货**：袋路径本审计探面未寻获（ls ~/sitl_sim/t2_results/ | grep -i m3 零命中；find ~ maxdepth4 -type d -iname '*M3*' 仅 M30 假命中）——先向 T2 域索取 M3′战役产物（git dfd36ba）袋路径指针，到手后按台账 §12 口径逐袋 rosbag info 收讫-待判。
5. **DFS δ细扫回放增量收货**：台账 §10 已登记 07:46 实测 record 在写 `~/sitl_sim/t3_results/DFS_*`——T2 细扫窗结束后按七 cohort 同口径补收（find DFS_*/vins_out.bag→rosbag info→收讫-待判）。
6. **其余 75 袋全量 md5 补锚**：仅 A1OBS 3 袋有 md5，其余 6 cohort 以 size+mtime 代记（台账 §9，红线④让路）——下个无 T2 在飞 IO 窗（STATUS 预告行先行）对 78 袋串行 md5sum 补齐。
7. **E4 cv2 像素级重放环节重跑**：E4 §8-1 登记未重跑（以 NUC↔3090 21 件 md5 对账采信）——另开 IO 窗在 3090 串行跑六袋 j3_fb_residual.py（各~1s+SITL_LOCK_FILE 侧锁）补重放面本身的 bitIdentical。
8. **U3PG 切点稳健=否与 U3PH σ触地板两旗标的判读处置**：E4 §5/§8-4/8-5 登记待主会话依预注册处理——归 verdicts 定稿一并裁，须进夜报待办防悬空。
9. **u3_hover_drift.py 补镜像**：MIRROR_RECORD:9 自曝"同目录伴生 u3_hover_drift.py 未搬运"（源在 nuc `/home/uav/catkin_ws/sitl_sim/t1_evidence/v10_2026-10-02/`）——小文件两段式 scp 补齐至 nuc2 `~/sitl_sim/t4_mirror_hover/`。
10. **3090 端 E4 der 件防 /tmp 易失**：/tmp/t4_v526_e4_der 三件（本审计 ls 实测在位）仅 3090 /tmp 单副本——入仓或回拉，防 nuc2 重启丢证据（本地 e4_der 已有回拉件，3090 端无持久副本）。
11. **STATUS 双副本分叉移交**：HOME=1109 行 vs repo 副本=1096 行、git status 显示 M sitl_sim/STATUS.md（本审计 wc -l 实测）——T3 卡点域非 T4 权属，但 T4 自 R3 起的双写防御行须显式交接 T3/主会话裁收敛机制。【夜报撰写员补注：写入时点实测 nuc2 唯一 STATUS=~/sitl_sim/STATUS.md（1109 行），HOME 侧 ~/STATUS.md 不存在——分叉现状与审计时点已有变化，移交本身维持。】
12. **心跳/开工行被吞机制查明移交**：R1/R2 心跳（04:37/04:57）被跨副本覆盖吞行（草稿异常注记 8-②）+本清单第 1 条开工行零残留——覆盖机制【待查明】未闭合，移交主会话/下任以 grep 轮询复核落点。
13. **预热对照批 E8P_A 原始对照位**：16 定义/15 实物，原始 run_WU_E8P_A_* 未飞且 t2_experiments.md grep E8P_A=0 命中（cohort1 分册实测）——是否 T2 补飞归 T2 域裁，T4 侧待收登记维持。

## ⑤ 挂账更新

- **销号 1 项：悬停 8.5m 镜像**（v5.22 期必答欠账后继件，"依赖 NUC .6 上电"阻塞解除）——本夜 NUC 实测可达（07:23/08:28/09:13 三探），四点 md5 镜像落定 nuc2 `~/sitl_sim/t4_mirror_hover/`（本审计远端 md5 实测 bag 7e3d56f1+判读文 c2350faa 与 MIRROR_RECORD 一致），STATUS L1104/L1105 在册。
- **新增挂账：不可解**（本夜无新增可解挂账；遗留悬空项见上节 13 条清单，均带阻塞原因与已试命令）。

## ⑥ 本夜关键凭据

- **HEAD/工具 md5/df**：catkin_ws：pull 前 HEAD=9d66a9c2 → pull RC=0…unchanged（台账已找到，六件全符）。台账正源：docs/t4_verdi…【待确认，ask 原文截断】。df=解析失败，见开工对账员复测。
- **prereg 判据源 md5**：fd750919（本审计远端 md5sum 实读同值）。
- **E4 复核件双 md5**：5aed12a1（正名件/别名件一致，diff IDENTICAL）；verdicts_v2 正本 md5 4f34d500（实测未变=零触碰）。
- **锚袋 A1OBS md5×3**：782619d5 / 06eaaca2 / 52483365（台账 §9 在册）。
- **镜像四点对账**：bag 7e3d56f1（68471710B）+判读文 c2350faa（3918B），凭据 D:/drone_VINS/t4_v526_out/staging_hover/MIRROR_RECORD.md。
- **工具正源**：tools/t4_ref_closure_v2.py=c3d233c5（待部署 3090 重跑，见清单第 3 条）；t4_e4_frame/e4_framelevel_recompute.py=v55（本地资产）。
- **round_result 正源**：7e907b7d（CTX 记忆线索口径）。

---
*本夜报由 T4 夜报撰写员依 ask 材料写成；收口行与末次心跳已按中文 scp 通道写 nuc2 `/home/ghj/sitl_sim/STATUS.md`，并同步本地镜像 D:/drone_VINS/t4_v526_out/STATUS_local_mirror.md（双写防御，防吞行机制未闭合——清单第 12 条）。*
