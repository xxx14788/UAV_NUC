#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""img_xaudit v1.2 driver — n=2 hostile extension (prereg v1_2, frozen first).
Pairs: H1=run_F3B11_155643 (climb-overestimate flatline), H2=run_F3B16_191620
(birth-failure never-flew) x C=run_X1final_040643. S2 window extended to
[arm, arm+60] per v1.2 (F3B16 B2 event at arm+32s). All thresholds and
A/A-/B/C criteria unchanged from v1.1. Combined verdict B+ if both hostile
bags indistinguishable in W_static/W_gnd/W_pre with hash uniq >99%."""
import sys, os, json, csv
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import img_xaudit as xa

H = {'H1': ('run_F3B11_155643', 'hostile climb-overestimate flatline'),
     'H2': ('run_F3B16_191620', 'hostile birth-failure never-flew')}
for k, v in H.items():
    xa.BAGS[k] = v


def detect_onset_v12(s, arm):
    out = {'S1': None, 'S2': None}
    rows = xa.paired_err(s['vins'], s['truth'])
    if rows:
        A = np.array(rows)
        err = A[:, 1]
        for i in range(len(A)):
            if err[i] > xa.S1_THR:
                m = (A[:, 0] > A[i, 0]) & (A[:, 0] <= A[i, 0] + xa.S1_SUSTAIN)
                if m.any() and bool((err[m] > xa.S1_THR).all()):
                    out['S1'] = float(A[i, 0])
                    break
    if arm is not None:
        w = sorted(t for t, _ in s['vins'] if arm - 0.5 <= t <= arm + 60.0)
        for k in range(len(w) - 1):
            if w[k + 1] - w[k] > xa.S2_GAP:
                out['S2'] = w[k]
                break
    cands = [v for v in (out['S1'], out['S2']) if v is not None]
    out['onset'] = min(cands) if cands else None
    return out


def pair_table(hs, cs, armH, armC, dt_on, t0L_H, t0L_C):
    def wins(arm, t0L):
        w = {'W_gnd': (arm, arm + 5.0),
             'W_arm': (arm, arm + 30.0),
             'W_pre': (arm, arm + dt_on - 2.0),
             'W_post': (arm + dt_on, arm + dt_on + 15.0)}
        if t0L is not None:
            w['W_static'] = (max(t0L + 1.0, arm - 10.0), arm - 0.2)
        return w
    W = {'H': wins(armH, t0L_H), 'C': wins(armC, t0L_C)}
    sc = {}
    for key, s in (('H', hs), ('C', cs)):
        sc[key] = {}
        for wn, (t0, t1) in W[key].items():
            if t1 is None or t1 <= t0:
                sc[key][wn] = None
                continue
            sel = xa.wsel(s['frames']['left'], t0, t1)
            st = xa.stats(sel) if sel else None
            if st and st['n'] < 30:
                st['degraded'] = True
            sc[key][wn] = st
    table = {}
    for wn in ('W_static', 'W_gnd', 'W_pre', 'W_arm', 'W_post'):
        sH, sC = sc['H'].get(wn), sc['C'].get(wn)
        if sH is None or sC is None:
            table[wn] = {'status': 'window-empty'}
            continue
        sep = xa.sep_of(sH, sC)
        core_ok, nblk = xa.combo(sep)
        table[wn] = {
            'n_H': sH['n'], 'n_C': sC['n'],
            'sep_core': [round(float(x), 2) for x in sep[0:3]],
            'n_blocks_gt3': nblk, 'combo_pass': bool(core_ok and nblk >= 4),
            'hash_uniq_H': round(sH['hash_uniq'], 5),
            'hash_uniq_C': round(sC['hash_uniq'], 5),
            'degraded_H': sH.get('degraded', False),
            'degraded_C': sC.get('degraded', False)}
    return table


def main():
    res = {'prereg': 'v1.2', 'bags': {}, 'pairs': {}}
    scans = {'C': xa.scan('C')}
    for k in H:
        scans[k] = xa.scan(k)
        fn = os.path.join(xa.OUT, 'img_xaudit_frames_%s.csv' % scans[k]['run'])
        with open(fn, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['t', 'md5', 'mean', 'std', 'grad_med'] +
                       ['bm%02d' % i for i in range(16)] + ['bs%02d' % i for i in range(16)])
            for fr in scans[k]['frames']['left']:
                w.writerow([fr[0], fr[1], fr[2], fr[3], fr[4]] +
                           ['%.4f' % v for v in fr[5]] + ['%.4f' % v for v in fr[6]])
        res['bags'][k] = {'run': scans[k]['run'], 'n_left': len(scans[k]['frames']['left']),
                          'arm_t': scans[k]['arm_t']}
        print('[scan] %s %s nL=%d' % (k, scans[k]['run'], len(scans[k]['frames']['left'])), flush=True)
    res['bags']['C'] = {'run': scans['C']['run'],
                        'n_left': len(scans['C']['frames']['left']),
                        'arm_t': scans['C']['arm_t']}
    onsets = {k: detect_onset_v12(scans[k], scans[k]['arm_t']) for k in list(H) + ['C']}
    res['onsets'] = onsets
    print('[onsets]', {k: v['onset'] for k, v in onsets.items()}, flush=True)
    if onsets['C']['onset'] is not None:
        res['abort'] = 'C onset found — void'
        json.dump(res, open(os.path.join(xa.OUT, 'img_xaudit_result_v12.json'), 'w'), indent=1)
        print('[ABORT] C onset', flush=True)
        return
    armC = scans['C']['arm_t']
    t0L = {k: (scans[k]['frames']['left'][0][0] if scans[k]['frames']['left'] else None)
           for k in list(H) + ['C']}
    combined_indist = True
    for k in H:
        if onsets[k]['onset'] is None:
            res['pairs'][k] = {'abort': 'no onset — pair void, annotated'}
            combined_indist = False
            continue
        armH = scans[k]['arm_t']
        dt = onsets[k]['onset'] - armH
        t = pair_table(scans[k], scans['C'], armH, armC, dt, t0L[k], t0L['C'])
        res['pairs'][k] = {'dt_onset': dt, 'onset_detail': onsets[k], 'table': t}
        print('[pair %s] dt_onset=%.2f' % (k, dt), flush=True)
        for wn in ('W_static', 'W_gnd', 'W_pre', 'W_arm', 'W_post'):
            e = t.get(wn, {})
            if e.get('status') == 'window-empty':
                print('  ', wn, 'EMPTY', flush=True)
            else:
                print('  ', wn, 'nH=%s nC=%s coreSep=%s blk>3=%s pass=%s uniqH=%s uniqC=%s' %
                      (e['n_H'], e['n_C'], e['sep_core'], e['n_blocks_gt3'],
                       e['combo_pass'], e['hash_uniq_H'], e['hash_uniq_C']), flush=True)
        # v1.1 B-condition per pair (static/gnd/pre no-combo + hash>0.99)
        def ok(wn):
            e = t.get(wn, {})
            if e.get('status') == 'window-empty':
                return False
            return bool(e.get('combo_pass')) and not (e.get('degraded_H') or e.get('degraded_C'))
        wins_b = [w for w in ('W_static', 'W_gnd', 'W_pre')
                  if t.get(w, {}).get('status') != 'window-empty']
        nopass = all(not ok(w) for w in wins_b) if wins_b else False
        hashes = all(t.get(w, {}).get('hash_uniq_H', 0) > 0.99 and
                     t.get(w, {}).get('hash_uniq_C', 0) > 0.99 for w in wins_b) if wins_b else False
        st, gd = ok('W_static'), ok('W_gnd')
        if st and gd:
            v = 'A'
        elif st or gd:
            v = 'A-'
        elif (not st) and ok('W_arm'):
            v = 'C'
        elif nopass and hashes:
            v = 'B'
        else:
            v = 'INDEFINITE'
        res['pairs'][k]['verdict'] = v
        if v != 'B':
            combined_indist = False
        print('[pair %s verdict] %s' % (k, v), flush=True)
    res['combined_verdict'] = 'B+' if combined_indist else 'MIXED (see per-pair)'
    json.dump(res, open(os.path.join(xa.OUT, 'img_xaudit_result_v12.json'), 'w'), indent=1)
    print('[combined]', res['combined_verdict'], flush=True)


if __name__ == '__main__':
    main()
