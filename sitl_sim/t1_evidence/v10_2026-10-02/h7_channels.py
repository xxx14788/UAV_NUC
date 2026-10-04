#!/usr/bin/env python3
# h7_channels.py — H-3 audit: full estimator channel inventory across ulogs.
# innovations keys + aid_src topics + fused fractions for ev channels.
import glob
import sys

from pyulog import ULog

paths = sys.argv[1:]
for p in paths:
    try:
        u = ULog(p, None)
    except Exception as e:
        print('ERR', p, e)
        continue
    inv = [d for d in u.data_list if d.name == 'estimator_innovations']
    aid = [d for d in u.data_list if d.name.startswith('estimator_aid_src')]
    name = p.split('/')[-2] + '/' + p.split('/')[-1]
    if inv:
        keys = sorted(k for k in inv[0].data.keys()
                      if not k.startswith('timestamp'))
        evk = [k for k in keys if 'ev' in k]
        print('== %s innovations ev-keys: %s' % (name, evk))
    aid_names = sorted('%s[%d]' % (d.name.replace('estimator_aid_src_', ''), d.multi_id)
                       for d in aid)
    print('   aid_src:', aid_names)
    for d in aid:
        if 'ev_yaw' in d.name and 'fused' in d.data:
            f = d.data['fused']
            print('   ev_yaw fused: n=%d fused_n=%d frac=%.3f' % (
                len(f), int(sum(1 for x in f if x)),
                sum(1 for x in f if x) / len(f) if len(f) else 0))
