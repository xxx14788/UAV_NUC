#!/usr/bin/env python3
import re, numpy as np
L=open('/home/uav/sitl_sim/vision_inputs/jr3_replay_U3PR2_213717/vins.log',errors='ignore').read().splitlines()
diag=[]; gate={}
pat=re.compile(r'\[T2diag\] t=([\d.]+) P=\[ *(-?[\d.e+-]+) *(-?[\d.e+-]+) *(-?[\d.e+-]+)\] V=\[ *(-?[\d.e+-]+) *(-?[\d.e+-]+) *(-?[\d.e+-]+)\] \|Bas\|=([\d.e+-]+) \|Bgs\|=([\d.e+-]+).*track=(\d+)')
pg=re.compile(r'\[T2gate\] t=([\d.]+) tri=(\d+) rej=(\d+) xrej=(\d+) init_replace=(\d+)')
ir_max=0; gate_last=None
for ln in L:
    m=pat.search(ln)
    if m:
        g=[float(x) for x in m.groups()]
        diag.append(g)
    mg=pg.search(ln)
    if mg:
        gate_last=[float(x) for x in mg.groups()]
        ir_max=max(ir_max, gate_last[4])
diag=np.array(diag)
print('T2diag frames:', len(diag), 'init_replace cumulative max:', ir_max)
print('gate last:', gate_last)
t=diag[:,0]
Pn=np.linalg.norm(diag[:,1:4],axis=1)
Vn=np.linalg.norm(diag[:,4:7],axis=1)
print('|P| p50=%.2f p95=%.2f max=%.2f | |V| max=%.2f' % (np.percentile(Pn,50),np.percentile(Pn,95),Pn.max(),Vn.max()))
i50=np.argmax(Pn>10) if (Pn>10).any() else -1
print('replay |P|>10 first at t=%.2fs' % t[i50] if i50>=0 else 'replay never |P|>10')
trk=diag[:,-1]
print('track: p5=%.0f p50=%.0f min=%.0f' % (np.percentile(trk,5),np.percentile(trk,50),trk.min()))
itr=np.argmax(trk<50) if (trk<50).any() else -1
print('track<50 first at t=%.2fs' % t[itr] if itr>=0 else 'never track<50')
Bas=diag[:,7]; Bgs=diag[:,8]
print('Bas max=%.3f (gate 2.5) Bgs max=%.4f (gate 1.0)' % (Bas.max(),Bgs.max()))
# profile around 25-45s (online div window)
for tt in np.arange(20,60,2.5):
    j=np.searchsorted(t,tt)
    if j<len(diag): print('  replay t=%5.1f P=[%7.3f %7.3f %7.3f] |P|=%6.2f track=%3d Bas=%.3f' % (tt,*diag[j,1:4],Pn[j],trk[j],Bas[j]))
# Bas>0.8 windows (approaching gate)
ib=np.argmax(Bas>0.8) if (Bas>0.8).any() else -1
print('Bas>0.8 first t=%.1fs' % t[ib] if ib>=0 else 'Bas never >0.8')
# final
print('replay final P:', diag[-1,1:4], 'final track:', trk[-1])
# count P frozen segments: std in last 300 frames
print('replay last300 P std:', diag[-300:,1:4].std(axis=0))
