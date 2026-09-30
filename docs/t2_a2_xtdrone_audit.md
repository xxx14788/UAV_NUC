# T2-A2 XTDrone 五方对照审计（2026-10-01 夜）

> 任务书 v6.0 A2（重定义版）。几何层引 T4-J3 E1/E2 交付（fx/FOV 双侧实测+runbook 勘误），本审计不重做。
> 素材：`~/sitl_sim/upstream/xtdrone/`（github robin-shaun/XTDrone，--depth 1，clone 2.6G/4064 文件，2026-10-01）。
> 上游基线：本仓库 commit `1a069ca`（VINS-Fusion 原仓库态，B-0 战役留存）；gazebo_ros_pkgs 基线=noetic-devel 分支 raw 文件。

## 结论速览

| 审计项 | 结论 | 吸收队列 |
|---|---|---|
| ① SDF 噪声建模对照 | 两栈噪声哲学互斥且各自自洽；XTDrone=零相机噪声+IMU 直连小噪声+参数逐字=SDF 真值；我方=注入相机噪声(LK 奇异修复)+PX4 链 IMU+参数=实测换算 | 无直接吸收；交叉判读入"噪声×离群"账 |
| ② VINS fork 全 diff | 仅 3 处化妆级改动（OpenCV3 旧宏/无守卫订阅/TF frame 名），**零算法改动** | 空队列 |
| ③ gazebo_ros_pkgs 覆盖层 | 与上游 noetic-devel 实质等价（melodic 代基底：tf_prefix 回退+旧 boost 语法+无 PROFILER），**相机时间戳零改动** | 空队列；整库覆盖目的=版本钉死非同步语义修改 |
| ④ vins_transfer.py | 30Hz 重复发布最新位姿+Time.now() 重打时间戳的 python 中转 | 作为 T1 EV 线反面参照（坑⑥实证） |

## ① SDF 噪声建模对照

**相机**：XTDrone `stereo_camera/model.sdf` **无 `<noise>` 块**（零噪声）；我方 `stereo_vins_rig` 双 camera 均注入 gaussian σ=0.004（T2-R3.3：无噪声合成图像弱纹理区梯度严格=0→pyrLK 奇异，C 段悬停 LK 存活率 0.00；注入后 0.51 全段复活）。**两者均自洽**：他们的场景用带纹理 mesh（世界资产自带梯度），我们 obstacles 世界有平色弱纹理区。零相机噪声不是"更干净"而是"更脆"——搬到弱纹理场景即触发我方已实证的 LK 奇异死亡形态。

**IMU**：链路结构不同——XTDrone `imu_gazebo.sdf` 用 gazebo_ros_imu_sensor 插件**直连 VINS**（500Hz，NoiseDensity 型参数）；我方走 gazebo→PX4→mavros 链（上游 250Hz/实测 223Hz，每样本 σ 注入，SITL IMU 频率网格锁账）。

**噪声×离群交叉判读**（核心发现）：

| 栈 | SDF 注入真值 | VINS 参数 | 配对关系 |
|---|---|---|---|
| XTDrone | acc 0.002/gyr 0.0006/RW 2e-5,3e-6 | acc_n 0.002/gyr_n 0.0006/acc_w 0.00002/gyr_w 0.000003 | **逐字一致**（参数=真值的理想配对） |
| 我方 canonical | PX4 链每样本 σ（acc σ≈0.0065 稳态/0.056 init 段, B0 实测） | acc_n 0.2/gyr_n 0.01/acc_w 0.001/gyr_w 0.0001 | 参数=实测换算+机动稳健超设（acc_n 0.1→0.2 = goal 加速 Bas 3.0 爆炸的修复；gyr_w 0.0001 = 上游 Fast-Drone-250 值，10× 超设定案） |

含义：**"参数必须=SDF 真值"只在理想直连链成立**。我方链有 PX4 EKF 中继+闭环激励（goal 加速瞬态），等效噪声≠SDF 标称——这正是 B-0 排除"参数源差错"后 acc_n 需超设的机理印证。XTDrone 的 0.002 若搬进我方链=过度自信（残差被放大归咎状态→Bas 爆炸形态风险）；反向（我方 0.2 搬进其理想链）=过度保守、跟踪迟钝但不死。**两栈参数互不可搬，红线 10（gyr_w 定案）再添一条域证据。**

