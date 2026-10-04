#!/usr/bin/env python3
# h9_imgdt.py — image timestamp regularity: dt histogram + sim-vs-publish lag.
# VINS z-scale during motion is exquisitely sensitive to stereo/IMU temporal
# alignment; irregular camera dt corrupts it while static hover stays immune.
import sys

import rosbag

bag = rosbag.Bag(sys.argv[1])
L, R = [], []
for row in bag.read_messages():
    if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
        t, tp, msg = row[0], row[1], row[2]
    else:
        tp, msg, t = row[0], row[1], row[2]
    if 'image_raw' in tp:
        ts = msg.header.stamp.to_sec() if msg.header.stamp else (
            t.to_sec() if hasattr(t, 'to_sec') else float(t))
        arr = L if 'left' in tp else R
        arr.append((ts, t.to_sec() if hasattr(t, 'to_sec') else float(t)))
bag.close()
for name, arr in (('left', L), ('right', R)):
    if len(arr) < 10:
        continue
    dts = [arr[i][0] - arr[i - 1][0] for i in range(1, len(arr))]
    dts_s = sorted(dts)
    neg = sum(1 for d in dts if d <= 0)
    dup = sum(1 for i in range(1, len(arr)) if arr[i][0] == arr[i - 1][0])
    # lag between bag-time (publish) and header stamp
    lags = [p - s for s, p in arr]
    lags_s = sorted(lags)
    print('%s n=%d dt_ms[p5=%0.1f p50=%0.1f p95=%0.1f max=%0.1f] neg_dt=%d dup_stamp=%d '
          'lag_ms[p50=%0.1f p95=%0.1f max=%0.1f]' % (
              name, len(arr),
              dts_s[int(0.05 * len(dts))] * 1000, dts_s[len(dts) // 2] * 1000,
              dts_s[int(0.95 * len(dts))] * 1000, dts_s[-1] * 1000,
              neg, dup,
              lags_s[len(lags) // 2] * 1000, lags_s[int(0.95 * len(lags))] * 1000,
              lags_s[-1] * 1000))
# stereo sync: pair left/right nearest stamps, residual
if L and R:
    import bisect
    rs = [r[0] for r in R]
    resid = []
    for s, _ in L:
        j = bisect.bisect_left(rs, s)
        if 0 < j < len(rs):
            resid.append(abs(rs[j] - s) * 1000)
    resid.sort()
    print('stereo pair residual ms: p50=%.2f p95=%.2f max=%.2f n=%d' % (
        resid[len(resid) // 2], resid[int(0.95 * len(resid))], resid[-1], len(resid)))
