# UAV 仿真平台 Docker 开发环境设计

日期：2026-10-22

状态：设计已确认，等待实施计划

目标仓库：`/home/rick/桌面/UAV_NUC`

## 1. 目标

建立一个可复现、可重建、可由 VS Code 直接进入的 ROS Noetic 仿真开发环境，用于持续优化以下完整链路：

```text
PX4 SITL
  → Gazebo Classic 11
  → MAVROS
  → VINS-Fusion
  → px4ctrl
  → EGO-Planner
```

环境与项目数据分离：系统依赖进入 Docker 镜像，源码、PX4 源码、实验数据和日志保留在宿主机。删除或重建容器不得造成源码或实验数据丢失。

本阶段只实现并验收默认 headless 模式。GPU 模式保留设计接口，但在 headless 模式验收后暂停，不安装 NVIDIA Container Toolkit，不修改宿主机 GPU/Docker 配置。

## 2. 范围

### 2.1 本阶段包含

- 保存并安全删除旧容器 `noetic-sim`。
- 从源码构建新的开发镜像，而不是继续使用旧容器的不可审计可写层。
- 将 `UAV_NUC` 工作树绑定挂载到容器。
- 准备干净且固定在 `v1.17.0` 的 PX4-Autopilot 工作树。
- 安装 ROS、Gazebo、MAVROS、VINS、EGO-Planner 和 PX4 SITL 所需依赖。
- 提供 Docker Compose 默认 headless 服务。
- 提供 VS Code Dev Containers 配置。
- 完成分层验证和一次 `00→04→06` 仿真冒烟。

### 2.2 本阶段不包含

- D435、Pixhawk、串口、USB 或其他真机设备访问。
- 真机飞行配置或 udev 规则修改。
- NVIDIA Container Toolkit 安装。
- GPU 容器启动、Gazebo GUI 或 RViz GPU 验收。
- 修改 VINS、px4ctrl、EGO-Planner 或 PX4 算法行为。
- 用现有宿主机 `/home/rick/UAV/PX4-Autopilot` 作为仿真正源；该工作树版本不符且存在未提交修改。

## 3. 已验证现状与约束

### 3.1 宿主机源码

- `UAV_NUC` 当前位于 `/home/rick/桌面/UAV_NUC`。
- 当前分支为 `main`，设计前 HEAD 为 `eee7aaef264b556feaca9ed250e44a067132c8ff`。
- 仓库是 catkin 工作空间根，源码位于 `src/`。
- 运行脚本广泛依赖：
  - `$HOME/catkin_ws`
  - `$HOME/PX4-Autopilot`
  - `$HOME/sitl_sim`
- 仿真脚本固定使用 ROS Noetic、Gazebo Classic、PX4 SITL 和 Xvfb `:99`。

### 3.2 旧容器

- 容器名：`noetic-sim`。
- 基础镜像：`osrf/ros:noetic-desktop-full-focal`。
- 容器无 bind mount，可写层约 7.8 GB。
- 容器内存在 `catkin_ws`、编译产物和部分运行数据。
- 容器内 Git 当前分支为 `feature/algorithm-development`，提交为 `b2b351bde07dca7faefe115307e1db0b1de3ba78`；该提交不在当前宿主机仓库对象库中。
- 容器内未发现源码要求的 `$HOME/PX4-Autopilot` 和 `$HOME/sim_ws`，因此旧容器不能直接作为完整仿真环境正源。
- 旧容器仍有恢复价值，只作为迁移备份保留，不作为新镜像基底。

### 3.3 依赖基线

源码声明和旧环境快照共同确认的关键依赖包括：

- Ubuntu 20.04、ROS Noetic、Gazebo Classic 11.15。
- MAVROS/MAVROS Extras 1.20 系列。
- Eigen3、OpenCV 4.2、PCL、Ceres 1.14、SuiteSparse、gflags、glog。
- catkin tools、Python 3、NumPy、PyYAML、empy 3.x、PX4 Python 工具链。
- Xvfb、Mesa/OpenGL、GeographicLib 数据。
- 编译工具：gcc/g++、CMake、Ninja、Make、Git、pkg-config。

## 4. 方案选择

采用“单一源码驱动开发镜像 + Docker Compose 运行模式”的方案。

未采用的方案：

