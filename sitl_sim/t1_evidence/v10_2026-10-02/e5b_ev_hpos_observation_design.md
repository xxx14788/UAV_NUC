# E-5b 观测臂设计稿 v1 — ev_hpos 活窗熄灭的滚动观测计划（T1 v10.4 深挖池⑥）
（0 锁；2026-10-03 01:3x；背景=C-7 翻案在册：ev_hpos 曾激活 22s（9.3-31.4s，cs_ev_pos 7.78%）被 33.2s VINS 爆走毒化熄灭——"熄灭"是**结果面**，观测目标=随 VINS 健康恢复量化其延长）

## 1. 观测命题（可证伪式预注册）

- P1：EV 融合活窗长度 = odometry 流存活面的 EKF2 层镜像（毒化/流截断→EV 超时熄灭；A.4 §5 流截断事件对齐预期：ev 熄灭时刻 ≈ odom 流死时刻 + EV_MAX_INTERVAL）
- P2：E-5a L-odom 臂上线后 cs_ev_vel 从恒 0 转 activate（J2 分臂预期已在 u5_J1_J6_prereg 注册——本臂只观测不判 PASS/FAIL，判据归 J2）
- P3：VINS 健康轮（零 fail 零 reboot）⟹ cs_ev_pos 激活覆盖率 ≥ 对齐后全程（健康基线带首测即立）

## 2. 度量集（每 ulog 轮提取，无新埋点——全部复用现有 ulog 通道）

| 度量 | 通道/算法 | 说明 |
|---|---|---|
| ev_hpos innov 健康 | med/p95（有限样本占比） | C-7 已验工具路径（31032 样本口径） |
| cs_ev_pos 激活覆盖率 | 置位时长/对齐后时长 | 对齐=tilt_align 后 |
| 激活窗分段 | [t_start, t_end] 列表 | 熄灭事件=段尾 |
| vo 输入面 | n / position_variance 非 0 占比 / velocity NaN frac | NaN frac=1 基线（E-5a 前时代锚） |
| 熄灭-事件对齐 | 段尾时刻 vs VINS 事故时刻（T2diag/[T2fail]/A.4 流截断表） | P1 判定核心 |

## 3. 滚动计划与消费面

- 素材=未来一切产 ulog 轮（E-4 复排/X 线/T2 验证轮）；**随轮顺手提取，不占锁不排窗**——挂在 round_result 判读流水（T3 域工具链同源）。
- 汇总=滚动表 ev_hpos_obs.md（v10 目录）：每轮一行，5 轮后出健康基线带与 P1 对齐率。
- 消费：①X7 sim2real 声明素材（EV 融合健康=架构层指标）②T2 健康恢复验证的第三独立面（VINS 自报/袋级真值/EKF2 融合行为三面互证）③J2 判读的背景带。

## 4. 边界（防越权）
- 本臂纯观测：不改参数（EV_CTRL 维持现值）、不预设修复；E-5a 判据归 u5 预注册；EV_CTRL 启用与否的架构裁定归用户（悬案池"实机 EV 启用（暂定不启用）"维持）。
- ulog 读取纪律：PX4-Autopilot/build 域（T3 已勘误路径）+ 只读。
