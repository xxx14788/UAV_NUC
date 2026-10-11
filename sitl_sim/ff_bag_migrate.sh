#!/usr/bin/env bash
# ff_bag_migrate.sh v1.0 — 首飞袋旧机→3090 迁移预案（专项① 单元4，2026-10-11）
# 沿 r2 滚动迁移经验：旧机磁盘 28G 级（88% 高位），飞后袋迁移 3090（421G 空闲）。
# 双通道: 主=LAN 直连(192.168.0.4) 副=经 Win 跳板（LAN 断时: 旧机→Win scp→3090）
# 用法: bash ff_bag_migrate.sh            # 迁移全部 firstflight_*.bag（已迁 md5 同者跳过）
#       bash ff_bag_migrate.sh <file.bag> # 迁移单个
# 纪律: md5 双端一致才删源（对账纪律）；3090 落点 ~/sitl_sim/ff_bags/
set -u
SRC_DIR="$HOME/sitl_realmachine/bags"
DST_HOST="ghj@192.168.0.4"
DST_DIR="\$HOME/sitl_sim/ff_bags"

migrate_one() {
  local F="$1" BASE MD5_S MD5_D
  BASE=$(basename "$F")
  MD5_S=$(md5sum "$F" | awk '{print $1}')
  # 目标端已有同名同 md5 = 跳过
  MD5_D=$(ssh -o ConnectTimeout=5 "$DST_HOST" "md5sum $DST_DIR/$BASE 2>/dev/null | awk '{print \$1}'" 2>/dev/null)
  if [ "$MD5_S" = "$MD5_D" ] && [ -n "$MD5_D" ]; then
    echo "[migrate] $BASE 已在 3090 且 md5 一致——删源释放旧机磁盘"
    rm -f "$F" && return 0
  fi
  echo "[migrate] $BASE (${MD5_S:0:8}) 传输中..."
  if scp -o ConnectTimeout=8 "$F" "$DST_HOST:/tmp/" 2>/dev/null; then
    ssh "$DST_HOST" "mkdir -p $DST_DIR && mv /tmp/$BASE $DST_DIR/ && md5sum $DST_DIR/$BASE" > /tmp/ff_mig_dst.out 2>&1
    MD5_D=$(awk '{print $1}' /tmp/ff_mig_dst.out)
    if [ "$MD5_S" = "$MD5_D" ]; then
      echo "[migrate] $BASE md5 双端一致 ✓ —— 删源"
      rm -f "$F"
    else
      echo "[migrate] $BASE md5 不一致！（源=$MD5_S 目标=$MD5_D）——保留源，人工核查" >&2
      return 1
    fi
  else
    echo "[migrate] LAN 直连失败——启用 Win 跳板预案：旧机→Win(D:\\ff_bags)→3090，手册 v2 附录执行" >&2
    return 1
  fi
}

if [ -n "${1:-}" ]; then
  migrate_one "$1"
else
  ls "$SRC_DIR"/firstflight_*.bag 2>/dev/null | while read -r F; do migrate_one "$F"; done
  echo "[migrate] 毕。3090 侧清单:"
  ssh -o ConnectTimeout=5 "$DST_HOST" "ls -lh $DST_DIR/ 2>/dev/null | tail -8"
fi
