# E-4 复排 J1-J6 判据预注册（T1 v10.1 单元 5a；2026-10-02 02:2x 锁定）
**纪律**：数据到手后只对号入座，禁止事后改阈/补判据（红线"判据未预注册不出 PASS/FAIL"）。
**排飞条件**：优先排 T2-R2F 验证轮之后（R2F 解除爬升初段载爆减少废轮）；窗紧可先行，按 R3 判别口径管理（场景载爆只登记不停跑；连续 2 轮 EKF2 域异常才触发）。
**栈**：285278cc（一切轮前核 vins_node md5，红线 24）。**剖面**：悬停 60s（w2a 型）。**轮序**：G-off×D10 先。

## 0. 矩阵（面四并入后的最小充分集）
| 面 | 态 | 实现 |
|---|---|---|
| 一 GPS | G-on=GPS_CTRL 7 / G-off=0 | rcS 注入（e4_wheel.sh v2） |
| 二 EV 密度 | D10 现状 / D30 / D60 | throttle 侧实现（禁动 VINS 侧发布率） |
| 三 IMU | I223 现状 / I125 | 仅域对照 |
| **四 EV 链形态（E-5a 并入，单元 4 结论）** | **L-pose=vision_pose 现状 / L-odom=odometry/out 含 twist** | **vins_to_mavros 发布段 launch 开关双臂** |
主矩阵 {G-on,G-off}×{D10,D30}×{I223}=4 + G-off×D60×I223 + G-off×D30×I125 + **E-5a 臂 G-off×D10×L-odom×I223（vs 同格 L-pose 基线配对）** = 7 轮 + 每态悬停回归。
E-5a 改动=launch 开关（不破坏现链），实现过 STATUS 预告 15min 异议窗。

## 1. 判据（阈值与计算口径，数据窗=起飞后 15% 截尾至袋尾）
| # | 判据 | PASS 阈值 | 计算口径（字段/源） |
|---|---|---|---|
| **J1 稳定性主判** | GT 悬停保持≤1m 无振荡 + EKF2 XY 创新比门内 | max|GT_xy−med|≤1.0m 且 ev_hpos ratio p95<1.0 | bag /gazebo/model_states（GT）；estimator_innovation_test_ratios 或 e4_judge J1_xy_drift+ev ratio |
| **J2 EV 融合活性** | ev_hpos/ev_vpos innov 非零且门内；**分臂活性预注册**：L-pose 臂 cs_ev_vel 置位率**预期=0**（链无速度，翻案凭据）；L-odom 臂 cs_ev_vel>0 且 ev_hvel innov 有限 | n_active>0 ∧ ratio p95<1（hpos/vpos 各列）；L-odom 加 cs_ev_vel frac>0.01 | estimator_innovations + estimator_status_flags.cs_ev_pos/cs_ev_vel（翻案后正确口径） |
| **J3 拒收率（健康指标非缺陷）** | ev ratio>1 计数与 VINS 健康度分列上报 | 信息项无门 | e4_judge J2_J3_ev ratio_gt1 + simvins T2diag 心跳 |
| **J4 对照不变量** | px4ctrl 直供链全程健康 | imu_propagate 悬停保持≤0.15m（V1 基线级） | bag /vins_estimator/imu_propagate 窗内 max|p−med| |
| **J5 z 通道分列** | EKF2 z vs GT z 紧性 | rel p50≤0.1m 级（E4 首窗 0.074 同阶）；G-on/G-off 分列 | e4_judge J5_z_rel |
| **J6 跳变四型对号（U2 产出并入，A.4 重估数据源）** | Bgs 领先/平静**双分流计数**：H-S1 型=事件前 1 拍 Bgs≥10× 基线 med 的 dP>0.02 事件数；H-S2 型=Bgs 平静的 dP>0.02 事件数 | 信息项（喂 A.4 重估三分支，见 u2_jump_mechanism_hypotheses.md §3） | simvins [E2uls]+[T2diag] 合并时间轴（t1_u2_dissect.py 同款解析） |

## 2. 预注册对号表（R2F 后复排预期）
- 若 R2F 已解除 input-domain 载爆：E-4 复排轮 J1 可 PASS 悬停 60s（首窗 2/2 爆的反证）；J6 双计数应大幅低于 E4 首窗（1 枚/轮 → 0）
- 若仍爆：按 R3 判别口径登记不停跑（连续 2 轮 EKF2 域异常才触发停）；J6 计数喂 A.4 分支 4（两型均不降→R2F 未命中回 T2）
- E-5a 臂 J2 若 cs_ev_vel 仍=0：odometry/out 链未生效（mavros 侧 vision 源选择问题），登记链排查不动矩阵

## 3. τ_pipe 通道 B（任务书 C-3）
复排首袋=vins_smoke:145 自带 debugPx4ctrl → 袋到位即跑 tau_pipe 消费器（在库，自测过）。

---
## 4. 补注（v10.4 单元 4 落笔；2026-10-03 02:1x；依用户 10-02 夜裁定②）

- **VINS 域事故轮按受控/未受控分层标注**（受控=cost 门在场且触发于爆窗起点±5s 内、reboot 后 odometry 恢复输出——判据口径同 T3 prereg v1.1 §2.6-g L1b）：受控性只作 J 判读的**分项注记列**（J-pass-controlled / J-fail-controlled / J-fail-uncontrolled 三态计数），**不改 J1-J6 判据本身**。
- 依据：T2 单元 2 改判链（A3"恢复"不成立案）与 T3 v8.7 受控识别器在库（wa_gate f0905154）；判读时直接消费其 PASS-CONTROLLED 计数路径，不重复实现。
- 栈号位（C-10）：本节不锁栈；复排执行时按 T2 栈定稿通告在 §0 登记（现行候选=lib d43504d9+node 4701bd3a，配对实验在测未定稿）。

- 栈号登记（2026-10-03 03:2x）：依 T2 03:20 栈定稿通告，E-4 复排在用栈=**lib d43504d9 + vins_node 4701bd3a**（fixface 栈，双件存档 stack_archive/）；本行=C-10 关账标记。
