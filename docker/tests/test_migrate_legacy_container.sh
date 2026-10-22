#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
SUT="$ROOT/docker/scripts/migrate_legacy_container.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_fails() {
  local label=$1; shift
  if "$@" >"$TMP/${label}.out" 2>&1; then
    fail "$label: expected failure"
  fi
}
assert_no_rm() {
  ! grep -q '^rm ' "$DOCKER_LOG" || fail "unexpected docker rm: $(grep '^rm ' "$DOCKER_LOG")"
}

mkdir -p "$TMP/bin" "$TMP/git-src"
cat > "$TMP/bin/dpkg-query" <<'FAKE_DPKG'
#!/usr/bin/env bash
printf 'fake-package\t1\n'
FAKE_DPKG
chmod +x "$TMP/bin/dpkg-query"
git -C "$TMP/git-src" init -q
git -C "$TMP/git-src" config user.name test
git -C "$TMP/git-src" config user.email test@example.invalid
echo legacy > "$TMP/git-src/legacy.txt"
git -C "$TMP/git-src" add legacy.txt
git -C "$TMP/git-src" commit -qm 'legacy commit'
EXPECTED_LEGACY_HEAD=$(git -C "$TMP/git-src" rev-parse HEAD)
git -C "$TMP/git-src" branch feature/algorithm-development
git -C "$TMP/git-src" bundle create "$TMP/valid.bundle" --all >/dev/null

cat > "$TMP/bin/docker" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
echo "$*" >> "$DOCKER_LOG"
cmd=${1:-}; shift || true
case "$cmd" in
  inspect)
    [ "${FAKE_EXISTS:-1}" = 1 ] || exit 1
    if [ "${1:-}" = "--type" ]; then shift 2; fi
    if [ "${1:-}" = "--format" ]; then
      fmt=$2
      case "$fmt" in
        *Config.Image*) echo 'osrf/ros:noetic-desktop-full-focal' ;;
        *) echo "${FAKE_CONTAINER_ID}" ;;
      esac
    else
      printf '[{"Id":"%s"}]\n' "$FAKE_CONTAINER_ID"
    fi
    ;;
  logs) echo 'legacy log' ;;
  commit) echo "${FAKE_BACKUP_IMAGE_ID}" ;;
  image)
    [ "${1:-}" = inspect ] || exit 64
    shift
    if [ "${1:-}" = "--format" ]; then echo "${FAKE_BACKUP_IMAGE_ID}"; else echo '[{"RepoTags":["backup"]}]'; fi
    ;;
  run)
    joined=" $* "
    if [[ "$joined" == *"git bundle create"* ]]; then
      snapshot_script=${!#}
      format_command=$(printf '%s\n' "$snapshot_script" | grep '^dpkg-query ')
      format_command=${format_command/\/backup\/dpkg.tsv/$TEST_TMP\/dpkg-probe.tsv}
      bash -uc "$format_command" >/dev/null
      mount=''
      while [ $# -gt 0 ]; do
        if [ "$1" = -v ]; then mount=${2%%:*}; shift 2; continue; fi
        shift
      done
      [ -n "$mount" ] || exit 65
      cp "$FAKE_VALID_BUNDLE" "$mount/catkin_ws.bundle"
      printf 'feature/algorithm-development\n' > "$mount/current-branch.txt"
      printf '%s\n' "$EXPECTED_LEGACY_HEAD" > "$mount/head.txt"
      : > "$mount/git-status.txt"
      : > "$mount/staged.diff"
      : > "$mount/unstaged.diff"
      : > "$mount/untracked-files.list"
      tar -czf "$mount/untracked-files.tar.gz" --files-from /dev/null
      tar -czf "$mount/vins_smoke_runs.tar.gz" --files-from /dev/null
      printf 'pkg\t1\n' > "$mount/dpkg.tsv"
      printf 'pip==1\n' > "$mount/pip-freeze.txt"
    else
      [ "${FAKE_DIRS_READABLE:-1}" = 1 ] || exit 66
    fi
    ;;
  rm) : ;;
  *) echo "unsupported fake docker command: $cmd $*" >&2; exit 67 ;;
esac
FAKE
chmod +x "$TMP/bin/docker"

export PATH="$TMP/bin:$PATH"
export DOCKER_LOG="$TMP/docker.log"
export TEST_TMP="$TMP"
export FAKE_CONTAINER_ID='sha256:container-one'
export FAKE_BACKUP_IMAGE_ID='sha256:image-one'
export FAKE_VALID_BUNDLE="$TMP/valid.bundle"
export EXPECTED_LEGACY_HEAD
export FAKE_EXISTS=1
export FAKE_DIRS_READABLE=1

assert_fails missing_container env FAKE_EXISTS=0 "$SUT" backup \
  --container noetic-sim --output "$TMP/missing" --backup-image noetic-sim:backup-test

: > "$DOCKER_LOG"
out="$TMP/migration"
"$SUT" backup --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
test -s "$out/catkin_ws.bundle" || fail 'backup did not save bundle'
test -s "$out/SHA256SUMS" || fail 'backup did not save checksums'
[ "$(stat -c %u "$out/catkin_ws.bundle")" = "$(id -u)" ] || fail 'backup artifact has wrong owner'

cp "$out/catkin_ws.bundle" "$out/catkin_ws.bundle.good"
printf 'not a bundle\n' > "$out/catkin_ws.bundle"
(cd "$out" && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name verified.ok ! -name 'catkin_ws.bundle.good' -printf '%P\0' | sort -z | xargs -0 sha256sum > SHA256SUMS)
assert_fails bad_bundle "$SUT" verify \
  --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
assert_no_rm
mv "$out/catkin_ws.bundle.good" "$out/catkin_ws.bundle"
(cd "$out" && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name verified.ok -printf '%P\0' | sort -z | xargs -0 sha256sum > SHA256SUMS)

assert_fails no_receipt "$SUT" delete \
  --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
assert_no_rm

assert_fails unreadable_restore env FAKE_DIRS_READABLE=0 "$SUT" verify \
  --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
assert_no_rm

"$SUT" verify --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
test -s "$out/verified.ok" || fail 'verify did not create receipt'

assert_fails changed_id env FAKE_CONTAINER_ID=sha256:container-two "$SUT" delete \
  --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
assert_no_rm

"$SUT" delete --container noetic-sim --output "$out" --backup-image noetic-sim:backup-test
grep -qx 'rm noetic-sim' "$DOCKER_LOG" || fail 'exact container was not removed'
! grep -q '^image rm ' "$DOCKER_LOG" || fail 'backup image was removed'
test -s "$out/deleted.ok" || fail 'delete receipt missing'

echo 'PASS: migration state machine guards destructive deletion'
