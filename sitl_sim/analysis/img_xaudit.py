#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1 img_xaudit v1.1 — takeoff-segment image fingerprint cross-audit.

Prereg v1.1: t1_evidence/v10_2026-10-02/img_xaudit_prereg_v1_1.md (frozen
BEFORE any window statistic; v1 aborted per its ABORT clause — see prereg).
H = run_F3B11_155643 (hostile hover reproducer, images on)
C = run_X1final_040643 (clean X1prime-type route takeoff, images on)
Deterministic: numpy + hashlib only.
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

# v1.1 frozen constants
S1_THR = 0.35      # m, z-error sustained threshold
S1_SUSTAIN = 2.0   # s
S2_GAP = 1.0       # s, odom silence within [arm, arm+30]
PAIR_TOL = 0.5     # s


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
                # v1.1: state events by BAG time (header stamps non-monotonic)
                if getattr(msg, 'armed', False) and arm_t is None:
                    arm_t = ts
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


def paired_err(vins, truth):
    T = np.array([x[0] for x in truth])
    Z = np.array([x[1] for x in truth])
    rows = []
    for tt, zz in vins:
        j = int(np.argmin(np.abs(T - tt)))
        if abs(T[j] - tt) <= PAIR_TOL:
            rows.append((tt, abs(zz - Z[j])))
    return rows


def detect_onset_v11(s, arm):
    """returns dict {S1: t|None, S2: t|None, onset: t|None}"""
    out = {'S1': None, 'S2': None}
    rows = paired_err(s['vins'], s['truth'])
    arr = None
    if rows:
        A = np.array(rows)
        err = A[:, 1]
        for i in range(len(A)):
            if err[i] > S1_THR:
                m = (A[:, 0] > A[i, 0]) & (A[:, 0] <= A[i, 0] + S1_SUSTAIN)
                if m.any() and bool((err[m] > S1_THR).all()):
                    out['S1'] = float(A[i, 0])
                    break
        arr = A
    if arm is not None:
        w = sorted(t for t, _ in s['vins'] if arm - 0.5 <= t <= arm + 30.0)
        for k in range(len(w) - 1):
            if w[k + 1] - w[k] > S2_GAP:
                out['S2'] = w[k]
                break
    cands = [v for v in (out['S1'], out['S2']) if v is not None]
    out['onset'] = min(cands) if cands else None
    return out, arr


def wsel(fr, t0, t1):
    return [f for f in fr if t0 <= f[0] <= t1]


def stats(fr):
    if not fr:
        return None
    core = np.array([[f[2], f[3], f[4]] for f in fr])
    blk = np.array([f[5] for f in fr])
    med = np.concatenate([np.median(core, axis=0), np.median(blk, axis=0)])
    iqr = np.concatenate([np.percentile(core, 75, axis=0) - np.percentile(core, 25, axis=0),
                          np.percentile(blk, 75, axis=0) - np.percentile(blk, 25, axis=0)])
    uniq = len(set(f[1] for f in fr)) / float(len(fr))
    return {'n': len(fr), 'med': med.tolist(), 'iqr': iqr.tolist(),
            'hash_uniq': uniq}


def sep_of(sH, sC):
    medH = np.array(sH['med']); medC = np.array(sC['med']); iqrC = np.array(sC['iqr'])
    return np.abs(medH - medC) / np.maximum(iqrC, 1e-6)


def combo(sep):
    core = sep[0:3]
    blocks = sep[3:19]
    return bool((core > 3.0).sum() >= 3), int((blocks > 3.0).sum())