1. 旧容器固化后继续开发：构建快，但依赖来源不透明、PX4 缺失、代码版本与宿主机分叉。
2. 多容器拆分 PX4/Gazebo 与算法栈：模块边界更清晰，但 ROS1、MAVLink UDP、Gazebo 插件和共享内存的跨容器协调复杂度过高。

## 5. 宿主机目录设计

全部项目相关内容集中在同一目录下：

```text
/home/rick/桌面/UAV_NUC/
├── src/                         # UAV_NUC 源码，Git 管理
├── sitl_sim/                    # 已有脚本、文档和入库证据
├── external/                    # 外部源码，不纳入 UAV_NUC Git
│   └── PX4-Autopilot/           # 干净、固定 v1.17.0
├── runtime/                     # 运行产物，不纳入 Git
│   ├── sitl_sim/                # bag、轮次结果、运行日志
│   ├── ros_logs/                # ~/.ros/log
│   └── migration/
│       └── noetic-sim-20261022/ # 旧容器迁移凭据
├── docker/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── dependencies/            # 显式依赖清单
├── .devcontainer/
│   └── devcontainer.json
└── compose.yaml
```

`.gitignore` 必须新增：

```gitignore
external/
runtime/
```

`external/` 中的 PX4 自身仍是独立 Git 仓库，但父仓库不追踪它。

## 6. 容器内目录与挂载

容器内继续使用源码现有脚本假定的历史路径：

| 宿主机 | 容器内 | 模式 |
|---|---|---|
| `/home/rick/桌面/UAV_NUC` | `/home/ghj/catkin_ws` | 读写 |
| `UAV_NUC/external/PX4-Autopilot` | `/home/ghj/PX4-Autopilot` | 读写 |
| `UAV_NUC/runtime/sitl_sim` | `/home/ghj/sitl_sim` | 读写 |
| `UAV_NUC/runtime/ros_logs` | `/home/ghj/.ros/log` | 读写 |

项目根挂载后，`external/` 和 `runtime/` 也会在 `/home/ghj/catkin_ws/` 下可见；独立挂载为旧脚本提供 `$HOME/PX4-Autopilot` 和 `$HOME/sitl_sim` 的稳定路径。

容器中创建用户 `ghj`。构建参数传入宿主机 UID/GID，使其与 `rick` 对齐，避免容器生成 root 所有的宿主机文件。

## 7. 镜像设计

### 7.1 基础镜像

使用：

```text
osrf/ros:noetic-desktop-full-focal
```

首次成功构建后记录解析出的镜像 digest，后续构建使用该 digest，防止同名 tag 漂移。

### 7.2 Dockerfile 职责

Dockerfile 只负责稳定环境，不复制项目源码：

1. 安装构建工具、ROS 包和 C++ 库。
2. 安装 PX4 v1.17 需要的 Python 依赖，约束 `empy>=3.3,<4`。
3. 安装并初始化 MAVROS GeographicLib 数据。
4. 安装 Xvfb、Mesa 与 headless 渲染依赖。
5. 创建 `ghj` 用户并处理 UID/GID。
6. 安装 VS Code Server 所需的基础工具。
7. 配置入口脚本，但不自动启动 PX4 或 Gazebo。

镜像构建不得执行 `catkin build`，也不得把宿主机源码烘焙进镜像。

### 7.3 入口脚本

`docker/entrypoint.sh` 负责：

- source `/opt/ros/noetic/setup.bash`；
- 若存在则 source `/home/ghj/catkin_ws/devel/setup.bash`；
- 创建运行目录；
- 设置 `ROS_DISTRO=noetic`、`ROS_MASTER_URI=http://localhost:11311`；
- 保留传入命令并以 `exec` 启动；
- 不隐式启动 roscore、PX4、Gazebo 或飞行脚本。

## 8. Compose 默认模式

服务名为 `sim-headless`，固定容器名为 `uav-sim-dev`。

核心配置：

- `network_mode: host`，避免 ROS1 与 MAVLink UDP 端口映射碎片化。
- `shm_size: 2gb`，降低 Gazebo 相机和共享内存不足风险。
- `stdin_open: true`、`tty: true`。
- `init: true`，改善子进程回收。
- `cap_add: SYS_PTRACE`，支持 GDB；不使用 `privileged`。
- `DISPLAY=:99`。
- 容器常驻命令为 `sleep infinity`，由用户或测试脚本显式启动仿真链。
- restart policy 为 `unless-stopped`，宿主机 Docker 重启后环境可恢复，但不会自动触发飞行流程。

