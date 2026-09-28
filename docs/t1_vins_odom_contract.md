# T1-V1.1 px4ctrl odom 输入契约差异表：EKF2 odom vs VINS imu_propagate

> 2026-09-28，T1 v5（任务书 2026-09-28_T1_px4ctrl_vision_infra.md V1.1）。
> 结论先行：**px4ctrl 对 VINS imu_propagate 的现有消费契约全部满足，无需改 px4ctrl 参数**；
> 唯一行为差异是"VINS init 完成前零消息"（被 FSM 安全拒绝+起飞重试环吸收）
> 与"init 瞬态速度须 <0.1 m/s"（V1.2 地面轮验证点）。频率 100Hz vs 0.5s 超时余量 50 帧。

## 消费端契约（px4ctrl 实码依据）

px4ctrl 对 odom 的全部消费行为（`src/px4ctrl/src/input.cpp:134-144`）：
- `uav_utils::extract_odometry(pMsg, p, v, q, w)` —— 仅取 pose/twist，**不读 frame_id、不读协方差**
  （`grep -rn covariance src/px4ctrl/src/` 为空）
- `VEL_IN_BODY` 为注释态（input.cpp:136）→ 期望 **world 系线速度**
- 有效性判断 = 收包时刻新鲜度：`(now - rcv_stamp) < msg_timeout.odom(0.5s)`
  （PX4CtrlFSM.cpp:577-580，ctrl_param_sitl.yaml:66-71）
- FSM 门控（PX4CtrlFSM.cpp:73/98）：MANUAL_CTRL→AUTO_HOVER / AUTO_TAKEOFF 均要求
  odom 有效，否则 `Reject ... No odom!`；起飞另有静止门 `odom.v ≤ 0.1 m/s`（非静止拒绝）
- 飞行中 odom 失效（PX4CtrlFSM.cpp:176/220/286）：回 MANUAL_CTRL（降级安全）

## 差异表

| 维度 | EKF2 odom（GPS 代位链 run_ctrl_sitl.launch） | VINS imu_propagate（run_ctrl_sitl_vins.launch） | 对 px4ctrl 影响 |
|---|---|---|---|
| 话题 | /mavros/local_position/odom（~30Hz，frame_id=map，ENU 原点=起飞点） | /vins_estimator/imu_propagate | 仅 remap 差异 |
| 发布时机 | mavros 连接+EKF2 收敛即流（boot 后数十秒） | **solver_flag==NON_LINEAR 才发布**（estimator.cpp:193-213，inputIMU 内逐 IMU 帧发布 latest_P/Q/V）；init 前零消息 | init 前 FSM 拒绝起飞（安全）；04_takeoff.sh v3 重试环吸收，但 90s 预算要求 VINS init <~60s（T2 域） |
| 频率 | ~30Hz（PX4 流默认） | =VINS IMU 输入率 = mavros /mavros/imu/data_raw 率（SITL 实测 ~100Hz，R6 登记项；实机 D435 200Hz） | 0.5s 超时余量：30Hz→15 帧 / 100Hz→50 帧，均宽裕，**不调** |
| 位姿语义 | EKF2 融合位姿（body=机体系） | IMU 体系位姿（launch 注释：body=IMU 系，与机体系近似对齐——D435/SDF 装配决定） | 近似对齐即同构前提（R6 登记装配差异）；姿态控制 yaw 闭环自洽 |
| 速度语义 | world 系 | latest_V，**world 系**（fastPredictIMU 输出） | 满足 VEL_IN_BODY=0 契约 ✓ |
| yaw 参考 | 磁/GPS-course 绝对（GPS 代位链语义） | init 时刻 IMU yaw 冻结，无绝对参考，缓慢漂移 | 控制环/planner 同源自洽，无影响；跨源对齐只能走 vins_to_mavros（vision_pose 喂 EKF2，同实机） |
| 原点 | EKF2 home（起飞点） | VINS init 时刻机体位置（sim=出生点 gazebo(1.01,0.98)，T2b "出生点平移假象"同源） | 静止 init 时两者重合；起飞后再 init 才会分裂（流程上 init 先于起飞，无风险） |
| 协方差 | 填充 | 全零 | 不读，无影响 |
| 时间戳 | fcu 时域（经 timesync） | 传感器（IMU）时域 | px4ctrl 超时判断用 rcv_stamp 本地时刻，不受时域差影响；离线对齐分析须注意（T2b 跨域 dt 教训） |
| 连续性 | EKF 光滑 | 每 IMU 帧预测 + 每次视觉优化重锚（微跳）+ 缓慢漂移（无回环） | 悬停保持质量 V1.3 量化（对照 GPS 代位 ≤0.03m 量级） |
| 丢失含义 | mavros 链路问题（v4 断连自愈已覆盖） | 视觉失效（tracking lost→停发） | 同一门控行为（回 MANUAL_CTRL）；语义不同，排障入口不同 |

## 参数结论（V1.1）

- `msg_timeout.odom/imu/cmd/rc/bat = 0.5s`：100Hz 下 50 帧余量，**保持不动**
- VINS 丢帧窗口（优化线程阻塞时 inputIMU 仍逐帧发布，实际无周期性丢帧窗口）→ 无需调
- 需要的只是**流程顺序**：起栈→VINS init→再触发起飞；run_ctrl_sitl_vins.launch 已按此顺序
  被 start_sitl_vins.sh 编排，V1.2 地面轮验证

## V1.2/V1.3 待验证点（由本表派生）

1. init 完成瞬态：latest_V 首帧速度幅度（FSM 静止门 0.1 m/s 是否被瞬态卡住）
2. 地面静止 60s：imu_propagate vs gazebo 真值漂移（量化 VINS world 原点漂移+漂移率）
3. fsm_state 在 init 前后的稳定性（odom 超时抖动有无）
4. 悬停 30s 位置保持（V1.3，与 T2-W1.2 共享轮次）
