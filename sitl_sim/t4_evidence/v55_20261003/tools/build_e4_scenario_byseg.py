# -*- coding: utf-8 -*-
"""T4 pool E4 appendix: per-bag x per-manifest-seg mechanical recompute of the
three registered bimodality conditions (docs/t4_e4_bimodal_prereg.md).

Estimator functions below are copied VERBATIM from the registered estimator
  t4_evidence/v54_20261002/derived/d5_compute.py (md5 e6fec99c1a62f056458471c4a785b333)
seeds kept as registered: GMM seed=0 (p50) / seed=1 (p90); BC bootstrap
seed=20261002 (p50) / 20261003 (p90); N_BOOT=10000.

Data sources:
  fbres    = v55_20261003/derived/e4_framelevel_fbres_<bag>.json
             (21db0db verified bin p50 == vision_inputs/fbres_<bag>.json;
             equality is re-checked here against the judgement input)
  manifest = ~/sitl_sim/vision_inputs/<bag>_j3/manifest.json
             (frames[].t_rec / .topic / .seg; seg scheme = pool 49d2ac3:
             bag time base thirds t_min+span*i/3, left-closed right-open)

Bin->seg mapping: bin k covers left-frame indices
  [floor(k*N/K), floor((k+1)*N/K))   (same half-open rule as d5 load_bag)
seg = majority of manifest seg labels over covered indices (straddles flagged).
Secondary consistency check: seg recomputed from time thirds vs manifest label.

REGISTER SCOPE NOTE: docs/t4_e4_bimodal_prereg.md defines NO per-segment
minimum-frame gate and NO per-segment type mapping (its section 3 mapping is
bag-level). This script therefore emits statistics and the three registered
condition booleans per cell only -- no segment type label, no verdict line.
Cells whose estimator cannot run are flagged ok=False with the reason.
"""
import json
import math
import os
import csv

import numpy as np

HOME = os.path.expanduser('~')
V55 = HOME + '/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived'
VI = HOME + '/sitl_sim/vision_inputs'
OUT_JSON = '/tmp/e4_scenario_byseg_out.json'
OUT_MD = '/tmp/e4_scenario_byseg_tables.md'

BAGS = [
    # (bag, pool tag)  -- same six bags / pool tags as registered E4 material
    ('U3PG_210307', 'zhuchi'),
    ('U3PO_211438', 'zhuchi'),
    ('U3PR2_213717', 'zhuchi'),
    ('U3PR1_212450', 'kuochongchi'),
    ('U3PH_210708', 'kuochongchi'),
    ('X1final_173345', 'kuochongchi'),
]

N_BOOT = 10000
SEED = 20261002

# registered box-level reference (_d5_tables.md @ v54_20261002) for the
# replication gate: this run must reproduce these before seg cells are used.
REF = {
    'U3PG_210307':    dict(dbic=3.4042,   bc=0.4798,  cut=40.7225),
    'U3PO_211438':    dict(dbic=-49.9484, bc=0.6573,  cut=1.3555),
    'U3PR2_213717':   dict(dbic=5.8233,   bc=0.3704,  cut=33.3478),
    'U3PR1_212450':   dict(dbic=-47.7269, bc=0.7767,  cut=2.1398),
    'U3PH_210708':    dict(dbic=-278.0038, bc=0.9997, cut=43.9620),
    'X1final_173345': dict(dbic=-161.6918, bc=0.9753, cut=5.9162),
}


# ---------- pure numpy GMM-EM (verbatim from d5_compute.py) ----------
def kmeanspp_init(x, k, rng):
    x = np.asarray(x, float)
    centers = [float(rng.choice(x))]
    for _ in range(k - 1):
        d2 = np.min([(x - c) ** 2 for c in centers], axis=0)
        s = d2.sum()
        if s <= 0:
            centers.append(float(rng.choice(x)))
            continue
        centers.append(float(rng.choice(x, p=d2 / s)))
    return np.sort(np.array(centers))


