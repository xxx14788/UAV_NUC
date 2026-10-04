#!/usr/bin/env python3
# h8_freeze.py — pixel-level frame-freeze forensics: md5 raw image bytes per
# message, find longest consecutive-duplicate runs in bins around motion.
import hashlib
import sys

import rosbag

bag_path = sys.argv[1]
t_win = [float(x) for x in sys.argv[2:4]] if len(sys.argv) > 3 else None

bag = rosbag.Bag(bag_path)
rows = []  # (ts, md5, size)
for row in bag.read_messages():
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, tp, msg = row[0], row[1], row[2]
    else:
        tp, msg, t = row[0], row[1], row[2]
    if 'image_raw' in tp and 'left' in tp:
        ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
        data = msg.data
        rows.append((ts, hashlib.md5(data).hexdigest(), len(data)))
bag.close()
print('n=%d size=%s' % (len(rows), rows[0][2] if rows else 0))
if not rows:
    sys.exit(0)
t0 = rows[0][0]
# longest duplicate runs overall + in window
best = (0, None, None)
cur = 1
runs = []
for i in range(1, len(rows)):
    if rows[i][1] == rows[i - 1][1]:
        cur += 1
    else:
        if cur >= 3:
            runs.append((round(rows[i - 1][0] - t0, 1), cur))
        cur = 1
if cur >= 3:
    runs.append((round(rows[-1][0] - t0, 1), cur))
runs.sort(key=lambda r: -r[1])
print('dup-runs(>=3) top10 [t, len]:', runs[:10])
uniq = len(set(r[1] for r in rows))
print('unique_frames=%d / %d (%.1f%%)' % (uniq, len(rows), 100.0 * uniq / len(rows)))
# 10s-binned unique fraction
bins = {}
for ts, h, _ in rows:
    bins.setdefault(int((ts - t0) // 10), []).append(h)
print('bin unique_frac:', [(b * 10, round(len(set(v)) / len(v), 3), len(v))
                            for b, v in sorted(bins.items())[:14]])
