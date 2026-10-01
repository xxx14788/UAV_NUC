#!/usr/bin/env python3
import re, numpy as np
pat=re.compile(r'\[T2diag\] t=([\d.]+) P=\[ *(-?[\d.e+-]+) *(-?[\d.e+-]+) *(-?[\d.e+-]+)\].*\|Bas\|=([\d.e+-]+) \|Bgs\|=([\d.e+-]+) Bas=\[(-?[\d.e+-]+) (-?[\d.e+-]+) (-?[\d.e+-]+)\].*track=(\d+)')
rows=[]
for ln in open('/home/uav/sitl_sim/vins_smoke_runs/run_U3PO_211438/simvins.log',errors='ignore'):
    m=pat.search(ln)
    if m: rows.append([float(x) for x in m.groups()])
a=np.array(rows)
print('U3PO online diag n=%d span=%.1f-%.1f' % (len(a),a[0,0],a[-1,0]))
for tt in np.arange(20,360,20):
    j=np.searchsorted(a[:,0],tt)
    if j<len(a): print('  t=%5.1f P=[%7.2f %7.2f %6.2f] |P|=%6.2f Bas3=[%7.4f %7.4f %7.4f] |Bas|=%6.3f trk=%3.0f' % (tt,a[j,1],a[j,2],a[j,3],np.linalg.norm(a[j,1:4]),a[j,6],a[j,7],a[j,8],a[j,4],a[j,9]))
# Bas frozen check: consecutive identical Bas triples
same=0; tot=0
for i in range(1,len(a)):
    tot+=1
    if abs(a[i,6]-a[i-1,6])<1e-9 and abs(a[i,7]-a[i-1,7])<1e-9 and abs(a[i,8]-a[i-1,8])<1e-9: same+=1
print('Bas bit-frozen frame ratio: %.1f%% (%d/%d)' % (100.0*same/tot, same, tot))