默认启动命令：

```bash
cd /home/rick/桌面/UAV_NUC
docker compose up -d sim-headless
```

进入容器：

```bash
docker compose exec sim-headless bash
```

## 9. Headless 显示设计

默认模式使用容器内 Xvfb `:99`。启动仿真前保证：

```text
Xvfb :99 -screen 0 1280x1024x24
DISPLAY=:99
```

Xvfb 由显式辅助命令或项目现有 harness 启动，不在容器入口脚本中无条件常驻，以免与已有脚本的 `pgrep -x Xvfb` 管理逻辑冲突。

headless 验收以 `gzserver`、传感器话题和完整飞行链为准，不要求 `gzclient` 或 RViz 窗口显示。

## 10. PX4 管理

### 10.1 正源

PX4 从官方仓库克隆到：

```text
/home/rick/桌面/UAV_NUC/external/PX4-Autopilot
```

检出 `v1.17.0`，递归初始化该版本声明的 submodule。验收时必须同时记录：

- `git rev-parse HEAD`
- `git describe --tags --always`
- `git status --porcelain`
- submodule 状态

工作树必须为干净状态。宿主机已有 `/home/rick/UAV/PX4-Autopilot` 不参与新环境。

### 10.2 构建

PX4 在挂载后的源码目录内构建 `px4_sitl_default`。构建产物保留在宿主机，容器重建后可复用；任何依赖或工具链变化后必须允许全量重建。

## 11. catkin 构建

容器内以 catkin tools 作为标准构建入口，因为现有历史脚本引用 `devel/.private`，且旧环境安装了 catkin tools：

```bash
cd /home/ghj/catkin_ws
catkin config \
  --extend /opt/ros/noetic \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build
```

构建输出保留在宿主机工作树的 `build/`、`devel/`、`logs/`，这些路径已经被 Git 忽略。构建前后检查宿主机文件所有者，必须保持为宿主机用户可读写。

## 12. VS Code 集成

`.devcontainer/devcontainer.json` 复用 Compose 的 `sim-headless` 服务：

- `workspaceFolder`：`/home/ghj/catkin_ws`
- `remoteUser`：`ghj`
- 不再创建第二套镜像或第二个容器。
- 安装 ROS/C++/Python 开发扩展。
- 将 ROS Noetic、catkin `devel` 和项目 include 路径加入 IntelliSense。
- 排除 `build/`、`logs/` 和大体量运行数据的文件监听。

打开方式：

1. 宿主机 VS Code 打开 `/home/rick/桌面/UAV_NUC`。
2. 选择 `Dev Containers: Reopen in Container`。
3. VS Code 进入现有 `uav-sim-dev`；未运行时由 Compose 创建。

现有 `.vscode` 中的 ROS 2 Humble 配置不作为容器环境依据；Dev Container 使用独立的 Noetic 配置覆盖，不删除用户现有本地配置。

## 13. GPU 模式预留

GPU 模式未来使用同一镜像和同一挂载，仅增加：

- NVIDIA GPU 设备；
- 宿主机 X11 socket；
- 宿主机 `DISPLAY`；
- OpenGL renderer 验证；
- Gazebo GUI/RViz 验收。

本阶段不创建会诱导用户误认为已可运行的 GPU 服务，不安装 NVIDIA Container Toolkit。headless 验收完成后停止实施并报告 GPU 阶段前置条件。

## 14. 旧容器迁移与删除

删除流程必须按顺序执行，任一步失败都停止删除：

1. 将 `docker inspect noetic-sim`、容器日志、镜像信息和关键依赖清单写入 `runtime/migration/noetic-sim-20261022/`。
2. 创建恢复镜像：

   ```text
   noetic-sim:backup-20261022
   ```

3. 保存容器内 `catkin_ws` 的：
   - 所有 Git refs 的 bundle；
   - 当前分支和 HEAD；
   - `git status --porcelain=v1`；
   - staged、unstaged diff；
   - 未跟踪文件清单和未跟踪文件归档。
4. 保存 `feature/algorithm-development@b2b351b...`，验证 bundle 可列出并可在临时目录恢复。
5. 保存容器内独有的必要运行数据，至少包括 `vins_smoke_runs` 及其清单和校验值。
6. 从备份镜像创建临时验证容器，确认 `/home/ghj/catkin_ws` 和 `/home/ghj/sitl_sim` 可读。
7. 记录原容器 ID 后删除 `noetic-sim`。
8. 备份镜像保留到新 headless 环境全部验收完成；本阶段不删除该备份镜像。

