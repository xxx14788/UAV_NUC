#!/usr/bin/env bash
# C14 independent-audit merged final regression (33 base v57 cells + 12 extended
# audit cells), single run on NUC. ASCII only; final verdict line is UTF-8 via
# scp channel. Guards identical to regress_fix3.sh: SITL.lock free (atomic take,
# auto release), /tmp free >= 20G, rosbag/gzserver both 0. Verdict written to
# $ST/last_verdict_audit_v58.txt (does NOT touch the fix engineer's verdict file).
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
ROOT=/tmp/t4_v57_selftest
VF=$ST/last_verdict_audit_v58.txt
LOCK_TARGET="t4wf-$$-$(date +%H%M%S)"
verdict() { printf '%s\n' "$1" > "$VF.tmp"; mv "$VF.tmp" "$VF"; printf '%s\n' "$1"; }
if [ -e "$LOCK" ] || [ -L "$LOCK" ]; then
  verdict "AUDIT-RED detail: ${LOCK} busy (held elsewhere)"; exit 1
fi
if ! ln -s "$LOCK_TARGET" "$LOCK" 2>/dev/null; then
  verdict "AUDIT-RED detail: ${LOCK} busy (race lost)"; exit 1
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
  verdict "AUDIT-RED detail: /tmp free=${avail}G < 20G, no new round"; exit 1
fi
g=$(pgrep -c gzserver || true); r=$(pgrep -c rosbag || true)
if [ "$g" != "0" ] || [ "$r" != "0" ]; then
  verdict "AUDIT-RED detail: SITL busy gzserver=$g rosbag=$r"; exit 1
fi
set +u
source /opt/ros/noetic/setup.bash >/dev/null 2>&1 || true
set -u
rc_run=0
timeout 900 nice -n 10 python3 "$ST/build_and_run_v58_audit.py" > /tmp/t4_v58_audit_run.log 2>&1 || rc_run=$?
if [ ! -f "$ROOT/results.jsonl" ]; then
  verdict 'AUDIT-RED detail: runner produced no results.jsonl, see /tmp/t4_v58_audit_run.log'
  tail -5 /tmp/t4_v58_audit_run.log
  exit 1
fi
# split: base 33 rows (fix-engineer expected table) vs extended 12 audit rows
rc_split=0
python3 - "$ROOT/results.jsonl" "$ROOT/results_base33.jsonl" "$ROOT/results_ext12.jsonl" <<'PYEOF' || rc_split=$?
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8')]
BASE = {'case1a_emptydir', 'case1b_manifestonly', 'case2_singleframe', 'case3_allwhite',
        'case4_allblack', 'case5_constnoise', 'case6_truncpng', 'case7_dupts',
        'case8_missingfield', 'case9_trailspace', 'case12_odddepth'}
b = [r for r in rows if r['case'] in BASE]
e = [r for r in rows if r['case'] not in BASE]
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    for r in b:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
with open(sys.argv[3], 'w', encoding='utf-8') as f:
    for r in e:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('split base=%d ext=%d' % (len(b), len(e)))
PYEOF
if [ "$rc_split" != "0" ]; then
  verdict 'AUDIT-RED detail: split failed'; exit 1
fi
rc_base=0
python3 "$ST/check_fix4.py" "$ST/expected_fix4.json" "$ROOT/results_base33.jsonl" > /tmp/t4_v58_audit_checkbase.log 2>&1 || rc_base=$?
rc_ext=0
python3 "$ST/check_audit_ext.py" "$ROOT/results.jsonl" > /tmp/t4_v58_audit_checkext.log 2>&1 || rc_ext=$?
echo "--- check_fix4 (base33, incl P/Q probes) rc=$rc_base ---"
cat /tmp/t4_v58_audit_checkbase.log
echo "--- check_audit_ext (12 extended) rc=$rc_ext ---"
cat /tmp/t4_v58_audit_checkext.log
if [ "$rc_run" = "0" ] && [ "$rc_base" = "0" ] && [ "$rc_ext" = "0" ]; then
  verdict 'MATRIX-GREEN=绿 (merged 45 rows: base33 expected_fix4 + probes, ext12 audit)'
  exit 0
fi
verdict "AUDIT-RED detail: rc_run=$rc_run rc_base=$rc_base rc_ext=$rc_ext (logs /tmp/t4_v58_audit_*.log)"
exit 1
