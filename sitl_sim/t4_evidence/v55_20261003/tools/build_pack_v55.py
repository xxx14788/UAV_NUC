#!/usr/bin/env python3
# T4-5.5 smooth-lie pack builder -- MECHANICAL SEGMENTATION + QUANTILES ONLY.
# NO PASS/FAIL/verdict wording: verdict text is main-session-only per prereg
#   ~/catkin_ws/docs/t4_smooth_lie_prereg.md (md5 6784d008bd50230cc388094c5e698d68)
# Frozen segment = consecutive odom pz>5.0 m window (z col read from csv header).
# Frame membership = manifest t_rec inside window.
# Metrics source: existing per-frame JSONs (segmented directly, no re-run),
#   per ask step 3 branch "逐帧明细已存在则直接分段".
import csv, json, os, sys
import numpy as np

ODOM_CSV = '/home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/tools/out/jr3_replay_U3PR2_213717_odom.csv'
VI = '/home/uav/sitl_sim/vision_inputs'
PR2 = 'U3PR2_213717'
PG = 'U3PG_210307'
PH = 'U3PH_210708'
Z_THR = 5.0
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else '/tmp/t455_derived'
QS = [10, 25, 50, 75, 90]

def fail(msg):
    sys.stderr.write('PACK-BUILD-STOP: %s\n' % msg)
    sys.exit(2)

def qstats(vals, qs=QS):
    a = np.array([float(v) for v in vals if v is not None], dtype=float)
    if a.size == 0:
        return {'n': 0}
    return {'n': int(a.size),
            **{('p%d' % q): float(np.percentile(a, q)) for q in qs}}

def load_manifest(tag):
    with open(os.path.join(VI, tag + '_j3', 'manifest.json')) as f:
        return json.load(f)

def load_json(path):
    with open(path) as f:
        return json.load(f)

# ---------- fbres tool-order replication (j3_fb_residual.py:125-133,157-168) ----------
def primary_lr(man):
    frames = list(man['frames'])
    lf = sorted([fr for fr in frames
                 if ('cam_left' in fr['topic'] or 'infra1' in fr['topic']
                     or 'left' in fr['topic']) and fr.get('tag', '') == ''],
                key=lambda x: x['t_rec'])
    rf = sorted([fr for fr in frames
                 if ('cam_right' in fr['topic'] or 'infra2' in fr['topic']
                     or 'right' in fr['topic']) and fr.get('tag', '') == ''],
                key=lambda x: x['t_rec'])
    return lf, rf

def fb_join(tag):
    """Return {file_of_frame_i: (t_med,t_p90,s_med,s_p90)}.
    Join valid ONLY if pool count == nf (stereo) and nf-1 (temporal),
    i.e. every fb_residual succeeded and append order == frame order."""
    man = load_manifest(tag)
    lf, rf = primary_lr(man)
    nf = min(len(lf), len(rf))
    fb = load_json(os.path.join(VI, 'fbres_%s.json' % tag))
    st, tp = fb['stereo'], fb['temporal']
    if not (len(st) == nf and len(tp) == nf - 1):
        # honest downgrade: per-frame FB join would misalign (tool appends only
        # on success); caller must fall back, no guessed alignment.
        return (None, nf, len(lf), len(rf), len(st), len(tp))
    out = {}
    for i in range(nf):
        fi = lf[i]['file']
        s = st[i]
        row_s = (s['p50'], s['p90'])
        if i < nf - 1:
            t = tp[i]
            row_t = (t['p50'], t['p90'])
        else:
            row_t = (None, None)   # last frame has no temporal pair
        out[fi] = (row_t, row_s)
    return out, nf, len(lf), len(rf), len(st), len(tp)

# ---------- metrics per_frame keyed by file ----------
def perframe_map(tag):
    m = load_json(os.path.join(VI, 'metrics_%s.json' % tag))
    return {e['file']: e for e in m['per_frame']}, m

