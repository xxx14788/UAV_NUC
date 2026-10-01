#!/usr/bin/env python3
import re, numpy as np
path='/home/uav/sitl_sim/t2v3_simvins_route.log.1'
slv=re.compile(r'\[T2slv\] t=([\d.]+) phase=(\d+) init_cost=([\d.]+) final_cost=([\d.]+) iters=(\d+)')
x=re.compile(r'\[T2xcross\] t=([\d.]+) id=\d+ est=([\d.eE+-]+) svd=([\d.eE+-]+) rel=([\d.eE+-]+)')
dep=re.compile(r'\[T2depth\] t=([\d.]+) id=\d+ src=(\w+).*depth=([\d.eE+-]+).*flag=(\w+)')
S=[];X={};D={'ok':0,'init_neg':0};Xrows=[]
for ln in open(path,errors='ignore'):
    m=slv.search(ln)
    if m: S.append([float(m.group(1)),float(m.group(3)),float(m.group(4)),int(m.group(5))])
    mx=x.search(ln)
    if mx:
        t=float(mx.group(1)); e=float(mx.group(2)); s=float(mx.group(3))
        Xrows.append((t,e,s))
    md=dep.search(ln)
    if md: D[md.group(4)]=D.get(md.group(4),0)+1
S=np.array(S)
print('T2slv frames:',len(S),'depth flags:',D)
print('cost: t init final iters')
for tt in np.arange(40,70,2):
    j=np.searchsorted(S[:,0],tt)
    if j<len(S): print('  %5.1f %10.2f %10.2f %3d' % (S[j,0],S[j,1],S[j,2],S[j,3]))
Xa=np.array(Xrows)
print('xcross rel (est vs svd) by window:')
for tt in np.arange(35,75,5):
    m=(Xa[:,0]>=tt)&(Xa[:,0]<tt+5)
    if m.sum()>3:
        rel=Xa[m,3]; bad=(rel>0.5).mean(); est=Xa[m,1]
        print('  t=%2d-%2d n=%5d rel>0.5 frac=%.2f est p50=%6.2f p95=%7.2f' % (tt,tt+5,m.sum(),bad,np.percentile(est,50),np.percentile(est,95)))