def main():
    res = {'prereg': 'v1.1', 'v1_abort_note':
           'v1 (7fb0ad14) aborted per ABORT clause: onset |z-t|>1.0m not found in H '
           '(hover-regime signature is sub-meter overestimate + stream starvation); '
           'redesign frozen in v1.1 before window stats.',
           'bags': {}}
    scans = {}
    for key in ('H', 'C'):
        s = scan(key)
        scans[key] = s
        fn = os.path.join(OUT, 'img_xaudit_frames_%s.csv' % s['run'])
        with open(fn, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['t', 'md5', 'mean', 'std', 'grad_med'] +
                       ['bm%02d' % i for i in range(16)] + ['bs%02d' % i for i in range(16)])
            for fr in s['frames']['left']:
                w.writerow([fr[0], fr[1], fr[2], fr[3], fr[4]] +
                           ['%.4f' % v for v in fr[5]] + ['%.4f' % v for v in fr[6]])
        t0L = s['frames']['left'][0][0] if s['frames']['left'] else None
        res['bags'][key] = {'run': s['run'], 'encodings': s['encs'], 'arm_t': s['arm_t'],
                            'n_left': len(s['frames']['left']), 't0_left': t0L,
                            'csv': os.path.basename(fn)}
        print('[scan] %s arm=%s t0L=%s nL=%d' % (key, s['arm_t'], t0L,
                                                 len(s['frames']['left'])), flush=True)

    onH, errH = detect_onset_v11(scans['H'], scans['H']['arm_t'])
    onC, errC = detect_onset_v11(scans['C'], scans['C']['arm_t'])
    res['onset_H'] = onH
    res['onset_C_safety'] = onC
    print('[onset] H=%s C=%s' % (onH, onC), flush=True)
    if onH['onset'] is None or (onC['onset'] is not None):
        res['abort'] = 'onset_H none or C onset found — void, redesign'
        json.dump(res, open(os.path.join(OUT, 'img_xaudit_result.json'), 'w'), indent=1)
        print('[ABORT]', res['abort'], flush=True)
        return

    armH = scans['H']['arm_t']; armC = scans['C']['arm_t']
    dt_on = onH['onset'] - armH
    res['dt_onset'] = dt_on

    def wins(arm, t0L):
        w = {'W_gnd': (arm, arm + 5.0),
             'W_arm': (arm, arm + 30.0),
             'W_pre': (arm, arm + dt_on - 2.0),
             'W_post': (arm + dt_on, arm + dt_on + 15.0)}
        if t0L is not None:
            w['W_static'] = (max(t0L + 1.0, arm - 10.0), arm - 0.2)
        return w

    W = {'H': wins(armH, res['bags']['H']['t0_left']),
         'C': wins(armC, res['bags']['C']['t0_left'])}
    res['windows'] = {k: {wn: list(wv) for wn, wv in W[k].items()} for k in W}

    sc = {}
    for key in ('H', 'C'):
        sc[key] = {}
        for wn, (t0, t1) in W[key].items():
            if t1 is None or t1 <= t0:
                sc[key][wn] = None
                continue
            sel = wsel(scans[key]['frames']['left'], t0, t1)
            st = stats(sel) if sel else None
            if st and st['n'] < 30:
                st['degraded'] = True
            sc[key][wn] = st
    res['win_stats'] = sc

    table = {}
    for wn in ('W_static', 'W_gnd', 'W_pre', 'W_arm', 'W_post'):
        sH, sC = sc['H'].get(wn), sc['C'].get(wn)
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

    def ok(wn):
        e = table.get(wn, {})
        if e.get('status') == 'window-empty':
            return False
        return bool(e.get('combo_pass', False)) and not (e.get('degraded_H') or e.get('degraded_C'))

    st, gd, pre, armw = ok('W_static'), ok('W_gnd'), ok('W_pre'), ok('W_arm')

    def uniq_both(wn):
        e = table.get(wn, {})
        return (e.get('hash_uniq_H', 0) > 0.99 and e.get('hash_uniq_C', 0) > 0.99)

    pre_empty = table.get('W_pre', {}).get('status') == 'window-empty'
    b_windows = [w for w in ('W_static', 'W_gnd', 'W_pre')
                 if table.get(w, {}).get('status') != 'window-empty']
    B_all_nopass = all(not ok(w) for w in b_windows) if b_windows else False
    B_hash = all(uniq_both(w) for w in b_windows) if b_windows else False

    if st and gd:
        verdict = 'A'
    elif st or gd:
        verdict = 'A-'
    elif (not st) and armw:
        verdict = 'C'
    elif B_all_nopass and B_hash:
        verdict = 'B'
    else:
        verdict = 'INDEFINITE'
    res['verdict'] = verdict
    res['verdict_detail'] = {'W_static_pass': st, 'W_gnd_pass': gd,
                             'W_pre_pass': pre, 'W_pre_empty': pre_empty,
                             'W_arm_pass': armw}
    json.dump(res, open(os.path.join(OUT, 'img_xaudit_result.json'), 'w'), indent=1)
    print('[verdict]', verdict, json.dumps(res['verdict_detail']), flush=True)
    for wn in ('W_static', 'W_gnd', 'W_pre', 'W_arm', 'W_post'):
        e = table.get(wn, {})
        if e.get('status') == 'window-empty':
            print(' ', wn, 'EMPTY', flush=True)
        else:
            print(' ', wn, 'nH=%s nC=%s coreSep=%s blk>3=%s pass=%s uniqH=%s uniqC=%s dH=%s dC=%s' %
                  (e['n_H'], e['n_C'], e['sep_core_mean_std_grad'], e['n_blocks_gt3'],
                   e['combo_pass'], e['hash_uniq_H'], e['hash_uniq_C'],
                   e['degraded_H'], e['degraded_C']), flush=True)


if __name__ == '__main__':
    main()
