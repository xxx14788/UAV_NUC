#!/usr/bin/env python3
# T1-v5 V1.2 地面静态分析器（离线 bag）。
# 用法: v1_ground_analysis.py <bag>
# 输出: 各话题 rate/maxgap、imu_propagate 静态漂移(幅度+首末差)、真值漂移、
#       VINS init 时点(首条 imu_propagate vs bag 首 vs 首帧图像)
import rosbag, sys, math, statistics

b = rosbag.Bag(sys.argv[1])
first_t = None; first_img = None
prop = {"t": [], "p": []}; gt = {"t": [], "p": []}
imu_raw = []; ekf = []; vis = []
TOPICS = ["/vins_estimator/imu_propagate", "/gazebo/model_states",
          "/mavros/imu/data_raw", "/mavros/local_position/odom",
          "/mavros/vision_pose/pose", "/iris_stereo_vins/vins_cam_left/image_raw"]
for topic, msg, t in b.read_messages(topics=TOPICS):
    ts = msg.header.stamp.to_sec() if topic not in ("/gazebo/model_states",) else t.to_sec()
    if first_t is None: first_t = ts
    if topic == "/vins_estimator/imu_propagate":
        prop["t"].append(ts)
        prop["p"].append((msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z))
    elif topic == "/gazebo/model_states":
        try:
            k = msg.name.index([n for n in msg.name if "iris" in n][0])
            gt["t"].append(ts)
            gt["p"].append((msg.pose[k].position.x, msg.pose[k].position.y, msg.pose[k].position.z))
        except (ValueError, IndexError): pass
    elif topic == "/mavros/imu/data_raw": imu_raw.append(ts)
    elif topic == "/mavros/local_position/odom": ekf.append(msg.header.stamp.to_sec())
    elif topic == "/mavros/vision_pose/pose": vis.append(msg.header.stamp.to_sec())
    elif topic.endswith("image_raw") and first_img is None: first_img = ts
b.close()

def rate_gap(name, ts):
    if len(ts) < 3:
        print("  %-16s n=%d 不足" % (name, len(ts))); return
    s = sorted(ts); dts = [s[i+1]-s[i] for i in range(len(s)-1)]
    print("  %-16s %.1fHz n=%d maxgap=%.3fs p50dt=%.4fs" % (
        name, len(s)/(s[-1]-s[0]), len(s), max(dts), statistics.median(dts)))

print("== V1.2 地面静态 %s ==" % sys.argv[1].split("/")[-1])
rate_gap("imu/data_raw", imu_raw)
rate_gap("imu_propagate", prop["t"])
rate_gap("ekf odom", ekf)
rate_gap("vision_pose", vis)
if prop["t"]:
    print("  VINS init: 首条 imu_propagate 距 bag 首 %.1fs, 距首帧图像 %.1fs"
          % (prop["t"][0]-first_t, (prop["t"][0]-first_img) if first_img else -1))
    xs, ys, zs = list(zip(*prop["p"]))
    print("  imu_propagate 静态: 漂移幅度(x/y/z)=%.3f/%.3f/%.3f m, 首末差=%.3f/%.3f/%.3f m, 60s 内预计 %.3f m"
          % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs),
             xs[-1]-xs[0], ys[-1]-ys[0], zs[-1]-zs[0],
             max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))))
if gt["p"]:
    xs, ys, zs = list(zip(*gt["p"]))
    print("  真值(gazebo)静态: 漂移幅度 %.4f/%.4f/%.4f m" % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)))
if prop["p"] and gt["p"]:
    print("  VINS 原点 vs 真值出生点: 首条 prop=(%.3f,%.3f,%.3f) gt=(%.3f,%.3f,%.3f)"
          % (prop["p"][0][0], prop["p"][0][1], prop["p"][0][2], gt["p"][0][0], gt["p"][0][1], gt["p"][0][2]))
