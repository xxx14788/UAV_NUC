#!/usr/bin/env python3
"""批内 depth 活性监测探针（v5.2 §三.3 条款：每 6 轮探一次）
用法: depth_activity_probe.py [采样秒数, 默认12] [输出文件, 默认 /tmp/c3_depth_activity.tsv 追加]
判定: finite_ratio = 有限像素占比; <0.05 → ACTIVITY-LOSS (停批止损信号)
"""
import sys, time
import rospy
import numpy as np
from sensor_msgs.msg import Image

dur = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
outf = sys.argv[2] if len(sys.argv) > 2 else '/tmp/c3_depth_activity.tsv'
rospy.init_node('depth_activity_probe', anonymous=True, disable_signals=True)
frames = []

def cb(m):
    a = np.frombuffer(m.data, dtype=np.float32)
    frames.append(float(np.isfinite(a).sum()) / max(len(a), 1))

rospy.Subscriber('/iris_stereo_vins/camera/depth/image_raw', Image, cb, queue_size=2)
t0 = time.time()
while time.time() - t0 < dur and len(frames) < 10:
    time.sleep(0.5)
if not frames:
    line = '%s NO-FRAMES ACTIVITY-UNKNOWN(check-sim-alive)' % time.strftime('%F %T')
else:
    r = max(frames)
    verdict = 'OK' if r >= 0.05 else 'ACTIVITY-LOSS'
    line = '%s n=%d finite_ratio_max=%.4f ratio_first5=%s %s' % (
        time.strftime('%F %T'), len(frames), r, [round(f, 3) for f in frames[:5]], verdict)
with open(outf, 'a') as f:
    f.write(line + '\n')
print('DEPTH-ACTIVITY:', line)
