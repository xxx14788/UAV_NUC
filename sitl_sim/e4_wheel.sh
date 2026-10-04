#!/usr/bin/env bash
# e4_wheel.sh v2 — T1-E4 单轮驱动(2026-10-01; P0C3_E4_design §1-3; v1 撤轮整改版)
# 用法: e4_wheel.sh <TAG> <EV_CTRL> <GPS_CTRL>
#   回归轮: EV_CTRL=0 GPS_CTRL=7 → 不注入(rcS 不动), 纯 canonical
# v1 教训: mavlink_shell 14557 系 2018 前死约定(v1.17 无 shell 实例)→撤轮;
#   v2 改 rcS 文件预注入: 快照→ekf2 start 行前插 param set→轮后 trap 恢复。
#   param set 系 RAM-only(无 param save 不落 bson, 磁写回须 save=既有定案), 满足"实验值不 save"。
set -u
TAG="${1:?TAG}"; EVC="${2:?EV_CTRL}"; GPC="${3:?GPS_CTRL}"
L="$HOME/sitl_sim"; SMOKE="$L/vins_smoke.sh"
RCS="$HOME/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS"
BAK="${RCS}.t1e4bak"
OUT="/tmp/e4_${TAG}.out"
# T1-H4 layer-3 fix (2026-10-04): ALWAYS inject. PX4 SITL persists params to
# rootfs/parameters.bson (file present, mtime recent) — injected EV/GPS values
# leak into later no-injection "regression" boots (F3B2 ulg logged EV15/GPS0
# on a 0/7 reg call). Explicit canonical injection makes every boot
# deterministic without touching the bson on disk (mag calibration lives there
# — do NOT delete/restore that file).
REG=0
echo "[e4v2] wheel=$TAG EV_CTRL=$EVC GPS_CTRL=$GPC regression=$REG $(date +%H:%M:%S)"
cleanup_rcs() { if [ -f "$BAK" ]; then cp "$BAK" "$RCS" && rm -f "$BAK" && echo "[e4v2] rcS 已恢复基线"; fi; }
trap 'cleanup_rcs' EXIT
if [ $REG = 0 ]; then
  [ -f "$RCS" ] || { echo "[e4v2] FATAL rcS 缺失: $RCS"; exit 1; }
  cp "$RCS" "$BAK"
  python3 - "$RCS" "$EVC" "$GPC" <<'PYEOF' || exit 1
import io, sys
rcs, evc, gpc = sys.argv[1], sys.argv[2], sys.argv[3]
lines = io.open(rcs, encoding="utf-8").read().splitlines(keepends=True)
out, done = [], False
for l in lines:
    if not done and l.lstrip().startswith("ekf2 start"):
        out.append("param set EKF2_EV_CTRL %s\nparam set EKF2_GPS_CTRL %s\n" % (evc, gpc))
        done = True
    out.append(l)
assert done, "ekf2 start anchor not found in rcS"
io.open(rcs, "w", encoding="utf-8").writelines(out)
print("rcS injected: EV_CTRL=%s GPS_CTRL=%s before ekf2 start" % (evc, gpc))
PYEOF
  grep -n "EKF2_EV_CTRL" "$RCS" || { echo "[e4v2] FATAL 注入未落盘"; exit 1; }
fi
# 后台起轮(锁/录/判/清场全在 smoke 内)
SMOKE_OWNER=T1-E4 nohup bash "$SMOKE" --world sitl_world_obstacles --goal 0 0 1 --tag "$TAG" --budget 90 > "$OUT" 2>&1 &
SPID=$!
echo "[e4v2] smoke pid=$SPID"
wait $SPID; RC=$?
# 轮后取证: mavparam 读回五参数(轮已清场, 此处只留 rcS 注入回执与 smoke 侧 round_result)
# X3 窗内采样(轮栈存活期): odom hz + mavparam 参数实值 —— 由并发观察器执行, 不阻塞本脚本
echo "[e4v2] wheel=$TAG done rc=$RC $(date +%H:%M:%S); rcS 基线由 trap 恢复"
exit $RC
