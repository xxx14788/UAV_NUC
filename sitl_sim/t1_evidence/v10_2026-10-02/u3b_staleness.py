#!/usr/bin/env python3
# u3b: px4ctrl odom-input freshness around the drift onset (VR3)
import sys

import rosbag

BAG = sys.argv[1]

bag = rosbag.Bag(BAG)
rows = []
for row in bag.read_messages(topics=['/debugPx4ctrl']):
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, msg = row[0], row[2]
    else:
        msg, t = row[1], row[2]
    ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
    rows.append((ts, getattr(msg, 'odom_delay_ms', -1),
                 getattr(msg, 'odom_staleness_ms', -1), msg.des_thr))
bag.close()
if not rows:
    print('no dbg')
    sys.exit(0)
t0 = rows[0][0]
# 10s bins: p50 staleness, p50 delay, thr range
import math
bins = {}
for ts, dm, sm, thr in rows:
    b = int((ts - t0) // 10) * 10
    bins.setdefault(b, []).append((dm, sm, thr))
print('bin_s  n   delay_p50  stale_p50  stale_max  thr_p50  thr_max')
for b in sorted(bins):
    v = bins[b]
    dm = sorted(x[0] for x in v if x[0] >= 0)
    sm = sorted(x[1] for x in v if x[1] >= 0)
    th = sorted(x[2] for x in v)
    print('%5d %4d %8.2f %10.2f %10.2f %8.4f %7.4f' % (
        b, len(v),
        dm[len(dm) // 2] if dm else -1,
        sm[len(sm) // 2] if sm else -1,
        sm[-1] if sm else -1,
        th[len(th) // 2], th[-1]))
