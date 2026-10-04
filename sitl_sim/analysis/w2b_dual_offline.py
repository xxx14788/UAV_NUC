#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w2b B-path dual-stream detector — offline calibration/joint-test (prereg v1).

Prereg: t1_evidence/v10_2026-10-02/w2b_joint_prereg_v1.md (frozen before stats).
B1 value divergence: |z_odom - z_prop| > 1.0 m for >=2 consecutive odom samples
   (nearest prop sample within 0.5 s).
B2 rate divergence:  sliding — at prop time t, zero new odom samples in the
   previous 2.0 s while >=5 prop samples arrived -> gap-beat; alert when gap
   beats persist >=2 s.
Deterministic, read-only.
"""
import sys, os, json
import bisect
import numpy as np
import rosbag

RUNS = os.path.expanduser('~/sitl_sim/vins_smoke_runs')
OUT = os.path.expanduser('~/catkin_ws/sitl_sim/t1_evidence/v10_2026-10-02')
TOPICS = ['/vins_estimator/odometry', '/vins_estimator/imu_propagate',
          '/mavros/state']

FOUR = {
    'T1_z_overestimate': ['run_F3B10_154733', 'run_T2ZETA2_132510'],
    'T2_render_flatline': ['run_F3B11_155643', 'run_F3B13_161000'],
    'T3_origin_drift': ['run_F3B12_160420'],
    'T4_cruise_jump': ['run_F3B14_163613', 'run_F3B6_093203'],
}
HEALTHY_GLOBS = ['run_F3B2_', 'run_F3B3_', 'run_F3B4_', 'run_F3B8_094417',
                 'run_WD1_024016', 'run_X1final_040643']

MATCH_TOL = 0.5
D_THR = 1.0
B1_CONSEC = 2
B2_ODOM_SILENT = 2.0
B2_PROP_MIN = 5
B2_STREAK_S = 2.0


def read_bag(run):
    path = os.path.join(RUNS, run, 'flight.bag')
    if not os.path.exists(path):
        return None
    od, pr, arm = [], [], []
    t_disarm = None
    armed_prev = False
    with rosbag.Bag(path) as bag:
        for topic, msg, t in bag.read_messages(topics=TOPICS):
            ts = t.to_sec()
            hs = msg.header.stamp.to_sec() if hasattr(msg, 'header') and msg.header.stamp.to_sec() > 0 else ts
            if topic.endswith('/odometry'):
                od.append((hs, msg.pose.pose.position.z))
            elif topic.endswith('/imu_propagate'):
                pr.append((hs, msg.pose.pose.position.z))
            else:
                if getattr(msg, 'armed', False) and not armed_prev:
                    arm = hs
                if not getattr(msg, 'armed', False) and armed_prev:
                    t_disarm = hs
                armed_prev = bool(getattr(msg, 'armed', False))
    od.sort()
    pr.sort()
    return {'run': run, 'od': od, 'pr': pr, 'arm': arm, 'disarm': t_disarm}


def rates(s):
    if len(s) < 2:
        return 0.0, None
    dt = s[-1][0] - s[0][0]
    return (len(s) / dt if dt > 0 else 0.0), dt


def detect(bag):
    od, pr = bag['od'], bag['pr']
    alerts = []
    # --- B1 value divergence
    if od and pr:
        P = np.array(pr)
        consec = 0
        for t, z in od:
            j = int(np.argmin(np.abs(P[:, 0] - t)))
            if abs(P[j, 0] - t) <= MATCH_TOL:
                d = abs(z - P[j, 1])
                if d > D_THR:
                    consec += 1
                    if consec >= B1_CONSEC:
                        alerts.append({'type': 'B1', 't': round(t, 2),
                                       'd_m': round(float(d), 3)})
                        consec = 0  # re-armable after an alert
                else:
                    consec = 0
            else:
                consec = 0
    # --- B2 rate divergence (odom starvation vs prop alive)
    # v1.1 warmup guard: B2 active only after both streams delivered >=20
    # samples (startup-race artifact found in v1 run: prop floods ms before
    # first odom -> spurious alert at bag start in EVERY bag, see verdict).
    if od and pr:
        od_t = [x[0] for x in od]
        pr_t = [x[0] for x in pr]
        warm = max(od_t[19], pr_t[19]) if (len(od_t) >= 20 and len(pr_t) >= 20) else None
        streak_start = None
        for t in pr_t:
            if warm is None or t <= warm:
                continue
            i0 = bisect.bisect_right(od_t, t - B2_ODOM_SILENT)
            i1 = bisect.bisect_right(od_t, t)
            j0 = bisect.bisect_right(pr_t, t - B2_ODOM_SILENT)
            n_prop = len(pr_t) - j0  # samples in (t-2, t] inclusive of t
            if (i1 - i0) == 0 and n_prop >= B2_PROP_MIN:
                if streak_start is None:
                    streak_start = t - B2_ODOM_SILENT
                if t - streak_start >= B2_STREAK_S:
                    alerts.append({'type': 'B2', 't': round(t, 2),
                                   'silent_s': round(t - streak_start, 2)})
                    streak_start = None  # re-armable
            else:
                streak_start = None
    # merge/dedup: keep first per type per 5s
    seen = {}
    ded = []
    for a in alerts:
        k = (a['type'], int(a['t'] // 5))
        if k not in seen:
            seen[k] = True
            ded.append(a)
    r_od, dur_od = rates(od)
    r_pr, dur_pr = rates(pr)
    in_armed = []
    for a in ded:
        if bag['arm'] is None:
            in_armed.append(True)  # no state stream: not gated, annotated
        else:
            end = bag['disarm'] if bag['disarm'] else float('inf')
            in_armed.append(bag['arm'] - 0.5 <= a['t'] <= end + 0.5)
    return {'n_odom': len(od), 'n_prop': len(pr),
            'odom_hz': round(r_od, 3), 'prop_hz': round(r_pr, 3),
            'arm': bag['arm'], 'disarm': bag['disarm'],
            'alerts': ded, 'alerts_in_armed': int(sum(in_armed))}


def main():
    res = {'bags': {}, 'four': {}, 'healthy': []}
    allruns = sorted(os.listdir(RUNS))
    healthy = []
    for g in HEALTHY_GLOBS:
        for r in allruns:
            if r.startswith(g.rstrip('_') + '_') or r == g or r.startswith(g):
                if r not in healthy:
                    healthy.append(r)
    for typ, runs in FOUR.items():
        res['four'][typ] = {}
        for r in runs:
            b = read_bag(r)
            if b is None:
                res['four'][typ][r] = {'missing': True}
                continue
            d = detect(b)
            res['bags'][r] = d
            res['four'][typ][r] = {'alerts': len(d['alerts']),
                                   'in_armed': d['alerts_in_armed']}
            print('[four] %-16s %s alerts=%d armed=%d odom_hz=%s prop_hz=%s' %
                  (typ, r, len(d['alerts']), d['alerts_in_armed'],
                   d['odom_hz'], d['prop_hz']), flush=True)
    for r in sorted(healthy):
        b = read_bag(r)
        if b is None:
            continue
        d = detect(b)
        res['bags'][r] = d
        res['healthy'].append({'run': r, 'alerts': len(d['alerts']),
                               'in_armed': d['alerts_in_armed']})
        print('[health] %s alerts=%d odom_hz=%s prop_hz=%s' %
              (r, len(d['alerts']), d['odom_hz'], d['prop_hz']), flush=True)
    # gate eval (frozen): 4/4 primary(or backup noted) + healthy zero
    cov = {}
    for typ, runs in FOUR.items():
        ok = False
        used = None
        for r in runs:
            e = res['four'][typ].get(r, {})
            if e.get('alerts', 0) > 0 and e.get('in_armed', 0) > 0:
                ok = True
                used = r
                break
        cov[typ] = {'covered': ok, 'bag': used}
    h_fp = [h for h in res['healthy'] if h['alerts'] > 0]
    res['gate'] = {'four_of_four': all(c['covered'] for c in cov.values()),
                   'coverage': cov,
                   'healthy_false_positive_runs': h_fp,
                   'verdict': 'PASS' if (all(c['covered'] for c in cov.values())
                                         and not h_fp) else 'FAIL'}
    json.dump(res, open(os.path.join(OUT, 'w2b_joint_result.json'), 'w'), indent=1)
    print('[verdict]', res['gate']['verdict'], flush=True)


if __name__ == '__main__':
    main()
