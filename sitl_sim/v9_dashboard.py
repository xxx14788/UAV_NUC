#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8.6 §二.5 dashboard generator: per-round 8 items + aggregate headline (Wilson CI, conditional decomposition, failure-clan accounting).
Sources: trial_report.md (GATES-V9 / ARRIVED_TRUTH / TIMEOUT / lane= lines), run dirs (RESULT.txt z_end/thrust, planner.log SDB-STAT), tune_diag optional.
Usage: v9_dashboard.py <batch_dir> <runs_root> [--tunediag]"""
import sys, os, re, math, glob, json
BATCH=sys.argv[1]; RUNS=sys.argv[2]
TD='--tunediag' in sys.argv
rpt=os.path.join(BATCH,'trial_report.md')
lines=open(rpt,encoding='utf-8').read().splitlines()
rounds=[]; cur=None
for ln in lines:
    m=re.search(r'round (\S+) goal=', ln)
    if m: cur={'round':m.group(1)}; rounds.append(cur); continue
    if cur is None: continue
    g=re.search(r'GATES-V9: infl<0.2=(\w+) ndetour>=2=(\w+) maxlat>=0.32=(\w+) ratio>=1.07=(\w+) alternating=(\w+) \| SFORM_ALL=(\w+)', ln)
    if g:
        cur['infl'],cur['ndetour'],cur['maxlat'],cur['ratio'],cur['alt'],cur['sform']=[v=='True' for v in g.groups()]
    a=re.search(r'ARRIVED_TRUTH min_d=([0-9.]+)', ln)
    if a and 'arrived' not in cur: cur['arrived']=float(a.group(1))
    t=re.search(r'TIMEOUT min_truth=([0-9.]+)', ln)
    if t and 'timeout' not in cur: cur['timeout_miss']=float(t.group(1))
    n=re.search(r'WARN NEVER-FLEW', ln)
    if n: cur['neverflew']=True
    p=re.search(r'lane=LAB path_len=([0-9.]+) ratio=([0-9.]+) \| box_min ctr/surf/infl=[0-9.]+/([0-9.]+)/[0-9.]+', ln)
    if p and 'path_len' not in cur:
        cur['path_len']=float(p.group(1)); cur['ratio']=float(p.group(2)); cur['min_surf']=float(p.group(3))
    d=re.search(r'detours=(\d+) (.*)$', ln)
    if d and 'detours' not in cur:
        cur['detours']=int(d.group(1))
        segs=re.findall(r'\[([NS]) p([0-9.]+)', d.group(2))
        cur['max_seg_p']=max([float(s[1]) for s in segs], default=0.0)
# runaway flag: path beyond 6x6 room physical bound OR segment p way outside
for cur in rounds:
    cur['runaway']=bool(cur.get('path_len',0)>50 or cur.get('max_seg_p',0)>10)
    cur['pseudo_s']=bool(cur.get('sform') and cur['runaway'])
# per-round run-dir enrichment (z_end / sdb finite)
for cur in rounds:
    rd=glob.glob(os.path.join(RUNS,'run_%s_*'%cur['round']))
    cur['z_end']=None; cur['finite_med']=None; cur['t_done']=None
    if rd:
        rd=sorted(rd)[-1]
        rz=os.path.join(rd,'RESULT.txt')
        if os.path.exists(rz):
            mm=re.search(r'z_end=([0-9.]+)', open(rz,encoding='utf-8',errors='ignore').read())
            if mm: cur['z_end']=float(mm.group(1))
        pl=os.path.join(rd,'planner.log')
        if os.path.exists(pl):
            fr=[float(x) for x in re.findall(r'finite_ratio_med.: ([0-9.]+)', open(pl,encoding='utf-8',errors='ignore').read())]
            if fr: cur['finite_med']=sorted(fr)[len(fr)//2]
        gp=os.path.join(rd,'goal.txt')
        if os.path.exists(gp) and os.path.exists(rz):
            try:
                gt=os.path.getmtime(rz)-os.path.getmtime(os.path.join(rd,'preflight.txt'))
                cur['t_done']=round(gt,1)
            except OSError: pass
# composite: takeoff-safe (not neverflew) & S5 & arrived<=1.0 (180-primary;120-deputy same here since arrival min_d is whole-window) & land z_end<0.15 & not runaway
def composite(r):
    if r.get('neverflew'): return False
    ok=bool(r.get('sform',False)) and r.get('arrived') is not None and r['arrived']<=1.0 and r.get('z_end') is not None and r['z_end']<0.15 and not r['runaway']
    return ok
for cur in rounds: cur['composite']=composite(cur)
# Wilson
def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (p, max(0,c-h), min(1,c+h))
n=len(rounds); valid=[r for r in rounds if not r.get('neverflew')]
ns=sum(1 for r in valid if r.get('sform')); na=sum(1 for r in valid if r.get('arrived') is not None)
nc=sum(1 for r in rounds if r['composite']); nr=sum(1 for r in valid if r['runaway'])
print('round | sform | pseudo | arrived | timeout_miss | runaway | min_surf | z_end | finite_med | composite')
for r in rounds:
    print('%s | %s | %s | %s | %s | %s | %s | %s | %s | %s'%(r['round'],r.get('sform'),r.get('pseudo_s'),
        r.get('arrived'),r.get('timeout_miss'),r['runaway'],r.get('min_surf'),r.get('z_end'),r.get('finite_med'),r['composite']))
print('--- headline ---')
for nm,k,nn in [('composite',nc,n),('S-form (raw)',ns,len(valid)),('arrival',na,len(valid)),('runaway',nr,len(valid))]:
    p,lo,hi=wilson(k,nn); print('%s: %d/%d = %.1f%% [%.1f, %.1f] Wilson95 halfw=%.1fpp'%(nm,k,nn,100*p,100*lo,100*hi,50*(hi-lo)))
# conditional decomposition
joint=sum(1 for r in valid if r.get('sform') and r.get('arrived') is not None)
arr=[r for r in valid if r.get('arrived') is not None]
condS=sum(1 for r in arr if r.get('sform'))
if arr: print('S∧arrival joint: %d; P(S|arrived) = %d/%d = %.1f%%'%(joint,condS,len(arr),100*condS/len(arr)))
cleanS=sum(1 for r in valid if r['sform'] and not r['runaway'])
print('clean-domain S (runaway excluded): %d/%d'%(cleanS,len(valid)-nr))
print('neverflew: %d'%sum(1 for r in rounds if r.get('neverflew')))
json.dump(rounds,open(os.path.join(BATCH,'dashboard_rounds.json'),'w'),indent=1)
print('JSON -> %s/dashboard_rounds.json'%BATCH)
