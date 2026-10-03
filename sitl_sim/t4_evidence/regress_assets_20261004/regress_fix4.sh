#!/usr/bin/env bash
# C14-FIX-4 regression, self-contained on NUC. ASCII only; the final verdict line
# (MATRIX-GREEN=.. / MATRIX-RED=..) is printed by check_fix4.py (UTF-8, scp-delivered).
# v2: every exit path writes the verdict atomically to $ST/last_verdict.txt so the
# caller can read the authoritative verdict from the file even if the ssh stream
# drops (observed twice on 2026-10-03: silent ssh exit=1 during lock race windows).
# Guards: SITL.lock free (atomic take, auto release), /tmp free >= 20G,
# rosbag/gzserver both 0. Runner per-cell timeout 90, batch timeout 560.
# v3 2026-10-04 lock-leak fix (E1 alignment, T4-lockfix):
#   1) 【测试必走侧锁】LOCK="${SITL_LOCK_FILE:-/home/uav/sitl_sim/SITL.lock}" --
#      self-tests MUST export SITL_LOCK_FILE=/tmp/xxx.lock, never the real lock;
#   2) lock target follows E1 format t4wf-<PID>-<HHMMSS> so dead-lock takeover
#      can readlink the owner PID (was literal "t4wf", no PID);
#   3) cleanup() removes the lock ONLY if readlink still shows OUR target (never
#      deletes someone else's lock); trap covers EXIT INT TERM ERR (set -E, HUP
#      backstop) so signal/ERR kill paths release too (2026-10-03 orphan locks);
#   4) 60s touch heartbeat keeps the lock fresh during the long locked section.
set -u
set -E
ST=/home/uav/sitl_sim/t4_selftest
# 【测试必走侧锁】override with SITL_LOCK_FILE=/tmp/xxx.lock for all self-tests
LOCK="${SITL_LOCK_FILE:-/home/uav/sitl_sim/SITL.lock}"
VF=$ST/last_verdict.txt
LOCK_TARGET="t4wf-$$-$(date +%H%M%S)"
verdict() { printf '%s\n' "$1" > "$VF.tmp"; mv "$VF.tmp" "$VF"; printf '%s\n' "$1"; }
if [ -e "$LOCK" ] || [ -L "$LOCK" ]; then
  verdict "MATRIX-RED detail: ${LOCK} busy (held elsewhere)"; exit 1
fi
if ! ln -s "$LOCK_TARGET" "$LOCK" 2>/dev/null; then
  verdict "MATRIX-RED detail: ${LOCK} busy (race lost)"; exit 1
fi
# E1 heartbeat: refresh lock mtime every 60s while the long locked section runs
( while :; do
    sleep 60
    [ "$(readlink "$LOCK" 2>/dev/null || true)" = "$LOCK_TARGET" ] || break
    touch -h "$LOCK" 2>/dev/null || true
  done ) &
HB_PID=$!
cleanup() {
  local cur
  kill "$HB_PID" 2>/dev/null || true
  cur=$(readlink "$LOCK" 2>/dev/null || true)
  if [ "$cur" = "$LOCK_TARGET" ]; then
    rm -f "$LOCK"
  fi
}
trap cleanup EXIT INT TERM ERR
trap 'exit 129' HUP   # untrapped fatal signals (ssh drop) skip the EXIT trap
trap 'exit 130' INT   # signal/ERR paths exit -> EXIT trap -> cleanup releases
trap 'exit 143' TERM
trap 'exit 1' ERR
avail=$(df -BG --output=avail /tmp | tail -1 | tr -dc '0-9')
if [ -z "$avail" ] || [ "$avail" -lt 20 ] 2>/dev/null; then
  verdict "MATRIX-RED detail: /tmp free=${avail}G < 20G, no new round"; exit 1
fi
g=$(pgrep -c gzserver || true); r=$(pgrep -c rosbag || true)
if [ "$g" != "0" ] || [ "$r" != "0" ]; then
  verdict "MATRIX-RED detail: SITL busy gzserver=$g rosbag=$r"; exit 1
fi
# ROS setup chain touches unset vars (ROS_DISTRO) -> fatal under set -u
# (observed: 1.ros_distro.sh line 3). Scope strictness OFF around source only.
set +u
source /opt/ros/noetic/setup.bash >/dev/null 2>&1 || true
set -u
timeout 60 nice -n 10 python3 "$ST/make_fix3_bag.py" > /tmp/t4_fix3_bag.log 2>&1   || { echo 'MATRIX-RED detail: probe bag build failed, see /tmp/t4_fix3_bag.log'; exit 1; }
timeout 560 nice -n 10 python3 "$ST/build_and_run_v57.py" > /tmp/t4_v57_run.log 2>&1 || true
if [ -f /tmp/t4_v57_selftest/results.jsonl ]; then
  python3 "$ST/check_fix4.py" "$ST/expected_fix4.json" /tmp/t4_v57_selftest/results.jsonl | tee "$VF.tmp" >/dev/null
  rc=${PIPESTATUS[0]}
  mv "$VF.tmp" "$VF"
  cat "$VF"
  exit $rc
fi
verdict 'MATRIX-RED detail: runner failed, see /tmp/t4_v57_run.log'
tail -5 /tmp/t4_v57_run.log
exit 1
