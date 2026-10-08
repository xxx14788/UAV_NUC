#!/usr/bin/env bash
# Start PX4 v1.17 SITL with the measured UAV_NUC Gazebo Classic model.

set -u

PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
DISPLAY="${DISPLAY:-:1}"
XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"

if [ ! -d "$PX4_DIR" ]; then
  echo "PX4 directory not found: $PX4_DIR" >&2
  exit 1
fi

if pgrep -x px4 >/dev/null 2>&1; then
  echo "PX4 SITL is already running; instance 0 is unavailable:" >&2
  pgrep -a -x px4 >&2
  echo "Stop the existing simulation first, then run this script again." >&2
  exit 2
fi

if pgrep -x gzserver >/dev/null 2>&1 || pgrep -x gzclient >/dev/null 2>&1; then
  echo "Gazebo Classic is already running:" >&2
  pgrep -a -x gzserver >&2 || true
  pgrep -a -x gzclient >&2 || true
  echo "Close the existing Gazebo session first, then run this script again." >&2
  exit 2
fi

if [ -f /opt/ros/noetic/setup.bash ]; then
  set +u
  # shellcheck disable=SC1091
  . /opt/ros/noetic/setup.bash
  set -u
fi

export DISPLAY XAUTHORITY
export PX4_SITL_WORLD=uav_nuc_preview
# The stock PX4 GUI plugin calls TrackVisual every frame, which prevents
# manual camera zoom. Disable it for this close-up inspection world.
export PX4_GZ_DISABLE_CAMERA_TRACKING=1

cd "$PX4_DIR" || exit 1
exec make px4_sitl gazebo-classic_uav_nuc
