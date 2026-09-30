# P0-C.2：W2 五场景 ulog 层2取证与机制假设表（T1 v8.0 夜1，2026-10-01）

素材：PX4 rootfs log/2026-09-29/ 六 ulg（04_09_48..04_18_17；UTC 名+8=本地，与 w2b 袋 tag
12:11:41 精确配对；w2d 两跑取有效 w2d2）。工具：analysis/t1_w2_ulog_forensics.py + 两轮 pass
（JSON 在 t1_evidence/v8_2026-10-01/w2_ulogs/ + /tmp/pass2/pass3 快照并入本目录）。
口径红线：estimator aid 类 ulog 2Hz 采样≠融合率（C01-D2）；参数=initial_parameters 实值。

## 1. 实锤事实（F 系，全部参数/流级证据）

| # | 事实 | 证据 |
|---|---|---|
| F-A | **EKF2_EV_CTRL=0 六轮全部**——EV 融合从未入环（红线8 PX4 参数侧终实锤）；t2v3_flight.sh 注释"EV 融合闭环"=设计意图，从未激活 | initial_parameters |
| F-B | **EKF2_GPS_CTRL=7**（hpos+vpos+vel 全开）+ SITL GPS fix3/10星/~1Hz（n=82-115/85-116s）——**EKF2 位置源=GPS(+baro)，非视觉** | sensor_gps + params |
| F-C | EKF2 XY 全程贴合 GT（cm 级，estimator_local_position ≈ groundtruth：如 w2c ekf2 y[−0.11,8.07] vs gt y[−0.19,7.99]）——EKF2/GPS 不是失控方 | 双流范围对照 |
| F-D | **EKF2 z 通道背离 GT**：w2a ekf2 z span 3.8m vs gt 1.9m；w2e 4.7 vs 1.0（z 源=baro 为主 EKF2_HGT_REF=1+GPS vpos）——z 环嫌疑 | 同上 |
| F-E | **EV 创新晚段爆表被拒**：w2c ev_hpos 峰 48.4（t=73.1s 起，飞行止于 79.2s）；w2e ev_vpos 峰 156.6（74.5s 起）=VINS odometry 在飞行尾段背离 GPS-真值估计，EKF2 门控正确拒收 | estimator_innovation_test_ratios 时间线 |
| F-G | 飞行窗 offboard(nav14) **pos_en=vel_en=att_en=1 全使能**（w2b 中段 10.4-24.5s pos_en=0 例外）——PX4 全位置级联在环迹象，与"px4ctrl 姿态 offboard"架构预期相悖 | vehicle_control_mode 分段 |
| F-H | 链路率实值：att_sp 20Hz(dt48ms)｜traj_sp 5Hz(仅 yaw 字段非空)｜lp_sp 10Hz｜local_position 输出 125Hz(dt8ms)；EKF2_PREDICT_US=10000（10ms 网格） | 各消息 dt 统计 |
| F-I | MPC 面：MPC_XY_VEL_MAX=12.0（**上游 12m/s 档，非巡飞调低值**）、MPC_XY_P=0.95、TILTMAX=45°、THR_HOVER=0.5；EKF2_EV_QMIN=0/EV_DELAY=0（EV 参数全默认未调） | params |

## 2. 层2 机制假设表（W2 失控形态的层2解释候选）

| # | 机制 | 与 F 系的一致性 | 可证伪判据（下一探针） | 状态 |
|---|---|---|---|---|
| L2-H1 | **EKF2-z 发散驱动 z/俯仰失控**：baro/GPS 高度混融 z 背离(F-D)→若位置级联在环(F-G)则 z 环追错高度→GT z 振荡（w2a 悬停 z 冲 1.9/w2b 3.77 振荡形态吻合） | F-D+F-G+F-B | w2b 袋（3.6G 在库）内 /mavros/local_position/odom 的 z 时间线 vs GT z 逐秒对齐；发散起点应在 GT z 失常之前 | 🟡最强 |
| L2-H2 | **VINS 直供流(层1)经 px4ctrl 驱动**：px4ctrl 位置环@223Hz 消费 imu_propagate（VINS 尾段发散 F-E）→姿态/推力失控 | F-E+t2v3_flight.sh 链路（run_ctrl 直供） | w2b 袋 imu_propagate 流健康性（T2 已录 ATE 53.7m=VINS 巨散）；但需解释 EKF2(GPS)健康为何 GT 仍失控——px4ctrl 姿态模式在环时 PX4 位置级联不应参与(F-G 矛盾点) | 🟡与H1复合 |
| L2-H3 | **双控制主体分段混跑**：w2b pos_en 翻转段=px4ctrl 姿态模式与 PX4 位置 offboard 交替，模式抖动放大瞬态 | F-G w2b 段 | ulg 内 vehicle_command/offboard_control_mode 变更序列与 pos_en 翻转时刻对齐；/mavros/setpoint_raw 双话题率（W2 袋未录——需 E-4 录制清单补） | ⬜ |
| L2-H4 | EV 供给率带外（10Hz vo 流，F-H）本身致 EKF2 失稳 | 被 F-A 直接杀死（EV_CTRL=0，融合未跑） | — | ❌排除 |
| L2-H5 | 223Hz IMU 供给致 EKF2 失稳 | EKF2_PREDICT_US=10ms=100Hz 网格(F-H)，IMU 223Hz 实为 2.2× 过供给但 XY 全程健康(F-C) | E-4 复现对（223vs125 同 EV_CTRL=15）仍值得做——供 E-4 启用域设计 | 🟡削弱（层2独立性降） |

## 3. 对 E-4 设计（P0-C.3）的强制输入

1. **SITL 有 GPS 且 EKF2 一直融 GPS（F-B）**——E-4 启用 EV_CTRL=15 将成 GPS×EV 并融竞争；
   设计必须显式处置（关 GPS_CTRL 或声明并融实验面），且触碰"纯视觉架构红线"的边界须用户可见。
2. EV_CTRL=0 全史实锤 ⟹ **"223Hz EKF2-EV 失稳"原命题对象不存在**；E-4 复现对的真实问题改写为
   "EV 启用域下 GPS 并融/延迟/协方差零(EVP_NOISE 下限)三面的稳定性刻画"。
3. VINS 尾段发散-被拒（F-E）与层1 已修域重叠——E-4 供给面须钉死 gyr_w 修复栈（5adf593 后）。
4. 录制清单缺口（W2 袋无 setpoint_raw 双话题、无 /mavros/imu/data）→ E-4 轮录制清单补齐
   （已向 T2/T3 发过 imu/data 请求，setpoint_raw 本条再登记一次）。

## 4. 剩余判别工作（挂 E-4 前夜窗口）

- w2b 袋 /mavros/local_position/odom z 时间线 vs GT z（L2-H1 判据，0锁袋分析）；
- PX4 v1.14 vehicle_control_mode flag 语义源码核对（offboard 姿态模式下 pos_en=1 是否
  表示"级联在环"还是"能力位"——L2-H1/H2 归属的开关性判别，0锁源码读）；
- ulog 内 vehicle_command/offboard_control_mode 序列提取（L2-H3，0锁）。
