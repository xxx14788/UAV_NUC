# T1-V1.1 px4ctrl odom 输入契约差异表：EKF2 odom vs VINS imu_propagate

> 2026-09-28，T1 v5（任务书 2026-09-28_T1_px4ctrl_vision_infra.md V1.1）。
> 本版为双 T1 会话产物合并（源码级分析 + bag 实证）。
> 实证 bag：`~/sitl_sim/bags/t2w5_p1_092335.bag`（09-28 晨，152s，511 提频后链路）。
> 源码：VINS-Fusion `src/VINS-Fusion/vins_estimator/src/{utility/visualization.cpp,estimator/estimator.cpp}`；
> px4ctrl `src/px4ctrl/src/{input.cpp,PX4CtrlFSM.cpp}`。
>
> 结论先行：**px4ctrl 对 VINS imu_propagate 的现有消费契约全部满足，无需改 px4ctrl 参数**；
> 两个真差异均属流程适配（非代码改动）：VINS init 前零发布（FSM 安全拒绝+起飞重试环吸收）
> 与位姿参考点 IMU vs base_link 差 2cm（小于控制阈值，仅真值对比工具需登记）。

## 消费端契约（px4ctrl 实码依据）

- `input.cpp:134-144`：`uav_utils::extract_odometry` 仅取 pose/twist——**不读 frame_id、
  不读协方差**（`grep -rn covariance src/px4ctrl/src/` 零命中）
- `input.cpp:136` `VEL_IN_BODY` 注释态 → 期望 **world 系线速度**
- 有效性 = 收包新鲜度：`(now - rcv_stamp) < msg_timeout.odom(0.5s)`（PX4CtrlFSM.cpp:577-580）
- FSM 门控（PX4CtrlFSM.cpp:73/98）：MANUAL_CTRL→AUTO_HOVER / AUTO_TAKEOFF 均要求
  odom 有效否则 `Reject ... No odom!`；起飞另有静止门 `odom.v ≤ 0.1 m/s`
- 飞行中 odom 失效（:176/220/286）：回 MANUAL_CTRL（降级安全）
- **IMU 桥独立**：px4ctrl 姿态桥消费 `/mavros/imu/data`（ATT_QUATERNION 流 ~50Hz，
  与 VINS 的 data_raw/511 无关——拓扑详见 t1_evidence/v4_imu_freq_assessment.md）

## 差异表

| 维度 | EKF2 odom（/mavros/local_position/odom，GPS 代位链） | VINS imu_propagate（run_ctrl_sitl_vins.launch） | 对 px4ctrl 影响 |
|---|---|---|---|
| 发布机制 | mavros local_position 插件（PX4 ODOMETRY 流，默认 30Hz；bag 实测 30.1Hz） | estimator.cpp:212 `inputIMU()` 内逐 IMU 帧（solver_flag==NON_LINEAR 时 `fastPredictIMU` 后立即发布） | 无 |
| 首条可用 | mavros connected 即有（boot 后 ~3s） | **VINS nonlinear init 完成前一条不发** | init 窗内 FSM 拒绝自动态（安全）；04_takeoff v3 长窗重掷兼容；T2 preflight 门控已覆盖 |
| 频率 | 30.1Hz（bag 实测 4579/152s） | =IMU 流频率：**bag 实测 125.5Hz**（19078/152s，与 imu/data_raw 同条数=逐帧实锤）；无 511 时受 mavlink 节拍顶（W2 钉 50Hz） | 0.5s 超时余量 15 帧→60+ 帧，超时抖动风险降低，**不调参数** |
| frame_id / child | `map` / `base_link`（bag 实测） | `world` / `world`（visualization.cpp 源码；px4ctrl 不读） | 无功能影响；RVIZ/tf 消费者需感知 |
| 位姿参考点 | EKF2 机体位置（≈base_link） | VINS body=IMU 系原点 = iris `/imu_link`（模型安装 (0,0.02,0)，base_link 左 2cm） | ≤2cm，与 hover 判据 0.03m 同量级；hover 目标取自同源 odom，自消 |
| 原点/yaw | EKF2 local 系（boot 定位点，磁/GPS-course 绝对 yaw） | VINS world=init 时机体位姿：原点=init 位置（sim=出生点 gazebo(1.01,0.98)，T2b"出生点平移假象"同源），yaw=init 时机头向（无绝对参考，慢漂） | 全链同用 VINS 系自洽；与 ENU/真值对齐需 T2b U9 配方 |
| twist.linear | EKF2 速度（ENU） | latest_V（VINS world 系） | 语义一致（各自世界系）✓（VEL_IN_BODY=0 契约满足） |
| twist.angular | 填充（非零，bag 实测） | **恒零**（pubLatestOdometry 只赋 linear） | px4ctrl 不消费 odom 角速度（`odom_data.w` 全源码零命中）→ 无影响 |
| 协方差 | 全零（mavros local_position 不填充，bag 实测） | 全零（不赋值） | 两侧等价；px4ctrl 本就不读 |
| header.stamp 域 | FCU 时钟经 timesync（U6 域配方下=SIM 域） | IMU msg 戳原样透传 | px4ctrl 超时判定用 rcv_stamp（接收时刻）→ 无影响；离线对齐须注意（T2b 跨域 dt 教训） |
| 静止漂移 | EKF2 有 GPS/baro 锚，近零 | 纯视觉递推，静止亦有慢漂 | V1.2 地面 60s 实测量化 |
| 连续性 | EKF 光滑 | 每 IMU 帧预测 + 每次视觉优化重锚（微跳）+ 慢漂（无回环） | 悬停保持 V1.3 量化（对照 GPS 代位 ≤0.03m 量级） |
| 丢失含义 | mavros 链路问题（v4 断连自愈覆盖） | 视觉失效（tracking lost→停发） | 同一门控降级（回 MANUAL_CTRL）；排障入口不同 |

## 参数结论（V1.1）

1. `msg_timeout/odom=0.5` 在 125Hz 下余量 60+ 帧，**不调**；init 窗是零发布不是超时，
   调大 timeout 无意义且有害（掩盖真断链）
2. 需要的只是**流程顺序**：起栈→VINS init→再触发起飞（start_sitl_vins 编排已如此）
3. 参考点 2cm 差异：真值对比类工具登记（map_truth_diff / analyze_flight 对齐段），不动参数

## V1.2/V1.3 实测结果（已回填,2026-09-28 晚）

见 `sitl_sim/t1_evidence/v1_flight_results.md`：悬停保持中位 0.005m（PASS,优于
0.03m 基线与 EKF2 参照 0.050m）；静态漂移 2-3cm/45s；imu_propagate 125Hz 逐帧零断流
（maxgap 12ms）；出生点平移假象(+1.01,+0.98)复现。msg_timeout 不调的结论获实测支持。

## V1.2 待补点（剩余）

1. init 完成瞬态：latest_V 首帧速度幅度（FSM 静止门 0.1 m/s 是否被瞬态卡住）
2. 地面静止 60s：imu_propagate vs gazebo 真值漂移量化（漂移率）
3. fsm_state 在 init 前后稳定性（odom 超时抖动有无）
4. 悬停 30s 位置保持（V1.3，与 T2-W1.2 共享轮次）