def gmm_em(x, k, rng, max_iter=500, tol=1e-8, p_floor=1e-6):
    x = np.asarray(x, float)
    n = x.size
    s_floor = max(1e-12, 0.01 * x.std())
    mu = kmeanspp_init(x, k, rng)
    sigma = np.full(k, max(x.std(), s_floor))
    pi = np.full(k, 1.0 / k)
    ll_old = -np.inf
    for _ in range(max_iter):
        comp = np.stack([pi[j] / np.sqrt(2 * np.pi * sigma[j] ** 2) *
                         np.exp(-0.5 * ((x - mu[j]) / sigma[j]) ** 2)
                         for j in range(k)], axis=1) + 1e-300
        resp = comp / comp.sum(axis=1, keepdims=True)
        ll = np.log(comp.sum(axis=1)).sum()
        nk = np.maximum(resp.sum(axis=0), p_floor)
        pi = nk / n
        mu = (resp * x[:, None]).sum(axis=0) / nk
        var = np.maximum((resp * (x[:, None] - mu) ** 2).sum(axis=0) / nk, s_floor ** 2)
        sigma = np.sqrt(var)
        if abs(ll - ll_old) < tol:
            break
        ll_old = ll
    degenerate = bool(np.any(sigma <= s_floor * (1 + 1e-9)))
    return ll, pi, mu, sigma, degenerate


def best_gmm(x, k, n_restart=5, seed=0):
    rng = np.random.default_rng(seed + 7919 * k)
    best = None
    for _ in range(n_restart):
        out = gmm_em(x, k, rng)
        if best is None or out[0] > best[0]:
            best = out
    return best


def bic(ll, n, n_param):
    return -2.0 * ll + n_param * np.log(n)


def gmm_bic_compare(x, seed=0):
    x = np.asarray(x, float)
    n = x.size
    ll1, pi1, mu1, s1, dg1 = best_gmm(x, 1, seed=seed)
    ll2, pi2, mu2, s2, dg2 = best_gmm(x, 2, seed=seed)
    b1, b2 = bic(ll1, n, 2), bic(ll2, n, 5)
    order = np.argsort(mu2)
    pi_s, mu_s, s_s = pi2[order], mu2[order], s2[order]
    comp = np.stack([pi_s[j] / np.sqrt(2 * np.pi * s_s[j] ** 2) *
                     np.exp(-0.5 * ((x - mu_s[j]) / s_s[j]) ** 2) for j in (0, 1)], axis=1) + 1e-300
    post_hi = comp[:, 1] / comp.sum(axis=1)
    return dict(n=n, ll1=ll1, bic1=b1, ll2=ll2, bic2=b2, dbic=b2 - b1,
                pi1=pi1, mu1=mu1, s1=s1, deg1=dg1, deg2=dg2,
                pi2=(pi_s[0], pi_s[1]), mu2=(mu_s[0], mu_s[1]), s2=(s_s[0], s_s[1]),
                post_hi=post_hi, x=x)


def posterior_half_cross(g):
    pl, ph = g['pi2']
    ml, mh = g['mu2']
    sl, sh = g['s2']
    grid = np.linspace(ml, mh, 100001)
    fl = pl / sl * np.exp(-0.5 * ((grid - ml) / sl) ** 2)
    fh = ph / sh * np.exp(-0.5 * ((grid - mh) / sh) ** 2)
    pv = fh / (fl + fh + 1e-300)
    d = pv - 0.5
    sign_change = np.where(np.diff(np.sign(d)) != 0)[0]
    if len(sign_change) == 0:
        return float('nan')
    crosses = []
    for i in sign_change:
        t = grid[i] - d[i] * (grid[i + 1] - grid[i]) / (d[i + 1] - d[i])
        crosses.append((t, d[i] < 0))
    asc = [t for t, is_asc in crosses if is_asc]
    if asc:
        return float(asc[0])
    return float(min(crosses, key=lambda c: abs(c[0] - 0.5 * (ml + mh)))[0])


def skew_kurt(x):
    x = np.asarray(x, float)
    m = x.mean()
    m2 = ((x - m) ** 2).mean()
    m3 = ((x - m) ** 3).mean()
    m4 = ((x - m) ** 4).mean()
    g1 = m3 / m2 ** 1.5
    g2ex = m4 / m2 ** 2 - 3.0
    return g1, g2ex


def bimod_coef(x):
    g1, g2ex = skew_kurt(x)
    return (g1 ** 2 + 1.0) / (g2ex + 3.0)


