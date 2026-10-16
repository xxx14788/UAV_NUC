#!/usr/bin/env python3
"""逐帧长探针：打印每帧 RGB std + depth finite，60s——判定渲染死亡时刻"""
import sys, time
import rospy
import numpy as np
from sensor_msgs.msg import Image

rospy.init_node('long_probe', anonymous=True, disable_signals=True)
rgb = []
depth = []

def rb(m):
    a = np.frombuffer(m.data, dtype=np.uint8)
    rgb.append((time.time(), float(a.std())))

def db(m):
    a = np.frombuffer(m.data, dtype=np.float32)
    depth.append((time.time(), int(np.isfinite(a).sum())))

rospy.Subscriber('/min2/image_raw', Image, rb, queue_size=10)
rospy.Subscriber('/min2/depth/image_raw', Image, db, queue_size=10)
t0 = time.time()
last_print = 0
n_print = 0
while time.time() - t0 < 60 and n_print < 60:
    time.sleep(1.0)
    n_print += 1
    r = rgb[-1] if rgb else None
    d = depth[-1] if depth else None
    rs = 'rgb_std=%.1f' % r[1] if r else 'rgb=NONE'
    ds = 'depth_fin=%d' % d[1] if d else 'depth=NONE'
    print('t+%02ds frames=%d/%d %s %s' % (n_print, len(rgb), len(depth), rs, ds), flush=True)
print('SUMMARY rgb_alive_frames=%d/%d last_rgb_std=%.1f depth_total_finite=%d' % (
    sum(1 for _, s in rgb if s > 0), len(rgb), rgb[-1][1] if rgb else -1,
    sum(f for _, f in depth)))
