#!/usr/bin/env python3
# C14-FIX-4 regression checker (matrix + FIX-3 probes + manifest schema probes). ASCII except final GREEN/RED line (scp channel, UTF-8 safe).
# usage: python3 check_fix4.py [expected_json] [results_jsonl]
# Compares per-cell classification fields against expected table.
# GREEN: exit 0, last stdout line "MATRIX-GREEN=绿". RED: exit 1, detail lines + "MATRIX-RED=红".
import json
import sys

EXPECTED = sys.argv[1] if len(sys.argv) > 1 else '/home/uav/sitl_sim/t4_selftest/expected_fix4.json'
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

# ---- C14-FIX-3 probes: shift source unification (run only if matrix part is clean so far)
TOOL = '/home/uav/catkin_ws/sitl_sim/analysis/j3_feature_density.py'
BAG = '/tmp/t4_fix3_probe.bag'
SF_OK = '/tmp/t4_fix3_shiftfile.json'
SF_BAD = '/tmp/t4_fix3_badfile.json'


def run_tool(args):
    import subprocess
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True,
                       text=True, timeout=90)
    return p.returncode, p.stdout, p.stderr


if not bad:
    open(SF_OK, 'w').write('{"shift": [0.5, 0.5, 0.2]}')
    open(SF_BAD, 'w').write('{"foo": 1}')
    try:
        probes = []
        rc, so, se = run_tool(['--mode', 'density', '--bag', BAG])
        probes.append(('P1-no-shift', rc == 3 and 'SHIFT-MISSING' in se,
                       'rc=%s stderr_tail=%r' % (rc, se[-120:])))
        rc, so, se = run_tool(['--mode', 'density', '--bag', BAG,
                               '--shift', '1,2,0.3', '--shift-file', SF_OK])
        probes.append(('P2-conflict', rc == 3 and 'SHIFT-CONFLICT' in se,
                       'rc=%s stderr_tail=%r' % (rc, se[-120:])))
        for name, extra, want_src, want_shift in (
                ('P3-legacy', ['--allow-legacy-shift'], 'legacy', [1.01, 0.98, 0.104]),
                ('P4-explicit', ['--shift', '1.0,2.0,0.3'], 'explicit', [1.0, 2.0, 0.3]),
                ('P5-shift-file', ['--shift-file', SF_OK], 'shift-file', [0.5, 0.5, 0.2])):
            rc, so, se = run_tool(['--mode', 'density', '--bag', BAG] + extra)
            ok = rc == 0
            obj = None
            if ok:
                try:
                    obj = json.loads(so)
                except Exception:
                    ok = False
            ok = ok and obj is not None and obj.get('shift_source') == want_src                 and obj.get('shift') == want_shift                 and obj.get('points_total') == 16                 and obj.get('zones', {}).get('air', {}).get('n') == 8                 and obj.get('zones', {}).get('ground', {}).get('n') == 8
            probes.append((name, ok, 'rc=%s so_head=%r' % (rc, so[:160])))
        rc, so, se = run_tool(['--mode', 'density', '--bag', BAG, '--shift-file', SF_BAD])
        probes.append(('P6-bad-shift-file', rc == 3 and 'SHIFT-FILE-INVALID' in se,
                       'rc=%s stderr_tail=%r' % (rc, se[-120:])))
        rc, so, se = run_tool(['--mode', 'offset', '--bag', BAG])
        probes.append(('P7-offset-unaffected', rc == 1 and 'FAIL' in so,
                       'rc=%s so_head=%r' % (rc, so[:80])))
        for name, ok, detail in probes:
            if not ok:
                bad.append('PROBE %s FAILED: %s' % (name, detail))
    finally:
        import os
        for f in (SF_OK, SF_BAD):
            if os.path.exists(f):
                os.remove(f)

# ---- C14-FIX-4 probes: manifest schema versioning (run only if everything above clean)
if not bad:
    import shutil
    pairs4 = [('Q1-metrics-v9', '/tmp/t4_v57_selftest/cases/case2_singleframe',
               'metrics', '9'),
              ('Q2-fb-v9', '/tmp/t4_v57_selftest/cases/case7_dupts',
               'fb', '9'),
              ('Q3-metrics-v2', '/tmp/t4_v57_selftest/cases/case2_singleframe',
               'metrics', '2'),
              ('Q4-fb-v2', '/tmp/t4_v57_selftest/cases/case7_dupts',
               'fb', '2')]

    def run_tool4(tool, d, out):
        exe = '/home/uav/catkin_ws/sitl_sim/analysis/j3_image_metrics.py'             if tool == 'metrics'             else '/home/uav/catkin_ws/sitl_sim/analysis/j3_fb_residual.py'
        import subprocess
        p = subprocess.run([sys.executable, exe, '--frames-dir', d, '--out', out],
                           capture_output=True, text=True, timeout=90)
        return p.returncode, p.stdout, p.stderr

    for name, base, tool, ver in pairs4:
        d = '/tmp/t4_fix4_%s' % name
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(base, d)
        try:
            mp = d + '/manifest.json'
            man = json.load(open(mp, encoding='utf-8'))
            man['schema_version'] = ver
            json.dump(man, open(mp, 'w', encoding='utf-8'), ensure_ascii=False)
            rc, so, se = run_tool4(tool, d, d + '/probe_out.json')
            if ver == '9':
                ok = rc == 3 and 'MANIFEST-SCHEMA-UNKNOWN' in se
                detail = 'rc=%s stderr_tail=%r' % (rc, se[-120:])
            else:
                ok = rc == 0
                obj = None
                if ok:
                    try:
                        obj = json.load(open(d + '/probe_out.json', encoding='utf-8'))
                    except Exception:
                        ok = False
                ok = ok and obj is not None                     and obj.get('schema_version') == '2'                     and obj.get('manifest_schema_version') == '2'                     and 'legacy_keys' not in obj
                detail = 'rc=%s so_head=%r' % (rc, so[:120])
            if not ok:
                bad.append('PROBE %s FAILED: %s' % (name, detail))
        finally:
            shutil.rmtree(d, ignore_errors=True)

if bad:
    for b in bad:
        print('MATRIX-RED detail: %s' % b)
    print('MATRIX-RED=红 (%d problem(s))' % len(bad))
    sys.exit(1)
print('all 33 cells match expected classification (FIX-1 signatures + FIX-2 nonfinite + FIX-3/FIX-4 probes)')
print('MATRIX-GREEN=绿')
sys.exit(0)
