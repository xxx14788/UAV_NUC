#!/usr/bin/env bash
# 启动 PX4 SITL + Gazebo Classic 11（headless，不启动 GUI）。
# 退出：在本终端 Ctrl-C。
set -u
cd "$HOME/PX4-Autopilot" || { echo "找不到 ~/PX4-Autopilot"; exit 1; }
export HEADLESS=1     # 不启动 Gazebo Classic UI：NoMachine 软件渲染下更稳、更省资源
echo "[sitl] PX4: $(git describe --tags 2>/dev/null)  HEADLESS=$HEADLESS"
exec make px4_sitl gazebo-classic
