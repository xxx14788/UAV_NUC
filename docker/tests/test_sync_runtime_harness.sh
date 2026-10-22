#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
SUT="$ROOT/docker/scripts/sync_runtime_harness.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

repo="$TMP/带空格 与中文/repo"
runtime="$TMP/运行 数据"
mkdir -p "$repo/sitl_sim/nested" "$runtime/vins_smoke_runs" "$runtime/logs"
git -C "$repo" init -q
git -C "$repo" config user.name test
git -C "$repo" config user.email test@example.invalid
printf '#!/usr/bin/env bash\necho tracked-v2\n' > "$repo/sitl_sim/runner.sh"
chmod 755 "$repo/sitl_sim/runner.sh"
printf 'tracked config\n' > "$repo/sitl_sim/nested/config.yaml"
printf 'must not copy\n' > "$repo/sitl_sim/untracked.txt"
git -C "$repo" add sitl_sim/runner.sh sitl_sim/nested/config.yaml
git -C "$repo" commit -qm 'tracked harness'

printf 'stale tracked content\n' > "$runtime/runner.sh"
printf 'keep run evidence\n' > "$runtime/vins_smoke_runs/KEEP"
printf 'keep bag\n' > "$runtime/flight.bag"
printf 'keep log\n' > "$runtime/logs/session.log"

"$SUT" "$repo" "$runtime"

grep -qx 'echo tracked-v2' "$runtime/runner.sh" || fail 'tracked script was not refreshed'
[ -x "$runtime/runner.sh" ] || fail 'executable mode was not preserved'
grep -qx 'tracked config' "$runtime/nested/config.yaml" || fail 'nested tracked file missing'
[ ! -e "$runtime/untracked.txt" ] || fail 'source untracked file was copied'
grep -qx 'keep run evidence' "$runtime/vins_smoke_runs/KEEP" || fail 'runtime evidence was changed'
grep -qx 'keep bag' "$runtime/flight.bag" || fail 'bag was changed'
grep -qx 'keep log' "$runtime/logs/session.log" || fail 'log was changed'
printf 'nested/config.yaml\nrunner.sh\n' > "$TMP/expected-manifest"
diff -u "$TMP/expected-manifest" "$runtime/.uav-sim-managed-files" \
  || fail 'managed manifest is not deterministic'

printf 'echo tracked-v3\n' >> "$repo/sitl_sim/runner.sh"
"$SUT" "$repo" "$runtime"
grep -qx 'echo tracked-v3' "$runtime/runner.sh" || fail 'second sync did not refresh tracked file'
grep -qx 'keep run evidence' "$runtime/vins_smoke_runs/KEEP" || fail 'second sync changed runtime evidence'

if "$SUT" "$TMP/not-a-repo" "$runtime" >/dev/null 2>&1; then
  fail 'non-repository source was accepted'
fi

echo 'PASS: tracked harness sync preserves runtime-only data'
