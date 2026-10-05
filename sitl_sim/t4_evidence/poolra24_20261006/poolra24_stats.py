#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# T4 poolra24 (RA24 visual-face annotation) - statistics facts only, no verdicts.
# Read-only inputs; writes /tmp/poolra24_stats.json; prints compact summary.
import json, os, re, hashlib, random

VI = '/home/ghj/sitl_sim/vision_inputs'
RE = '/home/ghj/catkin_ws/sitl_sim/t4_evidence/t4_recept_20261006'
RUNS = '/home/ghj/sitl_sim/vins_smoke_runs'
OUT = '/tmp/poolra24_stats.json'
TAGS = ['T2MACH3_011804', 'T2MACH8_015411']
METRICS = ['supply_frac', 'grid4x4_occupancy_frac', 'd12_sigma_p25', 'med_gray', 'corners_gFT']
REG_WIN_MACH8 = (114.8, 116.9)  # registered: t4_verdicts_v2.md:550 (max_step 18.87m)

res = {'meta': {}, 'mach': {}, 'ra': {}}

def md5f(p, n=32):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:n]

def q(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[i]

def boot_ci(vals, p, B=2000, seed=7):
    n = len(vals)
    if n < 20:
        return None
    rnd = random.Random(seed)
    bs = sorted(q([vals[rnd.randrange(n)] for _ in range(n)], p) for _ in range(B))
    return [bs[int(0.025 * B)], bs[int(0.975 * B)]]

def group_census(steps, key, thr=0.5, gap=2.0):
    big = sorted([s for s in steps if s[0] > thr], key=lambda s: s[key])
    out = []
    for s in big:
        t = s[key]
        if out and t - out[-1]['t_end'] <= gap:
            g = out[-1]
            g['t_end'] = t
            g['n'] += 1
            if s[0] > g['max_d']:
                g['max_d'], g['t_max'] = s[0], t
        else:
            out.append({'t_beg': t, 't_end': t, 't_max': t, 'max_d': s[0], 'n': 1})
    return out

# ---------- ledger md5 chain check ----------
md5file = os.path.join(os.path.expanduser('~'),
                       'catkin_ws/sitl_sim/t4_evidence/t4_w1_recept3090_20261005/MD5SUMS_vision_inputs.txt')
want = {}
if os.path.exists(md5file):
    for line in open(md5file):
        m = re.match(r'^([0-9a-f]{32})\s+\S*(metrics_|fbres_)(T2MACH[38]_\d+)\.json', line.strip())
        if m:
            want[(m.group(2), m.group(3))] = m.group(1)
for tag in TAGS:
    for kind in ['metrics_', 'fbres_']:
        p = os.path.join(VI, '%s%s.json' % (kind, tag))
        got = md5f(p)
        exp = want.get((kind, tag))
        res['meta']['%s%s_md5' % (kind, tag)] = {'md5_8': got[:8],
                                                 'chain': (exp == got) if exp else 'not_in_md5sums_file'}

# ---------- MACH replay census + window in/out ----------
import rosbag

DOM_FIXED = [None]  # domain decided on MACH8, reused for MACH3

for tag in TAGS:
    r = {}
    fb = os.path.join(VI, 'jr3_replay_%s' % tag, 'features.bag')
    r['features_bag'] = {'md5_8': md5f(fb, 8), 'bytes': os.path.getsize(fb)}
    bag = rosbag.Bag(fb, 'r')
    t0r = s0 = None
    prev = None
    steps = []
    n = 0
    for topic, msg, t in bag.read_messages(topics=['/vins_estimator/odometry']):
        rt = t.to_sec()
        st = float(msg.header.stamp.to_sec())
        p = msg.pose.pose.position
        cur = (st, p.x, p.y, p.z)
        if t0r is None:
            t0r, s0 = rt, st
        if prev is not None:
            d = ((cur[1] - prev[1]) ** 2 + (cur[2] - prev[2]) ** 2 + (cur[3] - prev[3]) ** 2) ** 0.5
            steps.append((d, st, st - s0, rt - t0r))  # d, stamp_abs, stamp_rel, rec_rel
        prev = cur
        n += 1
    bag.close()
    r['odom_n'] = n
    r['first_stamp_abs'] = round(s0, 3)
    r['dur_stamp_s'] = round(steps[-1][1] - s0, 3) if steps else None
    r['jump_cnt_gt05'] = sum(1 for s in steps if s[0] > 0.5)
    r['max_step_d'] = round(max(s[0] for s in steps), 4)
    r['top5_steps'] = [{'d': round(s[0], 4), 't_stamp_abs': round(s[1], 3),
                        't_stamp_rel': round(s[2], 3), 't_rec_rel': round(s[3], 3)} for s in
                       sorted(steps, key=lambda s: -s[0])[:5]]
    doms = {'stamp_abs': 1, 'stamp_rel': 2, 'rec_rel': 3}
    cens = {k: group_census(steps, ki) for k, ki in doms.items()}
    r['clusters'] = {k: [{'t_beg': round(c['t_beg'], 3), 't_end': round(c['t_end'], 3),
                          'max_d': round(c['max_d'], 4), 'n': c['n']} for c in v]
                     for k, v in cens.items()}
    # cluster containing global max step (same cluster in any domain by construction)
    win = {}
    if cens['stamp_abs']:
        for k, ki in doms.items():
            c = max(cens[k], key=lambda c: c['max_d'])
            win[k] = [c['t_beg'], c['t_end']]
    r['max_cluster_windows'] = {k: [round(x, 3) for x in v] for k, v in win.items()} if win else None

    # registered window pinning (t4_verdicts_v2.md:550): [114.8,116.9] in replay-odom
    # stamp-relative domain; frames compared in t_rec==stamp_abs domain via +first_stamp.
    if tag == 'T2MACH8_015411':
        dom = 'registered_stamp_rel'
        r['window_domain'] = dom
        reg_meas = [s for s in steps if REG_WIN_MACH8[0] + s0 <= s[1] <= REG_WIN_MACH8[1] + s0]
        r['reg_window_meas'] = {'n_steps_in_win': len(reg_meas),
                                'max_d': round(max(s[0] for s in reg_meas), 4) if reg_meas else None,
                                'max_d_t_stamp_rel': round(max(reg_meas, key=lambda x: x[0])[2], 3) if reg_meas else None}
    else:
        dom = None
        r['window_domain'] = None

    mj = json.load(open(os.path.join(VI, 'metrics_%s.json' % tag)))
    man = json.load(open(os.path.join(VI, '%s_j3/manifest.json' % tag)))
    tmap = {f['file']: f['t_rec'] for f in man['frames']}
    prim = [f for f in mj['per_frame'] if f.get('tag', '') == '' and f['topic'].endswith('cam_left/image_raw')]
    for f in prim:
        f['t_rec'] = tmap[f['file']]
    prim.sort(key=lambda f: f['t_rec'])
    r['n_primary'] = len(prim)
    r['t_rec_range'] = [round(prim[0]['t_rec'], 3), round(prim[-1]['t_rec'], 3)]

    if dom == 'registered_stamp_rel':
        w_trec = [REG_WIN_MACH8[0] + s0, REG_WIN_MACH8[1] + s0]
        r['window_trec'] = [round(v, 3) for v in w_trec]
    else:
        w_trec = None
        r['window_trec'] = None
        if 'window_note' not in r:
            r['window_note'] = 'no replay step >0.5m -> no jump cluster -> window comparison not applicable'
    wins = {}
    if w_trec:
      for name, w in [('as_is', w_trec),
                      ('pad10', [w_trec[0] - 10, w_trec[1] + 10]),
                      ('pad30', [w_trec[0] - 30, w_trec[1] + 30]),
                      ('pad60', [w_trec[0] - 60, w_trec[1] + 60])]:
        ins = [f for f in prim if w[0] <= f['t_rec'] <= w[1]]
        outs = [f for f in prim if not (w[0] <= f['t_rec'] <= w[1])]
        d = {}
        for k in METRICS:
            dv = [f[k] for f in ins if k in f]
            ov = [f[k] for f in outs if k in f]
            e = {'in_n': len(dv), 'out_n': len(ov),
                 'out_p25': q(ov, .25), 'out_p50': q(ov, .5), 'out_p90': q(ov, .9)}
            if len(dv) >= 4 and q(ov, .5) is not None:
                e.update({'in_p25': q(dv, .25), 'in_p50': q(dv, .5), 'in_p90': q(dv, .9),
                          'in_out_p50_delta': q(dv, .5) - q(ov, .5)})
            else:
                e['in_raw'] = dv
            d[k] = e
        wins[name] = {'window_trec': [round(w[0], 3), round(w[1], 3)], 'metrics': d}
    r['windows'] = wins

    agg = {}
    for k in METRICS:
        v = [f[k] for f in prim if k in f]
        agg[k] = {'n_avail': len(v), 'n_missing': len(prim) - len(v),
                  'p25': q(v, .25), 'p50': q(v, .5), 'p90': q(v, .9),
                  'p50_ci95_boot': boot_ci(v, .5)}
    r['agg_primary'] = agg

    fbr = json.load(open(os.path.join(VI, 'fbres_%s.json' % tag)))
    pools = {}
    for side in ['temporal', 'stereo']:
        for suf in ['', '_pool']:
            key = side + suf
            val = fbr.get(key, [])
            if not isinstance(val, list):
                pools[key] = {'type': 'non-list', 'preview': str(val)[:120]}
                continue
            pools[key] = [{'label': e.get('label'), 'n': e.get('n'), 'p50': e.get('p50'), 'p90': e.get('p90'),
                           'p95': e.get('p95'), 'p99': e.get('p99'), 'p90_ci': e.get('p90_ci')}
                          for e in val if isinstance(e, dict)]
    r['fbres_pools'] = pools
    res['mach'][tag] = r
    print('[%s] odom_n=%d max_step=%.4f jumps>0.5=%d dom=%s win_trec=%s reg_meas=%s' % (
        tag, n, r['max_step_d'], r['jump_cnt_gt05'], dom, r['window_trec'],
        r.get('reg_window_meas')))

# ---------- RA summary (zero-image guard-arm rounds) ----------
draft = open(os.path.join(RE, 'judging_draft.md')).read()
ra_rows = []
for b in re.split(r'\n## ', draft):
    m = re.match(r'\[(COMPACT|NOBAG)\] (run_T2RA\w+|run_RAREP1\S+) ', b)
    if not m:
        continue
    klass_hdr, run = m.group(1), m.group(2).strip()
    row = {'run': run, 'draft_class': klass_hdr}
    mm = re.search(r'bag时长([\d.]+)s\s*\|\s*odom n=(\d+) dur=([\d.]+)s pz=\[([^\]]*)\]\s*\|\s*'
                   r'mavros n=(\d+) pz=\[([^\]]*)\]\s*\|\s*truth n=(-?) pz=\[([^\]]*)\]', b)
    if mm:
        row['bag_dur_s'] = float(mm.group(1))
        row['odom'] = {'n': int(mm.group(2)), 'dur_s': float(mm.group(3)), 'pz': mm.group(4).strip()}
        row['mavros'] = {'n': int(mm.group(5)), 'pz': mm.group(6).strip()}
        row['truth_n'] = mm.group(7)
    jm = re.search(r'odom cnt=(\d+) max=([\d.\-]+)m', b)
    if jm:
        row['jump'] = {'cnt_gt05': int(jm.group(1)), 'max_d': float(jm.group(2))}
    pb = os.path.join(RE, 'perbag', run + '.json')
    if os.path.exists(pb):
        d = json.load(open(pb))
        row['perbag_class'] = d.get('class')
        row['j0d_ref'] = d.get('j0d_ref')
    jd = os.path.join(RUNS, run, 'j0_decomp.json')
    if os.path.exists(jd):
        j = json.load(open(jd)).get('j0_decomp', {})
        if j.get('available'):
            row['j0d'] = {'j0_total_m': j.get('j0_total_m'), 'dominant': j.get('dominant'),
                          'jump_frac': j.get('jump_frac'), 'n_jump_frames': j.get('n_jump_frames')}
    row['scene_from_name'] = 'hov' if 'hov' in run else ('gnd' if 'gnd' in run else 'no-suffix')
    ra_rows.append(row)
res['ra']['rows'] = ra_rows
res['ra']['n_rows'] = len(ra_rows)
print('[RA] rows=%d' % len(ra_rows))

with open(OUT, 'w') as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print('WROTE %s %d bytes' % (OUT, os.path.getsize(OUT)))
