#!/usr/bin/env bash
set -uo pipefail

require_built=0
case "${1:-}" in
  '') ;;
  --require-built) require_built=1 ;;
  *) echo "ERROR: usage: verify_environment.sh [--require-built]" >&2; exit 2 ;;
esac

workspace=${CATKIN_WS:-/home/ghj/catkin_ws}
px4_dir=${PX4_DIR:-/home/ghj/PX4-Autopilot}
runtime=${SITL_RUNTIME:-/home/ghj/sitl_sim}
failures=0
pass() { printf 'PASS\t%s\t%s\n' "$1" "$2"; }
fail() { printf 'FAIL\t%s\t%s\n' "$1" "$2"; failures=$((failures + 1)); }
info() { printf 'INFO\t%s\t%s\n' "$1" "$2"; }
need_cmd() {
  local cmd=$1
  if command -v "$cmd" >/dev/null 2>&1; then pass "cmd.$cmd" "$(command -v "$cmd")"; else fail "cmd.$cmd" missing; fi
}

if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  info os "${ID:-unknown} ${VERSION_ID:-unknown}"
else
  fail os /etc/os-release-missing
fi
info identity "uid=$(id -u) gid=$(id -g) user=$(id -un)"

if [ -f /opt/ros/noetic/setup.bash ]; then
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/noetic/setup.bash
  set -u
  pass ros.setup /opt/ros/noetic/setup.bash
else
  fail ros.setup missing
fi

for cmd in gcc g++ cmake git python3 pip3 catkin gazebo gzserver rosversion rospack; do need_cmd "$cmd"; done
if command -v rosversion >/dev/null 2>&1 && [ "$(rosversion -d 2>/dev/null)" = noetic ]; then
  pass ros.distro noetic
else
  fail ros.distro "${ROS_DISTRO:-unknown}"
fi
if command -v gazebo >/dev/null 2>&1; then info gazebo.version "$(gazebo --version 2>/dev/null | head -n1)"; fi
if command -v rospack >/dev/null 2>&1 && mavros_path=$(rospack find mavros 2>/dev/null); then
  pass ros.mavros "$mavros_path"
else
  fail ros.mavros missing
fi

if python3 - <<'PY' >/tmp/uav-python-probe.txt 2>&1
import em, numpy, yaml, jinja2, packaging, pymavlink
assert hasattr(em, "RAW_OPT")
print("python modules ok; empy=" + getattr(em, "__version__", "unknown"))
PY
then pass python.modules "$(tail -n1 /tmp/uav-python-probe.txt)"; else fail python.modules "$(tail -n1 /tmp/uav-python-probe.txt)"; fi
rm -f /tmp/uav-python-probe.txt

[ -f /usr/include/eigen3/Eigen/Core ] && pass cpp.eigen /usr/include/eigen3 || fail cpp.eigen missing
pkg-config --exists opencv4 2>/dev/null && pass cpp.opencv "$(pkg-config --modversion opencv4)" || fail cpp.opencv missing
pcl_pkg=
for candidate in pcl_common pcl_common-1.10; do
  if pkg-config --exists "$candidate" 2>/dev/null; then pcl_pkg=$candidate; break; fi
done
if [ -n "$pcl_pkg" ]; then
  pass cpp.pcl "$(pkg-config --modversion "$pcl_pkg") ($pcl_pkg)"
else
  fail cpp.pcl missing
fi
if dpkg-query -W -f='${Status} ${Version}' libceres-dev 2>/dev/null | grep -q '^install ok installed '; then
  pass cpp.ceres "$(dpkg-query -W -f='${Version}' libceres-dev)"
else
  fail cpp.ceres missing
fi

for path in "$workspace" "$px4_dir" "$runtime"; do
  if [ -d "$path" ] && probe=$(mktemp "$path/.uav-write-probe.XXXXXX" 2>/dev/null); then
    rm -f "$probe"
    pass "write.$path" ok
  else
    fail "write.$path" unavailable
  fi
done

if [ -d "$px4_dir/.git" ]; then
  info px4.commit "$(git -C "$px4_dir" rev-parse HEAD 2>/dev/null)"
  info px4.describe "$(git -C "$px4_dir" describe --tags --always 2>/dev/null)"
  if [ -z "$(git -C "$px4_dir" status --porcelain=v1 2>/dev/null)" ]; then pass px4.clean yes; else fail px4.clean no; fi
  if git -C "$px4_dir" submodule status --recursive 2>/dev/null | grep -Eq '^[-+U]'; then fail px4.submodules mismatch; else pass px4.submodules matched; fi
else
  info px4.checkout not-prepared
fi

if [ "$require_built" -eq 1 ]; then
  [ -x "$px4_dir/build/px4_sitl_default/bin/px4" ] && pass px4.binary present || fail px4.binary missing
  [ -f "$workspace/devel/setup.bash" ] && pass catkin.devel present || fail catkin.devel missing
else
  [ -f "$workspace/devel/setup.bash" ] && info catkin.devel present || info catkin.devel not-built
fi

info result "failures=$failures"
[ "$failures" -eq 0 ]
