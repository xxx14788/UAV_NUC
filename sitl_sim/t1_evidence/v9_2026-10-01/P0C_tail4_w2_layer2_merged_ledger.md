# P0-C 尾件4 — W2 层2 假设表修订版（合并单一账；2026-10-01 T1）

> 任务书 v9.0 等待池①尾件4。合并三源：v8.1 P0C2_w2_layer2_forensics.md §5 勘误 + v7 E1-E1 考古 + 尾件2 v1.17 OFFBOARD 位域决定论（P0C_tail2_v117_control_mode_flags.md）。本表为层2 假设终账，替代 v8 册散页。

## 假设状态终表

| # | 假设 | 状态 | 定案依据 |
|---|---|---|---|
| L2-H1 | EKF2-z 发散驱动 z/俯仰失控（baro/GPS 混融 z 背离→级联追错） | **主候选维持，判据面改写** | 原 w2b 袋逐秒对齐判据部分可保留；但 v7 考古"GT-local 恒差=出生点常值"口径冲突已由尾件1 方法约束（范围跨度法不适用，须时间线级创新法）登记；**位域证据加入后其 F-G 前提判别已可机械化**（见下） |
| L2-H2 | VINS 直供流经 px4ctrl 驱动层2 | **作废（维持）** | 前提"px4ctrl 在环"错误（v7 E1-E1 考古：w2* 分支 flyer 直控 PX4 位置环，px4ctrl 未启动）；与 v8 §5 勘误一致 |
| L2-H3 | 双控制主体分段混跑（pos_en 翻转段模式抖动） | **判据解锁（本件核心增量）** | 尾件3 已提取 ulog offboard_control_mode/vehicle_command 序列（X3_offline_w2.json transitions：w2a/c/e 单段、w2b 三段、w2d1 无 offboard、w2d2 单段）；**尾件2 位域决定论给出解读律**：pos_en=1 ⇔ offboard_control_mode.position 位=1（级联在环），宽口径 multicopter_position_control_enabled 不可作证据。w2b 三段 offboard=存在模式切换段，L2-H3 的"分段混跑"形态在位域层面可逐段核 |
| L2-H4 | EV 供给率带外致失稳 | **排除（维持+加码）** | EV_CTRL=0 全史（红线16 参数级）；E-4 首窗进一步实证 EV_CTRL=15 启用时 ev_vpos 融合健康（ratio p50=0.32 门内零超），反向加码 |
| L2-H5 | 223Hz IMU 供给致 EKF2 失稳 | **削弱（维持）+E-4 对照臂挂账** | EKF2 XY 全程 cm 级贴 GT（F-C）；E-4 矩阵 I223/I125 档保留为对照臂（设计 §1 面三），飞行域复排时执行 |

## 尾件2 位域决定论对层2 判读的操作化律（新，本件交付）

1. **判"级联在环"唯一口径** = ulog `offboard_control_mode.position` 位（或 `vehicle_control_mode.flag_control_position_enabled` 严格字段）；`flag_multicopter_position_control_enabled` 为宽口径并集（含 altitude/climb_rate），禁作级联证据。
2. **判"发的是什么"与"按什么解释"分离**：setpoint 内容（attitude vs position 消息）不决定控制模式；位域才决定。w2b 的 setpoint_raw 双话题结构性静默（local 无发布者，21:04 T2 C-5 包实证）与此自洽：attitude 流+position 位亦可解释。
3. **L2-H3 判读路径**：w2b 三段 offboard 段逐段读 position 位 → 全 1=级联常在环（H3 弱化为"单主体多段切换"）；翻转段=H3 实锤形态。
4. **L2-H1 残余路径**：位域判级联在环为真后，z 背离→z 环追错才成立；z 时间线判别待尾件1 创新法（深推理件，模型升级条款适用）。

## 悬案移交

- L2-H1 尾件1（w2b z 判别）：**模型升级条款件**（flash 不硬啃），升级路径=GLM5.3 会话续做/@用户换模型/捎带 5.3 线三选一（v9.0 头部条款）。
- 层2 判读素材完备度：位域证据已齐（尾件2+3）+模式序列已齐+袋在库——w2b 层2 判读可在升级件完成前先行出 70%（L2-H3 判读路径无需尾件1）。
