#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
PREPARE="$ROOT/docker/scripts/prepare_px4.sh"
BUILD="$ROOT/docker/scripts/build_workspace.sh"
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
  'config --extend /opt/ros/noetic --cmake-args -DCMAKE_BUILD_TYPE=Release' \
  'build --jobs 3' > "$TMP/expected.calls"
diff -u "$TMP/expected.calls" "$CATKIN_CALLS" || fail 'catkin invocation contract changed'

assert_fails missing_build env CATKIN_WS="$TMP/catkin ws" PX4_DIR="$TMP/px4 clean" "$VERIFY" --require-built

echo 'PASS: PX4 and catkin build helpers reject unsafe state'
