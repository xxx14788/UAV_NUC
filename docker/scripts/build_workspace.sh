#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

workspace=${CATKIN_WS:-/home/ghj/catkin_ws}
ros_setup=${ROS_SETUP:-/opt/ros/noetic/setup.bash}
[ "$(id -u)" -ne 0 ] || die 'refusing to build bind-mounted sources as root'
[ -f "$ros_setup" ] || die "ROS setup is missing: $ros_setup"
[ -d "$workspace/src" ] || die "catkin source directory is missing: $workspace/src"
command -v catkin >/dev/null 2>&1 || die 'catkin tools is not installed'

if [ -n "${CATKIN_JOBS:-}" ]; then
  jobs=$CATKIN_JOBS
else
  cpus=$(nproc)
  memory_kib=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
  memory_jobs=$((memory_kib / 2097152))
  [ "$memory_jobs" -ge 1 ] || memory_jobs=1
  jobs=$cpus
  [ "$jobs" -le "$memory_jobs" ] || jobs=$memory_jobs
  [ "$jobs" -le 8 ] || jobs=8
fi
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || die "CATKIN_JOBS must be a positive integer: $jobs"

set +u
source "$ros_setup"
set -u
cd "$workspace"
catkin config --extend /opt/ros/noetic --cmake-args -DCMAKE_BUILD_TYPE=Release
catkin build --jobs "$jobs"
