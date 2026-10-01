#!/usr/bin/env python3
import re, numpy as np
import sys
for tag, path in [('ONLINE_PR2','/home/uav/sitl_sim/t2v3_simvins_route.log.1'),
                  ('REPLAY_PR2','/home/uav/sitl_sim/vision_inputs/jr3_replay_U3PR2_213717/vins.log')]:
    pat=re.compile(r'\[T2diag\] t=([\d.]+) P=\[ *(-?[\d.e+-]+) *(-?[\d.e+-]+) *(-?[\d.e+-]+)\].*\|Bas\|=([\d.e+-]+) \|Bgs\|=([\d.e+-]+) Bas=\[(-?[\d.e+-]+) (-?[\d.e+-]+) (-?[\d.e+-]+)\]')
    rows=[]
    for ln in open(path,errors='ignore'):
        m=pat.search(ln)
        if m: rows.append([float(x) for x in m.groups()])
    a=np.array(rows)
    print('== %s n=%d' % (tag,len(a)))
    for tt in [15,20,25,30,35,40,45,48,50,52,55,60]:
        j=np.searchsorted(a[:,0],tt)
        if j<len(a): print('  t=%4.1f Bas3=[%7.4f %7.4f %7.4f] |Bas|=%6.3f Pz=%8.3f' % (tt,a[j,6],a[j,7],a[j,8],a[j,4],a[j,3]))
