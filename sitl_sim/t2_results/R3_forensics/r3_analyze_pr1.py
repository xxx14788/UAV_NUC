#!/usr/bin/env python3
# R3: five-line alignment analysis for U3PR1 (preregistered criteria)
import numpy as np
B = '/tmp/r3_pr1'
gt   = np.load(B+'.gt.npy');    odom = np.load(B+'.odom.npy')
cmd  = np.load(B+'.cmd.npy');   goal = np.load(B+'.goal.npy')
vp   = np.load(B+'.vp.npy');    tl   = np.load(B+'.tl.npy')
t0 = gt[0,0]
print('=== birth alignment ===')
print('odom[0] P:', odom[0,1:4], ' gt[0] P:', gt[0,1:4])
print('birth offset (odom-gt):', odom[0,1:4]-gt[0,1:4])
print('spans: gt %.1fs odom %.1fs cmd %.1fs goal %.1fs vp %.1fs' % (gt[-1,0]-t0, odom[-1,0]-t0, cmd[-1,0]-t0, goal[-1,0]-t0, vp[-1,0]-t0))
print('=== goal sequence (leg timeline) ===')
for g in goal[::1]: print('  t=%.1f -> (%.1f, %.1f, %.1f)' % (g[0]-t0, g[1], g[2], g[3]))
print('=== takeoff_land cmds ===')
prev=None
for r in tl:
    if r[1]!=prev: print('  t=%.1f cmd=%d' % (r[0]-t0, r[1])); prev=r[1]
# interpolators
def interp(xs, ys, xq):
    return np.stack([np.interp(xq, xs, y) for y in ys.T], axis=1)
tq = odom[:,0]
g_i = interp(gt[:,0], gt[:,1:8], tq)
# residual err = odom - gt - birth_offset
off = odom[0,1:4] - gt[0,1:4]
err = odom[:,1:4] - g_i[:,0:3] - off
errn = np.linalg.norm(err, axis=1)
print('=== err(t) profile (odom vs GT, birth-corrected) ===')
for pct in [1,10,50,90,95,99,100]:
    print('  p%d = %.2f m' % (pct, np.percentile(errn, pct) if pct<100 else errn.max()))
# divergence times
i1 = np.argmax(errn>1.0) if (errn>1.0).any() else -1
i5 = np.argmax(errn>5.0) if (errn>5.0).any() else -1
i10 = np.argmax(errn>10.0) if (errn>10.0).any() else -1
i50 = np.argmax(errn>50.0) if (errn>50.0).any() else -1
print('t_div1=%.1fs t_div5=%.1fs t_div10=%.1fs t_div50=%.1fs' % (tq[i1]-t0, tq[i5]-t0, tq[i10]-t0, tq[i50]-t0) if i1>=0 else 'no div', '(err>1 first)')
# per-axis err at landmarks
for tt in [30,60,120,240,360,480,600]:
    j = np.searchsorted(tq, t0+tt)
    if j < len(tq): print('  t=%3ds err=[%7.2f %7.2f %7.2f] |err|=%7.2f odomP=[%7.1f %7.1f %6.1f] gtP=[%7.1f %7.1f %6.1f]' % (tt, err[j,0],err[j,1],err[j,2],errn[j], *odom[j,1:4], *g_i[j,0:3]))
print('=== odom speed profile ===')
v = np.linalg.norm(odom[:,4:7], axis=1)
for pct in [50,90,95,99,100]: print('  |V| p%d = %.2f m/s' % (pct, np.percentile(v,pct) if pct<100 else v.max()))
iov = np.argmax(v>5.0) if (v>5.0).any() else -1
print('first |V|>5: t=%.1fs (t=%.1f rel)' % (tq[iov]-t0, tq[iov]-t0) if iov>=0 else 'no |V|>5')
iov20 = np.argmax(v>20.0) if (v>20.0).any() else -1
print('first |V|>20: t=%.1fs' % (tq[iov20]-t0) if iov20>=0 else 'no |V|>20')
print('=== cmd health (prereg criteria 3) ===')
cv = np.linalg.norm(cmd[:,4:7], axis=1)
for pct in [50,90,95,99,100]: print('  |cmdV| p%d = %.2f' % (pct, np.percentile(cv,pct) if pct<100 else cv.max()))
icv = np.argmax(cv>6.0) if (cv>6.0).any() else -1
print('first |cmdV|>6: t=%.1fs' % (cmd[icv,0]-t0) if icv>=0 else 'no |cmdV|>6')
dP = np.linalg.norm(np.diff(cmd[:,1:4],axis=0),axis=1)
ijmp = np.argmax(dP>2.0) if (dP>2.0).any() else -1
print('first cmd jump>2m: t=%.1fs (n_jumps=%d, maxdP=%.2f)' % (cmd[ijmp,0]-t0,(dP>2.0).sum(),dP.max()) if ijmp>=0 else 'no cmd jump>2m')
dtc = np.diff(cmd[:,0]); hz = 1.0/np.median(dtc)
print('cmd rate: median %.1f Hz, min %.1f Hz (gap max %.2fs)' % (hz, 1.0/dtc.max(), dtc.max()))
print('=== cmd-odom tracking (criteria 4) ===')
o_i = interp(odom[:,0], odom[:,1:4], cmd[:,0])
trk = np.linalg.norm(cmd[:,1:4]-o_i, axis=1)
for pct in [50,90,95,99,100]: print('  |cmd-odom| p%d = %.2f m' % (pct, np.percentile(trk,pct) if pct<100 else trk.max()))
print('=== vp vs odom (reanchor surface) ===')
v_i = interp(vp[:,0], vp[:,1:4], tq)
dvo = np.linalg.norm(v_i - odom[:,1:4], axis=1)
print('  |vp-odom| p50=%.3f p95=%.3f max=%.3f' % (np.percentile(dvo,50), np.percentile(dvo,95), dvo.max()))
print('=== GT motion profile ===')
gv = np.linalg.norm(np.diff(g_i[:,0:3],axis=0)/np.diff(tq)[:,None],axis=1)
print('  |GT V| p50=%.2f p90=%.2f max=%.2f' % (np.percentile(gv,50),np.percentile(gv,90),gv.max()))
gterr = np.linalg.norm(g_i[:,0:3]+off - odom[:,1:4], axis=1)
