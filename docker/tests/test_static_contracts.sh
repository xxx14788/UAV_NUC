#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
cd "$ROOT"
fail() { echo "FAIL: $*" >&2; exit 1; }

for path in compose.yaml .dockerignore docker/Dockerfile docker/entrypoint.sh \
            docker/dependencies/apt.txt docker/dependencies/python.txt \
            .devcontainer/devcontainer.json; do
  [ -s "$path" ] || fail "missing required file: $path"
done

git check-ignore -q runtime/probe || fail '/runtime/ is not ignored'
git check-ignore -q external/probe || fail '/external/ is not ignored'

compose_json=$(mktemp)
trap 'rm -f "$compose_json"' EXIT
LOCAL_UID=1234 LOCAL_GID=2345 docker compose config --format json > "$compose_json"
python3 - "$compose_json" "$ROOT" <<'PY'
import json, os, sys

cfg = json.load(open(sys.argv[1]))
root = os.path.realpath(sys.argv[2])
assert set(cfg["services"]) == {"sim-headless"}, cfg["services"].keys()
svc = cfg["services"]["sim-headless"]
assert svc["container_name"] == "uav-sim-dev"
assert svc["network_mode"] == "host"
assert int(svc["shm_size"]) == 2 * 1024**3
assert svc["stdin_open"] is True and svc["tty"] is True and svc["init"] is True
assert svc["restart"] == "unless-stopped"
assert svc.get("privileged", False) is False
assert not svc.get("devices")
assert svc["cap_add"] == ["SYS_PTRACE"]
assert svc["environment"]["DISPLAY"] == ":99"
assert svc["environment"]["ROS_DISTRO"] == "noetic"
assert svc["environment"]["ROS_VERSION"] == "1"
assert svc["environment"]["ROS_PYTHON_VERSION"] == "3"
assert svc["environment"]["CMAKE_PREFIX_PATH"] == "/opt/ros/noetic"
assert svc["environment"]["PYTHONPATH"] == "/opt/ros/noetic/lib/python3/dist-packages"
assert svc["environment"]["ROS_PACKAGE_PATH"] == "/opt/ros/noetic/share"
assert svc["environment"]["PATH"].split(":")[0] == "/opt/ros/noetic/bin"
assert svc["command"] == ["sleep", "infinity"]
assert svc["working_dir"] == "/home/ghj/catkin_ws"
args = svc["build"]["args"]
assert args["USER_UID"] == "1234" and args["USER_GID"] == "2345"
mounts = {v["target"]: os.path.realpath(v["source"]) for v in svc["volumes"]}
assert mounts == {
    "/home/ghj/catkin_ws": root,
    "/home/ghj/PX4-Autopilot": os.path.join(root, "external/PX4-Autopilot"),
    "/home/ghj/sitl_sim": os.path.join(root, "runtime/sitl_sim"),
    "/home/ghj/.ros/log": os.path.join(root, "runtime/ros_logs"),
}, mounts
assert all("docker.sock" not in v["source"] for v in svc["volumes"])
PY

python3 - .devcontainer/devcontainer.json <<'PY'
import json, sys

cfg = json.load(open(sys.argv[1]))
assert cfg["dockerComposeFile"] == "../compose.yaml"
assert cfg["service"] == "sim-headless"
assert cfg["workspaceFolder"] == "/home/ghj/catkin_ws"
assert cfg["remoteUser"] == "ghj"
assert cfg["shutdownAction"] == "none"
assert "image" not in cfg and "build" not in cfg
vscode = cfg["customizations"]["vscode"]
extensions = set(vscode["extensions"])
assert {"ms-iot.vscode-ros", "ms-vscode.cpptools", "ms-python.python"} <= extensions
watchers = vscode["settings"]["files.watcherExclude"]
for path in ("**/build/**", "**/logs/**", "**/runtime/**"):
    assert watchers.get(path) is True, path
includes = vscode["settings"]["C_Cpp.default.includePath"]
assert "/opt/ros/noetic/include" in includes
assert "${containerWorkspaceFolder}/devel/include" in includes
assert cfg["remoteEnv"]["ROS_DISTRO"] == "noetic"
PY

grep -qxF '**' .dockerignore || fail '.dockerignore must default-deny build context'
grep -qxF '!docker/**' .dockerignore || fail '.dockerignore must allow docker assets'
if grep -Eiq '^[[:space:]]*COPY[[:space:]].*(src|sitl_sim|external|runtime)' docker/Dockerfile; then
  fail 'Dockerfile copies project source/runtime data'
