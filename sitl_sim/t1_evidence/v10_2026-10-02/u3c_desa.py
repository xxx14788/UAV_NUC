#!/usr/bin/env python3
# u3c: des_a (position-loop output) timeline — is px4ctrl's error channel dead?
import sys

import rosbag

bag = rosbag.Bag(sys.argv[1])
rows = []
for row in bag.read_messages(topics=['/debugPx4ctrl']):
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, msg = row[0], row[2]
    else:
        msg, t = row[1], row[2]
    ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
    rows.append((ts, msg.des_a_x, msg.des_a_y, msg.des_a_z))
bag.close()
t0 = rows[0][0]
bins = {}
for ts, ax_, ay, az in rows:
    b = int((ts - t0) // 10) * 10
    bins.setdefault(b, []).append((abs(ax_), abs(ay), (ax_*ax_+ay*ay) ** 0.5, az))
import math
print('bin_s   n  |a_xy|_p50 |a_xy|_p95  a_z_p50')
for b in sorted(bins):
    v = bins[b]
    xy = sorted(x[2] for x in v)
    az = sorted(x[3] for x in v)
    print('%5d %4d %10.4f %10.4f %8.4f' % (b, len(v), xy[len(xy) // 2], xy[int(0.95 * len(xy))], az[len(az) // 2]))
