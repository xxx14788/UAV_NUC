#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1 img_xaudit v1 — takeoff-segment image fingerprint cross-audit (prereg v1).

Prereg: t1_evidence/v10_2026-10-02/img_xaudit_prereg_v1.md
        md5 7fb0ad14aac97ce444d76274358a8b30 (frozen BEFORE any stat computed)
H = run_F3B11_155643 (hostile, hover reproducer, images on)
C = run_X1final_040643 (clean takeoff, X1prime-type route, images on)
Deterministic: numpy + hashlib only, no randomness.
"""
import sys, os, json, hashlib, csv
import numpy as np
import rosbag

RUNS = os.path.expanduser('~/sitl_sim/vins_smoke_runs')
BAGS = {
    'H': ('run_F3B11_155643', 'hostile hover reproducer'),
    'C': ('run_X1final_040643', 'clean X1prime-type route'),
}
OUT = os.path.expanduser('~/catkin_ws/sitl_sim/t1_evidence/v10_2026-10-02')
TOPICS = ['/mavros/state', '/gazebo/model_states', '/vins_estimator/odometry',
          '/iris_stereo_vins/vins_cam_left/image_raw',
          '/iris_stereo_vins/vins_cam_right/image_raw']

def to_gray(msg):
    enc = msg.encoding
    if enc == 'mono8':
        return np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width).astype(np.float64), enc
    if enc in ('bgr8', 'rgb8'):
        a = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, 3)
        return a.mean(axis=2), enc
    if enc == 'mono16':
        return np.frombuffer(msg.data, dtype=np.uint16).reshape(
            msg.height, msg.width) / 256.0, enc
    raise ValueError('encoding %s unsupported' % enc)

def frame_feats(msg):
    g, enc = to_gray(msg)
    h, w = g.shape
    md5 = hashlib.md5(msg.data).hexdigest()
    mean = float(g.mean())
    std = float(g.std())
    gx = np.abs(np.diff(g, axis=1))[:h - 1, :w - 1]
    gy = np.abs(np.diff(g, axis=0))[:h - 1, :w - 1]
    grad_med = float(np.median(gx + gy))
    bh, bw = h // 4, w // 4
    c = g[:4 * bh, :4 * bw].reshape(4, bh, 4, bw).transpose(0, 2, 1, 3).reshape(16, bh * bw)
    return md5, enc, mean, std, grad_med, c.mean(axis=1).tolist(), c.std(axis=1).tolist()

def scan(key):
    run, desc = BAGS[key]
    path = os.path.join(RUNS, run, 'flight.bag')
    frames = {'left': [], 'right': []}
    encs = set()
    arm_t = None
    truth, vins = [], []
    with rosbag.Bag(path) as bag:
        for topic, msg, t in bag.read_messages(topics=TOPICS):
            ts = t.to_sec()
            if topic == '/mavros/state':
                if getattr(msg, 'armed', False) and arm_t is None:
                    hs = msg.header.stamp.to_sec() if msg.header.stamp.to_sec() > 0 else ts
                    arm_t = hs
            elif topic == '/gazebo/model_states':
                if 'iris_stereo_vins' in msg.name:
                    i = msg.name.index('iris_stereo_vins')
                    truth.append((ts, msg.pose[i].position.z))
            elif topic == '/vins_estimator/odometry':
                tt = msg.header.stamp.to_sec() if msg.header.stamp.to_sec() > 0 else ts
                vins.append((tt, msg.pose.pose.position.z))
            elif 'image_raw' in topic:
                side = 'left' if 'left' in topic else 'right'
                tt = msg.header.stamp.to_sec() if msg.header.stamp.to_sec() > 0 else ts
                md5, enc, mean, std, gm, bm, bs = frame_feats(msg)
                encs.add(enc)
                frames[side].append((tt, md5, mean, std, gm, bm, bs))
    return {'key': key, 'run': run, 'desc': desc, 'arm_t': arm_t,
            'truth': truth, 'vins': vins, 'frames': frames, 'encs': sorted(encs)}

def detect_onset(vins, truth, thr=1.0, sustain=2.0, pair_tol=0.5):
    if not vins or not truth:
        return None, []
    T = np.array([x[0] for x in truth])
    Z = np.array([x[1] for x in truth])
    rows = []
    for tt, zz in vins:
        j = int(np.argmin(np.abs(T - tt)))
        if abs(T[j] - tt) <= pair_tol:
            rows.append((tt, zz, Z[j]))
    if not rows:
        return None, []
    A = np.array(rows)
    err = np.abs(A[:, 1] - A[:, 2])
    for i in range(len(A)):
        if err[i] > thr:
            m = (A[:, 0] > A[i, 0]) & (A[:, 0] <= A[i, 0] + sustain)
            if m.any() and bool((err[m] > thr).all()):
                return float(A[i, 0]), A.tolist()
    return None, A.tolist()

def wsel(fr, t0, t1):
    return [f for f in fr if t0 <= f[0] <= t1]

def stats(fr):
    """median vector: [mean,std,grad_med]+16 blockmeans; plus IQRs; hash uniq."""
    if not fr:
        return None
    core = np.array([[f[2], f[3], f[4]] for f in fr])          # mean,std,grad
    blk = np.array([f[5] for f in fr])                          # n x 16
    med = np.concatenate([np.median(core, axis=0), np.median(blk, axis=0)])
    iqr = np.concatenate([np.percentile(core, 75, axis=0) - np.percentile(core, 25, axis=0),
                          np.percentile(blk, 75, axis=0) - np.percentile(blk, 25, axis=0)])
    uniq = len(set(f[1] for f in fr)) / float(len(fr))
    n = len(fr)
    # auxiliary right-cam core medians (non-gating)
    return {'n': n, 'med': med.tolist(), 'iqr': iqr.tolist(), 'hash_uniq': uniq}

def sep_of(sH, sC):
    medH = np.array(sH['med']); medC = np.array(sC['med']); iqrC = np.array(sC['iqr'])
    return np.abs(medH - medC) / np.maximum(iqrC, 1e-6)

def combo(sep):
    """prereg threshold combo on 19 scalars: core(all 3)>3 AND blocks>=4/16>3."""
    core = sep[0:3]
    blocks = sep[3:19]
    return bool((core > 3.0).sum() >= 3), int((blocks > 3.0).sum())

def main():
    res = {'prereg_md5': '7fb0ad14aac97ce444d76274358a8b30', 'bags': {}}
    scans = {}
    for key in ('H', 'C'):
        s = scan(key)
        scans[key] = s
        res['bags'][key] = {
            'run': s['run'], 'desc': s['desc'], 'encodings': s['encs'],
            'arm_t': s['arm_t'],
            'n_left': len(s['frames']['left']), 'n_right': len(s['frames']['right']),
            'n_truth': len(s['truth']), 'n_vins': len(s['vins']),
            't0_left': s['frames']['left'][0][0] if s['frames']['left'] else None,
            't1_left': s['frames']['left'][-1][0] if s['frames']['left'] else None,
        }
        # frames CSV (left)
        fn = os.path.join(OUT, 'img_xaudit_frames_%s.csv' % s['run'])
        with open(fn, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['t', 'md5', 'mean', 'std', 'grad_med'] +
                       ['bm%02d' % i for i in range(16)] + ['bs%02d' % i for i in range(16)])
            for fr in s['frames']['left']:
                w.writerow([fr[0], fr[1], fr[2], fr[3], fr[4]] +
                           ['%.4f' % v for v in fr[5]] + ['%.4f' % v for v in fr[6]])
        res['bags'][key]['csv'] = os.path.basename(fn)
        print('[scan] %s %s arm=%s nL=%d nR=%d enc=%s' %
              (key, s['run'], s['arm_t'], len(s['frames']['left']),
               len(s['frames']['right']), s['encs']), flush=True)

    # onset: H primary; C safety scan (expect none)
    onset_H, pairsH = detect_onset(scans['H']['vins'], scans['H']['truth'])
    onset_C, pairsC = detect_onset(scans['C']['vins'], scans['C']['truth'])
    res['onset_H'] = onset_H
    res['onset_C_safety'] = onset_C
    print('[onset] H=%s C=%s' % (onset_H, onset_C), flush=True)
    if onset_H is None or onset_C is not None:
        res['abort'] = ('onset_H None' if onset_H is None else 'C bag onset found') + \
                       ' — per prereg: cross-audit voided, redesign needed'
        json.dump(res, open(os.path.join(OUT, 'img_xaudit_result.json'), 'w'), indent=1)
        print('[ABORT]', res['abort'], flush=True)
        return

    armH = scans['H']['arm_t']; armC = scans['C']['arm_t']
    if armH is None or armC is None:
        res['abort'] = 'arm time missing (%s/%s)' % (armH, armC)
        json.dump(res, open(os.path.join(OUT, 'img_xaudit_result.json'), 'w'), indent=1)
        print('[ABORT]', res['abort'], flush=True)
        return
    dt_on = onset_H - armH
    res['dt_onset'] = dt_on

    def wins(arm):
        return {
            'W_arm': (arm, arm + 30.0),
            'W_pre': (arm, arm + dt_on - 2.0),
            'W_gnd': (arm, arm + 5.0),
            'W_post': (arm + dt_on, arm + dt_on + 15.0),
        }
    W = {'H': wins(armH), 'C': wins(armC)}
    res['windows'] = {k: {wn: list(wv) for wn, wv in W[k].items()} for k in W}

    sc = {}
    for key in ('H', 'C'):
        sc[key] = {}
        for wn, (t0, t1) in W[key].items():
            if t1 <= t0:
                sc[key][wn] = None
                continue
            sel = wsel(scans[key]['frames']['left'], t0, t1)
            st = stats(sel) if sel else None
            if st and st['n'] < 30:
                st['degraded'] = True
            sc[key][wn] = st
    res['win_stats'] = sc

    table = {}
    for wn in ('W_arm', 'W_pre', 'W_gnd', 'W_post'):
        sH, sC = sc['H'][wn], sc['C'][wn]
        if sH is None or sC is None:
            table[wn] = {'status': 'window-empty'}
            continue
        sep = sep_of(sH, sC)
        core_ok, nblk = combo(sep)
        table[wn] = {
            'n_H': sH['n'], 'n_C': sC['n'],
            'sep_core_mean_std_grad': [round(float(x), 2) for x in sep[0:3]],
            'n_blocks_gt3': nblk,
            'combo_pass': bool(core_ok and nblk >= 4),
            'hash_uniq_H': round(sH['hash_uniq'], 5), 'hash_uniq_C': round(sC['hash_uniq'], 5),
            'degraded_H': sH.get('degraded', False), 'degraded_C': sC.get('degraded', False),
            'med_H_core': [round(x, 3) for x in sH['med'][0:3]],
            'med_C_core': [round(x, 3) for x in sC['med'][0:3]],
            'iqr_C_core': [round(x, 3) for x in sC['iqr'][0:3]],
            'sep_blocks16': [round(float(x), 2) for x in sep[3:19]],
        }
    res['sep_table'] = table

    # criteria (frozen)
    def ok(wn):
        e = table.get(wn, {})
        return bool(e.get('combo_pass', False)) and not (e.get('degraded_H') or e.get('degraded_C'))
    pre, gnd, armw = ok('W_pre'), ok('W_gnd'), ok('W_arm')
    B_core = (table.get('W_pre', {}).get('sep_core_mean_std_grad') is not None and
              max(table['W_pre']['sep_core_mean_std_grad']) <= 3.0 and
              table['W_pre']['n_blocks_gt3'] < 4 and
              table.get('W_pre', {}).get('hash_uniq_H', 0) > 0.99 and
              table.get('W_pre', {}).get('hash_uniq_C', 0) > 0.99)
    if pre and gnd:
        verdict = 'A'
    elif pre or gnd:
        verdict = 'A-'
    elif B_core:
        verdict = 'B'
    elif armw and not pre:
        verdict = 'C'
    else:
        verdict = 'INDEFINITE'
    res['verdict'] = verdict
    json.dump(res, open(os.path.join(OUT, 'img_xaudit_result.json'), 'w'), indent=1)
    print('[verdict]', verdict, flush=True)
    for wn in ('W_arm', 'W_pre', 'W_gnd', 'W_post'):
        e = table.get(wn, {})
        if e.get('status') == 'window-empty':
            print(' ', wn, 'EMPTY', flush=True)
        else:
            print(' ', wn, 'nH=%s nC=%s coreSep=%s blk>3=%s pass=%s uniqH=%s uniqC=%s' %
                  (e['n_H'], e['n_C'], e['sep_core_mean_std_grad'], e['n_blocks_gt3'],
                   e['combo_pass'], e['hash_uniq_H'], e['hash_uniq_C']), flush=True)

if __name__ == '__main__':
    main()
