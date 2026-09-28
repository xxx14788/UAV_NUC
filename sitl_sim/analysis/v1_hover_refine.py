#!/usr/bin/env python3
# V1.3 精细悬停提取：真悬停窗（爬升完→降落起），双口径保持统计。
import rosbag, math, sys

b = rosbag.Bag('/home/uav/sitl_sim/bags/t2v3_hover_203248.bag')
prop, truth = [], []
names = None
for topic, msg, t in b.read_messages(topics=['/vins_estimator/imu_propagate','/gazebo/model_states']):
    ts = t.to_sec()
    if topic.endswith('imu_propagate'):
        p = msg.pose.pose.position
        prop.append((ts, p.x, p.y, p.z))
    else:
        if names is None: names = msg.name
        i = names.index('iris_stereo_vins')
        p = msg.pose[i].position
        truth.append((ts, p.x, p.y, p.z))
b.close()
prop.sort(); truth.sort()

# 悬停窗：z 首 >0.65 后 3s 起，至 z <0.5 止（VINS 系）
t_up = next(ts for ts,_,_,z in prop if z > 0.65)
t_dn = next((ts for ts,_,_,z in prop if ts > t_up + 5 and z < 0.5), prop[-1][0])
win = [(ts,x,y,z) for ts,x,y,z in prop if t_up + 3 <= ts <= t_dn]
print('悬停窗: +%.1fs ~ +%.1fs (%.1fs, %d 帧)' % (t_up+3-prop[0][0], t_dn-prop[0][0], t_dn-t_up-3, len(win)))

def hold(seg, label):
    n0 = min(30, len(seg)//4)
    hx = sum(p[1] for p in seg[:n0])/n0; hy = sum(p[2] for p in seg[:n0])/n0; hz = sum(p[3] for p in seg[:n0])/n0
    dxy = [math.hypot(p[1]-hx, p[2]-hy) for p in seg]
    dz  = [p[3]-hz for p in seg]
    d3  = [math.sqrt((p[1]-hx)**2+(p[2]-hy)**2+(p[3]-hz)**2) for p in seg]
    mean = sum(d3)/len(d3); rms = math.sqrt(sum(x*x for x in d3)/len(d3))
    sx = math.sqrt(sum((x-hx)**2 for x in (p[1] for p in seg))/len(seg))
    sy = math.sqrt(sum((y-hy)**2 for y in (p[2] for p in seg))/len(seg))
    print('%s 保持: XY mean=%.4f max=%.4f (σx=%.4f σy=%.4f) | z mean|%.4f| max|%.4f| | 3D mean=%.4f rms=%.4f max=%.4f'
          % (label, sum(dxy)/len(dxy), max(dxy), sx, sy,
             sum(abs(v) for v in dz)/len(dz), max(abs(v) for v in dz), mean, rms, max(d3)))

hold(win, 'VINS 系(控制口径)')
# 真值同窗（锚同一时刻窗）
tw = [(ts,x,y,z) for ts,x,y,z in truth if t_up + 3 <= ts <= t_dn]
hold(tw, 'gazebo 真值系(绝对口径)')
# 窗内 VINS vs 真值偏差变化（真值系下 VINS 锚点漂移）
if len(tw) > 10:
    def near(arr, tt):
        return min(arr, key=lambda p: abs(p[0]-tt))
    a = near(tw, win[0][0]); c = near(tw, win[-1][0])
    print('真值系窗内锚点位移(VINS 漂移的真世界投影): dx=%.3f dy=%.3f dz=%.3f m'
          % (c[1]-a[1], c[2]-a[2], c[3]-a[3]))