旧容器数据不得直接覆盖当前宿主机 `main`。旧分支只作为迁移资产保存，后续是否合并另行审查。

## 15. 验证策略

验证按由低风险到高耦合的顺序进行。

### 15.1 静态配置验证

- `docker compose config` 成功。
- Dockerfile 可构建。
- `.gitignore` 正确忽略 `external/` 和 `runtime/`。
- 宿主机 `UAV_NUC` 原有 Git 工作树无意外源码修改。

### 15.2 镜像与用户验证

- 容器内为 Ubuntu 20.04、ROS Noetic、Gazebo 11。
- `ghj` UID/GID 与宿主机一致。
- 容器创建文件后宿主机可正常编辑和删除。
- ROS、MAVROS、Ceres、OpenCV、PCL、Eigen 和 Python 探针通过。

### 15.3 PX4 验证

- PX4 为干净的 `v1.17.0`。
- submodule 状态正确。
- `px4_sitl_default` 构建成功。
- 项目需要的 Gazebo Classic 模型和目标存在。

### 15.4 catkin 验证

- `catkin build` 零错误。
- 关键节点存在：VINS、px4ctrl、planner、bridge。
- `devel/setup.bash` 可 source。

### 15.5 Headless 启动验证

- Xvfb `:99` 可用。
- `gzserver`、PX4、roscore 和 MAVROS 无孤儿残留。
- MAVROS 与 PX4 的 14580 链路建立。
- 双目、IMU、深度、VINS odom、控制和规划关键话题出现。
- `env_health_check.sh --with-sitl` 的适用检查通过，警告逐项解释。

### 15.6 完整冒烟

按仓库现有 `00→04→06` 流程完成一次：

1. 环境检查。
2. PX4/Gazebo headless 启动。
3. MAVROS、VINS、px4ctrl、EGO-Planner 启动。
4. 起飞、悬停、降落。
5. 确认正常 disarm、关键话题持续、无残留进程。

验证只使用 SITL，不触发任何真机入口。

## 16. 故障处理与回滚

- 旧容器迁移校验失败：不删除旧容器。
- 新镜像构建失败：保留日志，修复 Dockerfile 后重建，不在运行容器内手工补包作为最终方案。
- PX4 v1.17 构建失败：核对官方 tag、submodule 和 Python 版本，不回退到宿主机脏的 v1.16 工作树。
- catkin 构建失败：以源码依赖和旧环境快照为依据补齐显式依赖，不通过复制旧二进制绕过。
- headless 冒烟失败：保留旧备份镜像和全部日志，新容器可删除重建。
- 宿主机源码所有权异常：停止构建，修复 UID/GID 设计，不使用递归 root 写入掩盖问题。

## 17. 安全边界

- 不启用 `privileged`。
- 不挂载 `/dev/bus/usb`、Pixhawk 串口或 D435。
- 不把宿主机 Docker socket 挂入容器。
- 不把 Git 凭据写入镜像。
- 不自动执行 arm、takeoff 或完整飞行脚本。
- `network_mode: host` 只用于本机 ROS1/MAVLink 仿真通信；验证时检查端口冲突。
- 旧容器 Git 分支不自动合并到 `main`。

## 18. 验收标准与暂停边界

本阶段同时满足以下条件才算完成：

1. 旧容器已形成可验证恢复件并安全删除。
2. 新环境可由 Dockerfile 和 Compose 从零重建。
3. 默认命令 `docker compose up -d sim-headless` 可直接启动开发容器。
4. VS Code 可直接 Reopen/Attach。
5. PX4 v1.17 和 catkin 工作空间构建成功。
6. headless 完整仿真链通过一次 `00→04→06` 冒烟。
7. 源码和运行数据全部位于宿主机，删除新容器后仍存在。
8. `UAV_NUC` Git 状态没有被构建产物或运行数据污染。

达到以上标准后立即暂停，不进入 GPU 阶段。交付报告应列出：镜像 ID、PX4 commit、UAV_NUC commit、依赖指纹、启动命令、验证结果、备份位置和 GPU 阶段尚未执行的前置条件。
