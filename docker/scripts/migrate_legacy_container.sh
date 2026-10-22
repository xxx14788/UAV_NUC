#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_LEGACY_HEAD=b2b351bde07dca7faefe115307e1db0b1de3ba78

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat >&2 <<'EOF'
Usage: migrate_legacy_container.sh backup|verify|delete \
  --container noetic-sim --output DIR --backup-image IMAGE:TAG
EOF
  exit 2
}

[ $# -ge 1 ] || usage
action=$1
shift
container=''
output=''
backup_image=''
while [ $# -gt 0 ]; do
  case "$1" in
    --container) [ $# -ge 2 ] || usage; container=$2; shift 2 ;;
    --output) [ $# -ge 2 ] || usage; output=$2; shift 2 ;;
    --backup-image) [ $# -ge 2 ] || usage; backup_image=$2; shift 2 ;;
    *) usage ;;
  esac
done

[ "$container" = noetic-sim ] || die 'this tool only accepts the exact legacy container name: noetic-sim'
[[ "$backup_image" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]*:[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || die 'invalid backup image tag'
[ -n "$output" ] || die 'output directory is required'
if [ -L "$output" ]; then die 'output directory must not be a symbolic link'; fi
output=$(realpath -m -- "$output")
[ "$output" != / ] || die 'refusing filesystem root as output'
[ "$output" != "${HOME:-/nonexistent}" ] || die 'refusing home directory as output'

container_id() {
  docker inspect --type container --format '{{.Id}}' "$container" 2>/dev/null
}

image_id() {
  docker image inspect --format '{{.Id}}' "$backup_image" 2>/dev/null
}

write_checksums() {
  (
    cd "$output"
    find . -maxdepth 1 -type f \
      ! -name SHA256SUMS ! -name verified.ok ! -name deleted.ok \
      -printf '%P\0' | sort -z | xargs -0 -r sha256sum > SHA256SUMS
  )
}

backup() {
  local cid source_image bid
  cid=$(container_id) || die "container not found: $container"
  if [ -d "$output" ] && [ -n "$(find "$output" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    die "output directory is not empty: $output"
  fi
  mkdir -p -- "$output"
  printf '%s\n' "$cid" > "$output/original-container.id"
  docker inspect "$container" > "$output/container-inspect.json"
  docker logs "$container" > "$output/container.log" 2>&1 || true
  source_image=$(docker inspect --type container --format '{{.Config.Image}}' "$container")
  printf '%s\n' "$source_image" > "$output/source-image.ref"
  docker image inspect "$source_image" > "$output/source-image-inspect.json"

  docker commit "$container" "$backup_image" > "$output/docker-commit.txt"
  bid=$(image_id) || die "backup image was not created: $backup_image"
  printf '%s\n' "$bid" > "$output/backup-image.id"

  docker run --rm --entrypoint /bin/bash \
    -e "MIGRATION_UID=$(id -u)" -e "MIGRATION_GID=$(id -g)" \
    -v "$output:/backup" "$backup_image" -lc '
set -Eeuo pipefail
ws=/home/ghj/catkin_ws
[ -d "$ws/.git" ]
cd "$ws"
git branch --show-current > /backup/current-branch.txt
git rev-parse HEAD > /backup/head.txt
git status --porcelain=v1 > /backup/git-status.txt
git diff --cached --binary > /backup/staged.diff
git diff --binary > /backup/unstaged.diff
git bundle create /backup/catkin_ws.bundle --all
git ls-files --others --exclude-standard -z > /tmp/uav-untracked.zlist
tr "\0" "\n" < /tmp/uav-untracked.zlist > /backup/untracked-files.list
tar --null -czf /backup/untracked-files.tar.gz -T /tmp/uav-untracked.zlist
if [ -d /home/ghj/sitl_sim/vins_smoke_runs ]; then
  tar -C /home/ghj/sitl_sim -czf /backup/vins_smoke_runs.tar.gz vins_smoke_runs
else
  tar -czf /backup/vins_smoke_runs.tar.gz --files-from /dev/null
fi
dpkg-query -W -f="\${binary:Package}\t\${Version}\n" > /backup/dpkg.tsv
pip3 freeze > /backup/pip-freeze.txt 2>/dev/null || true
chown -R "$MIGRATION_UID:$MIGRATION_GID" /backup
'

  write_checksums
  printf 'Backup created at %s\n' "$output"
}

verify() {
  local cid saved_cid bid saved_bid expected_head verify_name
  [ -d "$output" ] || die "migration output missing: $output"
  for file in original-container.id backup-image.id head.txt catkin_ws.bundle \
              untracked-files.tar.gz vins_smoke_runs.tar.gz SHA256SUMS; do
    [ -f "$output/$file" ] || die "required artifact missing: $file"
  done
  cid=$(container_id) || die "container not found: $container"
  saved_cid=$(<"$output/original-container.id")
  [ "$cid" = "$saved_cid" ] || die 'container ID changed since backup'
  bid=$(image_id) || die "backup image missing: $backup_image"
  saved_bid=$(<"$output/backup-image.id")
  [ "$bid" = "$saved_bid" ] || die 'backup image ID changed since backup'

  (cd "$output" && sha256sum -c SHA256SUMS)
  git bundle verify "$output/catkin_ws.bundle" >/dev/null
  expected_head=${EXPECTED_LEGACY_HEAD:-$DEFAULT_LEGACY_HEAD}
  [ "$(<"$output/head.txt")" = "$expected_head" ] || die "legacy HEAD does not match expected commit: $expected_head"
  git bundle list-heads "$output/catkin_ws.bundle" | awk '{print $1}' | grep -Fxq "$expected_head" \
    || die "legacy HEAD is not recoverable from bundle: $expected_head"
  tar -tzf "$output/untracked-files.tar.gz" >/dev/null
  tar -tzf "$output/vins_smoke_runs.tar.gz" >/dev/null

  verify_name="uav-legacy-verify-$$"
  docker run --rm --name "$verify_name" --entrypoint /bin/bash "$backup_image" -lc \
    'test -r /home/ghj/catkin_ws && test -r /home/ghj/sitl_sim'
  {
    printf 'container_name=%s\n' "$container"
    printf 'container_id=%s\n' "$cid"
    printf 'backup_image=%s\n' "$backup_image"
    printf 'backup_image_id=%s\n' "$bid"
    printf 'legacy_head=%s\n' "$expected_head"
    printf 'verified_at=%s\n' "$(date --iso-8601=seconds)"
  } > "$output/verified.ok"
  printf 'Verification passed for %s\n' "$container"
}

receipt_value() {
  local key=$1
  sed -n "s/^${key}=//p" "$output/verified.ok" | head -n1
}

delete_container() {
  local cid bid
  [ -f "$output/verified.ok" ] || die 'verified.ok is required before deletion'
  cid=$(container_id) || die "container not found: $container"
  [ "$cid" = "$(receipt_value container_id)" ] || die 'container ID does not match verified receipt'
  [ "$container" = "$(receipt_value container_name)" ] || die 'container name does not match verified receipt'
  bid=$(image_id) || die "backup image missing: $backup_image"
  [ "$bid" = "$(receipt_value backup_image_id)" ] || die 'backup image ID does not match verified receipt'
  [ "$backup_image" = "$(receipt_value backup_image)" ] || die 'backup image tag does not match verified receipt'
  docker rm "$container"
  {
    printf 'container_name=%s\n' "$container"
    printf 'container_id=%s\n' "$cid"
    printf 'deleted_at=%s\n' "$(date --iso-8601=seconds)"
    printf 'backup_image=%s\n' "$backup_image"
    printf 'backup_image_id=%s\n' "$bid"
  } > "$output/deleted.ok"
  printf 'Deleted container %s; retained image %s\n' "$container" "$backup_image"
}

case "$action" in
  backup) backup ;;
  verify) verify ;;
  delete) delete_container ;;
  *) usage ;;
esac
