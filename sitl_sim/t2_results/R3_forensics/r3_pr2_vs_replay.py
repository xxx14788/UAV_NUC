#!/usr/bin/env python3
import rosbag, numpy as np
# 1) replay odom from features.bag
rep=[]
with rosbag.Bag('/home/uav/sitl_sim/vision_inputs/jr3_replay_U3PR2_213717/features.bag','r') as b:
    for _,m,t in b.read_messages(topics=['/vins_estimator/odometry']):
        p=m.pose.pose.position
        rep.append((t.to_sec(),p.x,p.y,p.z))
rep=np.array(rep)
print('replay odom n=%d span=%.1fs' % (len(rep), rep[-1,0]-rep[0,0]))
# 2) online PR2
on=np.load('/tmp/r3_pr2.odom.npy'); gt=np.load('/tmp/r3_pr2.gt.npy'); vp=np.load('/tmp/r3_pr2.vp.npy')
t0=gt[0,0]
print('online odom n=%d span=%.1fs' % (len(on), on[-1,0]-t0))
def norm(x): return np.linalg.norm(x,axis=1)
# online div profile
def interp(xs,ys,xq): return np.stack([np.interp(xq,xs,y) for y in ys.T],axis=1)
off=on[0,1:4]-interp(gt[:,0],gt[:,1:4],np.array([on[0,0]]))[0]
err=on[:,1:4]-interp(gt[:,0],gt[:,1:4],on[:,0])-off
en=norm(err)
i1=np.argmax(en>1.0) if (en>1.0).any() else -1
i10=np.argmax(en>10.0) if (en>10.0).any() else -1
i50=np.argmax(en>50.0) if (en>50.0).any() else -1
print('ONLINE PR2: t_div1=%.1fs t_div10=%.1fs t_div50=%.1fs errmax=%.1f' % (on[i1,0]-t0, on[i10,0]-t0, on[i50,0]-t0, en.max()) if i1>=0 else 'no div')
for tt in range(60,180,10):
    j=np.searchsorted(on[:,0],t0+tt)
    if j<len(on): print('  t=%3d online=[%7.1f %7.1f %7.1f] |err|=%6.1f  vp=[%7.1f %7.1f %7.1f]' % (tt,*on[j,1:4],en[j],*vp[np.searchsorted(vp[:,0],on[j,0]),1:4]))
# freeze check online tail
print('online odom P last-60s std:', on[-600:,1:4].std(axis=0))
# 3) replay profile (same bag-time axis: replay stamps should match bag stamps)
r0=rep[0,0]
ren_err = None
# replay has no GT interp here; use absolute motion: P(t) and step jumps
dP=norm(np.diff(rep[:,1:4],axis=0))
print('REPLAY: |dP| p50=%.3f p95=%.3f max=%.1f' % (np.percentile(dP,50),np.percentile(dP,95),dP.max()))
big=np.where(dP>5)[0]
print('replay jumps>5m count=%d' % len(big))
if len(big):
    for k in big[:10]:
        print('  jump at replay-bag-time ~%.1fs dP=%.1f' % (rep[k,0]-r0, dP[k]))
print('replay P last-60s std:', rep[-1200:,1:4].std(axis=0))
print('replay final P:', rep[-1,1:4])
# 4) alignment: replay vs online (same stamps?)
common_t = on[:,0]
r_i=interp(rep[:,0],rep[:,1:4],common_t)
dd=norm(r_i-on[:,1:4])
print('ONLINE-vs-REPLAY same-stamp diff: p50=%.2f p95=%.2f max=%.2f' % (np.percentile(dd,50),np.percentile(dd,95),dd.max()))
w=np.where(dd>10)[0]
if len(w): print('  first >10m divergence at t=%.1fs' % (common_t[w[0]]-t0))
for tt in range(60,180,10):
    j=np.searchsorted(common_t,t0+tt)
    if j<len(common_t): print('  t=%3d online=[%6.1f %6.1f %6.1f] replay=[%6.1f %6.1f %6.1f]' % (tt,*on[j,1:4],*r_i[j]))
