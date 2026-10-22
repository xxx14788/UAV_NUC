#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[ $# -eq 2 ] || die 'usage: sync_runtime_harness.sh SOURCE_REPO RUNTIME_DIR'

source_repo=$(realpath -e -- "$1" 2>/dev/null) || die "source repository does not exist: $1"
git_root=$(git -C "$source_repo" rev-parse --show-toplevel 2>/dev/null) \
  || die "source is not a Git repository: $source_repo"
git_root=$(realpath -e -- "$git_root")
[ "$source_repo" = "$git_root" ] || die 'SOURCE_REPO must be the Git worktree root'
[ -d "$source_repo/sitl_sim" ] || die "tracked harness directory missing: $source_repo/sitl_sim"

runtime_arg=$2
[ ! -L "$runtime_arg" ] || die 'runtime directory must not be a symbolic link'
mkdir -p -- "$runtime_arg"
runtime_dir=$(realpath -e -- "$runtime_arg")
[ "$runtime_dir" != / ] || die 'refusing filesystem root as runtime directory'

manifest_tmp=$(mktemp "$runtime_dir/.uav-sim-managed-files.tmp.XXXXXX")
trap 'rm -f -- "$manifest_tmp"' EXIT

count=0
while IFS= read -r -d '' tracked_path; do
  case "$tracked_path" in
    sitl_sim/*) relative=${tracked_path#sitl_sim/} ;;
    *) die "unexpected tracked path: $tracked_path" ;;
  esac
  case "$relative" in
    ''|/*|..|../*|*/..|*/../*|*$'\n'*) die "unsafe tracked path: $relative" ;;
  esac
  source_file="$source_repo/$tracked_path"
  [ -f "$source_file" ] && [ ! -L "$source_file" ] \
    || die "tracked harness entry is not a regular file: $tracked_path"
  target_file="$runtime_dir/$relative"
  mkdir -p -- "$(dirname -- "$target_file")"
  install -p -m "$(stat -c '%a' "$source_file")" -- "$source_file" "$target_file"
  printf '%s\n' "$relative" >> "$manifest_tmp"
  count=$((count + 1))
done < <(git -C "$source_repo" ls-files -z -- sitl_sim)

[ "$count" -gt 0 ] || die 'Git contains no tracked sitl_sim harness files'
mv -f -- "$manifest_tmp" "$runtime_dir/.uav-sim-managed-files"
trap - EXIT
printf 'Synchronized %d tracked harness files into %s\n' "$count" "$runtime_dir"