**config 对照附注**：tracker 参数两栈**完全一致**（max_cnt 150/min_dist 30/F_threshold 1.0/flow_back 1/keyframe_parallax 10/max_solver_time 0.04），唯一差异 freq（他们 80/我们 10，仅发布节流不影响处理）；estimate_td 0+td 0 两栈同——上游默认即此，互相印证我方定案。外参结构不同源（他们 body_T_cam0 z=-0.3 的机体后下置 vs 我们 tic0=[0.12,0.05,-0.02] 前置）——**几何层归 T4-J3，不重做**。

## ② VINS fork 全 diff（vins_estimator/src vs 1a069ca）

仅 5 文件差异，实质 3 处：
1. `featureTracker/feature_tracker.cpp`：`cv::COLOR_GRAY2RGB`→`CV_GRAY2RGB`（OpenCV3 旧宏兼容，无行为差）
2. `rosNodeTest.cpp`：IMU/image1 订阅去 USE_IMU/STEREO 守卫（单二进制双形态，立体模式无行为差）
3. `utility/visualization.cpp`：TF frame `camera`→`camera_link`（rviz 显示兼容）

KITTI 两个 test 文件差异为琐碎。**结论：XTDrone 的 SITL 可用性 100% 来自数据源层（①）与 config 层，VINS 算法零改动。吸收队列为空。**

## ③ gazebo_ros_pkgs 覆盖层

对 `gazebo_ros_{camera,camera_utils,multicamera,triggered_camera}.cpp` 与 noetic-devel 逐文件 diff：
- 全部差异=`boost::placeholders::_1`→`_1`（旧 boost 语法）+ `ENABLE_PROFILER` 块缺失（后加上游特性）+ camera_utils 一处 `tf_prefix_` 空则回退 robot_namespace（melodic 特性）。
- **`sensor_update_time_` 时间戳语义与上游逐行一致，零改动** → "涉相机时间戳即命中同步边界"的审计条件不成立；该覆盖层仅为 melodic 代基底版本钉死（与其 PX4 ≤v1.13/EKF2_AID_MASK 旧名时代自洽，印证移植坑⑤⑦）。

## ④ vins_transfer.py（EV 30Hz 投递参考，43 行）

机制：订阅 `/vins_estimator/camera_pose` → 固定旋转 q=euler(0,-π/2,π/2) 转体系 → `rospy.Rate(30)` 循环**重复发布最新缓存位姿**，每发**重打 `rospy.Time.now()` 时间戳**，投 `<vehicle>/mavros/vision_pose/pose`。

判读：
- **重复发布+重打时间戳** = VINS 停摆/滞后时会以新时间戳发陈旧位姿（EV 投毒形态，实机 EV_CTRL 启用时是已知风险模式）；
- python 中转引入 GC/调度延迟（我方移植坑⑥"EV 节流禁 python 中转"的实证参照）；
- 30Hz 频率点的选择可作为 T1 E-4/EV 线的对照基准（mavlink EV 带宽预算）。
- 帧转换四元数（camera 前视 FLU→PX4 body）与他们的 body_T_cam0 外参链配套——**我方 EV 接线（T1-E4/C0 方向）勿照抄其旋转约定**，外参域已定案（ext0+精确 z）。

## 登记与红线对照

- 来源：github.com/robin-shaun/XTDrone @ master（浅克隆, HEAD=`Sync master from Gitee` 2026-09-29 8079ce0）；license 见仓库 LICENSE（BSD-3-Clause 系，模型文件各自声明，A1 移植时逐模型登记）。
- gitee 镜像仅 md5 对照用（坑⑦），本审计未触发搬运故未做镜像对照。
- 上游三不纪律：本审计纯只读，未 vendor、未改上游、未抄参数。A1 场景移植（另一单元）时按八坑清单执行。
