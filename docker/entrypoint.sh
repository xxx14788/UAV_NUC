#!/usr/bin/env bash
set -Eeuo pipefail

workspace=/home/ghj/catkin_ws
runtime=/home/ghj/sitl_sim

[ -d "$workspace/sitl_sim" ] || {
  echo "ERROR: expected project bind mount at $workspace" >&2
  exit 1
}
mkdir -p "$runtime" /home/ghj/.ros/log
/usr/local/bin/sync_runtime_harness.sh "$workspace" "$runtime"

set +u
source /opt/ros/noetic/setup.bash
if [ -f "$workspace/devel/setup.bash" ]; then
  source "$workspace/devel/setup.bash"
fi
set -u

export ROS_DISTRO=noetic
export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}
exec "$@"
