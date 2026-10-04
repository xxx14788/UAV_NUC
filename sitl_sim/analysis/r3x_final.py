#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R3x final judgment (prereg v1): hostile-side three-face bands + inter-round
scatter quantification. Descriptive — no PASS/FAIL gate (prereg-frozen rules).
Faces: imu_jit / stampage / rtf (+cpu aux). Queue-depth face absent ([R3xQ]
not yet flown) per prereg."""
import os, json
import numpy as np

RUNS = [
    ('run_F3B9_094909', 'hostile-edge NEVER-FLEW'),
    ('run_F3B10_154733', 'hostile z-overestimate'),
    ('run_F3B11_155643', 'hostile flatline'),
    ('run_F3B12_160420', 'hostile origin-drift'),
    ('run_F3B13_161000', 'hostile flatline'),
    ('run_F3B14_163613', 'hostile cruise-jump'),
]
BASE = os.path.expanduser('~/sitl_sim/vins_smoke_runs')
OUT = os.path.expanduser('~/catkin_ws/sitl_sim/t1_evidence/v10_2026-10-02')

def pct(a, q):
    a = sorted(a)
    if not a:
        return None
    k = min(int(q * len(a)), len(a) - 1)
    return a[k]

def agg(run):
    f = os.path.join(BASE, run, 'r3x_probe.jsonl')
    faces = {}
    for ln in open(f):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        faces.setdefault(r.get('face'), []).append(r)
    out = {}
    ij = faces.get('imu_jit', [])
    if ij:
        g = lambda k: [x[k] for x in ij if x.get(k) is not None]
        out['imu_p50_ms'] = pct(g('p50_ms'), .5); out['imu_p95_ms'] = pct(g('p95_ms'), .5)
        out['imu_p99_ms'] = pct(g('p99_ms'), .5)
        allmax = g('max_ms'); out['imu_max_ms'] = max(allmax) if allmax else None
        out['imu_drop_n'] = sum(g('drop_n')); out['imu_spike_n'] = sum(g('spike_n'))
        sm = g('spike_max_ms2'); out['imu_spike_max'] = max(sm) if sm else 0.0
    for stream in ('odometry', 'imu_propagate'):
        st = [x for x in faces.get('stampage', []) if x.get('stream') == stream]
        if st:
            g = lambda k: [x[k] for x in st if x.get(k) is not None]
            out['age_%s_p50_ms' % stream] = pct(g('p50_ms'), .5)
            out['age_%s_p95_ms' % stream] = pct(g('p95_ms'), .5)
            am = g('max_ms'); out['age_%s_max_ms' % stream] = max(am) if am else None
    rt = faces.get('rtf', [])
    if rt:
        r1 = [x['rtf_1s'] for x in rt if x.get('rtf_1s') is not None]
        if r1:
            out['rtf1_min'] = min(r1); out['rtf1_med'] = pct(r1, .5)
        sl = [x['sim_lag_s'] for x in rt if x.get('sim_lag_s') is not None]
        if sl:
            out['simlag_max_s'] = max(sl)
    cp = faces.get('cpu', [])
    if cp:
        c = [x['cpu_pct'] for x in cp if x.get('cpu_pct') is not None]
        if c:
            out['cpu_med'] = pct(c, .5); out['cpu_max'] = max(c)
    out['w2bb_windows'] = len(faces.get('w2bb', []))
    out['w2bb_alerts'] = sum(1 for x in faces.get('w2bb', []) if x.get('W2BB_ALERT'))
    return out

def main():
    res = {'rounds': {}, 'scatter': {}}
    for run, desc in RUNS:
        try:
            res['rounds'][run] = {'desc': desc, **agg(run)}
        except (OSError, ValueError):
            res['rounds'][run] = {'desc': desc, 'missing': True}
    keys = ['imu_p50_ms', 'imu_p95_ms', 'imu_p99_ms', 'imu_max_ms', 'imu_drop_n',
            'age_odometry_p50_ms', 'age_odometry_p95_ms', 'age_odometry_max_ms',
            'age_imu_propagate_p50_ms', 'rtf1_min', 'rtf1_med', 'simlag_max_s',
            'cpu_med', 'cpu_max']
    for k in keys:
        vals = [res['rounds'][r].get(k) for r, _ in RUNS
                if res['rounds'][r].get(k) is not None and not res['rounds'][r].get('missing')]
        if len(vals) >= 3:
            med = float(np.median(vals))
            sc = (max(vals) - min(vals)) / med if med > 1e-9 else None
            res['scatter'][k] = {'min': round(min(vals), 4), 'max': round(max(vals), 4),
                                 'med': round(med, 4),
                                 'sc': round(sc, 3) if sc is not None else None,
                                 'n': len(vals)}
    MAIN = ['imu_p50_ms', 'imu_p95_ms', 'imu_p99_ms', 'age_odometry_p50_ms', 'rtf1_med']
    main_sc = {k: res['scatter'].get(k, {}).get('sc') for k in MAIN}
    stable = all(v is not None and v <= 0.30 for v in main_sc.values())
    wide = [k for k, v in main_sc.items() if v is not None and v > 1.0]
    res['judgment'] = {'main_features_sc': main_sc,
                       'all_stable_le_030': stable,
                       'high_scatter_features_gt_100': wide,
                       'clean_side_samples': 0,
                       'queue_face': 'absent — [R3xQ] flight pending',
                       'form': 'stable-band' if stable else
                               ('high-scatter-flag:' + ','.join(wide) if wide else 'banded-intermediate')}
    json.dump(res, open(os.path.join(OUT, 'r3x_final_result.json'), 'w'), indent=1)
    print('[judgment]', json.dumps(res['judgment'], indent=1))
    for k in MAIN + ['imu_max_ms', 'age_odometry_max_ms', 'cpu_med']:
        e = res['scatter'].get(k)
        if e:
            print(' %-24s min=%-9s max=%-9s med=%-9s sc=%s' %
                  (k, e['min'], e['max'], e['med'], e['sc']))
    for r, _ in RUNS:
        d = res['rounds'][r]
        print(' %-22s imu_p95=%s rtf_med=%s age_odom_p50=%s w2bb_alerts=%s' %
              (r, d.get('imu_p95_ms'), d.get('rtf1_med'),
               d.get('age_odometry_p50_ms'), d.get('w2bb_alerts')))

if __name__ == '__main__':
    main()
