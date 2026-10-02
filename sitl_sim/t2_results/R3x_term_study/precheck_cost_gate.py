#!/usr/bin/env python3
# T2 v8.2 unit-1 pre-check grid: retroactive cost-gate replay on PR1/PR2
# online logs (route.log.2.gz, 2026-10-01 U3' route rounds).
# Gate predicate replicated bit-exactly from estimator.cpp:1508-1521:
#   rolling deque of last 20 initial_cost (phase==NON_LINEAR only);
#   median of those 20; current > 10x median -> streak++, else streak=0;
#   fire when streak >= 5 (checked in failureDetection, line 1169).
# Also emits R3x data: iters distribution for term=1, slv_ms vs 40ms cap.
import gzip, re, sys
from collections import deque

LOG = sys.argv[1] if len(sys.argv)>1 else '/home/uav/sitl_sim/t2v3_simvins_route.log.2.gz'
pat_slv = re.compile(r'\[T2slv\] t=([0-9.]+) phase=([0-9]+) init_cost=([0-9.e+-]+) final_cost=([0-9.e+-]+) iters=([0-9]+) term=([0-9]+) slv_ms=([0-9.]+)')
pat_diag = re.compile(r'\[T2diag\] t=([0-9.]+) P=\[ *(-?[0-9.e+-]+) *(-?[0-9.e+-]+) *(-?[0-9.e+-]+)\].*\|Bas\|=([0-9.e+-]+) \|Bgs\|=([0-9.e+-]+).*track=([0-9]+)')

slv, diag = [], []
op = (gzip.open if LOG.endswith('.gz') else open)
with op(LOG, 'rt', errors='ignore') as f:
    for ln in f:
        m = pat_slv.search(ln)
        if m:
            slv.append((float(m.group(1)), int(m.group(2)), float(m.group(3)),
                        float(m.group(4)), int(m.group(5)), int(m.group(6)), float(m.group(7))))
            continue
        m = pat_diag.search(ln)
        if m:
            diag.append((float(m.group(1)), float(m.group(2)), float(m.group(3)),
                         float(m.group(4)), float(m.group(5)), float(m.group(6)), int(m.group(7))))

def split_rounds(rows, gap_drop=5.0):
    rounds, cur = [], []
    for r in rows:
        if cur and r[0] < cur[-1][0] - gap_drop:
            rounds.append(cur); cur = []
        cur.append(r)
    if cur: rounds.append(cur)
    return rounds

slv_rounds = split_rounds(slv)
diag_rounds = split_rounds(diag)
print('total T2slv=%d T2diag=%d  slv-rounds=%d diag-rounds=%d' % (len(slv), len(diag), len(slv_rounds), len(diag_rounds)))
for i, rr in enumerate(slv_rounds):
    print('  slv-round %d: n=%d span=%.1f-%.1f' % (i, len(rr), rr[0][0], rr[-1][0]))

W, RATIO, N = 20, 10.0, 5

def gate_replay(rr):
    hist = deque(maxlen=W)
    streak = 0
    fires = []
    series = []
    for (t, ph, ic, fc, it, tm, ms) in rr:
        fired_now = False
        if ph == 1:
            if len(hist) >= W:
                hs = sorted(hist)
                med = hs[len(hs)//2]
                if ic > RATIO * med:
                    streak += 1
                else:
                    streak = 0
                if streak >= N:
                    fires.append((t, ic, med))
                    fired_now = True
            else:
                streak = 0
            hist.append(ic)
        series.append((t, ph, ic, fired_now))
    return fires, series

def pct(v, q):
    if not v: return float('nan')
    s = sorted(v); return s[min(len(s)-1, int(q*len(s)))]

for i, rr in enumerate(slv_rounds):
    fires, series = gate_replay(rr)
    nl = [s for s in series if s[1] == 1]
    print('=== slv-round %d: n_nl=%d span=%.1f-%.1f ===' % (i, len(nl), rr[0][0], rr[-1][0]))
    if fires:
        print('  GATE-REPLAY FIRES: first@t=%.2f (ic=%.4g med=%.4g) total-fire-frames=%d' % (fires[0][0], fires[0][1], fires[0][2], len(fires)))
    else:
        print('  GATE-REPLAY: never fires')
    # cost extremes per 10s bucket (phase=1 only)
    t0 = nl[0][0] if nl else rr[0][0]
    import math
    bmax = {}
    for (t, ph, ic, _) in nl:
        b = int((t - t0) // 10)
        bmax[b] = max(bmax.get(b, 0), ic)
    line = ' '.join('%d:%.3g' % (b*10, v) for b, v in sorted(bmax.items())[:70])
    print('  cost-max per 10s: ' + line)
    # R3x: term/iters/slv_ms (all phases)
    t1 = [r for r in rr if r[5] == 1]
    t0f = [r for r in rr if r[5] == 0]
    print('  term: 0=%d 1=%d other=%d | conv-rate=%.1f%%' % (
        len(t0f), len(t1), len(rr)-len(t0f)-len(t1), 100.0*len(t0f)/max(1,len(rr))))
    if t1:
        it1 = [r[4] for r in t1]
        print('  term=1 iters: p50=%d p90=%d max=%d | iters==8:%d/%d (%.0f%%)' % (
            pct(it1,0.5), pct(it1,0.9), max(it1),
            sum(1 for x in it1 if x>=8), len(it1), 100.0*sum(1 for x in it1 if x>=8)/len(it1)))
    ms = [r[6] for r in rr]
    print('  slv_ms: p50=%.1f p90=%.1f p95=%.1f max=%.1f | >38ms:%d/%d | >40ms:%d' % (
        pct(ms,0.5), pct(ms,0.9), pct(ms,0.95), max(ms),
        sum(1 for x in ms if x>38), len(ms), sum(1 for x in ms if x>40)))

# diag rounds: burst localization (|P| crossing 10m, freeze onset)
print()
for i, rr in enumerate(diag_rounds):
    print('=== diag-round %d: n=%d span=%.1f-%.1f ===' % (i, len(rr), rr[0][0], rr[-1][0]))
    prev = None; over = []
    for (t, x, y, z, bas, bgs, trk) in rr:
        p = math.sqrt(x*x+y*y+z*z)
        if p > 10: over.append((t, p, x, y, z))
    if over:
        print('  |P|>10m first@t=%.1f last@t=%.1f peak=%.1f endP=[%.1f %.1f %.1f]' % (
            over[0][0], over[-1][0], max(o[1] for o in over), over[-1][2], over[-1][3], over[-1][4]))
    else:
        print('  |P| never exceeds 10m (max below)')
    mx = max(rr, key=lambda r: r[1]*r[1]+r[2]*r[2]+r[3]*r[3])
    print('  max|P|=%.1f @t=%.1f  Bas max=%.3f  trk p50=%d' % (
        math.sqrt(mx[1]**2+mx[2]**2+mx[3]**2), mx[0], max(r[4] for r in rr), pct([r[6] for r in rr], 0.5)))
