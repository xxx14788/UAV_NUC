# ③C 语料 MANIFEST（v9.0 终收口 2026-10-18；正源=3090 ~/sitl_sim/c3_corridor_20261013/）

| 层名 | N | 位置（3090 c3_corridor_20261013/ 下） | 聚合 md5 | 判读指针 |
|---|---|---|---|---|
| 13m 原生层 v7.3 | 25 | final_v73_jia | b27dad60e1d6 | final_v73_jia/LAYER_STATS.md（结论 v1.1 附录 B 链） |
| 对照批 13m 对齐+桥接 | 6 | cmp_v62 | 2f0773da1f05 | cmp_v62/cmp_verdict.md（417c448） |
| v9 试录 A 档 | 6 | trial_v9_v82 | e9b28af5e096 | trial_report.md+dashboard_rounds.json |
| v9 试录 B 档 | 6 | trial_v9_v82_B | 64a68edee808 | trial_report.md+dashboard_rounds.json |
| pilot v8.6（修复前） | 6 | pilot_v9_v86 | 591d5953abee | pilot 判读+runaway_root_cause.md |
| 调优批 | 4 | tuning_v82 | 63ff715c7e8a | tune_diag_report.md |
| pilot v8.8（修复+杠杆） | 6 | pilot_v9_v88 | 44cca25ec3a2 | pilot_judge_v88.md/json |
| certify v88 段（C1-16 有效） | 16 | certify_v9_v88 | 0940189339b5 | trial_report.md+dashboard_rounds.json |
| certify v88b 复飞段（R1-9） | 9 | certify_v9_v88b | 84346aaa63db | trial_report.md+dashboard_rounds.json |
| certify v88c 扩样段（S1-23） | 23 | certify_v9_v88c | e1fe5d38cf20 | trial_report.md+geom_*.json |
| N45 三数正源 | - | certify_45_triple.json | 9bf84d3300e6 | 本件=终版判读正源（到位 28/41=68.3%/v2 17/41/综合 10/41=24.4%；NF 7 全量含 C8/C15 勘误；健康域 36 池） |
| dashboard 45r | - | v9_dashboard_45r.json | 33c6172f7f68 | 48 轮×8 列零空格（§2.3 口径） |
| 健康旗全量 | - | health_45_all.json | 663c24b4d212 | 48 袋 init30s dmax（12 旗轮；旗轮零到达） |
| 图集 v2 | - | atlas_v9_v2 | 0b4ca8bb4c93 | verdict.csv（13m 机械/6m 适配双口径）+HERO_note.md+md5.txt |
| 图集 v1（18 轮） | - | atlas_v9_v86 | 41daaa72c150 | md5.txt（v9.0 保留=历史层） |

**保底口径注记**：两态皆达（主线 N45 终版=本表；保底=N25 版 certify_25_triple.json[10-18 定盘，含 C8/C15 勘误后修正版 14/20=70.0%]）。
**v88c 段注记**：S1-23 十月 18 日 03:53-05:15 烧毕（指纹门全绿预检 03:53:35 行）；五分支判定=B1/B2/B4/B5 不触发、B3 无四族外新形态（S3=出生病 odom 域变体注记、S5=导航段绕行过度子型 faildet 拦截）。
**bag 落点**：逐轮 flight.bag 在 ~/sitl_sim/vins_smoke_runs/run_<TAG>_*（48 轮；C17-25 九轮 mavros 死轮已由 R1-9 替补、不入语料）。
**Win 镜像**：t3/2026-10-17_v82_routeA/（结论/清账/图集 v2 判读件）+t1/2026-10-15_③C终局/paper_pack/（16+件）。