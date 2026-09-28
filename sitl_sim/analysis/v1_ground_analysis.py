#!/usr/bin/env python3
# T1-v5 V1.2/V1.3 bag 分析：VINS imu_propagate 静止漂移 / init 瞬态 / fsm 稳定性
# 用法: v1_ground_analysis.py <bag> [--hover]   (--hover=V1.3 悬停模式: 悬停保持统计)
# 输出: 全部数值到 stdout（供台账引用），无视觉产物。
import sys, math
from collections import Counter
import rosbag

bag_path = sys.argv[1]
HOVER = '--hover' in sys.argv

imu_prop = []   # (t, x, y, z, vx, vy, vz, qw, qx, qy, qz)
truth = []      # (t, x, y, z)  gazebo iris
ekf_odom = []   # (t, x, y, z)
fsm = []        # (t, state)
imu_raw_t = []  # IMU 到达时刻（gap 统计）

with rosbag.Bag(bag_path, 'r') as bag:
    for topic, msg, t in bag.read_messages():
        ts = t.to_sec()
        if topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position; v = msg.twist.twist.linear; q = msg.pose.pose.orientation
            imu_prop.append((ts, p.x, p.y, p.z, v.x, v.y, v.z, q.w, q.x, q.y, q.z))
        elif topic == '/gazebo/model_states':
            try:
                i = msg.name.index('iris_stereo_vins')
            except ValueError:
                continue
            p = msg.pose[i].position
            truth.append((ts, p.x, p.y, p.z))
        elif topic == '/mavros/local_position/odom':
            p = msg.pose.pose.position
            ekf_odom.append((ts, p.x, p.y, p.z))
        elif topic == '/debugPx4ctrl/fsm_state':
            fsm.append((ts, msg.data))
        elif topic == '/mavros/imu/data_raw':
            imu_raw_t.append(ts)

print('== v1_ground_analysis %s ==' % bag_path)
print('msgs: imu_propagate=%d truth=%d ekf_odom=%d fsm=%d imu_raw=%d'
      % (len(imu_prop), len(truth), len(ekf_odom), len(fsm), len(imu_raw_t)))
if not imu_prop:
    print('RESULT: NO_VINS (imu_propagate 零消息——init 未完成)'); sys.exit(1)

# ---- IMU 频率与 gap（V4.2 佐证） ----
if len(imu_raw_t) > 10:
    dt = [b - a for a, b in zip(imu_raw_t, imu_raw_t[1:])]
    dt.sort()
    med = dt[len(dt)//2]; mx = dt[-1]
    print('imu_raw: median_dt=%.4fs (%.1fHz) max_gap=%.4fs (%.1f 帧中位)' % (med, 1/med, mx, mx/med))

# ---- VINS odom 频率 ----
dtv = [b[0] - a[0] for a, b in zip(imu_prop, imu_prop[1:])]
dtv.sort()
print('imu_propagate: median_dt=%.4fs (%.1fHz)' % (dtv[len(dtv)//2], 1/(dtv[len(dtv)//2] or 1)))

# ---- init 瞬态（首条后 2s 内 |v|） ----
t0 = imu_prop[0][0]
vtrans = [math.sqrt(m[4]**2 + m[5]**2 + m[6]**2) for m in imu_prop if m[0] - t0 < 2.0]
print('init 瞬态: 首条后2s |v| max=%.4f m/s (FSM 静止门 0.1)' % (max(vtrans) if vtrans else -1))

# ---- 静止漂移（VINS world 系自身漂移 + 对 gazebo 真值） ----
dur = imu_prop[-1][0] - t0
print('VINS 段长: %.1fs (首条→末条)' % dur)
x0, y0, z0 = imu_prop[0][1], imu_prop[0][2], imu_prop[0][3]
dx = [math.sqrt((m[1]-x0)**2 + (m[2]-y0)**2) for m in imu_prop]
dz = [m[3] - z0 for m in imu_prop]
print('VINS 静止漂移(自锚首条): XY max=%.4f 终值=%.4f | z max|%.4f| 终值=%.4f | 漂移率=%.4f m/min'
      % (max(dx), dx[-1], max(abs(v) for v in dz), dz[-1], math.hypot(dx[-1], dz[-1]) / (dur/60) if dur > 0 else -1))

# 对真值：取 VINS 首条时刻最近的 truth 锚（位置差；静止下 yaw 恒定无需旋转）
if truth:
    def nearest(tt):
        best, bd = None, 1e18
        for m in truth:
            d = abs(m[0] - tt)
            if d < bd: bd, best = d, m
        return best
    a = nearest(imu_prop[0][0]); b = nearest(imu_prop[-1][0])
    gdrift = math.sqrt((b[1]-a[1])**2 + (b[2]-a[2])**2 + (b[3]-a[3])**2)
    print('gazebo 真值自身漂移(同窗): %.4f m (sim 底噪)' % gdrift)

# ---- EKF2 odom 对照（同轮静止） ----
if ekf_odom:
    e0 = ekf_odom[0]; e1 = ekf_odom[-1]
    ed = math.sqrt((e1[1]-e0[1])**2 + (e1[2]-e0[2])**2 + (e1[3]-e0[3])**2)
    edur = e1[0] - e0[0]
    print('EKF2 odom 同轮静止漂移: %.4f m / %.1fs' % (ed, edur))

# ---- fsm 稳定性 ----
if fsm:
    c = Counter(s for _, s in fsm)
    print('fsm_state 分布: %s' % dict(c))
    trans = [(a, b) for (t1, a), (t2, b) in zip(fsm, fsm[1:]) if a != b]
    print('fsm 转移次数: %d %s' % (len(trans), trans[:6] if trans else '(全程稳定)'))

# ---- 悬停模式（V1.3）：起飞后位置保持 ----
if HOVER:
    # 悬停段 = |v| 低且 z>0.3 的最长连续区间；保持目标 = 该段前 3s 均值
    hover_seg, cur = [], []
    for m in imu_prop:
        if m[3] > 0.3:
            cur.append(m)
        else:
            if len(cur) > len(hover_seg): hover_seg = cur
            cur = []
    if len(cur) > len(hover_seg): hover_seg = cur
    if len(hover_seg) > 50:
        hx = sum(m[1] for m in hover_seg[:30]) / 30
        hy = sum(m[2] for m in hover_seg[:30]) / 30
        hz = sum(m[3] for m in hover_seg[:30]) / 30
        dev = [math.sqrt((m[1]-hx)**2 + (m[2]-hy)**2) for m in hover_seg]
        dzs = [m[3] - hz for m in hover_seg]
        d3 = [math.sqrt((m[1]-hx)**2 + (m[2]-hy)**2 + (m[3]-hz)**2) for m in hover_seg]
        mean = sum(d3) / len(d3)
        rms = math.sqrt(sum(x*x for x in d3) / len(d3))
        print('悬停段: %.1fs %d 帧 | XY dev max=%.4f std=%.4f | z dev max|%.4f| | 3D mean=%.4f rms=%.4f max=%.4f'
              % (hover_seg[-1][0]-hover_seg[0][0], len(hover_seg), max(dev),
                 math.sqrt(sum((x-sum(dev)/len(dev))**2 for x in dev)/len(dev)),
                 max(abs(v) for v in dzs), mean, rms, max(d3)))
        print('对照: GPS 代位链悬停量级 ≤0.03m')
    else:
        print('悬停段不足(<%.1fs 或未检出)' % (len(hover_seg)/125.0))

print('RESULT: OK')
