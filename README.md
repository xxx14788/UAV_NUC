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
| `planner/plan_manage/launch/run_planner_sitl.launch`（新增） | EGO-Planner SITL 入口：odom←`/mavros/local_position/odom`、深度←`/iris_depth_camera/camera/depth/image_raw`、内参 848x480 fx454.68（SDF hfov 推算）、map 30x30、max_vel 0.5；traj_server 输出 `/position_cmd` 对接 px4ctrl |
| `planner/plan_env/src/grid_map.cpp` | `setCacheOccupancy` 加 `boundIndex(id)` 防御：raycast 端点被 `closetPointInMap` 夹到地图边界表面时浮点误差可使 index 越界（SITL 远距离深度可复现 segfault，2026-09-26 addr2line 定位） |
| `planner/plan_manage/src/traj_server.cpp` | 删除轨迹完成分支的 `return`：原版到点后停发 /position_cmd，px4ctrl 0.5s 超时退回悬停、40s 后自动降落；现到达后持续发布终点悬停目标（对实机同样为改进） |
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
| `gzserver_wrapper.sh`（新增） | gzserver 包装脚本，附加 libgazebo_ros_api_plugin.so（noetic 传感器插件依赖全局 ros::init）；由 start_sitl_depth.sh 经 PATH 前置生效，不改 PX4 上游 |

**仿真已验证**：2026-09-23 三次完整"起飞→悬停→降落"（SITL，非实飞；`~/sitl_sim/bags/` 下 3 个 bag，最长 106s；px4ctrl 100Hz 姿态控制 + mavros EKF2 里程计）。
**当前缺口**：planner（EGO-Planner）尚未接入 SITL 回路——需要深度相机模型（PX4 自带 `iris_depth_camera`）+ 深度/odom 话题接线 + goal 触发 + `traj_server` `/position_cmd` → px4ctrl。

## 5. 已知注意事项

- 真机与 SITL 的 px4ctrl 入口分离：真机 `run_ctrl.launch`（VINS 里程计）/ SITL `run_ctrl_sitl.launch`（EKF2），互不影响
- 校验上游差异的方法：浅克隆上游后 `diff -rq upstream/src ~/catkin_ws/src -x .git`
- 协作与推送纪律见 [CONTRIBUTING.md](CONTRIBUTING.md)
