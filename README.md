# UAV_NUC — Fast-Drone-250 复现工作区

本仓库 = NUC 机载电脑（Ubuntu 20.04.6 + ROS Noetic + Gazebo Classic 11）上的 `~/catkin_ws`，
基于 [ZJU-FAST-Lab/Fast-Drone-250](https://github.com/ZJU-FAST-Lab/Fast-Drone-250) 复现。
仓库根即 catkin 工作空间根（内含 `src/`），clone 后 `catkin_make` 即可编译（build/devel 已 gitignore）。

> **多人/多 agent 协作仓库**：动手前先读 [CONTRIBUTING.md](CONTRIBUTING.md)（凭据安全、提交与推送纪律）。
> **项目规范**：[docs/workflow.md](docs/workflow.md)（工作流与验证门槛）· [docs/coding-style.md](docs/coding-style.md)（代码与配置风格）· [docs/flight_log.md](docs/flight_log.md)（飞行/仿真实验记录）。

## 1. NUC 整体布局（本仓库只是其中一块）

| 路径 | 内容 |
|---|---|
| `~/catkin_ws`（本仓库） | Fast-Drone-250 实机栈：planner / px4ctrl / VINS-Fusion / realsense-ros / vins_to_mavros / utils / launch + `sitl_sim/`（SITL 流程脚本与环境快照） |
| `~/sim_ws` | EGO-Planner 官方纯仿真（planner 全套 + uav_simulator + utils），入口 `plan_manage/launch/single_run_in_sim.launch` |
| `~/PX4-Autopilot` | PX4 v1.17.0，`px4_sitl_default` 已编译；gazebo-classic 模型含 `iris_depth_camera` |
| `~/sitl_sim` | SITL 运行目录：bags/ 存飞行记录；脚本已入库到本仓库 `sitl_sim/`（以仓库为准） |

## 2. 相对上游 Fast-Drone-250 的结构差异

- 上游 `src/realflight_modules/{px4ctrl, realsense-ros, VINS-Fusion}` 拍平到本仓库 `src/` 顶层
- 上游 `src/uav_simulator` 不在本仓库（仿真器单独放在 `~/sim_ws`）
- 新增 `src/vins_to_mavros`：把 VINS 里程计转发给 mavros（起飞阶段为 EKF2 提供外部位姿）
- 新增 `src/launch/` 系统级入口（见 §3）
- 新增 `sitl_sim/`：SITL 全流程脚本 + 环境快照（见 §4）
- `VINS-Fusion/support_files/paper/` 下的 VINS-Mono pdf 文件名含冒号（Windows 无法检出），已改为 `-` 连接（2026-09-26）

## 3. 实机链路（2026-06 已按实际硬件标定）

入口 `src/launch/full_vins_px4.launch`，按序拉起：

1. mavros（`fcu_url=/dev/pixhawk:921600`）
2. 启动后 5s / 8s 用 `mavcmd 511` 把 HIGHRES_IMU、ATTITUDE_QUATERNION 各设为 200Hz
3. RealSense D435（`VINS-Fusion/config/realsense_d435/rs_camera_vins.launch`）
4. VINS-Fusion `vins_estimator`（`realsense_stereo_imu_config.yaml`，话题前缀 `/vins_estimator`）
5. `vins_to_mavros` 位姿转发

代码级改动（相对上游 HEAD，2026-09-26 diff 校验，共 4 处修改 + 2 个新增）：

| 文件 | 改动 |
|---|---|
| `planner/plan_env/src/grid_map.cpp` | 外参话题 `/vins_fusion/extrinsic` → `/vins_estimator/extrinsic` |
| `planner/plan_manage/launch/advanced_param_exp.xml` | 增加 extrinsic remap；`obstacles_inflation` 0.299 → 0.337（曾遗留 gdb `launch-prefix`，2026-09-26 已清理） |
| `planner/plan_manage/launch/default.rviz` | 可视化话题 → `/vins_estimator/*` |
| `planner/plan_manage/launch/single_run_in_exp.launch` | 地图 100×50 → 20×20；odom → `/vins_estimator/imu_propagate`；换真实 D435 内参（fx≈387.51, cx≈323.50, cy≈232.69）；`max_vel` 0.5 → 0.75 |
| `px4ctrl/launch/run_ctrl_sitl.launch`（新增） | SITL 版控制：`~odom` → `/mavros/local_position/odom`（EKF2），`~cmd` ← `/position_cmd`；node 名必须保持 `px4ctrl` |
| `px4ctrl/config/ctrl_param_sitl.yaml`（新增） | SITL 控制参数，不影响真机 `ctrl_param.yaml` |
| `src/px4ctrl/src/`（T1-W1 修改 5 文件） | FCU/SITL 重启韧性：主循环 ros::Rate→WallRate（免疫 /clock 归零倒跳导致的主循环分钟级冻结，gdb 栈+解冻时点+240s 心跳零间隙三重实证）；OFFBOARD 拒绝时 AUTO_TAKEOFF 回退+看门狗；/mavros/state 流断连自愈重置；新增 /debugPx4ctrl/fsm_state 1Hz 自监视。armed 态行为零改动；实机 use_sim_time=false 下 WallRate 与原行为完全一致 |
| `src/depth_caminfo_relay/`（T1-W4 新增包） | depth camera_info 合成转发（根因：openni_kinect 的 DepthInfoConnect 不激活传感器，仅订阅 camera_info 时零消息）；K/D 与 rgb 同源逐位一致 |
| `plan_manage/launch/run_planner_sitl.launch`（T1-W4 修改） | 挂 depth_caminfo_relay 节点（depth/rgb 内参话题参数化） |
| `sitl_sim/`（T1-W5/W6 新增+修改） | sitl_smoke.sh 一键冒烟（到位/避障/100Hz/自动disarm 四指标）；sitl_lock.sh 三任务运行时锁；status_append.py UTF-8 追加；04/06 改 -r 1 发布+重试制（TCP 建连竞态 + SITL 重启后约 30s 投递停滞）；README_runtime.md 运行时纪律；log_truncate_guard.sh 日志防爆；worlds/sitl_north*.world 磁北对齐 +X；test/ 复现与恢复脚本；05 补双目图像话题 |
| `planner/plan_manage/launch/run_planner_sitl.launch`（新增） | EGO-Planner SITL 入口：odom←`/mavros/local_position/odom`、深度←`/iris_depth_camera/camera/depth/image_raw`、内参 848x480 fx454.68（SDF hfov 推算）、map 30x30、max_vel 0.5；traj_server 输出 `/position_cmd` 对接 px4ctrl |
| `planner/plan_env/src/grid_map.cpp` | `setCacheOccupancy` 加 `boundIndex(id)` 防御：raycast 端点被 `closetPointInMap` 夹到地图边界表面时浮点误差可使 index 越界（SITL 远距离深度可复现 segfault，2026-09-26 addr2line 定位） |
| `planner/plan_manage/src/traj_server.cpp` | 删除轨迹完成分支的 `return`：原版到点后停发 /position_cmd，px4ctrl 0.5s 超时退回悬停、40s 后自动降落；现到达后持续发布终点悬停目标（对实机同样为改进） |
| `px4ctrl/src/controller.cpp` + `PX4CtrlParam.{h,cpp}` + `config/ctrl_param_sitl.yaml`（T3-W2 修改） | ①姿态目标改期望加速度向量直接构造（几何控制器法，zb.z≥0.1g 护栏）——修复大偏航误差下旧欧拉组合式的发散（2026-09-26 两轮坠机第一层根因，V1 独立复现；实机小 yawchg 场景数学等价）。②新增 thrust_model/enable_rls 参数（默认 true 实机零改动）+thr2acc 使用点钳位[5,40]，SITL yaml 置 false——RLS 推力映射在快速机动段被加速度伪影喂爆致油门塌 0（V2f/V2g 实证；SITL 推力曲线恒定无需自适应） |
| `planner/plan_manage/src/traj_server.cpp`（T3-W2 修改） | YAW_DOT_MAX_PER_SEC PI→PI/4（180→45deg/s）：消除轨迹起点无速率限制的偏航硬甩（~145° 掉头 0.6s 内甩完），自旋 transient 致跟踪发散（四轮实证）；145° 掉头 3.2s 完成，成功腿行为无感知差异 |
| `planner/plan_manage/launch/run_planner_sitl.launch`（T3 修改） | T1-W4 relay 临时下架为注释（含 T1 relay-v2 设计存档）：relay 订阅 rgb_info 激活 rgb 渲染，单传感器双流在 Xvfb llvmpipe 饱和压垮深度流→grid_map 空图直线穿箱（smoke5/run_182104 A/B 两轮实证；grid_map 内参来自 launch 参数不消费 caminfo 话题） |
| `sitl_sim/`（T3 新增） | analysis/analyze_takeoff_divergence.py（P1 离线复盘：到达序锚定/时戳修复/翻转-振荡-盲图签名）；t3_verify_flight.sh（障碍区侧场景验证 harness：传送+EKF2 settle+goal 重发+四看门狗）；t3_clean.sh；snap_rviz.sh；b0_headless.rviz（轨迹/膨胀占据/深度云 display）；worlds/sitl_world_obstacles_v2.world（box_D/E 1.5m 狭缝，已装 PX4 worlds）；analysis/analyze_flight.py 加 --world v2；docs/t3_experiments.md 试验台账 |
| `planner/plan_manage/launch/advanced_param_sitl.xml`（新增） | `_exp` 版的仿真参数：obstacles_inflation 0.337→0.299；外参走 grid_map 默认 optical→body 矩阵（SITL 相机 RPY=0 时旋转正确，平移差 0.1m 在膨胀半径内） |

## 4. SITL 全流程仿真（脚本在本仓库 `sitl_sim/`，每脚本一个终端，按编号执行）

| 脚本 | 作用 |
|---|---|
| `00_env_check.sh` | 环境自检，输出 `sitl_env_check.txt` + dpkg/pip/src-md5 快照（快照文件已入库供日后 diff） |
| `01_start_px4_sitl.sh` | PX4 SITL + Gazebo Classic 11（HEADLESS，`make px4_sitl gazebo-classic`） |
| `02_start_mavros.sh` | mavros，`fcu_url:=udp://:14540@127.0.0.1:14557` |
| `03_start_px4ctrl.sh` | px4ctrl（`run_ctrl_sitl.launch`） |
| `04_takeoff.sh` | `/px4ctrl/takeoff_land` cmd=1 自动起飞 |
| `05_record_bag.sh` | rosbag record（起飞前启动，降落后 Ctrl-C；bag 落在 `~/sitl_sim/bags/`，脚本内为绝对路径） |
| `06_land.sh` | cmd=2 降落，等 disarm（90s 超时，附手动兜底命令） |
| `start_sitl_depth.sh`（新增） | 深度相机模型 SITL 启动（iris_depth_camera + ROS 话题）。前置 roscore 与 Xvfb :99；自动处理 DISPLAY/gazebo 库路径/gzserver ROS 插件注入/pxh stdin 四个坑（详见脚本头注释） |
| `VINS-Fusion/config/sim_stereo/`（新增） | A7 仿真 VINS 配置：双目来自 iris_stereo_vins 模型、IMU 用 /mavros/imu/data_raw（mavcmd 511 提频 125Hz）、外参从 SDF 换算、estimate_extrinsic:2 在线标定（调试中） |
| `px4ctrl/launch/run_ctrl_sitl_vins.launch`（新增） | SITL+仿真 VINS 版控制：odom←/vins_estimator/imu_propagate；EKF2 版 run_ctrl_sitl.launch 永远可用 |
| `planner/plan_manage/launch/run_planner_sitl_vins.launch`（新增） | EGO-Planner SITL+VINS 版：odom←imu_propagate、深度←iris_stereo_vins 模型话题 |
| `launch/sim_vins.launch`（新增） | 仿真 VINS 入口：vins_node + vins_to_mavros（喂 /mavros/vision_pose/pose，照实机链路） |
| `sitl_sim/models/{iris_stereo_vins,stereo_vins_rig}/`（新增） | A7 模型副本（安装到 PX4 models 目录 + sitl_targets_gazebo-classic.cmake 注册 + airframes 1090 + build rootfs 拷贝，见 README §6） |
| `sitl_sim/start_sitl_vins.sh`（新增） | iris_stereo_vins 模型启动（同 start_sitl_depth 五坑处理） |
| `VINS-Fusion/vins_estimator/src/estimator/estimator.cpp/.h` | T2-W4 修复：①stereo+IMU 初始化质量门（原版窗口满即无条件完成，PnP 失败帧静默沿用废姿态→首帧 odometry 天文数字），前置查 bias/状态+后置查状态，不合格经 reinit_request 完全重启 ②failureDetection 启用（原版首行 return false 整个检测为死代码）+状态幅值判据 ③all_image_frame 拷贝循环加边界（越界写） |
| `VINS-Fusion/vins_estimator/src/estimator/feature_manager.cpp` | T2-W4：solvePoseByPnP 启用 RANSAC 版（上游注释掉的原选），抗退化三角化点 |
| `VINS-Fusion/vins_estimator/src/featureTracker/feature_tracker.cpp` | T2-W4：立体视差下限 1px 过滤（零视差错配→深度 e17→PnP e33 链路掐断） |
| `vins_to_mavros/src/vins_to_mavros_node.cpp` | T2-W4 健康门控：相邻帧跳变>1m 或速度>5m/s 停止转发 /mavros/vision_pose/pose 并 ROS_ERROR，连续 20 帧平稳自动恢复；阈值 rosparam（~gate_pos_jump/gate_vel/gate_stable_frames/gate_enabled）。2026-09-26 翻机事故防线，sitl_sim/analysis/vins_gate_test.py 集成单测通过 |
| `worlds/sitl_world_obstacles.world`（新增） | 避障测试 world：3 个静态箱（odom 系坐标表见文件头注释）；安装=复制到 PX4 sitl_gazebo-classic/worlds/，启动=SITL_WORLD=sitl_world_obstacles 配合 start_sitl_depth.sh；physics 必须 0.004s/250Hz（PX4 lockstep 硬约束） |
| `gzserver_wrapper.sh`（新增） | gzserver 包装脚本，附加 libgazebo_ros_api_plugin.so（noetic 传感器插件依赖全局 ros::init）；由 start_sitl_depth.sh 经 PATH 前置生效，不改 PX4 上游 |

**仿真已验证**：2026-09-23 三次完整"起飞→悬停→降落"（SITL，非实飞；`~/sitl_sim/bags/` 下 3 个 bag，最长 106s；px4ctrl 100Hz 姿态控制 + mavros EKF2 里程计）。
**当前缺口**：planner（EGO-Planner）尚未接入 SITL 回路——需要深度相机模型（PX4 自带 `iris_depth_camera`）+ 深度/odom 话题接线 + goal 触发 + `traj_server` `/position_cmd` → px4ctrl。

## 5. 已知注意事项

- 真机与 SITL 的 px4ctrl 入口分离：真机 `run_ctrl.launch`（VINS 里程计）/ SITL `run_ctrl_sitl.launch`（EKF2），互不影响
- 校验上游差异的方法：浅克隆上游后 `diff -rq upstream/src ~/catkin_ws/src -x .git`
- 协作与推送纪律见 [CONTRIBUTING.md](CONTRIBUTING.md)
