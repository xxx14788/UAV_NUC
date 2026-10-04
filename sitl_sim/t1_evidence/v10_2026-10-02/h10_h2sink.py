#!/usr/bin/env python3
# h10_h2sink.py — H-2: U25FIX EKF2 z-sink timeline (EV innovations vs estimate)
import sys

from pyulog import ULog

u = ULog(sys.argv[1], None)
dl = u.data_list


def get(n):
    return [d for d in dl if d.name == n]


lp = get('vehicle_local_position')
inv = get('estimator_innovations')
aid = [d for d in dl if d.name.startswith('estimator_aid_src_ev')]
t0 = None
zrow = []
if lp:
    d = lp[0].data
    ts = [float(x) for x in d['timestamp']]
    t0 = ts[0]
    for i in range(len(ts)):
        zrow.append((ts[i], float(d['z[0]'][i]) if 'z[0]' in d else 0.0))
    print('lp bins: t  z_efk')
    bins = {}
    for t, z in zrow:
        bins.setdefault(int((t - t0) / 5e6), []).append(z)
    for b in sorted(bins)[:26]:
        v = bins[b]
        print('%4d %8.2f' % (b * 5, sorted(v)[len(v) // 2]))
if inv:
    d = inv[0].data
    ts = [float(x) for x in d['timestamp']]
    t0 = t0 or ts[0]
    for ch in ('ev_vpos', 'ev_hpos[0]'):
        if ch not in d:
            continue
        bins = {}
        for i in range(len(ts)):
            v = abs(float(d[ch][i]))
            bins.setdefault(int((ts[i] - t0) / 5e6), []).append(v)
        print('%s innov |.| p50 per 5s:' % ch)
        out = []
        for b in sorted(bins)[:26]:
            v = bins[b]
            out.append('%d:%.2f' % (b * 5, sorted(v)[len(v) // 2]))
        print('  ' + ' '.join(out))
for a in aid:
    if 'fused' in a.data and ('ev_hgt' in a.name or 'ev_vvel' in a.name or 'ev_vel' in a.name):
        f = a.data['fused']
        ts = [float(x) for x in a.data['timestamp']]
        t0 = t0 or ts[0]
        n = len(f)
        third = n // 3
        print('%s fused frac thirds: %.2f %.2f %.2f' % (
            a.name.replace('estimator_aid_src_', ''),
            sum(1 for x in f[:third] if x) / max(third, 1),
            sum(1 for x in f[third:2 * third] if x) / max(third, 1),
            sum(1 for x in f[2 * third:] if x) / max(n - 2 * third, 1)))
