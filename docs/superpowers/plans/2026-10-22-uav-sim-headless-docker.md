# UAV 仿真默认无头 Docker 环境实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 安全迁移并删除旧 `noetic-sim`，在宿主机保留全部源码与运行数据，交付可由 Docker Compose 和 VS Code 直接使用、通过完整 SITL 冒烟的 ROS Noetic 默认无头环境。

**Architecture:** 使用单一源码驱动镜像承载 Ubuntu 20.04、ROS Noetic、Gazebo Classic 和构建依赖；Compose 把 `UAV_NUC`、固定 `v1.17.0` 的 PX4 以及运行目录绑定挂载到固定历史路径。旧容器先形成镜像、Git、未跟踪文件和运行数据四层恢复件再删除；默认服务只保持开发容器常驻，仿真由显式 harness 启动。

**Tech Stack:** Docker Engine、Docker Compose v2、Ubuntu 20.04、ROS Noetic、Gazebo Classic 11、MAVROS、PX4-Autopilot v1.17.0、catkin tools、Bash、VS Code Dev Containers。

**Spec:** `docs/superpowers/specs/2026-10-22-uav-sim-docker-design.md`

## Global Constraints

- 本阶段只实现并验收 `sim-headless`；headless 全部验收后立即暂停，不安装 NVIDIA Container Toolkit，不启动 GPU/GUI 模式。
- 不启用 `privileged`，不挂载 Docker socket、USB、D435、Pixhawk 或串口。
- 源码和运行数据必须留在 `/home/rick/桌面/UAV_NUC`；镜像不得复制项目源码。
- 容器用户固定为 `ghj`，其 UID/GID 必须与宿主机用户 `rick` 一致。
- 容器路径固定为 `/home/ghj/catkin_ws`、`/home/ghj/PX4-Autopilot`、`/home/ghj/sitl_sim` 和 `/home/ghj/.ros/log`。
- PX4 必须来自官方仓库、固定 `v1.17.0`、递归初始化 submodule，并保持干净；不得复用 `/home/rick/UAV/PX4-Autopilot`。
- 删除旧容器前，恢复镜像、Git bundle、差异/未跟踪文件、运行数据和临时恢复验证必须全部成功。
- `network_mode: host`、`shm_size: 2gb`、`DISPLAY=:99`、`restart: unless-stopped`；容器入口不得自动 arm、takeoff 或启动完整仿真。
- 运行期间只允许 SITL；任何真机入口、设备探测和真机配置均不执行。
- 每个 Git 工作单元提交前检查 staged 内容，提交后立即推送并核对 `origin/main`。

## Review Focus

- 旧容器分支提交不在宿主机对象库：Task 1 的假 Docker 测试与 Task 2 的 `git bundle verify/list-heads` 必须证明 `b2b351b...` 可恢复，失败时拒绝删除。
- `$HOME/sitl_sim` 同时承担 harness 双副本和运行输出：Task 3 测试只同步 Git 跟踪文件、不使用 `--delete`，并验证 `vins_smoke_runs/` 哨兵不被覆盖或删除。
- 宿主机 UID/GID 或中文路径引起权限/插值错误：Task 4 静态测试和 Task 6 文件往返测试必须覆盖真实绝对路径和所有者。
- `network_mode: host` 下已有 ROS/MAVLink/Gazebo 进程或端口冲突：Task 9 必须在启动前运行零残留/端口检查，冲突时停止而非强杀不明进程。
- 基础镜像 tag 与依赖随时间漂移：Task 6 必须记录镜像 digest、包版本和探针输出，并将成功基线的基础镜像改为 digest 固定后重建。

---

### Task 1: 旧容器迁移工具与删除闸门