def bc_bootstrap_ci(x, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        vals[i] = bimod_coef(rng.choice(x, size=x.size, replace=True))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------- data loading (bin->time mapping per d5 load_bag, adapted paths) ----------
def load_bag(bag):
    d = json.load(open(V55 + '/e4_framelevel_fbres_%s.json' % bag, encoding='utf-8'))
    man = json.load(open(VI + '/%s_j3/manifest.json' % bag, encoding='utf-8'))
    lefts = [f for f in man['frames'] if 'left' in f['topic']]
    lefts.sort(key=lambda f: float(f['t_rec']))
    by_t = {}
    for f in lefts:
        by_t.setdefault(float(f['t_rec']), set()).add(int(f['seg']))
    dup_conflict = sum(1 for t in by_t if len(by_t[t]) > 1)
    t_left, seg_left = [], []
    for t in sorted(by_t):
        t_left.append(t)
        seg_left.append(sorted(by_t[t])[0])
    bins = d['stereo']
    K = len(bins)
    N = len(t_left)
    spans, idx_ranges = [], []
    for k in range(K):
        lo_i = int(np.floor(k * N / K))
        hi_i = int(np.floor((k + 1) * N / K))
        t_end = float(t_left[hi_i]) if hi_i < N else float(t_left[N - 1])
        spans.append((float(t_left[lo_i]), max(t_end, float(t_left[lo_i]))))
        idx_ranges.append((lo_i, hi_i))
    return d, man, t_left, seg_left, bins, spans, idx_ranges, dup_conflict


def cell_stats(p50s, p90s, nbs, bag_cut=float('nan')):
    x = np.asarray(p50s, float)
    y = np.asarray(p90s, float)
    n = int(x.size)
    out = dict(n=n, sum_n=int(nbs.sum()) if n else 0)
    if n < 2 or float(np.std(x)) <= 0.0:
        out['ok'] = False
        out['reason'] = 'insufficient_or_degenerate n=%d std=%.3g' % (n, float(np.std(x)) if n else -1.0)
        return out
    g = gmm_bic_compare(x, seed=0)
    g90 = gmm_bic_compare(y, seed=1)
    cut = posterior_half_cross(g)
    bc = bimod_coef(x)
    bc90 = bimod_coef(y)
    lo, hi = bc_bootstrap_ci(x)
    hi_mask = (g['post_hi'] > 0.5) & (x > cut)
    ratio = float(g['mu2'][1] / g['mu2'][0]) if g['mu2'][0] != 0 else float('inf')
    out.update(
        ok=True,
        dbic=float(g['dbic']), bic1=float(g['bic1']), bic2=float(g['bic2']),
        dbic90=float(g90['dbic']),
        mu_lo=float(g['mu2'][0]), mu_hi=float(g['mu2'][1]), pi_hi=float(g['pi2'][1]),
        s_lo=float(g['s2'][0]), s_hi=float(g['s2'][1]),
        deg1=bool(g['deg1']), deg2=bool(g['deg2']),
        cut=float(cut), bc=float(bc), bc90=float(bc90), bc_ci=[lo, hi],
        ratio=ratio,
        c1=bool((g['bic1'] - g['bic2']) > 10.0),
        c2=bool(bc > 0.555),
        c3=bool(ratio >= 1.5),
        n_hi=int(hi_mask.sum()), occ=float(hi_mask.sum()) / n,
        occ_cut08=float((x >= 0.8 * cut).sum()) / n,
        occ_cut12=float((x >= 1.2 * cut).sum()) / n,
        n_hi_bagcut=int((x >= bag_cut).sum()), occ_bagcut=float((x >= bag_cut).sum()) / n,
        p50_med=float(np.percentile(x, 50)), p50_p90=float(np.percentile(x, 90)),
        series_p50=[float(v) for v in x])
    return out


def main():
    rep = {'bags': {}, 'validation': []}
    frames_csv = {}
    csv_path = V55 + '/e4_framelevel_frames.csv'
    with open(csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            frames_csv.setdefault(row['bag'], []).append(row)

    for bag, pool_tag in BAGS:
        d, man, t_left, seg_left, bins, spans, idx_ranges, dup_conflict = load_bag(bag)
        K = len(bins)
        N = len(t_left)
        p50 = np.array([b['p50'] for b in bins])
        p90 = np.array([b['p90'] for b in bins])
        nb = np.array([b['n'] for b in bins], float)

        # source equality: v55 framelevel json vs judgement input vision_inputs fbres
        dv = json.load(open(VI + '/fbres_%s.json' % bag, encoding='utf-8'))
        p50_vi = np.array([b['p50'] for b in dv['stereo']])
        src_max_d = float(np.max(np.abs(p50_vi - p50))) if p50_vi.size == K else None

        # bin->seg majority mapping + straddle flags
        bin_segs, straddle = [], []
        for k, (lo_i, hi_i) in enumerate(idx_ranges):
            labs = seg_left[lo_i:hi_i]
            cnt = {}
            for Lb in labs:
                cnt[Lb] = cnt.get(Lb, 0) + 1
            maj = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            bin_segs.append(int(maj))
            if len(cnt) > 1:
                straddle.append(dict(bin=k, counts={str(a): b for a, b in sorted(cnt.items())},
                                     seg=int(maj)))

        # consistency: manifest seg label vs time-thirds recomputation
        t_min, t_max = t_left[0], t_left[-1]
        span = t_max - t_min
        mism = 0
        for t, Lb in zip(t_left, seg_left):
            s_time = min(2, int(math.floor((t - t_min) * 3.0 / span))) if span > 0 else 0
            if s_time != Lb:
                mism += 1

        # full-bag replication gate (registered seeds)
        g50 = gmm_bic_compare(p50, seed=0)
        g90 = gmm_bic_compare(p90, seed=1)
        bc50 = float(bimod_coef(p50))
        cut = posterior_half_cross(g50)
        lo_ci, hi_ci = bc_bootstrap_ci(p50)
        hi_mask = (g50['post_hi'] > 0.5) & (p50 > cut)
        r = REF[bag]
        dval = dict(bag=bag,
                    d_dbic=abs(float(g50['dbic']) - r['dbic']),
                    d_bc=abs(bc50 - r['bc']),
                    d_cut=abs(float(cut) - r['cut']))
        rep['validation'].append(dval)

        # cross-check vs e4_framelevel_frames.csv (bag-level hi_at_cut + bin start times)
        csv_rows = frames_csv.get(bag, [])
        csv_mismatch = None
        span_start_maxd = None
        if len(csv_rows) == K:
            bad = 0
            maxd = 0.0
            for i, row in enumerate(csv_rows):
                if int(row['hi_at_cut']) != int(hi_mask[i]):
                    bad += 1
                maxd = max(maxd, abs(float(row['t_rec_assumed_s']) - spans[i][0]))
            csv_mismatch = bad
            span_start_maxd = maxd

        cells = {}
        for s in (0, 1, 2):
            m = np.array([b == s for b in bin_segs])
            cells[str(s)] = cell_stats(p50[m], p90[m], nb[m], bag_cut=float(cut))

        rep['bags'][bag] = dict(
            pool_tag=pool_tag, K=K, N_left=N,
            t_span=[t_min, t_max],
            bin_segs=bin_segs, straddle=straddle,
            seg_time_label_mismatch=mism,
            dup_conflict=dup_conflict,
            src_max_absd_p50=src_max_d,
            csv_mismatch=csv_mismatch, span_start_maxd=span_start_maxd,
            bag=dict(dbic=float(g50['dbic']), bc=bc50, bc_ci=[lo_ci, hi_ci],
                     cut=float(cut), dbic90=float(g90['dbic']), bc90=float(bimod_coef(p90)),
                     n_hi=int(hi_mask.sum()), occ=float(hi_mask.sum()) / K,
                     mu_lo=float(g50['mu2'][0]), mu_hi=float(g50['mu2'][1]),
                     deg2=bool(g50['deg2'])),
            cells=cells)

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    # ---------- markdown fragment (ASCII only) ----------
    L = []
    A = L.append
    A('## validation: full-bag replication vs registered _d5_tables.md values')
    A('')
    A('| bag | d_dbic | d_bc | d_cut | src_max_absd_p50 | csv_hi_mismatch | span_start_maxd | seg_time_label_mismatch |')
    A('|---|---|---|---|---|---|---|---|')
    for bag, _ in BAGS:
        b = rep['bags'][bag]
        v = [x for x in rep['validation'] if x['bag'] == bag][0]
        smd = b['src_max_absd_p50']
        A('| %s | %.2e | %.2e | %.2e | %s | %s | %s | %d |' % (
            bag, v['d_dbic'], v['d_bc'], v['d_cut'],
            ('%.2e' % smd) if smd is not None else 'K-mismatch',
            str(b['csv_mismatch']),
            ('%.2e' % b['span_start_maxd']) if b['span_start_maxd'] is not None else 'rows-mismatch',
            b['seg_time_label_mismatch']))
    A('')
    A('## bin->seg counts per bag (K bins; seg=0/1/2 manifest majority; straddle bins listed)')
    A('')
    A('| bag | K | n_seg0 | n_seg1 | n_seg2 | straddle bins (bin:counts->seg) |')
    A('|---|---|---|---|---|---|')
    for bag, _ in BAGS:
        b = rep['bags'][bag]
        bs = b['bin_segs']
        cnt = [bs.count(s) for s in (0, 1, 2)]
        st = '; '.join('b%d:%s->%d' % (s['bin'], s['counts'], s['seg']) for s in b['straddle'])
        if not st:
            st = '-'
        A('| %s | %d | %d | %d | %d | %s |' % (bag, b['K'], cnt[0], cnt[1], cnt[2], st))
    A('')
    A('## per-bag x per-seg three conditions (stereo bin p50 series; c1=BIC1-BIC2>10 i.e. dbic<-10; c2=BC>0.555; c3=mu_hi/mu_lo>=1.5)')
    A('')
    A('no per-seg gate/type mapping is registered; cells are statistics only')
    A('')
    A('| bag | seg | n | sum_n | dbic | BC | BC CI95 | mu_lo | mu_hi | ratio | cut | occ_hi | occ_x0.8 | occ_x1.2 | occ_bagcut | p50_med | p50_p90 | deg2 | c1 | c2 | c3 |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for bag, _ in BAGS:
        b = rep['bags'][bag]
        for s in ('0', '1', '2'):
            c = b['cells'][s]
            if not c.get('ok'):
                A('| %s | %s | %d | %d | NOT-RUN %s | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |' % (
                    bag, s, c['n'], c['sum_n'], c.get('reason', '')))
                continue
            A('| %s | %s | %d | %d | %+.4f | %.4f | [%.4f,%.4f] | %.4g | %.4g | %.4g | %.4f | %.4f | %.4f | %.4f | %.4f | %.4g | %.4g | %s | %s | %s | %s |' % (
                bag, s, c['n'], c['sum_n'], c['dbic'], c['bc'], c['bc_ci'][0], c['bc_ci'][1],
                c['mu_lo'], c['mu_hi'], c['ratio'], c['cut'], c['occ'], c['occ_cut08'], c['occ_cut12'],
                c['occ_bagcut'], c['p50_med'], c['p50_p90'], c['deg2'],
                str(c['c1']).lower(), str(c['c2']).lower(), str(c['c3']).lower()))
    A('')
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')

    # stdout summary
    mx = max(max(v['d_dbic'], v['d_bc'], v['d_cut']) for v in rep['validation'])
    print('VALIDATION max|d| over 6 bags (dbic, bc, cut) = %.3e' % mx)
    for bag, _ in BAGS:
        b = rep['bags'][bag]
        bs = b['bin_segs']
        print('%s K=%d segcount=%s straddle=%d seg_time_mismatch=%d srcdp50=%s' % (
            bag, b['K'], [bs.count(s) for s in (0, 1, 2)], len(b['straddle']),
            b['seg_time_label_mismatch'],
            ('%.1e' % b['src_max_absd_p50']) if b['src_max_absd_p50'] is not None else 'NA'))
        for s in ('0', '1', '2'):
            c = b['cells'][s]
            if c.get('ok'):
                print('  seg%s n=%2d dbic=%+9.4f bc=%.4f ratio=%9.4g cut=%8.4f occ=%.4f c=(%d,%d,%d)' % (
                    s, c['n'], c['dbic'], c['bc'], c['ratio'], c['cut'], c['occ'],
                    c['c1'], c['c2'], c['c3']))
            else:
                print('  seg%s n=%2d NOT-RUN %s' % (s, c['n'], c.get('reason', '')))
    print('wrote %s and %s' % (OUT_JSON, OUT_MD))


if __name__ == '__main__':
    main()
