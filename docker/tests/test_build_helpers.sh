#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
PREPARE="$ROOT/docker/scripts/prepare_px4.sh"
BUILD="$ROOT/docker/scripts/build_workspace.sh"
RUN_PX4="$ROOT/docker/scripts/run_px4_vins_sitl.sh"
VERIFY="$ROOT/docker/scripts/verify_environment.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_fails() {
  local label=$1; shift
  if "$@" >"$TMP/$label.out" 2>&1; then fail "$label: expected failure"; fi
}

mkdir -p "$TMP/upstream"
git -C "$TMP/upstream" init -q
git -C "$TMP/upstream" config user.name test
git -C "$TMP/upstream" config user.email test@example.invalid
printf 'v1.17\n' > "$TMP/upstream/version.txt"
git -C "$TMP/upstream" add version.txt
git -C "$TMP/upstream" commit -qm 'v1.17 baseline'
git -C "$TMP/upstream" tag v1.17.0
baseline=$(git -C "$TMP/upstream" rev-parse v1.17.0^{commit})
printf 'newer\n' >> "$TMP/upstream/version.txt"
git -C "$TMP/upstream" commit -qam 'main moves on'
git -C "$TMP/upstream" clone -q --bare . "$TMP/PX4-Autopilot.git"
repo="file://$TMP/PX4-Autopilot.git"

PX4_DIR="$TMP/px4 clean" PX4_REPOSITORY="$repo" PX4_TAG=v1.17.0 "$PREPARE"
[ "$(git -C "$TMP/px4 clean" rev-parse HEAD)" = "$baseline" ] || fail 'wrong tag was checked out'
[ -z "$(git -C "$TMP/px4 clean" status --porcelain)" ] || fail 'fresh PX4 checkout is dirty'
PX4_DIR="$TMP/px4 clean" PX4_REPOSITORY="$repo" PX4_TAG=v1.17.0 "$PREPARE"

printf 'dirty\n' >> "$TMP/px4 clean/version.txt"
assert_fails dirty_tree env PX4_DIR="$TMP/px4 clean" PX4_REPOSITORY="$repo" PX4_TAG=v1.17.0 "$PREPARE"
git -C "$TMP/px4 clean" restore version.txt

git -C "$TMP/px4 clean" remote set-url origin file:///wrong/repository.git
assert_fails wrong_remote env PX4_DIR="$TMP/px4 clean" PX4_REPOSITORY="$repo" PX4_TAG=v1.17.0 "$PREPARE"
git -C "$TMP/px4 clean" remote set-url origin "$repo"

git -C "$TMP/px4 clean" fetch -q origin master:refs/remotes/origin/master
wrong_head=$(git -C "$TMP/px4 clean" rev-parse refs/remotes/origin/master)
git -C "$TMP/px4 clean" checkout -q --detach "$wrong_head"
assert_fails wrong_commit env PX4_DIR="$TMP/px4 clean" PX4_REPOSITORY="$repo" PX4_TAG=v1.17.0 "$PREPARE"
[ "$(git -C "$TMP/px4 clean" rev-parse HEAD)" = "$wrong_head" ] || fail 'wrong commit was silently reset'

mkdir -p "$TMP/bin" "$TMP/catkin ws/src"
printf '# ROS test setup\n' > "$TMP/ros-setup.bash"
cat > "$TMP/bin/catkin" <<'FAKE_CATKIN'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$CATKIN_CALLS"
FAKE_CATKIN
chmod +x "$TMP/bin/catkin"
export CATKIN_CALLS="$TMP/catkin.calls"
PATH="$TMP/bin:$PATH" CATKIN_WS="$TMP/catkin ws" ROS_SETUP="$TMP/ros-setup.bash" CATKIN_JOBS=3 "$BUILD"
printf '%s\n' \
  'config --extend /opt/ros/noetic --skiplist realsense2_camera realsense2_description rviz_plugins --cmake-args -DCMAKE_BUILD_TYPE=Release' \
  'build --jobs 3' > "$TMP/expected.calls"
diff -u "$TMP/expected.calls" "$CATKIN_CALLS" || fail 'catkin invocation contract changed'

mkdir -p \
  "$TMP/px4 overlay/ROMFS/px4fmu_common/init.d-posix/airframes" \
  "$TMP/px4 overlay/Tools/simulation/gazebo-classic/sitl_gazebo-classic" \
  "$TMP/px4 overlay/build/px4_sitl_default/bin" \
  "$TMP/px4 overlay/build/px4_sitl_default/etc/init.d-posix/airframes" \
  "$TMP/sitl runtime/models/iris_stereo_vins" \
  "$TMP/sitl runtime/models/stereo_vins_rig" \
  "$TMP/sitl runtime/worlds"
