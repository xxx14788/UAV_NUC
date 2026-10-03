#!/usr/bin/env python3
# T2 v8.3 unit-2: aerial re-init forensics. Segment the log by [T2GATECFG]
# banners (each banner = post-reboot setParameter). For each segment extract:
# time-to-first-solve, first-solve (phase/term/init_cost), first diag (P/Bas/track),
# T2gate ir_st/ir_m2/ir_shift, AIF snapshots (Vs ramp shape), death cause
# (next T2fail verdict fields) or survival.
import re, sys

LOG = sys.argv[1]
txt = open(LOG, errors='ignore').read().splitlines()

re_banner = re.compile(r'T2GATECFG')
re_fail = re.compile(r'\[T2fail\] t=([0-9.]+) P=\[([^\]]+)\] V=\[([^\]]+)\] \|Bas\|=([0-9.e+-]+) \|Bgs\|=([0-9.e+-]+).*track=(\d+)')
re_slv = re.compile(r'\[T2slv\] t=([0-9.]+) phase=(\d) init_cost=([0-9.e+-]+) final_cost=([0-9.e+-]+) iters=(\d) term=(\d) slv_ms=([0-9.]+)')
re_diag = re.compile(r'\[T2diag\] t=([0-9.]+) P=\[ *(-?[0-9.e+-]+) *(-?[0-9.e+-]+) *(-?[0-9.e+-]+)\] V=\[ *(-?[0-9.e+-]+) *(-?[0-9.e+-]+) *(-?[0-9.e+-]+)\] \|Bas\|=([0-9.e+-]+) \|Bgs\|=([0-9.e+-]+).*track=(\d+)')
re_gate = re.compile(r'\[T2gate\] t=([0-9.]+) tri=(\d+) rej=(\d+) xrej=(\d+) init_replace=(\d+) gate=(\d+)(?: ir_st=(\d+) ir_m2=(\d+) ir_shift=(\d+))?')
re_snap = re.compile(r'T2SNAP pre AIF=(\d+) fc=(\d+) Vs: ([0-9. ]+)Ps: ([0-9. ]+)')
re_cost = re.compile(r'cost gate: streak=(\d+)')

# banner line times (sim time from the ROS_WARN stamp field [wall, sim])
segs = []  # (sim_t_of_banner, line_idx)
for i, ln in enumerate(txt):
    if re_banner.search(ln):
        m = re.search(r', ([0-9.]+)\]:', ln)
        segs.append((float(m.group(1)) if m else -1, i))
print('log=%s banners=%d' % (LOG.split("/")[-2], len(segs)))

for k, (bt, bi) in enumerate(segs):
    end = segs[k+1][1] if k+1 < len(segs) else len(txt)
    seg = txt[bi:end]
    slv = [re_slv.search(x) for x in seg]
    slv = [m for m in slv if m]
    diag = [re_diag.search(x) for x in seg]
    diag = [m for m in diag if m]
    fail = [re_fail.search(x) for x in seg]
    fail = [m for m in fail if m]
    gate = [re_gate.search(x) for x in seg]
    gate = [m for m in gate if m]
    snap = [re_snap.search(x) for x in seg]
    snap = [m for m in snap if m]
    if not slv:
        print('seg%02d t=%.1f: NO-SOLVE (len=%d)' % (k, bt, len(seg))); continue
    f0 = slv[0]
    d0 = diag[0] if diag else None
    g = gate[0] if gate else None
    print('seg%02d reboot_t=%.1f n_slv=%d | first_slv: dt=%.2fs phase=%s ic=%s term=%s | first_diag: t=%.1f P=[%s %s %s] |P|=%s Bas=%s trk=%s' % (
        k, bt, len(slv),
        float(f0.group(1))-bt, f0.group(2), f0.group(3), f0.group(6),
        *( [float(d0.group(1)), d0.group(2)[:6], d0.group(3)[:6], d0.group(4)[:6],
            '%.1f' % (float(d0.group(2))**2+float(d0.group(3))**2+float(d0.group(4))**2)**0.5,
            d0.group(8), d0.group(10)] if d0 else ['-', '-', '-', '-', '-', '-'] )))
    if snap:
        s0 = snap[0]
        vs = [float(v) for v in s0.group(3).split()]
        print('        first_AIF: fc=%s Vs[min,max]=%.2f,%.2f ramp=%s' % (
            s0.group(2), min(vs), max(vs), 'yes' if max(vs) > 1.0 else 'no'))
    if g:
        print('        gate: tri=%s ir(repl)=%s ir_st=%s ir_m2=%s ir_shift=%s' % (
            g.group(2), g.group(5), g.group(7) or '-', g.group(8) or '-', g.group(9) or '-'))
    if fail:
        f = fail[0]
        print('        DEATH: +%.1fs Bas=%s Bgs=%s trk=%s P=[%s]' % (
            float(f.group(1))-bt, f.group(4), f.group(5), f.group(6), f.group(2)[:14]))
    else:
        print('        SURVIVED to segment end (+%.1fs)' % (float(slv[-1].group(1))-bt if slv else 0))
