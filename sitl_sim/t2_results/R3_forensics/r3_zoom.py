import numpy as np
B='/tmp/r3_pr1'
gt=np.load(B+'.gt.npy'); odom=np.load(B+'.odom.npy'); cmd=np.load(B+'.cmd.npy'); vp=np.load(B+'.vp.npy')
t0=gt[0,0]
off=odom[0,1:4]-gt[0,1:4]
def interp(xs,ys,xq): return np.stack([np.interp(xq,xs,y) for y in ys.T],axis=1)
print('t  | odomP | gtP | err | vpP | cmdP(k=nearest)')
for tt in range(58,131,2):
    j=np.searchsorted(odom[:,0],t0+tt)
    k=np.searchsorted(cmd[:,0],t0+tt)
    m=np.searchsorted(vp[:,0],t0+tt)
    if j>=len(odom) or k>=len(cmd): continue
    e=odom[j,1:4]-interp(gt[:,0],gt[:,1:4],np.array([odom[j,0]]))[0]-off
    line='t=%3d o=[%6.1f %6.1f %6.1f] gt=[%6.1f %6.1f %5.1f] |e|=%6.1f v=[%6.1f %6.1f %6.1f]' % (
        tt,*odom[j,1:4],*interp(gt[:,0],gt[:,1:4],np.array([odom[j,0]]))[0],np.linalg.norm(e),*vp[m,1:4])
    print(line)
print('--- vp-odom diff timeline (where max 129m happens) ---')
d=np.linalg.norm(vp[:,1:4]-interp(odom[:,0],odom[:,1:4],vp[:,0]),axis=1)
for tt in range(60,131,4):
    m=np.searchsorted(vp[:,0],t0+tt)
    if m<len(vp): print('t=%3d |vp-odom|=%7.2f' % (tt,d[m]))
big=np.where(d>10)[0]
if len(big): print('first |vp-odom|>10 at t=%.1fs, >100 at t=%.1fs' % (vp[big[0],0]-t0, vp[np.argmax(d>100),0]-t0 if (d>100).any() else -1))
print('--- GT z min/max per 10s (60-160s) ---')
for a in range(60,161,10):
    i=(gt[:,0]>=t0+a)&(gt[:,0]<t0+a+10)
    if i.any(): print('t=%3d-%3d gtz=[%.2f,%.2f] gtxy=(%.1f,%.1f)' % (a,a+10,gt[i,3].min(),gt[i,3].max(),gt[i,1].mean(),gt[i,2].mean()))
print('--- cmd z per 10s ---')
for a in range(60,161,10):
    i=(cmd[:,0]>=t0+a)&(cmd[:,0]<t0+a+10)
    if i.any(): print('t=%3d-%3d cmdz=[%.2f,%.2f] cmdxy=(%.1f,%.1f)' % (a,a+10,cmd[i,3].min(),cmd[i,3].max(),cmd[i,1].mean(),cmd[i,2].mean()))
