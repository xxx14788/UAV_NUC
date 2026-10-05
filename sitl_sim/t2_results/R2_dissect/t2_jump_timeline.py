#!/usr/bin/env python3
# t2_jump_timeline.py — odometry 流帧跳时间线提取 v2（T2 v9.5 §1 机理侦察件）
# 双流独立扫描: /vins_estimator/odometry (10Hz solver) + /vins_estimator/imu_propagate (125Hz publish)
# truth=iris_stereo_vins (bag 接收时刻= sim 域, 与 header 同域)
import sys, os
import rosbag

run = sys.argv[1]
bagp = os.path.join(run, 'flight.bag')
TH = 0.5
streams = {'odom': [], 'prop': []}
truth = []
with rosbag.Bag(bagp) as bag:
    for topic, msg, t in bag.read_messages():
        if topic == '/vins_estimator/odometry':
            p = msg.pose.pose.position; v = msg.twist.twist.linear
            streams['odom'].append((msg.header.stamp.to_sec(), (p.x, p.y, p.z), sum(c*c for c in (v.x,v.y,v.z))**0.5))
        elif topic == '/vins_estimator/imu_propagate':
            p = msg.pose.pose.position; v = msg.twist.twist.linear
            streams['prop'].append((msg.header.stamp.to_sec(), (p.x, p.y, p.z), sum(c*c for c in (v.x,v.y,v.z))**0.5))
        elif topic == '/gazebo/model_states':
            i = next((k for k, n in enumerate(msg.name) if 'iris' in n), -1)
            if i >= 0:
                p = msg.pose[i].position
                truth.append((t.to_sec(), (p.x, p.y, p.z)))

def d3(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

def truth_at(ts):
    if not truth:
        return None
    lo, hi = 0, len(truth) - 1
    while lo < hi:
        m = (lo + hi) // 2
        if truth[m][0] < ts: lo = m + 1
        else: hi = m
    return truth[lo][1]

print(f"# run={os.path.basename(run)} n_odom={len(streams['odom'])} n_prop={len(streams['prop'])} n_truth={len(truth)}")
for name, rows in streams.items():
    if len(rows) < 2:
        print(f"## {name}: EMPTY"); continue
    t0 = rows[0][0]
    # truth 静止窗判定: 该时刻前后 1s 真值位移
    jumps = []
    for i in range(1, len(rows)):
        dt = rows[i][0] - rows[i-1][0]
        if dt <= 0 or dt > 1.0:
            continue
        dp = d3(rows[i][1], rows[i-1][1])
        if dp > TH:
            jumps.append((rows[i][0] - t0, rows[i][0], dp, rows[i][2]))
    # 大跳(>2m)全列 + 0.5-2m 计数
    big = [j for j in jumps if j[2] > 2.0]
    print(f"## {name}: jumps>0.5m={len(jumps)} big>2m={len(big)}")
    for rel, ts, dp, vm in big[:40]:
        tr = truth_at(ts)
        trs = f"({tr[0]:6.2f},{tr[1]:6.2f},{tr[2]:5.2f})" if tr else "NA"
        print(f"JUMP[{name}] t_rel={rel:8.2f} abs={ts:.2f} |dP|={dp:8.2f} |V|={vm:6.2f} truth={trs}")
