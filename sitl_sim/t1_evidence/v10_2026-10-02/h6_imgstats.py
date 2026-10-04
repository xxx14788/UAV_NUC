#!/usr/bin/env python3
# h6_imgstats.py — hostile-regime discriminator: stereo image statistics
# per 5s bin (mean brightness, contrast std, sharpness=laplacian var, supply
# fraction via corner count proxy). Compares clean vs hostile round bags.
import sys

import numpy as np
import rosbag
from cv_bridge import CvBridge

bridge = CvBridge()
topic_hint = sys.argv[2] if len(sys.argv) > 2 else "vins_cam_left"


def lap_var(gray):
    g = gray.astype(np.float32)
    lap = (np.roll(g, 1, 0) + np.roll(g, -1, 0) + np.roll(g, 1, 1) +
           np.roll(g, -1, 1) - 4 * g)
    return float(lap.var())


def corner_frac(gray):
    # fast proxy for feature supply: fraction of pixels with strong gradient
    g = gray.astype(np.float32)
    gx = np.abs(np.diff(g, axis=1)).mean()
    gy = np.abs(np.diff(g, axis=0)).mean()
    return float((gx + gy) / 2.0)


bag = rosbag.Bag(sys.argv[1])
topic = None
stats = []
for row in bag.read_messages():
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, tp, msg = row[0], row[1], row[2]
    else:
        tp, msg, t = row[0], row[1], row[2]
    if topic_hint in tp and tp.endswith('image_raw'):
        topic = tp
        ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
        try:
            cv = bridge.imgmsg_to_cv2(msg, 'mono8')
        except Exception:
            continue
        stats.append((ts, float(cv.mean()), float(cv.std()), lap_var(cv), corner_frac(cv)))
bag.close()
print('topic=%s n=%d' % (topic, len(stats)))
if not stats:
    sys.exit(0)
t0 = stats[0][0]
bins = {}
for s in stats:
    bins.setdefault(int((s[0] - t0) / 5), []).append(s[1:])
print('bin  n   mean    std    lapvar      grad')
for b in sorted(bins)[:16]:
    v = bins[b]
    print('%3d %4d %6.1f %6.1f %9.0f %7.2f' % (
        b * 5, len(v),
        sum(x[0] for x in v) / len(v),
        sum(x[1] for x in v) / len(v),
        sum(x[2] for x in v) / len(v),
        sum(x[3] for x in v) / len(v)))
