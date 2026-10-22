#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

px4_dir=${PX4_DIR:-/home/ghj/PX4-Autopilot}
repository=${PX4_REPOSITORY:-https://github.com/PX4/PX4-Autopilot.git}
tag=${PX4_TAG:-v1.17.0}

if [ ! -e "$px4_dir" ] || { [ -d "$px4_dir" ] && [ -z "$(find "$px4_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]; }; then
  mkdir -p -- "$(dirname -- "$px4_dir")"
  git clone --branch "$tag" --recurse-submodules "$repository" "$px4_dir"
else
  [ -d "$px4_dir/.git" ] || die "existing PX4_DIR is not a Git checkout: $px4_dir"
fi

actual_remote=$(git -C "$px4_dir" remote get-url origin 2>/dev/null) \
  || die 'PX4 checkout has no origin remote'
[ "$actual_remote" = "$repository" ] \
  || die "PX4 origin mismatch: expected $repository, found $actual_remote"
[ -z "$(git -C "$px4_dir" status --porcelain=v1)" ] \
  || die 'PX4 checkout is dirty; refusing to reset or overwrite it'

tag_commit=$(git -C "$px4_dir" rev-parse "refs/tags/$tag^{commit}" 2>/dev/null) \
  || die "PX4 tag is unavailable locally: $tag"
head_commit=$(git -C "$px4_dir" rev-parse HEAD)
[ "$head_commit" = "$tag_commit" ] \
  || die "PX4 HEAD is not $tag; refusing to change an existing checkout"

git -C "$px4_dir" submodule sync --recursive
git -C "$px4_dir" submodule update --init --recursive
[ -z "$(git -C "$px4_dir" status --porcelain=v1)" ] \
  || die 'PX4 checkout became dirty after submodule initialization'
if git -C "$px4_dir" submodule status --recursive | grep -Eq '^[-+U]'; then
  die 'PX4 submodule state is incomplete or does not match the pinned commit'
fi

printf 'PX4_DIR=%s\n' "$px4_dir"
printf 'PX4_TAG=%s\n' "$tag"
printf 'PX4_COMMIT=%s\n' "$head_commit"
