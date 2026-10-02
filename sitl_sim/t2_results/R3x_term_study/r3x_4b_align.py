#!/usr/bin/env python3
# R3x 4b: per-10s alignment of solver convergence rate vs visual factor health
# (track from [T2diag], cost from [T2slv] init_cost) for one round's log.
import gzip, re, sys
from collections import defaultdict

LOG = sys.argv[1]
pat_slv = re.compile(r'\[T2slv\] t=([0-9.]+) phase=([0-9]+) init_cost=([0-9.e+-]+) final_cost=([0-9.e+-]+) iters=([0-9]+) term=([0-9]+) slv_ms=([0-9.]+)')
pat_diag = re.compile(r'\[T2diag\] t=([0-9.]+) P=\[ *(-?[0-9.e+-]+) *(-?[0-9.e+-]+) *(-?[0-9.e+-]+)\].*\|Bas\|=([0-9.e+-]+).*track=([0-9]+)')

op = gzip.open if LOG.endswith('.gz') else open
slv, diag = [], []
with op(LOG, 'rt', errors='ignore') as f:
    for ln in f:
        m = pat_slv.search(ln)
        if m:
            slv.append((float(m.group(1)), int(m.group(2)), float(m.group(3)), int(m.group(6))))
            continue
        m = pat_diag.search(ln)
        if m:
            diag.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(6))))

def split_rounds(rows):
    rounds, cur = [], []
    for r in rows:
        if cur and r[0] < cur[-1][0] - 5.0:
            rounds.append(cur); cur = []
        cur.append(r)
    if cur: rounds.append(cur)
    return rounds

import math
for ri, rr in enumerate(split_rounds(slv)):
    dr = split_rounds(diag)[ri] if ri < len(split_rounds(diag)) else []
    print('=== round %d  slv n=%d span=%.1f-%.1f ===' % (ri, len(rr), rr[0][0], rr[-1][0]))
    print(' t-bucket  conv%   med_cost  max_cost   trk_p50  trk_min   |P|end')
    B = defaultdict(list)
    for (t, ph, ic, tm) in rr:
        B[int(t//10)*10].append((ph, ic, tm))
    T = defaultdict(list)
    for (t, x, y, z, trk) in dr:
        T[int(t//10)*10].append((trk, x, y, z))
    for b in sorted(B):
        rows = B[b]
        nl = [r for r in rows if r[0] == 1]
        if not nl: continue
        conv = 100.0*sum(1 for r in nl if r[2]==0)/max(1,len(nl))
        costs = sorted(r[1] for r in nl)
        med = costs[len(costs)//2]
        mx = costs[-1]
        trows = T.get(b, [])
        if trows:
            trks = sorted(x[0] for x in trows)
            trk_p50, trk_min = trks[len(trks)//2], trks[0]
            last = trows[-1]
            p_end = math.sqrt(last[1]**2+last[2]**2+last[3]**2)
        else:
            trk_p50 = trk_min = p_end = -1
        print(' %4d    %5.1f  %8.3g  %8.3g   %5d   %5d   %6.1f' % (b, conv, med, mx, trk_p50, trk_min, p_end))
