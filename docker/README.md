# UAV 仿真 Docker 环境

本目录是 ROS Noetic + PX4 SITL 默认无头开发环境的可复现配置正本。项目源码、PX4 外部源码和运行数据都保留在宿主机，不烘焙到镜像。

## 旧容器迁移

迁移严格分为 `backup`、`verify`、`delete` 三阶段。任一校验失败都不得删除旧容器。

```bash
OUT=/home/rick/桌面/UAV_NUC/runtime/migration/noetic-sim-20261022
bash docker/scripts/migrate_legacy_container.sh backup \
  --container noetic-sim --output "$OUT" \
  --backup-image noetic-sim:backup-20261022
bash docker/scripts/migrate_legacy_container.sh verify \
  --container noetic-sim --output "$OUT" \
  --backup-image noetic-sim:backup-20261022
bash docker/scripts/migrate_legacy_container.sh delete \
  --container noetic-sim --output "$OUT" \
  --backup-image noetic-sim:backup-20261022
```

`verify` 会校验 SHA-256、Git bundle 中的旧 HEAD，并从备份镜像启动临时容器读取两个关键目录。只有它生成与容器 ID 和镜像 ID 匹配的 `verified.ok`，`delete` 才会删除精确名为 `noetic-sim` 的容器。备份镜像不会删除。

恢复时可用 `noetic-sim:backup-20261022` 启动临时容器，或在空 Git 仓库中执行 `git fetch <catkin_ws.bundle> refs/heads/feature/algorithm-development` 恢复旧分支。该分支只是迁移资产，不会自动合并到当前 `main`。

## Harness 双副本契约

Git 跟踪的 `sitl_sim/` 是脚本和配置的唯一正本；宿主机 `runtime/sitl_sim/` 是容器内 `$HOME/sitl_sim` 的运行副本，同时保存 bag、轮次结果和日志。

```bash
docker/scripts/sync_runtime_harness.sh \
  /home/rick/桌面/UAV_NUC \
  /home/rick/桌面/UAV_NUC/runtime/sitl_sim
```

同步只复制 `git ls-files sitl_sim` 列出的受管文件，并记录在 `.uav-sim-managed-files`；不使用广义 `--delete`，不会删除 `vins_smoke_runs/`、bag 或日志。容器启动时会刷新受管文件，因此不应直接修改 runtime 副本；修改必须回写 Git 正本。

## 默认 headless 容器

首次构建和启动：

```bash
cd /home/rick/桌面/UAV_NUC
mkdir -p external/PX4-Autopilot runtime/sitl_sim runtime/ros_logs
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose build sim-headless
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up -d sim-headless
docker compose exec sim-headless bash
```

默认容器名为 `uav-sim-dev`，常驻命令只是 `sleep infinity`。入口脚本会同步 harness 并 source ROS/catkin 环境，但不会自动启动仿真或执行飞行。

停止和重建容器不会删除宿主机的代码、PX4、bag 和 ROS 日志。本阶段不包含 GPU、Gazebo GUI 或 RViz 配置。
