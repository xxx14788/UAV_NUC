# 仿真平台升级分支：现状与交接（2026-10-25）

## 范围与版本

- 升级分支：`codex/sim-platform-upgrade`，从已 fetch 的最新 `origin/main` 创建，已推送同名远端分支。
- 代码基线：`0da27ebbbe7e55776be31cdd2f64a39044c83767`（`docs: 记录无头仿真环境验收`）。本文作为该基线上的文档提交，不修改算法、模型或运行配置。
- 容器 `uav-sim-dev` 的工作空间为宿主仓库 bind mount；容器内已核对相同分支与代码基线。
- 本次未启动仿真、未复飞、未重新构建，也未操作真机或修改宿主 Docker/GPU 配置。

## 本次验证

- 容器环境检查：`docker/scripts/verify_environment.sh --require-built` 返回 `failures=0`。
- Ubuntu 20.04、ROS Noetic、Gazebo Classic 11.15.1；PX4 v1.17.0，提交 `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`，源码干净、子模块匹配、PX4 可执行文件与 catkin devel 均存在。以上是环境/产物存在性检查，不等于本次编译或飞行验收。
- 四套脚本测试通过：`test_static_contracts.sh`、`test_build_helpers.sh`、`test_sync_runtime_harness.sh`、`test_migrate_legacy_container.sh`。迁移测试使用临时目录及 fake Docker，输出中的删除不是生产容器删除。
- 抽查正本与运行副本：`vins_smoke.sh`、`start_sitl_vins.sh`、`stereo_vins_rig.sdf` 一致。

## 功能盘点

| 能力 | 当前状态 | 证据/边界 |
|---|---|---|
| 无头 Docker / Compose / Dev Containers | 配置已存在，容器运行中 | `docker/`、`compose.yaml`、`.devcontainer/devcontainer.json` |
| 双目+IMU、VINS、MAVROS、px4ctrl、EGO-Planner | 代码及构建产物已存在 | 环境检查与包定位；不冒充本次全链复飞 |
| 起飞、航点、降落/disarm、录包、判读、清场 | 冒烟入口已实现，有既有运行记录 | `sitl_sim/vins_smoke.sh`；没有专门固定驻留时长的 hover-only 模式 |
| 双目 SGBM 深度桥 | 已有包、安装入口和独立 launch | `src/stereo_depth_bridge/`；需 `C3A_BRIDGE=1`，默认关闭；本次未验收桥接飞行 |
| GPU 透传及独显渲染验收 | 当前容器未配置设备请求/映射 | inspect 的 DeviceRequests/Devices 均为 null；未运行 glxinfo，不能据此断言实际 renderer 或瓶颈 |
| 可标定偏移/抖动/丢帧注入 | 未发现目标自定义相机插件实现 | 当前 SDF 加载两份 `libgazebo_ros_camera.so`，并非 multicamera 插件 |
| 独立可视化站点 | 当前容器未集成 | 不把现有日志/图表或历史平台文档等同于站点已部署 |

## 配置事实与实验风险

1. `sitl_sim/models/stereo_vins_rig/stereo_vins_rig.sdf` 当前为左右独立 camera sensor，各自标称 30Hz、640×480；基线 49.3mm，HFOV 1.38053965 rad，Gaussian stddev 0.004。标称频率不等于本机实测频率，亦不能再把该模型描述成零噪声、100mm 基线。
2. 默认规划 launch 读取 Gazebo 深度；桥接变体读取 `/sdb/depth/image_raw`。两者还包含速度参数差异（max_vel 0.5 与 0.75），因此不能直接把切换桥接的结果解释为仅深度来源的单变量效应。
3. 当前相机插件与历史文档所列 multicamera 注入点不一致。实现前需追踪实际加载库、源码版本、消息 stamp 生成位置和投递链；修改 stamp 不等同于施加真实消息延迟。
4. 既有 Docker 记录中，T9 A 为 FAIL，B/C 为 PASS，另一个 HOVER_LAND 命名轮为 PASS；名字不能证明固定时长悬停验收。该小样本不能代表平台总体成功率。
5. RESULT 中旧 `min_dist` 行有判据警告，避障净距应核对对应版本的几何 audit `min_surf`，不能直接拿旧 PASS 当安全结论。
6. README 有历史性陈旧描述（例如 planner 尚未接入），当前功能应以源码、启动配置和逐轮证据交叉核对。

## 建议的下一工作单元（待确认，不代表已实施）

1. 冻结本机基线与判读协议：记录代码/构建/模型/配置指纹，明确默认深度与桥接深度两种配置；统一真值、VINS、自报到位和几何净距的口径。
2. 建立可复现的静态传感器、定时悬停及导航基线，先验证探针，分别记录仿真 stamp、接收端单调时钟、左右配对、IMU、实时因子及起降结果；不要沿用历史机器数字替代本次测量。
3. 保留无头默认路径，独立测试 GPU 配置，先证实 renderer，再比较同场景同负载的时序与估计表现；GPU 提速不是定位问题必然解决的证据。
4. 在真实插件链明确后，先预注册最小注入设计，再实现默认关闭、可复现的偏移/抖动/丢帧功能及单测；先过零扰动等价门，不扩为完整时序仿真器。
5. 桥接深度在本容器单独验收，控制速度等混杂变量；可视化站点集成、更广泛的对齐框架和估计器研究改动另立工作单元。

## 交接

- 本轮只新增本文；不改主分支，不修改飞行代码/参数，不打新的可飞 tag。
- 升级分支已创建且远端 SHA 已核对；本文提交后须立即推送并再次核对远端分支。后续实现前仍需检查工作区及上游更新。
