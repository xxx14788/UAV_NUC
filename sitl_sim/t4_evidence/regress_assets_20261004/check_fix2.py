#!/usr/bin/env python3
# C14-FIX-2 regression checker. ASCII except final GREEN/RED line (scp channel, UTF-8 safe).
# usage: python3 check_fix2.py [expected_json] [results_jsonl]
# Compares per-cell classification fields against expected table.
# GREEN: exit 0, last stdout line "MATRIX-GREEN=绿". RED: exit 1, detail lines + "MATRIX-RED=红".
import json
import sys

EXPECTED = sys.argv[1] if len(sys.argv) > 1 else '/home/uav/sitl_sim/t4_selftest/expected_fix2.json'
RESULTS = sys.argv[2] if len(sys.argv) > 2 else '/tmp/t4_v57_selftest/results.jsonl'
FIELDS = ['rc', 'out_exists', 'out_json_ok', 'out_nonfinite_hits', 'stderr_tokens',
          'stdout_json_ok', 'stdout_nonfinite_hits', 'out_top_keys', 'n_primary',
          'missing_pool_keys']

exp = json.load(open(EXPECTED, encoding='utf-8'))
rows = [json.loads(l) for l in open(RESULTS, encoding='utf-8')]
got = {'%s|%s' % (r['case'], r['tool']): r for r in rows}

bad = []
if len(rows) != 33:
    bad.append('cell-count expected=33 actual=%d' % len(rows))
for k in sorted(exp):
    if k not in got:
        bad.append('%s MISSING-CELL' % k)
        continue
    r = got[k]
    e = exp[k]
    if r['rc'] == 124 or r.get('elapsed_s', 0) >= 89:
        bad.append('%s HANG rc=%s elapsed=%s' % (k, r['rc'], r.get('elapsed_s')))
        continue
    for f in FIELDS:
        if r.get(f) != e[f]:
            bad.append('%s field=%s expected=%r actual=%r' % (k, f, e[f], r.get(f)))
    if r.get('out_nonfinite_hits') not in (0, None):
        bad.append('%s NONFINITE-LITERAL in out file (count=%s)' % (k, r.get('out_nonfinite_hits')))
    if e['flipped']:
        # spec core: stderr ERROR line + out JSON top-level error field
        se = (r.get('stderr_head') or '') + (r.get('stderr_tail') or '')
        if 'ERROR:' not in se or 'no readable frames' not in se:
            bad.append('%s stderr-ERROR-LINE missing (head=%r)' % (k, r.get('stderr_head')))
        try:
            obj = json.load(open(r['out_path'], encoding='utf-8'))
        except Exception as ex:
            obj = None
            bad.append('%s out-file-unreadable %s' % (k, ex))
        if not (isinstance(obj, dict) and isinstance(obj.get('error'), str)
                and obj['error'].startswith('no readable frames')):
            bad.append('%s out-error-FIELD missing/malformed' % k)

if bad:
    for b in bad:
        print('MATRIX-RED detail: %s' % b)
    print('MATRIX-RED=红 (%d problem(s))' % len(bad))
    sys.exit(1)
print('all 33 cells match expected classification (FIX-1 6 flipped + FIX-2 U3/U4 nonfinite cleaned)')
print('MATRIX-GREEN=绿')
sys.exit(0)