# ---------- step 1: mechanical segmentation of odom csv ----------
def segment_odom():
    with open(ODOM_CSV) as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        zcol = 'pz'
        if zcol not in cols:
            zcol = [c for c in cols if c.lower() in ('pz', 'z', 'pos_z')]
            if not zcol:
                fail('odom csv: no z column in header %r' % (cols,))
            zcol = zcol[0]
        tcol = 't'
        rows = [(float(r[tcol]), float(r[zcol])) for r in rd]
    rows.sort(key=lambda x: x[0])
    # prereg s2 verbatim: window edges = FIRST/LAST time the condition holds.
    # NOTE csv structure (extract_odom_pc.py: single topic /vins_estimator/odometry):
    # same-stamp DOUBLE rows exist (two solutions per stamp: honest z~0 + fictional
    # rising z). Interleaved honest rows do NOT break the window under the prereg
    # edge rule; the double-row structure is reported in the appendix as-is.
    import collections
    gt = [(t, z) for t, z in rows if z > Z_THR]
    if not gt:
        fail('no odom row with %s>%.1f found' % (zcol, Z_THR))
    frozen = (gt[0][0], gt[-1][0], len(gt))
    tc = collections.Counter(t for t, z in rows)
    dup_groups = sum(1 for c in tc.values() if c > 1)
    max_per_stamp = max(tc.values())
    singles = [t for t, c in tc.items() if c == 1]
    # row-level consecutive-run audit (kept as-is for the record; interleave makes
    # runs tiny -- this is csv structure, not the prereg window)
    runs = []
    cur = 0
    for t, z in rows:
        if z > Z_THR:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    audit = {'total_rows': len(rows), 'rows_gt': len(gt), 'rows_le': len(rows) - len(gt),
             'dup_stamp_groups': dup_groups, 'max_rows_per_stamp': max_per_stamp,
             'single_stamps': len(singles), 'single_stamps_max_t': max(singles) if singles else -1,
             'row_run_max': max(runs) if runs else 0, 'row_run_count': len(runs)}
    return frozen, cols, zcol, rows[0][0], rows[-1][0], audit

# ---------- assemble ----------
def metrics_table(tag, fbmap, pfmap, man, window=None):
    """window=None -> all primary frames (control bags). Else tuple (t0,t1).
    fbmap=None -> FB join unavailable; FB fields stay None (reported as n/a)."""
    lf, rf = primary_lr(man)
    lfiles = [fr['file'] for fr in lf]
    rfiles = [fr['file'] for fr in rf]
    primary = sorted(set(lfiles) | set(rfiles),
                     key=lambda f: man_file_t(man, f))
    sel = []
    for f in primary:
        t = man_file_t(man, f)
        if window is None or (window[0] <= t <= window[1]):
            sel.append(f)
    m1 = [pfmap[f].get('supply_frac') for f in sel]
    sig = [pfmap[f].get('d12_sigma_p25') for f in sel]
    m2 = [pfmap[f].get('grid4x4_occupancy_frac') for f in sel]
    mg = [pfmap[f].get('med_gray') for f in sel]
    ftm = [fbmap[f][0][0] if fbmap and f in fbmap else None for f in sel]
    ftp = [fbmap[f][0][1] if fbmap and f in fbmap else None for f in sel]
    fsm = [fbmap[f][1][0] if fbmap and f in fbmap else None for f in sel]
    fsp = [fbmap[f][1][1] if fbmap and f in fbmap else None for f in sel]
    return {
        'M1_supply_frac': qstats(m1),
        'sigma_d12_p25': qstats(sig),
        'M2_grid4x4_occupancy_frac': qstats(m2),
        'fb_temporal_med': qstats(ftm),
        'fb_temporal_p90': qstats(ftp),
        'fb_stereo_med': qstats(fsm),
        'fb_stereo_p90': qstats(fsp),
        'med_gray': qstats(mg),
        'n_primary_selected': len(sel),
    }