fi
if grep -Eiq 'catkin[_ -]?build|catkin_make' docker/Dockerfile; then
  fail 'Dockerfile builds the catkin workspace'
fi
grep -q '^empy>=3\.3,<4$' docker/dependencies/python.txt || fail 'empy range is not pinned below v4'
grep -q 'Acquire::Retries.*5' docker/Dockerfile || fail 'APT download retries are not configured'
grep -q 'Acquire::http::Timeout.*60' docker/Dockerfile || fail 'APT HTTP timeout is not configured'
grep -q 'pip install --retries 10 --timeout 60' docker/Dockerfile || fail 'pip retries and timeout are not configured'
if grep -q "pip install.*setuptools" docker/Dockerfile; then
  fail 'Dockerfile unnecessarily replaces the distro setuptools package'
fi
run_count=$(grep -c '^RUN ' docker/Dockerfile)
[ "$run_count" -ge 5 ] || fail 'networked install phases are not split into cacheable layers'
for pkg in build-essential python3-catkin-tools ros-noetic-mavros ros-noetic-mavros-extras \
           gazebo11 libgazebo11-dev libeigen3-dev libopencv-dev libpcl-dev libceres-dev \
           libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
           libsuitesparse-dev libgflags-dev libgoogle-glog-dev xvfb mesa-utils geographiclib-tools \
           ros-noetic-ddynamic-reconfigure; do
  grep -qx "$pkg" docker/dependencies/apt.txt || fail "missing apt dependency: $pkg"
done
grep -q '/home/ghj/\.ros /home/ghj/\.ros/log' docker/Dockerfile \
  || fail 'Dockerfile does not give the developer ownership of the .ros parent directory'
grep -Fq '/usr/local/bin/run_px4_vins_sitl.sh' sitl_sim/start_sitl_vins.sh \
  || fail 'VINS launcher must use the clean-PX4 runtime overlay helper'
[ -x sitl_sim/gzserver ] \
  || fail 'PATH-prepended Gazebo ROS wrapper is not installed under the gzserver command name'
grep -Fq 'gzserver_wrapper.sh' sitl_sim/gzserver \
  || fail 'gzserver command entry does not delegate to the ROS system-plugin wrapper'
if grep -Fq 'tail -1 | grep -oE' sitl_sim/env_health_check.sh; then
  fail 'health check discards the average-rate line before parsing rostopic hz output'
fi
if grep -Eq "pkill[^\n]*sleep infinit" sitl_sim/vins_smoke.sh; then
  fail 'smoke cleanup can kill the container sleep-infinity PID 1'
fi
grep -Fq 'pkill -TERM -P "$HBPID"' sitl_sim/vins_smoke.sh \
  || fail 'smoke cleanup leaves the heartbeat sleep child orphaned'
python3 - <<'PY'
from pathlib import Path
text = Path("sitl_sim/vins_smoke.sh").read_text()
final_log = text.rfind('LOG "轮完成 bag=$BAG"')
final_cleanup = text.rfind('\ncleanup\n')
assert final_log >= 0 and final_cleanup >= 0 and final_log < final_cleanup, \
    "smoke writes to its process-substitution pipe after cleanup kills tee"
PY
grep -Fq 'depth_camera.sdf.jinja' sitl_sim/env_health_check.sh \
  || fail 'health check does not derive the depth-rate contract from the pinned PX4 model'
grep -Fq 'DEPTH_MIN_FACTOR:-0.8' sitl_sim/env_health_check.sh \
  || fail 'health check lacks the declared model-relative depth-rate floor'
[ -s src/stereo_depth_bridge/CMakeLists.txt ] \
  || fail 'stereo_depth_bridge is not a buildable catkin package'
grep -q '<buildtool_depend>catkin</buildtool_depend>' src/stereo_depth_bridge/package.xml \
  || fail 'stereo_depth_bridge does not declare the catkin build tool'

grep -q 'exec "\$@"' docker/entrypoint.sh || fail 'entrypoint does not exec the requested command'
if grep -Eiq '(^|[[:space:]])(roscore|roslaunch|px4|gzserver|gazebo|04_takeoff)([[:space:]]|$)' docker/entrypoint.sh; then
  fail 'entrypoint implicitly starts simulation or flight commands'
fi
bash -n docker/entrypoint.sh

echo 'PASS: default headless container contracts'