printf '/build/\n' > "$TMP/px4 overlay/.gitignore"
printf '# generated simulator artifacts\n' > "$TMP/px4 overlay/Tools/simulation/gazebo-classic/sitl_gazebo-classic/.gitignore"
printf '#!/bin/sh\necho iris\n' > "$TMP/px4 overlay/ROMFS/px4fmu_common/init.d-posix/airframes/10015_gazebo-classic_iris"
printf '#!/bin/sh\nexit 0\n' > "$TMP/px4 overlay/build/px4_sitl_default/bin/px4"
printf '<sdf/>\n' > "$TMP/sitl runtime/models/iris_stereo_vins/iris_stereo_vins.sdf"
printf '<sdf/>\n' > "$TMP/sitl runtime/models/stereo_vins_rig/stereo_vins_rig.sdf"
printf '<sdf/>\n' > "$TMP/sitl runtime/worlds/test_world.world"
cat > "$TMP/px4 overlay/Tools/simulation/gazebo-classic/sitl_run.sh" <<'FAKE_SITL_RUN'
#!/usr/bin/env bash
printf 'args=%s\n' "$*" > "$PX4_RUN_CALLS"
printf 'model_path=%s\n' "$GAZEBO_MODEL_PATH" >> "$PX4_RUN_CALLS"
printf 'world=%s\n' "$PX4_SITL_WORLD" >> "$PX4_RUN_CALLS"
FAKE_SITL_RUN
chmod +x \
  "$TMP/px4 overlay/build/px4_sitl_default/bin/px4" \
  "$TMP/px4 overlay/Tools/simulation/gazebo-classic/sitl_run.sh"
cat > "$TMP/bin/cmake" <<'FAKE_CMAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$PX4_CMAKE_CALLS"
printf 'generated/by/cmake\n' >> "$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic/.gitignore"
mkdir -p "$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/uuv_bluerov2_heavy"
printf '<sdf generated="true"/>\n' > "$PX4_DIR/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/uuv_bluerov2_heavy/uuv_bluerov2_heavy.sdf"
FAKE_CMAKE
chmod +x "$TMP/bin/cmake"
git -C "$TMP/px4 overlay" init -q
git -C "$TMP/px4 overlay" config user.name test
git -C "$TMP/px4 overlay" config user.email test@example.invalid
git -C "$TMP/px4 overlay" add .
git -C "$TMP/px4 overlay" commit -qm 'clean PX4 fixture'
export PX4_CMAKE_CALLS="$TMP/px4-cmake.calls"
export PX4_RUN_CALLS="$TMP/px4-run.calls"
PATH="$TMP/bin:$PATH" PX4_DIR="$TMP/px4 overlay" SITL_SIM_DIR="$TMP/sitl runtime" PX4_BUILD_JOBS=2 \
  "$RUN_PX4" --prepare-only
diff -u \
  "$TMP/px4 overlay/ROMFS/px4fmu_common/init.d-posix/airframes/10015_gazebo-classic_iris" \
  "$TMP/px4 overlay/build/px4_sitl_default/etc/init.d-posix/airframes/1090_gazebo-classic_iris_stereo_vins" \
  || fail 'generated VINS airframe does not preserve the official Iris defaults'
grep -Fqx -- '--build '"$TMP/px4 overlay/build/px4_sitl_default"' --target sitl_gazebo-classic -- -j 2' "$PX4_CMAKE_CALLS" \
  || fail 'Gazebo Classic plugin build contract changed'
[ -z "$(git -C "$TMP/px4 overlay" status --porcelain --untracked-files=all)" ] \
  || fail 'Gazebo build side effects were left in the PX4 source tree'

printf 'local edit\n' >> "$TMP/px4 overlay/ROMFS/px4fmu_common/init.d-posix/airframes/10015_gazebo-classic_iris"
assert_fails dirty_px4_overlay env PATH="$TMP/bin:$PATH" PX4_DIR="$TMP/px4 overlay" \
  SITL_SIM_DIR="$TMP/sitl runtime" PX4_BUILD_JOBS=2 "$RUN_PX4" --prepare-only
git -C "$TMP/px4 overlay" restore .

PATH="$TMP/bin:$PATH" PX4_DIR="$TMP/px4 overlay" SITL_SIM_DIR="$TMP/sitl runtime" PX4_BUILD_JOBS=2 SITL_WORLD=test_world \
  "$RUN_PX4"
grep -Fq 'iris_stereo_vins none '"$TMP/px4 overlay $TMP/px4 overlay/build/px4_sitl_default" "$PX4_RUN_CALLS" \
  || fail 'SITL launcher arguments changed'
grep -Fqx 'model_path='"$TMP/sitl runtime/models" "$PX4_RUN_CALLS" \
  || fail 'project model path is not exported'
grep -Fqx 'world='"$TMP/sitl runtime/worlds/test_world.world" "$PX4_RUN_CALLS" \
  || fail 'named project world was not resolved to an absolute path'

assert_fails missing_world env PATH="$TMP/bin:$PATH" PX4_DIR="$TMP/px4 overlay" SITL_SIM_DIR="$TMP/sitl runtime" SITL_WORLD=missing "$RUN_PX4"

assert_fails missing_build env CATKIN_WS="$TMP/catkin ws" PX4_DIR="$TMP/px4 clean" "$VERIFY" --require-built

grep -q 'pcl_common-1\.10' "$VERIFY" || fail 'PCL probe does not support Ubuntu 20.04 versioned pkg-config name'

echo 'PASS: PX4, Gazebo Classic and catkin helpers reject unsafe state'
