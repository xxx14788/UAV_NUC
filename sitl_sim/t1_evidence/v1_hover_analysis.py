#!/usr/bin/env python3
# T1-v5 V1.3 悬停保持分析器（离线 bag 分析,双口径）。
# 用法: v1_hover_analysis.py <bag> [settle_s] [hold_s]
#   口径A(px4ctrl 视角): imu_propagate 位置对段内中位数的偏差(目标=起飞时刻
#     odom 读数,同源自消)——与 GPS 代位链 ≤0.03m 基线直接可比
#   口径B(真值视角):   gazebo model_states(iris) 同段偏差
# 分段: takeoff_land cmd=1 时刻 +settle_s 起, 至 cmd=2(或 bag 尾/hold_s 截)
import rosbag, sys, math

bag_path = sys.argv[1]
settle_s = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
hold_s   = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0

b = rosbag.Bag(bag_path)
t_to = t_land = None
prop, gt, ekf = [], [], []
TOPICS = ["/px4ctrl/takeoff_land", "/vins_estimator/imu_propagate",
          "/gazebo/model_states", "/mavros/local_position/odom"]
for topic, msg, t in b.read_messages(topics=TOPICS):
    ts = t.to_sec()
    if topic == "/px4ctrl/takeoff_land":
        if msg.takeoff_land_cmd == 1 and t_to is None: t_to = ts
        if msg.takeoff_land_cmd == 2 and t_to is not None and t_land is None: t_land = ts
    elif topic == "/vins_estimator/imu_propagate":
        prop.append((ts, (msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z)))
    elif topic == "/gazebo/model_states":
        try:
            k = msg.name.index([n for n in msg.name if "iris" in n][0])
            gt.append((ts, (msg.pose[k].position.x, msg.pose[k].position.y, msg.pose[k].position.z)))
        except (ValueError, IndexError): pass
    elif topic == "/mavros/local_position/odom":
        ekf.append((ts, (msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z)))
b.close()

if t_to is None:
    print("无 takeoff_land cmd=1, 非 hover bag"); sys.exit(1)
t0 = t_to + settle_s
t1 = min(t_land if t_land else t_to + settle_s + hold_s + 5, t0 + hold_s)

def seg(arr):
    return [(ts, p) for ts, p in arr if t0 <= ts <= t1]

def hold_stats(name, arr):
    s = seg(arr)
    if len(s) < 30:
        print("%-14s 段内样本不足(%d)" % (name, len(s))); return
    pos = list(zip(*[p for _, p in s]))
    med = [sorted(v)[len(v)//2] for v in pos]
    dev = [math.sqrt(sum((p[i]-med[i])**2 for i in range(3))) for p in [p for _, p in s]]
    dev_sorted = sorted(dev)
    import statistics
    print("%-14s n=%d  中位偏差=%.3fm  p95=%.3fm  max=%.3fm  σ_xyz=(%.3f,%.3f,%.3f)m"
          % (name, len(s), dev_sorted[len(dev)//2], dev_sorted[int(len(dev)*0.95)],
             max(dev),
             statistics.pstdev(pos[0]), statistics.pstdev(pos[1]), statistics.pstdev(pos[2])))
    print("               hold 中位位置=(%.3f,%.3f,%.3f) 段=[%.1f,%.1f]s"
          % (med[0], med[1], med[2], t0 - t_to, t1 - t_to))

print("== V1.3 悬停保持 %s ==" % bag_path.split("/")[-1])
print("takeoff@%.1fs land@%s 悬停段=[takeoff+%.0fs, takeoff+%.0fs]"
      % (t_to - t_to, ("%.1fs" % (t_land - t_to)) if t_land else "无cmd2", t0 - t_to, t1 - t_to))
hold_stats("A:imu_propagate", prop)
hold_stats("B:真值gazebo", gt)
hold_stats("C:EKF2(参照)", ekf)
print("判据: 口径A 中位偏差 ≤0.03m=与 GPS 代位基线同量级(PASS); 0.03-0.08=边界(结合 B 口径归因); >0.08=FAIL")
