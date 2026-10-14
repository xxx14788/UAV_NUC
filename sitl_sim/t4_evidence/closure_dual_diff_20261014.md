# 引用闭环 v2 双侧实例差集表（20261014，全域收尾册单元 2.2 凭据）

> 承 T4 v5.37 B2/B3（nuc_only 41 逐件对账中"应同步候选 2[1.6GB+30MB]登记不搬运随窗"——本册随窗执行）。
> 双侧实例：3090=`t4_evidence/t4_ref_closure_20261014.md`（v2 工具，19:09 落盘，含 ssh-NUC 探针腿）；旧机=`t4_evidence/t4_ref_closure_20261014_nucside.md`（v2 工具 --no-nuc，源=旧机 ~/sitl_sim/t4_evidence_nucside/，md5 7fefbae1 双端一致）。旧机 repo 同步=89dc2a1→abd1032（pull 后跑，工作树两 untracked 注记不动）。

## 双侧汇总对读

| 侧 | refs_total | present | missing | missing_both | nuc_only | nuc_skip |
|---|---|---|---|---|---|---|
| 3090 | 274 | 202 | 72 | 58 | 14 | 0 |
| 旧机 | 275 | 202 | 73 | 0 | 0 | 73（--no-nuc 语义=缺失不探针） |

refs_total 差 1=`t2v3_ground_205302`（bag stem token，stem 学习自本机 ~/sitl_sim bag inventory——旧机 bags/ 有该袋故学到；3090 扫描时[搬运前]无）。

## present 集合差集（199 共同 +3/+3）

### 旧机-only present（3）——搬运时序注记后实为 1 项衍生 stem
| token | 处置 |
|---|---|
| `t2v3_ground_205302.bag` | **本册 2.1 已搬运闭环**（3090 报告=搬运前快照[19:09<19:18]；现位 ~/sitl_sim/bags/，md5 664e881e 双端一致） |
| `v1_ground_salvage_211520.bag` | **本册 2.1 已搬运闭环**（同上时序；现位 ~/catkin_ws/sitl_sim/t1_evidence/v1_2026-09-28/，md5 28fe5193 双端一致） |
| `t2v3_ground_205302`（stem） | 衍生 token：随 .bag 在位后 3090 inventory 亦可学到，无独立载体，无需搬运 |

### 3090-only present（3）——单侧载体在位形态（非缺失）
| token | 归类 |
|---|---|
| `~/sitl_sim/plans_T4_v5.22.md` | T4 域任务书文件，3090 专属域，旧机从未部署（载体单侧在位=闭环态） |
| `~/sitl_sim/plans_T4_v5.37.md` | 同上 |
| `~/sitl_sim/vins_smoke_runs/run_T2BL5_203404/j0_decomp.json` | 3090 运行产物域（vins_smoke_runs 历史轮产物） |

## 差集裁定

- **新缺失项=0**：差集 6 项全部为单侧载体在位（2 项经 2.1 搬运后已闭环+1 衍生 stem+3 项 3090 域载体）——按既有五族口径（预期缺失/已删凭据销号/Windows[单侧]载体/typo 冻结/系统路径收窄）归类均为"登记不修"族的零新增确认，无预期族新条目。
- 本表不产 PASS/FAIL 判读，不触发修复动作（v2 工具语义沿用）。
