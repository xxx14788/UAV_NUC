#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

px4_dir=${PX4_DIR:-/home/ghj/PX4-Autopilot}
sitl_dir=${SITL_SIM_DIR:-/home/ghj/sitl_sim}
build_dir=${PX4_BUILD_DIR:-$px4_dir/build/px4_sitl_default}
source_airframe=$px4_dir/ROMFS/px4fmu_common/init.d-posix/airframes/10015_gazebo-classic_iris
overlay_airframe=$build_dir/etc/init.d-posix/airframes/1090_gazebo-classic_iris_stereo_vins
sitl_run=$px4_dir/Tools/simulation/gazebo-classic/sitl_run.sh
gazebo_source=$px4_dir/Tools/simulation/gazebo-classic/sitl_gazebo-classic
generated_uuv_sdf=models/uuv_bluerov2_heavy/uuv_bluerov2_heavy.sdf
px4_bin=$build_dir/bin/px4

[ "${1:-}" = "" ] || [ "$1" = "--prepare-only" ] || die "unsupported argument: $1"
[ -x "$px4_bin" ] || die "PX4 SITL binary is missing: $px4_bin"
[ -x "$sitl_run" ] || die "Gazebo Classic launcher is missing: $sitl_run"
[ -f "$source_airframe" ] || die "official Iris airframe is missing: $source_airframe"
[ -f "$sitl_dir/models/iris_stereo_vins/iris_stereo_vins.sdf" ] \
  || die "VINS vehicle model is missing under $sitl_dir/models"
[ -f "$sitl_dir/models/stereo_vins_rig/stereo_vins_rig.sdf" ] \
  || die "VINS stereo rig model is missing under $sitl_dir/models"
command -v cmake >/dev/null 2>&1 || die 'cmake is not installed'
command -v git >/dev/null 2>&1 || die 'git is not installed'

px4_status=$(git -C "$px4_dir" status --porcelain --untracked-files=all) \
  || die "cannot inspect PX4 source tree: $px4_dir"
[ -z "$px4_status" ] || die "PX4 source tree must be clean before simulator build:\n$px4_status"

if [ -n "${PX4_BUILD_JOBS:-}" ]; then
  jobs=$PX4_BUILD_JOBS
else
  cpus=$(nproc)
  memory_kib=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
  memory_jobs=$((memory_kib / 1572864))
  [ "$memory_jobs" -ge 1 ] || memory_jobs=1
  jobs=$cpus
  [ "$jobs" -le "$memory_jobs" ] || jobs=$memory_jobs
  [ "$jobs" -le 8 ] || jobs=8
fi
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || die "PX4_BUILD_JOBS must be a positive integer: $jobs"

# Keep upstream PX4 immutable: the historical 1090 airframe is generated only
# in the ignored build tree and is byte-for-byte the official Iris defaults.
install -d "$(dirname "$overlay_airframe")"
install -m 0644 "$source_airframe" "$overlay_airframe"

cleanup_upstream_gazebo_side_effect() {
  # PX4's upstream GENERATE_ROS_MODELS step appends generated model paths to
  # this tracked file. Restore only that known file; reject every other source
  # mutation below so the fixed v1.17.0 checkout remains a clean source truth.
  git -C "$gazebo_source" diff --quiet -- .gitignore \
    || git -C "$gazebo_source" restore -- .gitignore
  if git -C "$gazebo_source" ls-files --others --exclude-standard -- "$generated_uuv_sdf" \
      | grep -Fqx "$generated_uuv_sdf"; then
    rm -f "$gazebo_source/$generated_uuv_sdf"
  fi
}
trap cleanup_upstream_gazebo_side_effect EXIT
cmake --build "$build_dir" --target sitl_gazebo-classic -- -j "$jobs"
cleanup_upstream_gazebo_side_effect
trap - EXIT

px4_status=$(git -C "$px4_dir" status --porcelain --untracked-files=all) \
  || die "cannot re-inspect PX4 source tree: $px4_dir"
[ -z "$px4_status" ] || die "simulator build modified PX4 source unexpectedly:\n$px4_status"

if [ "${1:-}" = "--prepare-only" ]; then
  printf 'PX4_GAZEBO_OVERLAY=%s\n' "$overlay_airframe"
  exit 0
fi

requested_world=${SITL_WORLD:-${PX4_SITL_WORLD:-}}
if [ -z "$requested_world" ]; then
  export PX4_SITL_WORLD=
elif [[ "$requested_world" = /* ]]; then
  [ -f "$requested_world" ] || die "world file is missing: $requested_world"
  export PX4_SITL_WORLD=$requested_world
else
  world_name=${requested_world%.world}
  world_path=$sitl_dir/worlds/$world_name.world
  [ -f "$world_path" ] || die "named world is missing: $world_path"
  export PX4_SITL_WORLD=$world_path
fi

export GAZEBO_MODEL_PATH="$sitl_dir/models${GAZEBO_MODEL_PATH:+:$GAZEBO_MODEL_PATH}"
export HEADLESS=${HEADLESS:-1}

exec "$sitl_run" "$px4_bin" none iris_stereo_vins none "$px4_dir" "$build_dir"
