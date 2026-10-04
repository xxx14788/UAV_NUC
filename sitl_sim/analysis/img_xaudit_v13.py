#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""img_xaudit v1.3 driver — 3090 mid-drift band (prereg v1_3, frozen first).
H1=run_T2MACH3_011804 (anchor 0.008m + T2fail=1), H2=run_T2MACH8_015411
(T2fail=0, j0 FAIL) x C=run_X1final_040643 (NUC clean, imagery).
Windows: W_pre[arm-30,arm] / W_gnd[arm,arm+5] / W_arm[arm,arm+30] /
W_drift = truth-vs-first-goal horizontal-error peak t* +-10s (H rounds);
C has no drift segment -> W_drift replaced by [arm+30,arm+45] (prereg note).
Criteria verbatim v1.2: A = W_pre AND W_gnd all-3-core sep>3.0 & >=4/16
blocks; A- = single window; B = W_pre zero separation & hash uniq >99% both;
C-inversion = W_arm passes while W_pre does not. Discovery face, not a gate.
"""
import sys, os, json
import numpy as np
import rosbag

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import img_xaudit as xa

H = {'H1': ('run_T2MACH3_011804', '3090 mid-drift, anchor 0.008m, T2fail=1'),
     'H2': ('run_T2MACH8_015411', '3090 mid-drift, T2fail=0, j0 FAIL')}
for k, v in H.items():
    xa.BAGS[k] = v

OUT = os.path.expanduser('~/sitl_sim/t1_evidence/v11_4_2026-10-05')


def scan_goal_truthxy(run):
    """Light pass: truth x/y + first goal (x,y). MACH bags record
    /gazebo/model_states and /move_base_simple/goal (verified topic list)."""
    path = os.path.expanduser('~/sitl_sim/vins_smoke_runs/%s/flight.bag' % run)
    truth_xy, goal_xy = [], None
    with rosbag.Bag(path) as bag:
        for topic, msg, t in bag.read_messages(
                topics=['/gazebo/model_states', '/move_base_simple/goal']):
            ts = t.to_sec()
            if topic == '/move_base_simple/goal':
                if goal_xy is None:
                    goal_xy = (msg.pose.position.x, msg.pose.position.y)
            else:
                if 'iris_stereo_vins' in msg.name:
                    i = msg.name.index('iris_stereo_vins')
                    p = msg.pose[i].position
                    truth_xy.append((ts, p.x, p.y))
    return truth_xy, goal_xy


def main():
    res = {'prereg': 'v1.3', 'bags': {}}
    scans = {}
    import csv as _csv
    for key in ('H1', 'H2', 'C'):
        s = xa.scan(key)
        scans[key] = s
        fn = os.path.join(OUT, 'img_xaudit_v13_frames_%s.csv' % s['run'])
        with open(fn, 'w', newline='') as f:
            w = _csv.writer(f)
            w.writerow(['t', 'md5', 'mean', 'std', 'grad_med'])
            for fr in s['frames']['left']:
                w.writerow([fr[0], fr[1], fr[2], fr[3], fr[4]])
        t0L = s['frames']['left'][0][0] if s['frames']['left'] else None
        res['bags'][key] = {'run': s['run'], 'arm_t': s['arm_t'],
                            'n_left': len(s['frames']['left']), 't0_left': t0L}
        print('[scan] %s arm=%s nL=%d' % (key, s['arm_t'], len(s['frames']['left'])), flush=True)

    armC = scans['C']['arm_t']

    def wins_H(s, run):
        arm = s['arm_t']
        w = {'W_gnd': (arm, arm + 5.0),
             'W_arm': (arm, arm + 30.0),
             'W_pre': (max((s['frames']['left'][0][0] + 1.0) if s['frames']['left'] else arm - 30.0,
                           arm - 30.0), arm - 0.2),
             # v1.2-isomorphic 10s static window: cross-check for the W_pre
             # artifact hypothesis (C-side W_pre held only ~58 frames here
             # because X1final's image stream starts late -> IQR~0 blowup)
             'W_static': (max((s['frames']['left'][0][0] + 1.0) if s['frames']['left'] else arm - 10.0,
                              arm - 10.0), arm - 0.2)}
        tstar = None
        truth_xy, goal_xy = scan_goal_truthxy(run)
        if truth_xy and goal_xy is not None:
            gx, gy = goal_xy
            A = np.array(truth_xy)
            d = np.hypot(A[:, 1] - gx, A[:, 2] - gy)
            tstar = float(A[int(np.argmax(d)), 0])
            w['W_drift'] = (tstar - 10.0, tstar + 10.0)
        return w, tstar

    W = {}
    for key in ('H1', 'H2'):
        W[key], tstar = wins_H(scans[key], scans[key]['run'])
        res['bags'][key]['t_drift_peak'] = tstar
    W['C'] = {'W_gnd': (armC, armC + 5.0),
              'W_arm': (armC, armC + 30.0),
              'W_pre': (max(scans['C']['frames']['left'][0][0] + 1.0, armC - 30.0), armC - 0.2),
              'W_static': (max(scans['C']['frames']['left'][0][0] + 1.0, armC - 10.0), armC - 0.2),
              'W_drift': (armC + 30.0, armC + 45.0)}  # prereg: C has no drift segment
    res['windows'] = {k: {wn: list(wv) for wn, wv in W[k].items()} for k in W}

    sc = {k: {} for k in W}
    for key in W:
        for wn, (t0, t1) in W[key].items():
            if t1 is None or t1 <= t0:
                sc[key][wn] = None
                continue
            sel = xa.wsel(scans[key]['frames']['left'], t0, t1)
            st = xa.stats(sel) if sel else None
            if st and st['n'] < 30:
                st['degraded'] = True
            sc[key][wn] = st
    res['win_stats'] = sc

    def table_for(key):
        table = {}
        for wn in ('W_pre', 'W_static', 'W_gnd', 'W_arm', 'W_drift'):
            sH, sC = sc[key].get(wn), sc['C'].get(wn)
            if sH is None or sC is None:
                table[wn] = {'status': 'window-empty'}
                continue
            sep = xa.sep_of(sH, sC)
            core_ok, nblk = xa.combo(sep)
            table[wn] = {
                'n_H': sH['n'], 'n_C': sC['n'],
                'sep_core': [round(float(x), 2) for x in sep[0:3]],
                'n_blocks_gt3': nblk,
                'combo_pass': bool(core_ok and nblk >= 4),
                'hash_uniq_H': round(sH['hash_uniq'], 5),
                'hash_uniq_C': round(sC['hash_uniq'], 5),
                'med_H_core': [round(x, 3) for x in sH['med'][0:3]],
                'med_C_core': [round(x, 3) for x in sC['med'][0:3]],
            }
        return table

    res['sep_table'] = {k: table_for(k) for k in ('H1', 'H2')}

    def verdict(tb):
        pre, gnd = tb.get('W_pre', {}), tb.get('W_gnd', {})
        arm = tb.get('W_arm', {})
        if pre.get('status') == 'window-empty' or gnd.get('status') == 'window-empty':
            return 'VOID-window-empty'
        pre_pass = pre.get('combo_pass', False)
        gnd_pass = gnd.get('combo_pass', False)
        if pre_pass and gnd_pass:
            return 'A'
        if pre_pass or gnd_pass:
            return 'A-'
        zero_sep = all(v <= 3.0 for v in pre.get('sep_core', [9e9]))
        uniq_ok = pre.get('hash_uniq_H', 0) > 0.99 and pre.get('hash_uniq_C', 0) > 0.99
        if zero_sep and uniq_ok:
            return 'B'
        if arm.get('combo_pass', False) and not pre_pass:
            return 'C-inversion'
        return 'indefinite'

    res['verdict'] = {k: verdict(res['sep_table'][k]) for k in ('H1', 'H2')}
    fn = os.path.join(OUT, 'img_xaudit_v13_result.json')
    json.dump(res, open(fn, 'w'), indent=1, default=float)
    print('[verdict]', res['verdict'], '->', fn, flush=True)


if __name__ == '__main__':
    main()
