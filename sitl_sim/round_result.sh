#!/usr/bin/env bash
# round_result.sh — VINS 链路轮次四指标 RESULT(真值+VINS双口径,两段式按goal切窗)
# 用法: round_result.sh <bag> <gx> <gy> <gz> <world> <evdir> <arr1> <arr2> <hasl2> <l2x> <l2y> <l2z>
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
python3 - "$@" <<'PYEOF'
import sys, math
import rosbag
bag, gx, gy, gz, world, ev, arr, arr2, hasl2 = sys.argv[1:10]
l2x, l2y, l2z = float(sys.argv[10]), float(sys.argv[11]), float(sys.argv[12])
gx, gy, gz = float(gx), float(gy), float(gz); hasl2 = hasl2 == '1'
BOX = {"box_A": (3.5,-1.5,0.0,1.0,1.0,1.8), "box_B": (5.0,-2.5,0.0,1.5,1.0,1.2),
       "box_C": (4.5,-3.5,0.0,1.0,1.0,2.2)}
if world.endswith('_v2'):
    BOX["box_D"] = (6.4,-2.0,0.0,1.0,1.0,2.8); BOX["box_E"] = (6.4,0.5,0.0,1.0,1.0,2.8)
def dbox(p, b):
    cx,cy,z0,sx,sy,sz = b
    dx = max(abs(p[0]-cx)-sx/2, 0.0); dy = max(abs(p[1]-cy)-sy/2, 0.0)
    dz = max(max(z0-p[2], p[2]-(z0+sz)), 0.0)
    return math.sqrt(dx*dx+dy*dy+dz*dz)
prop, truth, cmd, armed, goals = [], [], [], [], []
with rosbag.Bag(bag,'r') as b:
    for topic, msg, t in b.read_messages():
        ts = t.to_sec()
        if topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position; prop.append((ts,p.x,p.y,p.z))
        elif topic == '/gazebo/model_states':
            try: i = msg.name.index('iris_stereo_vins')
            except ValueError: continue
            p = msg.pose[i].position; truth.append((ts,p.x,p.y,p.z))
        elif topic == '/position_cmd':
            p = msg.position; cmd.append((ts,p.x,p.y,p.z))
        elif topic == '/mavros/state':
            armed.append(msg.armed)
        elif topic == '/move_base_simple/goal':
            p = msg.pose.position; goals.append((ts,p.x,p.y,p.z))
if not prop: print('RESULT=FAIL 无 imu_propagate'); sys.exit()
def near(arr, tt): return min(arr, key=lambda p: abs(p[0]-tt))
p0 = prop[0]; a = None
# 锚点取 goal 后 5s 窗的均值对(目标生效帧;VINS 帧中途跳变时早期锚会误判,X1_234437 实证)
g1_ts0 = next((g[0] for g in goals if abs(g[1]-gx)<0.01 and abs(g[2]-gy)<0.01 and abs(g[3]-gz)<0.01), prop[0][0])
aw_from, aw_to = g1_ts0, g1_ts0 + 5
pw = [p for p in prop if aw_from <= p[0] <= aw_to]
if pw:
    tw = [near(truth, p[0]) for p in pw[:50]]
    if tw:
        a = (sum(t[1] for t in tw)/len(tw) - sum(p[1] for p in pw[:50])/len(pw),
             sum(t[2] for t in tw)/len(tw) - sum(p[2] for p in pw[:50])/len(pw),
             sum(t[3] for t in tw)/len(tw) - sum(p[3] for p in pw[:50])/len(pw))
if a is None:
    for t in truth:
        if t[0] >= p0[0]: a = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3]); break
if a is None and truth: t = truth[0]; a = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3])
# 帧稳定性:goal前锚 vs 末段锚(差>0.5m=VINS帧中途跳变→任务物理未完成,FAIL 定性)
a_pre = None
for t in truth:
    if t[0] >= p0[0]:
        a_pre = (t[1]-p0[1], t[2]-p0[2], t[3]-p0[3]); break
