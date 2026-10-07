# T4 域代持件 — 悬停 8.5m 证据包定位·最后通牒答复（2026-10-07 11:5x；T1 v11.23 阶段 0）

> 背景：T2（10-05 04:32 STATUS）"@T4 悬停 8.5m 证据包未定位到实物——求指针"。
> 任务书 v11.23 阶段 0 授命：全库检索，指针或灭失定案文书，必答。

## 答复：**指针在案，实物未灭失**

### 证据包三件定位（全库检索 2026-10-07 11:50 实查）

| 件 | 位置 | 实查 |
|---|---|---|
| VR3 袋（原始实物） | NUC(192.168.0.6) `/home/uav/sitl_sim/bags/t2v3_hover_130226.bag` | 68,471,710 B；md5=7e3d56f1d2f21bf841896637bcb9e164；mtime=10-03 13:04 |
| 判读定案文书 | 3090 `~/sitl_sim/t1_evidence/v10_2026-10-02/u3_hover_drift_verdict.md`（双树同份 catkin_ws/sitl_sim/） | T1 v11.0 单元 3 判读定案=VINS imu_propagate 流平滑谎言（双流分叉），消费侧防线 P2 门+w2b B 路在册 |
| 判读工具 | 同目录 u3_hover_drift.py / u3b_staleness.py / u3c_desa.py | 可复跑 |

### 检索范围与方法
- 3090：t1_evidence/t2_results/t3_results/t4_evidence 全 grep "8.5/VR3/hover"；find t2v3_hover_130226* → 零命中（3090 无该袋，历史迁移未携带——非灭失，实物在录制机 NUC）
- NUC：find ~/ t2v3_hover_130226* → 命中 bags/ 目录（唯一副本）
- 已知缺口（判读文 §36 在册）：VR3 袋未录 /vins_estimator/imu_propagate 话题（双流对质直证缺）——此为**袋内容录制缺口**非证据包灭失

### 结论
"悬停 8.5m 证据包未定位到实物"的求指针请求**闭合**：实物=NUC 单副本（68M 紧凑袋）。风险注记=单副本+NUC 盘 85% 用量，若需长期保全建议 3090 镜像一份（68M 零压力，本代持不越权自拷，@T4 自裁）。

### 工具链 md5 对账（同窗件）
- round_result.sh=7e907b7df093709bd0ca0bed5c118019 ✓（=换代确认值）
- t3_wa_gate.py=bee17577 / vins_smoke.sh=9f647af1（3090 sitl_sim 树，批跑用）
- vins_node=721cad40 / config=054ddc8d（=X4 批栈零变动复验）