def man_file_t(man, fname):
    for fr in man['frames']:
        if fr['file'] == fname:
            return fr['t_rec']
    fail('manifest: frame %s not found' % fname)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # --- segmentation ---
    frozen, cols, zcol, tmin, tmax, audit = segment_odom()
    t0, t1, nrows = frozen
    dur = t1 - t0

    # --- frame membership (PR2) ---
    man2 = load_manifest(PR2)
    pf2, mfull2 = perframe_map(PR2)
    fb2, nf2, nlf2, nrf2, nst2, ntp2 = fb_join(PR2)
    cnt = {'prim_in': 0, 'prim_out': 0, 'next_in': 0, 'next_out': 0}
    for fr in man2['frames']:
        inw = t0 <= fr['t_rec'] <= t1
        key = ('next_' if fr.get('tag') else 'prim_') + ('in' if inw else 'out')
        cnt[key] += 1

    # sanity: per_frame files == manifest files
    mf_files = {fr['file'] for fr in man2['frames']}
    if set(pf2.keys()) != mf_files:
        fail('PR2 per_frame files != manifest files (%d vs %d)'
             % (len(pf2), len(mf_files)))
    # sanity: tool aggregate n vs primary count
    n_prim_manifest = cnt['prim_in'] + cnt['prim_out']
    if mfull2['n_primary'] != n_prim_manifest:
        fail('PR2 n_primary=%d != manifest primary frames=%d'
             % (mfull2['n_primary'], n_prim_manifest))

    # --- quantile tables ---
    froz_tbl = metrics_table(PR2, fb2, pf2, man2, window=(t0, t1))
    all_tbl = metrics_table(PR2, fb2, pf2, man2, window=None)

    pg_fb, nf_pg, nlf_pg, nrf_pg, _, _ = fb_join(PG)
    pg_pf, pg_full = perframe_map(PG)
    pg_man = load_manifest(PG)
    pg_tbl = metrics_table(PG, pg_fb, pg_pf, pg_man, window=None)

    ph_fb, nf_ph, nlf_ph, nrf_ph, nst_ph, ntp_ph = fb_join(PH)
    ph_pf, ph_full = perframe_map(PH)
    ph_man = load_manifest(PH)
    ph_tbl = metrics_table(PH, ph_fb, ph_pf, ph_man, window=None)
    ph_ok = ph_fb is not None
    ph_pools = None
    if not ph_ok:
        ph_pools = load_json(os.path.join(VI, 'fbres_%s.json' % PH))
        ph_pools = {'temporal_pool': ph_pools.get('temporal_pool'),
                    'stereo_pool': ph_pools.get('stereo_pool')}

    # --- write segments.csv ---
    seg_path = os.path.join(OUT_DIR, 'smooth_lie_segments.csv')
    with open(seg_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['window_id', 't_start_s', 't_end_s', 'dur_s', 'n_rows_gt5',
                    'total_rows', 'rows_le5', 'dup_stamp_groups',
                    'max_rows_per_stamp', 'row_run_max', 'n_primary_in',
                    'n_primary_out', 'n_next_in', 'n_next_out'])
        w.writerow(['frozen', t0, t1, dur, nrows, audit['total_rows'],
                    audit['rows_le'], audit['dup_stamp_groups'],
                    audit['max_rows_per_stamp'], audit['row_run_max'],
                    cnt['prim_in'], cnt['prim_out'], cnt['next_in'], cnt['next_out']])

    # --- write perframe.csv (all PR2 sampled frames, membership flagged) ---
    pf_path = os.path.join(OUT_DIR, 'smooth_lie_perframe.csv')
    with open(pf_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'topic', 'tag', 'seg', 't_rec', 'in_window',
                    'supply_frac', 'd12_sigma_p25', 'grid4x4_occupancy_frac',
                    'med_gray', 'corners_gFT',
                    'fb_temporal_med', 'fb_temporal_p90',
                    'fb_stereo_med', 'fb_stereo_p90'])
        for fr in sorted(man2['frames'], key=lambda x: x['t_rec']):
            e = pf2.get(fr['file'], {})
            row_t, row_s = fb2.get(fr['file'], ((None, None), (None, None)))
            w.writerow([fr['file'], fr['topic'], fr.get('tag', ''), fr.get('seg'),
                        fr['t_rec'], int(t0 <= fr['t_rec'] <= t1),
                        e.get('supply_frac'), e.get('d12_sigma_p25'),
                        e.get('grid4x4_occupancy_frac'), e.get('med_gray'),
                        e.get('corners_gFT'),
                        row_t[0], row_t[1], row_s[0], row_s[1]])

    # --- write pack.md ---
    md_path = os.path.join(OUT_DIR, 'smooth_lie_pack.md')
    L = []
    A = L.append
    A('# T4-5.5 smooth-lie segment data pack (mechanical output)')
    A('')
    A('- prereg criteria: ~/catkin_ws/docs/t4_smooth_lie_prereg.md '
      '(md5 6784d008bd50230cc388094c5e698d68); segmentation per prereg section 2,')
    A('  metrics set per prereg section 3. **No verdict wording here; '
      'three-state reading is main-session-only per prereg section 4.**')
    A('- odom csv: %s' % ODOM_CSV)
    A('  - header=%r -> z column used: %s; threshold pz > %.1f m' % (cols, zcol, Z_THR))
    A('  - csv t range: %.3f .. %.3f s, total rows=%d' % (tmin, tmax, audit['total_rows']))
    A('- frozen window (prereg s2: first/last t with pz>%.1f): t=[%.3f, %.3f] s, '
      'dur=%.3f s, rows with pz>%.1f=%d'
      % (Z_THR, t0, t1, dur, Z_THR, nrows))
    A('- csv STRUCTURE AUDIT (fact, no reading): single topic /vins_estimator/odometry;')
    A('  same-stamp DOUBLE rows: dup_stamp_groups=%d, max rows per stamp=%d,'
      % (audit['dup_stamp_groups'], audit['max_rows_per_stamp']))
    A('  single-row stamps=%d (all t<=%.3f s, pz<=5) -- two odom solutions coexist per'
      % (audit['single_stamps'], audit['single_stamps_max_t']))
    A('  stamp (honest z~0 interleaved with fictional rising z); file row order =')
    A('  message arrival order, so row-level consecutive pz>5 runs fragment')
    A('  (max=%d over %d runs); row runs are NOT the segmentation basis -- prereg'
      % (audit['row_run_max'], audit['row_run_count']))
    A('  window-edges rule (first/last t holding) governs. rows_le5=%d (honest source'
      % audit['rows_le'])
    A('  + pre-onset), rows_gt5=%d (fictional source).' % nrows)
    A('- frame source: metrics_%s.json per_frame (per-frame detail EXISTS -> direct '
      'segmentation, no re-run; ask step-3 branch), joined to manifest t_rec by file.' % PR2)
    A('- FB per-frame join: fbres_%s.json temporal/stereo pools mapped to t_rec-sorted '
      'primary frames i / pair(i,i+1) per j3_fb_residual.py:125-133,157-168,179-180; '
      'join guarded by pool-count check (stereo==nf, temporal==nf-1; nf=%d L=%d R=%d) '
      'so no silent misalignment. FB n in tables counts LEFT-camera primary frames '
      'only (pools are built over the L-frame sequence; R frames carry no FB pool).'
      % (PR2, nf2, nlf2, nrf2))
    A('- primary-frame口径: metrics tool aggregates tag==\'\' frames (n_primary=%d); '
      'pack follows same口径. next-tagged frames flagged in perframe.csv but excluded '
      'from quantiles.' % mfull2['n_primary'])
    A('')
    A('## Six metrics, frozen window P25/P50/P90 + n (prereg section 3)')
    A('')
    A('| metric | frozen P25 | frozen P50 | frozen P90 | frozen n | PG P10 | PG P25 | PG P50 | PG P90 | PG n | PH P10 | PH P90 | PH n |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k in froz_tbl:
        if k == 'n_primary_selected':
            continue
        fz, pg, ph = froz_tbl[k], pg_tbl[k], (ph_tbl or {}).get(k, {'n': 0})
        def f3(d):
            return ('%.6g' % d['p25'], '%.6g' % d['p50'], '%.6g' % d['p90'], d['n']) if d.get('n') else ('-', '-', '-', 0)
        a, b, c, n = f3(fz)
        p10g = '%.6g' % pg['p10'] if pg.get('n') else '-'
        p25g = '%.6g' % pg['p25'] if pg.get('n') else '-'
        p50g = '%.6g' % pg['p50'] if pg.get('n') else '-'
        p90g = '%.6g' % pg['p90'] if pg.get('n') else '-'
        h10 = '%.6g' % ph['p10'] if ph.get('n') else '-'
        h90 = '%.6g' % ph['p90'] if ph.get('n') else '-'
        A('| %s | %s | %s | %s | %d | %s | %s | %s | %s | %d | %s | %s | %d |'
          % (k, a, b, c, n, p10g, p25g, p50g, p90g, pg['n'], h10, h90, ph['n']))
    A('')
    A('Mechanical numeric cross-ref ONLY (not a reading): for each metric, frozen P50 '
      'vs PG band [P10,P90]: inside/outside is a pure numeric comparison recorded below; '
      'band-membership mapping to states = prereg section 4 = main session.')
    A('')
    A('| metric | frozen P50 | PG band [P10,P90] | p50_within_pg_band | direction if outside |')
    A('|---|---|---|---|---|')
    for k in froz_tbl:
        if k == 'n_primary_selected':
            continue
        fz, pg = froz_tbl[k], pg_tbl[k]
        if fz.get('n') and pg.get('n'):
            v = fz['p50']
            lo, hi = pg['p10'], pg['p90']
            inw = 'yes' if lo <= v <= hi else 'no'
            dr = '' if inw == 'yes' else ('high' if v > hi else 'low')
            A('| %s | %.6g | [%.6g, %.6g] | %s | %s |' % (k, v, lo, hi, inw, dr))
        else:
            A('| %s | - | - | n/a | n/a |' % k)
    A('')
    A('## Appendix counters (prereg section 2 frame-membership accounting)')
    A('')
    A('- PR2 sampled frames total: %d (primary=%d, next=%d)'
      % (len(man2['frames']), n_prim_manifest, cnt['next_in'] + cnt['next_out']))
    A('- in frozen window: primary=%d next=%d' % (cnt['prim_in'], cnt['next_in']))
    A('- out of window: primary=%d next=%d' % (cnt['prim_out'], cnt['next_out']))
    A('- control PG primary frames=%d (nf=%d L=%d R=%d); PH primary frames=%d (nf=%d L=%d R=%d)'
      % (pg_tbl['n_primary_selected'], nf_pg, nlf_pg, nrf_pg,
         ph_tbl['n_primary_selected'], nf_ph, nlf_ph, nrf_ph))
    A('- PR2 all-window (no window filter) quantiles for reference: n_primary=%d'
      % all_tbl['n_primary_selected'])
    A('- sample-size gate (prereg section 4): frozen primary frame n=%d '
      '(per-metric n varies, see table; sigma n=%d due to per-frame d12 availability).'
      % (froz_tbl['n_primary_selected'], froz_tbl['sigma_d12_p25']['n']))
    A('- PH fb per-frame join: %s' % ('ok' if ph_ok else
      'UNAVAILABLE: per-frame pool LIST counts stereo=%d temporal=%d vs required '
      'stereo==nf=%d, temporal==nf-1=%d (%d temporal pairs failed fb_residual in '
      'the tool run; per-frame alignment would be a guess -> refused). '
      'PH non-FB metrics still valid (metrics json is file-keyed). PH pool-level '
      'whole-bag aggregates for reference ONLY (not per-frame segmented): '
      % (nst_ph, ntp_ph, nf_ph, nf_ph - 1, nf_ph - 1 - ntp_ph)))
    mg_set = sorted({e['med_gray'] for e in ph_pf.values()
                     if e.get('med_gray') is not None})
    A('- PH value-structure note (fact, no reading): PH per-frame med_gray set=%s; '
      'PH table quantiles inherit this spread.' % (mg_set,))
    if ph_pools:
        A('  - PH temporal_pool: n=%d p50=%.6g p90=%.6g'
          % (ph_pools['temporal_pool']['n'], ph_pools['temporal_pool']['p50'],
             ph_pools['temporal_pool']['p90']))
        A('  - PH stereo_pool: n=%d p50=%.6g p90=%.6g'
          % (ph_pools['stereo_pool']['n'], ph_pools['stereo_pool']['p50'],
             ph_pools['stereo_pool']['p90']))
    A('')
    A('## Known limitations carried into reading (prereg section 5.3)')
    A('')
    A('- vision_inputs frames are SAMPLED frame sets (j3 extraction), not every bag frame;')
    A('- PR2 has no in-bag healthy segment; control band from PG (stationary healthy) bag,')
    A('  PH hover healthy as side evidence -- reading must carry this annotation;')
    A('- cloud-side feature replay infeasible (registered limitation); image-side metrics')
    A('  are the only decisive surface here.')
    A('')
    A('Generated on NUC uav4 by /tmp build script; artifacts: smooth_lie_segments.csv,')
    A('smooth_lie_perframe.csv, smooth_lie_pack.md. 待主会话定稿（判读行不在本包）。')
    with open(md_path, 'w') as f:
        f.write('\n'.join(L) + '\n')

    print('PACK-BUILD-OK')
    print('frozen window: [%.3f, %.3f] dur=%.3f rows=%d' % (t0, t1, dur, nrows))
    print('members: prim_in=%d prim_out=%d next_in=%d next_out=%d'
          % (cnt['prim_in'], cnt['prim_out'], cnt['next_in'], cnt['next_out']))
    for k in froz_tbl:
        if k == 'n_primary_selected':
            continue
        print('  %-28s frozen n=%d' % (k, froz_tbl[k].get('n', 0)))
    print('PG n_primary=%d  PH n_primary=%s ph_join=%s'
          % (pg_tbl['n_primary_selected'],
             (ph_tbl or {}).get('n_primary_selected'), ph_ok))

if __name__ == '__main__':
    main()
