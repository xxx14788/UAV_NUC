# UAV_NUC — Fast-Drone-250 复现工作区

本仓库 = NUC 机载电脑（Ubuntu 20.04.6 + ROS Noetic + Gazebo Classic 11）上的 `~/catkin_ws`，
基于 [ZJU-FAST-Lab/Fast-Drone-250](https://github.com/ZJU-FAST-Lab/Fast-Drone-250) 复现。
仓库根即 catkin 工作空间根（内含 `src/`），clone 后 `catkin_make` 即可编译（build/devel 已 gitignore）。

> **多人/多 agent 协作仓库**：动手前先读 [CONTRIBUTING.md](CONTRIBUTING.md)（凭据安全、提交与推送纪律）。
> **项目规范**：[docs/workflow.md](docs/workflow.md)（工作流与验证门槛）· [docs/coding-style.md](docs/coding-style.md)（代码与配置风格）· [docs/flight_log.md](docs/flight_log.md)（飞行/仿真实验记录）· [docs/realflight_checklist.md](docs/realflight_checklist.md)（实飞检查单：IMU 250Hz 三步检查+固件台账）。


## 0. 架构红线：纯视觉导航（VINS + EGO-Planner + PX4），不许依赖 GPS

> 2026-09-28 用户裁定，优先级高于一切任务书/验收指标，T1/T2/T3/T4 全体生效。

**目标架构（实机）**：D435 双目+IMU → VINS-Fusion（**唯一位置源**）→
px4ctrl 的 `~odom` 直供 `/vins_estimator/imu_propagate`；EGO-Planner 用
深度流建图；PX4 只承担姿态/推力内环。EKF2 位置估计**不参与控制链路**。

**规则**：

- **R1 定位层验证必须走 VINS 链路**：估计质量/重锚/初始化/yaw 参考等
  定位层指标的验证，必须使用 iris_stereo_vins 模型 + sim_vins.launch +
  run_ctrl_sitl_vins.launch（均在库）。GPS 代位链路上的定位层结论
  对实机无效，不得作为验收依据。
- **R2 GPS 代位链路的合法用途**：EKF2 local_position 当 odom 的现有链路
  （iris_depth_camera + run_ctrl_sitl.launch）只允许验证流程/规划/
  控制器层（odom 视为黑盒，与定位源无关）。此类验证报告必须标注
  "GPS 代位"。
- **R3 修复的架构合规检查**：任何进入正式修复（入库/定版）的参数或
  代码改动，必须论证在 VINS 直供架构下有效或无害。GPS 专属操作
  （GPS origin 重置、GPS course 流程、GPS 域 EKF2 参数精调）不得进入
  VINS 链路的 harness 与配置。
- **R4 验收口径**：tag 门禁类验收（如 sitl-v0.x）中，定位层指标
  （到位精度/重锚质量）只计 VINS 链路结果；流程层指标可引 GPS 代位
  结果但须标注。
- **R5 实机配置零 GPS 现状保持**：ctrl_param.yaml（实机版）、*_exp.launch、
  VINS-Fusion 配置维持无 GPS 依赖；给 SITL 加的任何 GPS 相关参数
  不得同步到实机配置。

**R6 仿真-实机链路同构**（2026-09-28 用户强化裁定）：仿真验证链路的
节点拓扑与话题语义必须与实机 full_vins_px4.launch 同构——同环节：
传感器模型 → VINS-Fusion → vins_to_mavros → px4ctrl（~odom=VINS 直供）
→ EGO-Planner（odom=VINS、深度建图）→ traj_server → px4ctrl。允许的
差异仅限"传感器模型几何必然"与"已论证登记"两类。当前已登记差异：

| 差异点 | SITL | 实机 | 依据 |
|---|---|---|---|
| 相机内参 fx | 454.68（iris 模型 hfov 86° 推算） | 387.51（D435 实标） | 传感器模型几何必然（fx 必须匹配仿真相机） |
| obstacles_inflation | 0.299 | 0.337 | 实机含云台杆遮挡标定；SITL 无杆（A3 决策 2026-09-26，如需保守可统一 0.337 重验） |
| VINS IMU 源 | /mavros/imu/data_raw：511 105 5000→实测 **125Hz**（5000us 被 tick 量化到 8ms）；4000us 档实测 **223Hz** 可达实机级（切换待 T2 域验证） | mavcmd 511 设 200Hz | V4.2 实测 2026-09-28（bag+probe6 双证）：请求间隔被 mavlink tick ~4ms 网格量化；默认档 50Hz（W2）；频域影响在 VINS 域评估 |
| 相机平移外参 | 模型 0.1m 前置 | D435 实测外参 | sim_stereo 配置已按模型标定（T2 域） |
| PX4 固件 | px4_sitl v1.17 | fmu 实机版 | R5：SITL 动过的 PX4 参数（MAG_TYPE/SDLOG 等）一律不同步实机 |

**多会话并行纪律**（2026-09-28，历史事故固化）：
① 构建互斥——catkin_make 前在 STATUS 发预告行，等飞轮间隙执行（SITL
锁不管 build 目录，09-28 01:56 双会话并发编译 FAILED 实证）；② 离线会话
三不——不起 SITL 进程、不构建（预告窗除外）、重计算避开飞轮窗口
（CPU 挤压致探针/投递饿死实证）；③ 任何 boot/循环类脚本每轮前
`sitl_lock.sh get` 查锁（多实例混流事故实证）；④ force 抢占双条件——
锁龄超 30min 且 `pgrep -f "bin/px4|gzserver"` 为零；⑤ 锁 owner 一律带
任务线前缀（smoke 调用方传 `SMOKE_OWNER=T3` 等，缺省 T1 兼容）。

**切链路接口备忘**（SITL GPS→VINS 切换时）：iris_stereo_vins 的深度
话题前缀为 `/iris_stereo_vins/...`（run_planner_sitl.launch 的
depth_topic 当前硬编码 `/iris_depth_camera/...`，切链路时需参数化）；
VINS 话题见 config/sim_stereo/sim_stereo_imu_config.yaml。

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
| `sitl_sim/`（T1-W5/W6 新增+修改） | sitl_smoke.sh 一键冒烟（09-28 扩六指标：到位/避障/100Hz/自动disarm/est-vs-truth偏航<5°/飞行中深度流≥9Hz；RELAY_ON=1 透传认证轮）；sitl_lock.sh 三任务运行时锁；status_append.py UTF-8 追加；04/06 发布重试制（U3 定案：新 pub→px4ctrl TCPROS 建连随机失败~50%，roscpp 单次协商失败不重试，需新 publisherUpdate；04 轮长 12s 重掷）；02 fcu_url=14580（U2：PX4 v1.17 offboard 实际监听口，14557 为 2018 前死约定）；README_runtime.md 运行时纪律；log_truncate_guard.sh 日志防爆；worlds/sitl_north*.world 磁北对齐 +X；test/ 复现与恢复脚本；05 补双目图像话题 |
| `planner/plan_manage/launch/run_planner_sitl.launch`（新增） | EGO-Planner SITL 入口：odom←`/mavros/local_position/odom`、深度←`/iris_depth_camera/camera/depth/image_raw`、内参 848x480 fx454.68（SDF hfov 推算）、map 30x30、max_vel 0.5；traj_server 输出 `/position_cmd` 对接 px4ctrl |
| `planner/plan_env/src/grid_map.cpp` | `setCacheOccupancy` 加 `boundIndex(id)` 防御：raycast 端点被 `closetPointInMap` 夹到地图边界表面时浮点误差可使 index 越界（SITL 远距离深度可复现 segfault，2026-09-26 addr2line 定位） |
| `planner/plan_manage/src/traj_server.cpp` | 删除轨迹完成分支的 `return`：原版到点后停发 /position_cmd，px4ctrl 0.5s 超时退回悬停、40s 后自动降落；现到达后持续发布终点悬停目标（对实机同样为改进） |
| `px4ctrl/src/controller.cpp` + `PX4CtrlParam.{h,cpp}` + `config/ctrl_param_sitl.yaml`（T3-W2 修改） | ①姿态目标改期望加速度向量直接构造（几何控制器法，zb.z≥0.1g 护栏）——修复大偏航误差下旧欧拉组合式的发散（2026-09-26 两轮坠机第一层根因，V1 独立复现；实机小 yawchg 场景数学等价）。②新增 thrust_model/enable_rls 参数（默认 true 实机零改动）+thr2acc 使用点钳位[5,40]，SITL yaml 置 false——RLS 推力映射在快速机动段被加速度伪影喂爆致油门塌 0（V2f/V2g 实证；SITL 推力曲线恒定无需自适应） |
| `planner/plan_manage/src/traj_server.cpp`（T3-W2 修改） | YAW_DOT_MAX_PER_SEC PI→PI/4（180→45deg/s）：消除轨迹起点无速率限制的偏航硬甩（~145° 掉头 0.6s 内甩完），自旋 transient 致跟踪发散（四轮实证）；145° 掉头 3.2s 完成，成功腿行为无感知差异 |
| `planner/plan_manage/launch/run_planner_sitl.launch`（T3 修改） | T1-W4 relay 临时下架为注释（含 T1 relay-v2 设计存档）：relay 订阅 rgb_info 激活 rgb 渲染，单传感器双流在 Xvfb llvmpipe 饱和压垮深度流→grid_map 空图直线穿箱（smoke5/run_182104 A/B 两轮实证；grid_map 内参来自 launch 参数不消费 caminfo 话题） |
| `sitl_sim/`（T3 新增） | analysis/analyze_takeoff_divergence.py（P1 离线复盘：到达序锚定/时戳修复/翻转-振荡-盲图签名）；t3_verify_flight.sh（障碍区侧场景验证 harness：传送+EKF2 settle+goal 重发+四看门狗）；t3_clean.sh；snap_rviz.sh；b0_headless.rviz（轨迹/膨胀占据/深度云 display）；worlds/sitl_world_obstacles_v2.world（box_D/E 1.5m 狭缝，已装 PX4 worlds）；analysis/analyze_flight.py 加 --world v2；docs/t3_experiments.md 试验台账 |
| `planner/plan_manage/launch/advanced_param_sitl.xml`（新增） | `_exp` 版的仿真参数：obstacles_inflation 0.337→0.299；外参走 grid_map 默认 optical→body 矩阵（SITL 相机 RPY=0 时旋转正确，平移差 0.1m 在膨胀半径内） |
| `px4ctrl/src/attitude_utils.h` + `px4ctrl/test/test_controller_attitude.cpp`（T3-W9 新增） | 姿态公式抽取纯函数 + NaN/Inf 防护（非有限输入返回单位姿态）+ gtest 8 用例（悬停恒等/四向倾角/z<0 护栏/退化正交/yaw wrap 连续性/老式等价锁<0.5°@倾角≤4°/NaN 安全/网格性质）8/8 绿；controller.cpp 改调用（行为与 0de090e 内联版一致） |
| `planner/plan_manage/src/traj_server.cpp`（T3-W7 续篇修改） | ①YAW_DOT_MAX PI/4→PI/2 定版（45 已证致掠射建图侵蚀 run_193052 弃用；90=硬甩消除与掠射侵蚀的折中）；②新轨迹到达时 last_yaw_ 重置为机体实际 odom yaw（经 traj_server/odom_topic 参数订阅，空=上游行为；仅 SITL launch 传入）——消除起点 yaw 从上一轨迹残留值追赶的瞬态（V1 轮 58 次 >150°/s 追赶事件实证，yaw_closure_analysis.py） |
| `sitl_sim/analysis/`（T3 续篇新增 5 工具） | controller_replay.py（三实现 A/B/C 回放+保真核验+对齐率决策表：老欧拉法全历史失败腿倾角错向 78-170° 定罪，帧补丁 P 中位 0.01°→保留）；yaw_closure_analysis.py（Y2 阶跃-replan 对齐/Y3 速率跟踪滞后）；map_truth_diff.py（占据栅格重建 vs 真障碍体素 diff + 离线融合重演参数扫描；健康环境缺失率 0.000）；stoppage_analysis.py（停顿-replan 对齐：成功轮 100% 邻接 replan=重规划等待型）；leg_database.py（跨会话全 bag 指标库 → docs/analysis/legs.csv） |
| `sitl_sim/` harness（T3 续篇修改+新增） | t3_verify_flight.sh：传送前 world 就绪+单机体断言（W7v1 多实例混流事故加固）+SPAWN_YAW 环境参数化；two_leg_flight.sh（新增，无传送两段式返程腿 harness——EKF2 瞬爆隔离实验 2/2 复现载体）；env_health_check.sh（五项自检：磁参数/shm/进程孤儿/深度频率/日志体量）；teleport_stats.sh（EKF2 重锚统计）；t3_clean.sh 升级（shm+ipcs+Xvfb+大文件报告）；三脚本录制清单+occupancy/occupancy_inflate/bspline/深度流/相机内参 |

| `sitl_sim/param_hygiene.sh`（T1-v5 V2 新增） | 实机零 GPS 静态扫描（R5 落地）：四类对象（ctrl_param_fpv.yaml／*_exp* 链+full_vins_px4.launch／realsense_d435 全目录／PX4_PARAM_EXPORT 可选）；FAIL/INFO(显式关闭)/EXEMPT(注释/行内 hygiene-exempt) 三态；gps/MAV_CMD 176/course/global origin/MAV_FRAME GLOBAL 五类模式；自测 10/10（含四类注入捕获），当前实机 9 对象全 PASS；接入 env_health_check 第 6 项 |
| `sitl_sim/env_health_check.sh`（T1-v5 V3 修复+扩项） | 五项→六项；静默 EXIT=1 根因=set -u 下 source ROS 时 1.ros_distro.sh:3 引用未定义 ROS_DISTRO 直接中止外层脚本（2>/dev/null 吞掉报错），修复=source 先于 set -u；env -i 复现+回归双门禁过 |
| `sitl_sim/v1_flight.sh`+`t1_evidence/v1_{ground,hover}_analysis.py`+`t1_evidence/v1_flight_results.md`（T1-v5 V1/V4 新增） | VINS 链路轮编排器（锁 T1-V1/清场补杀 vins 系/fresh-master+use_sim_time 前置/VINS init 门/T2 preflight/511 三档探针/降落重掷/t3_clean 收尾释锁；bag 增录 fsm_state+debugPx4ctrl）+双口径分析器+实测：悬停保持中位 0.005m（PASS,优于 0.03m 基线与 EKF2 参照 0.050m）、静态漂移 2-3cm/45s、imu_propagate 125Hz 零断流（maxgap 12ms）、出生点平移假象(+1.01,+0.98)复现登记 |
| `docs/t1_vins_odom_contract.md`（T1-v5 V1.1 新增,双会话合并） | px4ctrl odom 契约差异表（源码级+bag 实证）：EKF2 odom vs VINS imu_propagate 12 维度；结论=契约兼容无需改参，两真差异属流程适配（init 前零发布/参考点 IMU 2cm），msg_timeout 不调（调大有害） |

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
| VINS-Fusion vins_estimator estimator.cpp | T2b-U1:①processMeasurements dt 钳制防线(dt∉[0,0.5]s 置 0+限流告警;跨时钟域/IMU 乱序不再产毒,机制见 docs/t2_experiments.md U1 章) ②毒槽位插桩四路(T2POISON/T2SNAP/T2OPT,保留为可观测性) ③stereo init 后置门 reject 分支 unreachable 死代码清理(行为不变,reinit 消费者已覆盖) | 2026-09-28 |
| PX4 sitl_gazebo-classic stereo_vins_rig.sdf | T2b-E18 实验临时改 update_rate 30→60 与分辨率变体(录制 60Hz 两变体 bag 后已还原基线 30Hz/640×480;机制与数据见 docs/t2_experiments.md E18 章) | 2026-09-28 |
| sitl_sim/analysis 新工具 8 个 | t2_segment_attribution.py(分段误差归因)/t2_dy_row_profile.py(dy 行×视差分桶)/t2_bag_concat.py(A+D 拼接)/t2_bag_transform.py(降帧降分)/t2_domain_guard.py(+selftest, 域卫士)/t2_preflight_check.py(五项自检)/t2_gate_test_v2.py(门控五阶段+真实回归)/t2_dump_stamps.py(域诊断) | 2026-09-28 |
| VINS-Fusion rosNodeTest.cpp / estimator.cpp / vins_to_mavros | T2-v3 W1:①RLIMIT_STACK 软限抬至硬限(vins_node 栈段陷阱崩溃防御) ②inputIMU 发布端有界性防线(ceres 发散毒值 e6 级不再外送 px4ctrl 直供链) ③imu_check_enabled 默认 false(地面静态误报实测,v2 设计要求在代码注释) | 2026-09-28 |
| VINS-Fusion vins_estimator estimator.cpp | T2-v4.1 R1/R3 插桩：①[T2diag] 每滑窗优化帧状态轨迹（P/V/\|Bas\|/\|Bgs\|/tic01/td/track，printf+fflush 防 nohup stdout 缓冲吞行）②[T2slv] 全阶段求解器健康（init/final cost/iters/termination/耗时，原版仅 INITIAL 阶段）③[T2fail] failureDetection 判据快照并入触发行（判据行被 stdout 缓冲丢失问题的根治）。回归：E20×bagA ATE 0.130 ∈ 历史 [0.115,0.137] | 2026-09-29 |
| sitl_sim 新工具 | t2v3_flight.sh(W1/W2 在线编排:延迟装配/goal回执重试/abort清场)/t2v3_eval.py(在线轮双口径评估)/t2_dx_col_profile.py;docs/vision_acceptance_protocol.md+sim2real_runbook.md 入库 | 2026-09-28 |
| `VINS-Fusion/vins_estimator/src/estimator/feature_manager.cpp` | T2-W4：solvePoseByPnP 启用 RANSAC 版（上游注释掉的原选），抗退化三角化点 |
| `VINS-Fusion/vins_estimator/src/featureTracker/feature_tracker.cpp` | T2-W4：立体视差下限 1px 过滤（零视差错配→深度 e17→PnP e33 链路掐断） |
| `vins_to_mavros/src/vins_to_mavros_node.cpp` | T2-W4 健康门控：相邻帧跳变>1m 或速度>5m/s 停止转发 /mavros/vision_pose/pose 并 ROS_ERROR，连续 20 帧平稳自动恢复；阈值 rosparam（~gate_pos_jump/gate_vel/gate_stable_frames/gate_enabled）。2026-09-26 翻机事故防线，sitl_sim/analysis/vins_gate_test.py 集成单测通过 |
| `worlds/sitl_world_obstacles.world`（新增） | 避障测试 world：3 个静态箱（odom 系坐标表见文件头注释）；安装=复制到 PX4 sitl_gazebo-classic/worlds/，启动=SITL_WORLD=sitl_world_obstacles 配合 start_sitl_depth.sh；physics 必须 0.004s/250Hz（PX4 lockstep 硬约束） |
| `gzserver_wrapper.sh`（新增） | gzserver 包装脚本，附加 libgazebo_ros_api_plugin.so（noetic 传感器插件依赖全局 ros::init）；由 start_sitl_depth.sh 经 PATH 前置生效，不改 PX4 上游 |
| `sitl_smoke.sh`（T1-W5 新增） | 一键冒烟：持锁→SITL(可选world)→mavros(300s窗)→px4ctrl→冷planner→bag→起飞→goal(7,-4,1)→四指标判定(到位<0.5m/避障>0.349m/poscmd≥50Hz/自动disarm)→清理→放锁；失败保留现场。回归标准入口 |
| `sitl_lock.sh` / `status_append.py`（T1 新增） | 三任务 SITL 运行时锁(get/release/force/status,属主前缀校验)；STATUS.md UTF-8 安全追加(ssh echo 中文乱码的替代) |
| `README_runtime.md` / `log_truncate_guard.sh`（T1 新增） | 运行时纪律一页纸(锁/重启序列/五坑/冷态/通用工程坑)；日志>1GB 自动截断到 10MB |
| `test/`（T1 新增） | repro_px4ctrl_stall / test_px4ctrl_recovery(W1 验收) / w1_recovery_boundary_probe / w2_imu_rate_sweep / w3_yaw_check |
| `worlds/sitl_north*.world`（T1-W3 新增） | 磁北对齐 +X(6e-5 0 0)三变体;⚠️换磁 world 会话后 PX4 会把磁校准写入 build/.../rootfs/parameters.bson,污染后续默认世界会话的偏航估计(2026-09-27 实证),混用 world 后需检查/复位(见 ~/sitl_sim/t1_evidence/w4_cert_runbook.md) |

**仿真已验证**：2026-09-23 三次完整"起飞→悬停→降落"（SITL，非实飞；`~/sitl_sim/bags/` 下 3 个 bag，最长 106s；px4ctrl 100Hz 姿态控制 + mavros EKF2 里程计）。
**当前缺口**：planner（EGO-Planner）尚未接入 SITL 回路——需要深度相机模型（PX4 自带 `iris_depth_camera`）+ 深度/odom 话题接线 + goal 触发 + `traj_server` `/position_cmd` → px4ctrl。

## 5. 已知注意事项

- 真机与 SITL 的 px4ctrl 入口分离：真机 `run_ctrl.launch`（VINS 里程计）/ SITL `run_ctrl_sitl.launch`（EKF2），互不影响
- 校验上游差异的方法：浅克隆上游后 `diff -rq upstream/src ~/catkin_ws/src -x .git`
- 协作与推送纪律见 [CONTRIBUTING.md](CONTRIBUTING.md)