a_post = None
if prop and truth:
    tp = near(prop, prop[-1][0]-3); tg = near(truth, tp[0])
    a_post = (tg[1]-tp[1], tg[2]-tp[2], tg[3]-tp[3])
jump = 99.9
if a_pre and a_post:
    jump = math.sqrt(sum((x-y)**2 for x,y in zip(a_pre, a_post)))
print('anchor(goal+5s窗): (%.3f, %.3f, %.3f) | 帧稳定性 |pre-post|=%.3f m%s'
      % (a[0], a[1], a[2], jump, '  <-- VINS 帧中途跳变!' if jump > 0.5 else ''))
t2_start = None
if hasl2:
    for g in goals:
        if abs(g[1]-l2x) < 0.01 and abs(g[2]-l2y) < 0.01 and abs(g[3]-l2z) < 0.01:
            t2_start = g[0]; break
def leg_min(pts, goal, ts_from, ts_to, anchored=True):
    if a is None and anchored: return -1
    tx, ty, tz = (goal[0]+a[0], goal[1]+a[1], goal[2]+a[2]) if anchored else goal
    sel = [p for p in pts if ts_from <= p[0] <= ts_to]
    if not sel: return -1
    return min(math.sqrt((p[1]-tx)**2+(p[2]-ty)**2+(p[3]-tz)**2) for p in sel)
t_end = truth[-1][0] if truth else prop[-1][0]
g1_ts = next((g[0] for g in goals if abs(g[1]-gx)<0.01 and abs(g[2]-gy)<0.01 and abs(g[3]-gz)<0.01), prop[0][0])
w1_to = t2_start if t2_start else t_end
dt1 = leg_min(truth, (gx,gy,gz), g1_ts, w1_to)
dv1 = leg_min(prop, (gx,gy,gz), g1_ts, w1_to, anchored=False)
mind = min(dbox(p, bx) for p in truth for bx in BOX.values()) if truth else -1
hz = len(cmd)/(cmd[-1][0]-cmd[0][0]) if len(cmd)>10 else 0
import bisect
dev = []; ts_prop = [p[0] for p in prop]
for c in cmd:
    j = bisect.bisect_left(ts_prop, c[0])
    if 0 < j < len(prop):
        p = prop[j]; dev.append(math.sqrt((c[1]-p[1])**2+(c[2]-p[2])**2+(c[3]-p[3])**2))
dev.sort(); p95 = dev[int(0.95*len(dev))] if dev else -1
disarm_ok = (not armed[-1]) if armed else False
ok = [dt1 < 0.5, mind > 0.349, hz >= 50, disarm_ok]
if jump > 0.5:
    ok[0] = 0
    print('判据: VINS 帧跳变(%.2fm)>0.5m → 到位判 FAIL(目标物理位置被跳变移走,T2 瞬态发散类)' % jump)
print('leg1 到位(真值) min=%.3f m (<0.5)->%d | leg1(VINS自报) min=%.3f m' % (dt1, ok[0], dv1))
if hasl2 and t2_start:
    dt2 = leg_min(truth, (l2x,l2y,l2z), t2_start, t_end)
    dv2 = leg_min(prop, (l2x,l2y,l2z), t2_start, t_end, anchored=False)
    ok[0] = ok[0] and (dt2 < 0.5)
    print('leg2 到位(真值) min=%.3f m (<0.5,与leg1合并判)->%d | leg2(VINS自报) min=%.3f m' % (dt2, dt2 < 0.5, dv2))
print('避障 min_dist=%.3f m (>0.349)->%d' % (mind, ok[1]))
print('poscmd %.1f Hz (>=50)->%d' % (hz, ok[2]))
print('auto_disarm->%d' % ok[3])
print('跟踪 p95=%.3f m (cmd-odom, 信息项)' % p95)
print('ARRIVE_WATCH1: %s' % arr)
print('ARRIVE_WATCH2: %s' % arr2)
print('RESULT=%s  (证据: %s)' % ('PASS' if all(ok) else 'FAIL', ev))
PYEOF