**Files:**
- Create: `docker/scripts/migrate_legacy_container.sh`
- Create: `docker/tests/test_migrate_legacy_container.sh`
- Create: `docker/README.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Docker CLI；旧容器名、迁移输出目录和备份镜像 tag。
- Produces: `migrate_legacy_container.sh backup|verify|delete --container NAME --output DIR --backup-image TAG`；`verify` 成功后生成 `verified.ok`，`delete` 只接受匹配原容器 ID 的有效凭据。

- [ ] **Step 1: 写迁移状态机的失败测试**

在假 `docker` 可执行文件与临时目录上覆盖：容器不存在时 `backup` 失败；bundle 缺目标提交时 `verify` 失败；无 `verified.ok`、容器 ID 改变或临时恢复容器读不到两个目录时 `delete` 拒绝；完整备份链成功时只删除精确容器名，不删除备份镜像。

- [ ] **Step 2: 运行测试并确认失败**

Run: `bash docker/tests/test_migrate_legacy_container.sh`

Expected: FAIL，原因是 `docker/scripts/migrate_legacy_container.sh` 尚不存在。

- [ ] **Step 3: 先隔离外部源码与运行数据**

在 `.gitignore` 增加根路径 `/external/` 与 `/runtime/`，并用 `git check-ignore -v runtime/probe external/probe` 确认迁移产物在生成前已被隔离。

- [ ] **Step 4: 实现三阶段迁移脚本**

`backup` 保存 `docker inspect/logs/image inspect`、`dpkg/pip`、当前分支与 HEAD、所有 refs 的 bundle、staged/unstaged diff、未跟踪清单及归档、`vins_smoke_runs` 归档与 SHA-256 清单，并执行 `docker commit`。所有路径均需 canonicalize 到指定输出目录内，不接受空目录、`/`、`$HOME` 或符号链接逃逸。

`verify` 执行 `git bundle verify`、检查目标 HEAD `b2b351bde07dca7faefe115307e1db0b1de3ba78`、验证归档校验值，并从备份镜像创建临时容器读取 `/home/ghj/catkin_ws` 与 `/home/ghj/sitl_sim`；全部成功后写入含原容器 ID、备份镜像 ID 和时间戳的 `verified.ok`。

`delete` 重新解析容器 ID 与凭据逐字匹配，只执行 `docker rm noetic-sim`，保留备份镜像。

- [ ] **Step 5: 运行迁移工具测试**

Run: `bash docker/tests/test_migrate_legacy_container.sh`

Expected: PASS，且测试断言删除闸门的每个失败分支均没有发出 `docker rm`。

- [ ] **Step 6: Shell 静态检查**

Run: `bash -n docker/scripts/migrate_legacy_container.sh docker/tests/test_migrate_legacy_container.sh`

Expected: exit 0。

- [ ] **Step 7: 更新操作文档并提交**

在 `docker/README.md` 写明三阶段命令、恢复方法、不会自动合并旧分支，以及任何校验失败都必须保留原容器。

Run: `git status --short && git diff --check && git diff --cached --stat`

Commit: `chore: 增加旧容器安全迁移工具`

随后 push，并验证 `git rev-parse HEAD` 等于 `git rev-parse origin/main`。

### Task 2: 备份并删除旧 `noetic-sim`

**Files:**
- Create outside Git: `runtime/migration/noetic-sim-20261022/**`
- Create Docker image: `noetic-sim:backup-20261022`
- Delete only after verification: Docker container `noetic-sim`

**Interfaces:**
- Consumes: Task 1 的迁移脚本及当前旧容器。
- Produces: 可独立恢复的迁移目录、备份镜像、删除收据；旧容器名释放。

- [ ] **Step 1: 记录执行前精确对象**

Run: `docker inspect --format '{{.Id}} {{.Name}} {{.Config.Image}} {{.State.Status}}' noetic-sim`

Expected: 唯一目标为 `/noetic-sim`；把 ID 人工与先前审计结果对账。若对象不存在或身份变化，停止本 Task。

- [ ] **Step 2: 执行备份阶段**

Run: `bash docker/scripts/migrate_legacy_container.sh backup --container noetic-sim --output /home/rick/桌面/UAV_NUC/runtime/migration/noetic-sim-20261022 --backup-image noetic-sim:backup-20261022`

Expected: exit 0；目录中存在 inspect、日志、依赖清单、bundle、diff、未跟踪归档、运行数据归档和 checksums。

- [ ] **Step 3: 执行独立验证阶段**

Run: `bash docker/scripts/migrate_legacy_container.sh verify --container noetic-sim --output /home/rick/桌面/UAV_NUC/runtime/migration/noetic-sim-20261022 --backup-image noetic-sim:backup-20261022`

Expected: exit 0；`verified.ok` 存在；`git bundle list-heads` 可见 `feature/algorithm-development` 或目标提交；临时容器验证结果为 PASS。

- [ ] **Step 4: 删除前做最后只读检查**

Run: `docker ps -a --filter name='^/noetic-sim$' --no-trunc && docker image inspect noetic-sim:backup-20261022 --format '{{.Id}}' && sha256sum -c runtime/migration/noetic-sim-20261022/SHA256SUMS`

Expected: 容器 ID 与 `verified.ok` 一致，镜像存在，校验全通过。

- [ ] **Step 5: 通过闸门删除旧容器**

Run: `bash docker/scripts/migrate_legacy_container.sh delete --container noetic-sim --output /home/rick/桌面/UAV_NUC/runtime/migration/noetic-sim-20261022 --backup-image noetic-sim:backup-20261022`

Expected: `noetic-sim` 不再存在；`noetic-sim:backup-20261022` 仍存在；删除收据记录原 ID。

- [ ] **Step 6: 做可恢复性复核**

从备份镜像启动一个带随机名称且只读的临时容器，读取两个关键目录后删除临时容器；再次执行 `git bundle verify`。任何失败都在继续新环境前报告，但不删除备份镜像或迁移目录。

### Task 3: Harness 正本到运行目录的受控同步

**Files:**
- Create: `docker/scripts/sync_runtime_harness.sh`
- Create: `docker/tests/test_sync_runtime_harness.sh`
- Modify: `docker/README.md`

**Interfaces:**
- Consumes: Git 工作树 `/home/ghj/catkin_ws` 和运行根 `/home/ghj/sitl_sim`。
- Produces: `sync_runtime_harness.sh SOURCE_REPO RUNTIME_DIR`；只复制 `git ls-files sitl_sim` 返回的文件，不清空运行目录。

- [ ] **Step 1: 写同步边界测试**

临时 Git 仓库中建立 tracked harness、untracked 文件和运行目录 `vins_smoke_runs/KEEP`。断言同步后 tracked 文件内容更新，源仓库 untracked 文件未复制，运行哨兵与已有 bag/log 未删除，路径含空格和中文时仍成功。

- [ ] **Step 2: 运行测试并确认失败**

Run: `bash docker/tests/test_sync_runtime_harness.sh`

Expected: FAIL，原因是同步脚本不存在。

- [ ] **Step 3: 实现同步脚本**

脚本以 NUL 分隔读取 `git -C "$SOURCE_REPO" ls-files -z -- sitl_sim`，逐个创建父目录并用 `install`/`rsync` 保留 mode；拒绝 `..` 和绝对路径；不使用广义 `--delete`；将本次清单写为 `$RUNTIME_DIR/.uav-sim-managed-files`。仓库 `sitl_sim` 是唯一正本，运行目录中的同名受管文件允许被刷新，其他文件不得触碰。

- [ ] **Step 4: 运行测试与静态检查**

Run: `bash docker/tests/test_sync_runtime_harness.sh && bash -n docker/scripts/sync_runtime_harness.sh`

Expected: PASS。

- [ ] **Step 5: 文档说明双副本契约并提交**

说明每次容器启动会刷新受管 harness，实验输出继续保存在 `runtime/sitl_sim`，本地修改必须回写仓库正本而不是改 runtime 副本。

Commit: `chore: 固化仿真运行脚本同步契约`

Push 后核对远端 HEAD。

### Task 4: 默认 headless 镜像、入口与 Compose

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/entrypoint.sh`
- Create: `docker/dependencies/apt.txt`
- Create: `docker/dependencies/python.txt`
- Create: `docker/tests/test_static_contracts.sh`
- Create: `compose.yaml`
- Modify: `docker/README.md`

**Interfaces:**
- Consumes: 宿主机 `UID`/`GID` build args、四个 bind mount、Task 3 同步脚本。
- Produces: Compose service `sim-headless`、container `uav-sim-dev`；入口 source ROS/devel、同步 harness、创建目录后 `exec "$@"`。

- [ ] **Step 1: 写静态契约失败测试**

测试至少断言：`.gitignore` 精确忽略 `/external/`、`/runtime/`；Compose 只有 `sim-headless`，包含四个挂载、host network、2 GB shm、`SYS_PTRACE`、`DISPLAY=:99`、非 privileged、无 devices/Docker socket、`sleep infinity`；Dockerfile 不含 `COPY src`/`catkin build`；入口最终使用 `exec` 且不启动 roscore/PX4/Gazebo/飞行命令。

- [ ] **Step 2: 运行静态测试并确认失败**

Run: `bash docker/tests/test_static_contracts.sh`

Expected: FAIL，缺少 Dockerfile/Compose/依赖清单。

- [ ] **Step 3: 添加显式依赖清单**

`apt.txt` 固定包名，覆盖 build-essential、cmake、ninja-build、ccache、git、rsync、catkin-tools、MAVROS/extras、Gazebo 11 开发包、Eigen/OpenCV/PCL/Ceres/SuiteSparse/gflags/glog、Xvfb/Mesa、GeographicLib 工具和常用调试工具。`python.txt` 固定 PX4 所需 Python 包范围，明确 `empy>=3.3,<4`，不得无约束升级到 empy 4。

- [ ] **Step 4: 实现 Dockerfile**

从 `osrf/ros:noetic-desktop-full-focal` 开始，非交互安装清单、Python 依赖和 GeographicLib 数据；创建 `ghj` 并使 UID/GID 来自 build args；配置 sudo 仅供开发必要命令；复制 docker 自身脚本，不复制 UAV 源码；设置 entrypoint。

- [ ] **Step 5: 实现入口脚本**

入口以 `ghj` 权限创建运行目录，调用 Task 3 同步，source `/opt/ros/noetic/setup.bash` 及可选 devel，导出 `ROS_MASTER_URI`/`ROS_DISTRO`，最后 `exec "$@"`。同步失败必须阻止容器进入伪可用状态；不存在挂载时给出清晰错误。

- [ ] **Step 6: 实现 Compose 默认服务**

使用 `${LOCAL_UID:-1000}`/`${LOCAL_GID:-1000}` build args；宿主机相对路径绑定到四个约定路径；保持唯一服务名与容器名；不定义 GPU profile 或 GUI 服务。

- [ ] **Step 7: 运行静态与解析测试**

Run: `bash docker/tests/test_static_contracts.sh && LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose config --quiet`

Expected: 两条命令均 exit 0。

- [ ] **Step 8: 检查差异并提交**

Run: `git status --short && git diff --check && git diff --cached --stat`

Commit: `feat: 搭建默认无头仿真容器`

Push 后核对远端 HEAD。

### Task 5: PX4 与 catkin 可复现准备命令

**Files:**
- Create: `docker/scripts/prepare_px4.sh`
- Create: `docker/scripts/build_workspace.sh`
- Create: `docker/scripts/verify_environment.sh`
- Create: `docker/tests/test_build_helpers.sh`
- Modify: `docker/README.md`

**Interfaces:**
- Consumes: `PX4_DIR`（默认 `/home/ghj/PX4-Autopilot`）、`CATKIN_WS`（默认 `/home/ghj/catkin_ws`）。
- Produces: 幂等的 PX4 clone/tag/submodule/cleanliness gate、catkin Release 构建命令、机器可读环境探针报告。

- [ ] **Step 1: 写 helper 的失败测试**

用本地临时 Git remote 验证：空目录可检出指定 tag；已有脏目录、错误 remote、错误 tag 均拒绝；正确 tag 重跑幂等。用假的 `catkin` 记录参数，断言只调用 `catkin config --extend /opt/ros/noetic --cmake-args -DCMAKE_BUILD_TYPE=Release` 和 `catkin build`。

- [ ] **Step 2: 运行测试并确认失败**

Run: `bash docker/tests/test_build_helpers.sh`

Expected: FAIL，helper 尚不存在。

- [ ] **Step 3: 实现 `prepare_px4.sh`**

默认克隆 `https://github.com/PX4/PX4-Autopilot.git`，检出 `v1.17.0`，递归同步/更新 submodule；已有目录必须是该官方 remote、目标 tag 的提交且干净，否则只报错，不 reset、不覆盖。

- [ ] **Step 4: 实现 `build_workspace.sh`**

验证 ROS setup 与 `src/` 存在，配置 catkin tools 的 Release profile 后构建；并行度允许由 `CATKIN_JOBS` 显式覆盖，默认根据内存保守计算，不写 root 所有文件。

- [ ] **Step 5: 实现 `verify_environment.sh`**

输出 Ubuntu、ROS、Gazebo、MAVROS、gcc/cmake、Python/empy、Eigen/OpenCV/PCL/Ceres、当前 UID/GID、挂载可写性、PX4 commit/status/submodules、catkin setup 的结构化文本；`--require-built` 时缺少 PX4 binary 或 `devel/setup.bash` 返回非零。

- [ ] **Step 6: 运行测试并提交**

Run: `bash docker/tests/test_build_helpers.sh && bash -n docker/scripts/prepare_px4.sh docker/scripts/build_workspace.sh docker/scripts/verify_environment.sh`

Expected: PASS。

Commit: `chore: 增加 PX4 与 catkin 可复现构建命令`

Push 后核对远端 HEAD。

### Task 6: 构建镜像、固定基线并验证默认容器

**Files:**
- Modify after first successful build: `docker/Dockerfile`（基础镜像 tag 改为解析出的 digest）
- Create outside Git: `runtime/migration/noetic-sim-20261022/new-environment/`

**Interfaces:**
- Consumes: Tasks 3–5 的 Docker 配置与宿主机 Docker Engine。
- Produces: 已固定基础镜像 digest 的新镜像、运行中的 `uav-sim-dev` 和环境/权限验收证据。

- [ ] **Step 1: 建立宿主机运行目录**

创建精确目录 `external/`、`runtime/sitl_sim/`、`runtime/ros_logs/` 和证据目录，确认所有者为 `rick` 的实际 UID/GID；不得递归改动仓库已有源码所有权。

- [ ] **Step 2: 首次构建镜像**

Run: `LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose build --pull sim-headless`

Expected: exit 0；构建日志保存到 runtime 证据目录。

- [ ] **Step 3: 解析并固定基础镜像 digest**

读取 `osrf/ros:noetic-desktop-full-focal` 的 repo digest，确认非空且为 `sha256:`；将 Dockerfile 的 `FROM` 改为 `osrf/ros:noetic-desktop-full-focal@sha256:...`，再次构建并运行静态测试。

- [ ] **Step 4: 启动默认服务**

Run: `LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up -d sim-headless`

Expected: 容器名 `uav-sim-dev`，状态 running，命令为 `sleep infinity`，没有自动出现 PX4/Gazebo/roscore/arm 进程。

- [ ] **Step 5: 验证用户和四个挂载**

在容器内断言 `id -u/-g` 与宿主机一致、四个路径为 mountpoint/可写；容器创建测试文件后宿主机所有者为 `rick`，再由宿主机删除。断言中文宿主机路径未被 Compose 截断。

- [ ] **Step 6: 验证依赖并保存指纹**

Run: `docker compose exec -T sim-headless bash -lc 'docker/scripts/verify_environment.sh'`

Expected: 基础探针全通过；把输出、`docker image inspect`、`dpkg-query` 和 `pip freeze` 保存到 new-environment 证据目录。

- [ ] **Step 7: 回归默认启动**

执行 `docker compose down` 后再次 `docker compose up -d sim-headless`；确认源码、运行目录哨兵和受管 harness 仍存在，容器仍未自动启动仿真。

- [ ] **Step 8: 提交 digest 固定**

Run: `git status --short && git diff --check && git diff --cached --stat`

Commit: `build: 固定无头仿真基础镜像`

Push 后核对远端 HEAD。

### Task 7: VS Code Dev Containers 集成

**Files:**
- Create: `.devcontainer/devcontainer.json`
- Modify: `docker/tests/test_static_contracts.sh`
- Modify: `docker/README.md`

**Interfaces:**
- Consumes: Compose service `sim-headless`。
- Produces: VS Code 以 `ghj` 打开 `/home/ghj/catkin_ws`，不创建第二镜像/第二容器。

- [ ] **Step 1: 扩展静态测试并确认失败**

断言 devcontainer 使用 `../compose.yaml`、service `sim-headless`、workspaceFolder `/home/ghj/catkin_ws`、remoteUser `ghj`、`shutdownAction: none`，并配置 ROS/C++/Python 扩展和 build/log/runtime watcher exclusions。

Run: `bash docker/tests/test_static_contracts.sh`

Expected: FAIL，缺少 devcontainer 配置。

- [ ] **Step 2: 写 `devcontainer.json`**

复用现有 Compose；设置 Noetic 环境和 CMake/catkin include 搜索路径；保留宿主机 `.vscode`，不删除或改写其 ROS 2 Humble 配置。

- [ ] **Step 3: 运行静态测试并做 CLI 级验证**

Run: `bash docker/tests/test_static_contracts.sh && docker compose config --quiet`

Expected: PASS。若宿主机已安装 Dev Containers CLI，则额外执行 `devcontainer read-configuration --workspace-folder /home/rick/桌面/UAV_NUC`；否则记录为需在 GUI 完成的验收项，不伪报已验证。

- [ ] **Step 4: 提交并推送**

Commit: `feat: 集成 VS Code 无头仿真容器`

Push 后核对远端 HEAD。

### Task 8: PX4 v1.17 与 catkin 全量构建

**Files:**
- Create outside Git: `external/PX4-Autopilot/**`
- Create outside Git: `build/`, `devel/`, `logs/`
- Create outside Git: `runtime/migration/noetic-sim-20261022/new-environment/{px4,catkin}/**`

**Interfaces:**
- Consumes: 已运行的 `sim-headless`、Task 5 helper。
- Produces: 干净 PX4 v1.17.0、`px4_sitl_default`、完整 catkin devel space 与构建日志。

- [ ] **Step 1: 检查资源与 Git 洁净度**

记录磁盘、内存、CPU、当前 Git HEAD/status；确认 free space 满足 PX4+catkin 全量构建预算。若空间低于设计时的安全余量，停止并报告，不清理用户数据。

- [ ] **Step 2: 准备 PX4 v1.17.0**

Run: `docker compose exec -T sim-headless bash -lc '/usr/local/bin/prepare_px4.sh'`

Expected: 官方 remote、`git describe --tags --always` 为 `v1.17.0`、status 为空、submodule 无 `-`/`+`/`U` 前缀；保存 commit 与 submodule 清单。

- [ ] **Step 3: 构建 PX4 SITL**

Run: `docker compose exec -T sim-headless bash -lc 'cd "$HOME/PX4-Autopilot" && make px4_sitl_default'`

Expected: exit 0，生成 PX4 SITL binary；保存完整日志。随后核对项目使用的 `gazebo-classic_iris_stereo_vins` target/model/world 资产存在。

- [ ] **Step 4: 构建 catkin 工作空间**

Run: `docker compose exec -T sim-headless bash -lc '/usr/local/bin/build_workspace.sh'`

Expected: `catkin build` 零 error，`devel/setup.bash` 存在；保存 build summary。

- [ ] **Step 5: 验证关键 ROS 资源**

source devel 后用 `rospack find`/`roslaunch --files` 验证 VINS、px4ctrl、ego_planner、bridge 及相关 launch；运行 `verify_environment.sh --require-built`。

- [ ] **Step 6: 验证所有权与仓库污染**

在宿主机检查新建 build/devel/external/runtime 文件没有 root 所有项；`git status --short` 不出现外部源码或运行数据，只允许本 Task 前已知的追踪文件修改。

### Task 9: Headless 链路与完整飞行冒烟

**Files:**
- Create outside Git: `runtime/migration/noetic-sim-20261022/new-environment/smoke/**`
- Modify only if a reproducible environment defect is found: `docker/**`
- Modify after successful run: `docs/flight_log.md`

**Interfaces:**
- Consumes: Task 8 的 PX4/catkin 构建、仓库现有 `env_health_check.sh` 与 `vins_smoke.sh`。
- Produces: Xvfb/PX4/Gazebo/MAVROS/VINS/controller/planner 的运行证据，以及一次起飞—悬停—降落—disarm 成功记录。

- [ ] **Step 1: 做非破坏性现场检查**

在宿主机与容器中记录 `pgrep`、11311 TCP 和 14540/14580 UDP 占用。若发现不属于本容器的进程或端口所有者，停止并报告；不得以 broad `pkill` 清除宿主机未知工作负载。

- [ ] **Step 2: 验证 Xvfb 和最小 SITL**

容器内启动 `Xvfb :99 -screen 0 1280x1024x24`，确认 display 可用；按仓库脚本启动 PX4/Gazebo VINS 机型，验证 `gzserver`、PX4、双目、IMU 和深度话题出现，且不要求 `gzclient`。

- [ ] **Step 3: 验证 MAVROS 链路和健康检查**

启动 MAVROS，断言 `/mavros/state` 中 `connected: True`，确认 14580 链路；运行 `bash "$HOME/sitl_sim/env_health_check.sh" --with-sitl`。FAIL 必须修复；WARN 逐项记录解释，不把 WARN 静默当 PASS。

- [ ] **Step 4: 运行权威完整冒烟**

优先使用现有 `vins_smoke.sh` 的标准 world、短预算和唯一 tag 完成五件套、起飞、悬停/目标段、planner 清场、降落和自动 disarm；该脚本包含项目已验证的投递重试、锁和清场逻辑，比手工并行执行 `00/01/02/03/04/06` 更接近仓库权威流程。

Expected: `RESULT.txt` 给出成功判定；`/mavros/state` 最终 `armed: False`；关键话题持续；cleanup 后 PX4、gzserver、roscore、MAVROS、VINS、px4ctrl 和 planner 无残留。

- [ ] **Step 5: 对照 `00→04→06` 验收语义**

保存 `00_env_check` 报告；从权威冒烟日志中明确映射 01 启动、02 MAVROS、03 控制器、04 TAKEOFF 和 06 LAND/disarm 各阶段结果。若权威 harness 因环境之外的算法判据红项失败，不伪报容器失败或成功：保留证据并区分环境链路与算法表现，再按设计回滚/修复环境部分。

- [ ] **Step 6: 登记飞行记录并提交必要修复**

在 `docs/flight_log.md` 追加日期、运行目录、时长、headless、PX4/UAV commit、结果和异常。若为补齐依赖或容器脚本而修改 `docker/**`，先增加回归测试再提交。

Commit: `docs: 记录无头仿真环境验收`

Push 后核对远端 HEAD。

### Task 10: 最终复现、交付报告与暂停

**Files:**
- Create: `docs/uav_sim_headless_acceptance_20261022.md`
- Modify: `docker/README.md`

**Interfaces:**
- Consumes: Tasks 2、6、8、9 的全部证据。
- Produces: 可复现启动说明、验收矩阵、恢复入口和明确的 GPU 阶段暂停声明。

- [ ] **Step 1: 从停止态复现默认命令**

Run: `docker compose down && LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up -d sim-headless && docker compose exec -T sim-headless bash -lc 'id; test -f /opt/ros/noetic/setup.bash; test -f "$HOME/catkin_ws/devel/setup.bash"; test -x "$HOME/PX4-Autopilot/build/px4_sitl_default/bin/px4"'`

Expected: 单条默认 `up` 命令恢复开发容器，核心构建产物与宿主机数据仍在。

- [ ] **Step 2: 编写验收报告**

记录镜像 ID、基础镜像 digest、PX4 commit/tag/status、UAV_NUC commit、UID/GID、依赖指纹、构建结果、smoke 结果、启动/进入/VS Code 命令、旧容器备份位置、已删除容器 ID、备份镜像 ID，以及所有 WARN/未决项。

- [ ] **Step 3: 明确暂停边界**

报告中明确：NVIDIA Container Toolkit 未安装、GPU/GUI service 未创建、Gazebo GUI/RViz 未验收；后续 GPU 模式必须另立计划。不得为“顺手验证”修改宿主机 Docker runtime 或 GPU 配置。

- [ ] **Step 4: 全量回归检查**

Run: `bash docker/tests/test_migrate_legacy_container.sh && bash docker/tests/test_sync_runtime_harness.sh && bash docker/tests/test_static_contracts.sh && bash docker/tests/test_build_helpers.sh && docker compose config --quiet && git diff --check && git status --short`

Expected: 所有测试通过；Git 只包含计划中的验收文档改动；`external/`、`runtime/`、build/devel/logs 不污染 Git。

- [ ] **Step 5: 提交、推送并核对**

Commit: `docs: 交付默认无头仿真环境`

Push 后运行 `git fetch origin main && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"`。

- [ ] **Step 6: 到此暂停**

保持 `uav-sim-dev` 可直接使用并保留 `noetic-sim:backup-20261022`；向用户交付报告链接、默认启动命令和 VS Code 打开方法，不进入 GPU 阶段。
