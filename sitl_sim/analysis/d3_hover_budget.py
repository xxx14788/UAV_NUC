#!/usr/bin/env python3
"""T1-D3: hover accuracy budget decomposition (pre-fix hover bag).

Decomposes the 0.117 m hover-hold error into:
  (a) slow drift    : linear regression slope of the VINS-vs-truth error over the window
  (b) reanchor steps: sum of |dP| jump events (per-frame dP > 0.02 m) and their envelope
  (c) tracking residual: std of detrended, de-stepped error

Reads only /vins_estimator/imu_propagate + /gazebo/model_states (truth).
"""
import argparse, math, statistics
import rosbag

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bag')
    ap.add_argument('--jumpth', type=float, default=0.02)
    ap.add_argument('--t0', type=float, default=None, help='analysis window start (bag time)')
    ap.add_argument('--t1', type=float, default=None)
    args = ap.parse_args()

    prop, truth = [], []
    with rosbag.Bag(args.bag) as b:
        for topic, msg, ts in b.read_messages(topics=['/vins_estimator/imu_propagate',
                                                      '/gazebo/model_states']):
            if topic.endswith('imu_propagate'):
                p = msg.pose.pose.position
                prop.append((msg.header.stamp.to_sec(), p.x, p.y, p.z))
            else:
                try:
                    i = msg.name.index('iris_stereo_vins')
                    p = msg.pose[i].position
                    truth.append((ts.to_sec(), p.x, p.y, p.z))
                except ValueError:
                    pass
    prop.sort(); truth.sort()
    if args.t0: prop = [r for r in prop if r[0] >= args.t0]
    if args.t1: prop = [r for r in prop if r[0] <= args.t1]

    # align truth by nearest-neighbor interpolation on prop stamps
    def truth_at(t):
        lo, hi = 0, len(truth) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if truth[mid][0] < t: lo = mid
            else: hi = mid
        dtl, dth = t - truth[lo][0], truth[hi][0] - t
        row = truth[lo] if dtl <= dth else truth[hi]
        return row[1], row[2], row[3]

    # error series (VINS - truth), anchored at window start
    e0 = None
    errs = []   # (t, ex, ey, ez)
    for t, x, y, z in prop:
        tx, ty, tz = truth_at(t)
        if e0 is None: e0 = (x - tx, y - ty, z - tz)
        errs.append((t, x - tx - e0[0], y - ty - e0[1], z - tz - e0[2]))

    T0 = errs[0][0]; span = errs[-1][0] - errs[0][0]
    n = len(errs)

    # absolute hold error (V1.3 metric): XY error vs window-start anchor
    abs_xy = [math.hypot(e[1], e[2]) for e in errs]
    abs_xy.sort()
    med = abs_xy[n // 2]; p95 = abs_xy[int(0.95 * n)]

    # (a) slow drift: linear fit of XY error magnitude? fit components separately
    def linfit(xs, ys):
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = sum((x - mx) ** 2 for x in xs)
        return num / den if den else 0.0
    ts_ = [e[0] - T0 for e in errs]
    slope_x = linfit(ts_, [e[1] for e in errs])
    slope_y = linfit(ts_, [e[2] for e in errs])
    drift_rate = math.hypot(slope_x, slope_y) * 60.0  # m/min
    drift_over_win = math.hypot(slope_x, slope_y) * span

    # (b) reanchor steps: frame-to-frame jumps of the ERROR series above threshold
    steps = []
    for i in range(1, n):
        dt = errs[i][0] - errs[i-1][0]
        if dt <= 0 or dt > 0.5: continue
        dxy = math.hypot(errs[i][1] - errs[i-1][1], errs[i][2] - errs[i-1][2])
        if dxy > args.jumpth:
            steps.append((round(errs[i][0] - T0, 2), round(dxy, 4)))
    step_total = sum(s for _, s in steps)

    # (c) residual: remove linear drift from error, measure std
    rx = [e[1] - slope_x * (e[0] - T0) for e in errs]
    ry = [e[2] - slope_y * (e[0] - T0) for e in errs]
    res = [math.hypot(a, b) for a, b in zip(rx, ry)]
    res_med = statistics.median(res)

    print('window: %.1fs, %d frames (start bag-t %.1f)' % (span, n, T0))
    print('ABS hold XY: median=%.3f m  p95=%.3f m   (V1.3 contract median 0.117)' % (med, p95))
    print('(a) slow drift: rate=%.3f m/min, over-window=%.3f m (slope %.4f,%.4f m/s)' % (
        drift_rate, drift_over_win, slope_x, slope_y))
    print('(b) reanchor steps>n=%.0fm: n=%d, total magnitude=%.3f m, largest=%s' % (
        args.jumpth, len(steps), step_total, max((s for _, s in steps), default=0)))
    if steps[:10]:
        for t, s in steps[:10]: print('    step @%.1fs  %.4f m' % (t, s))
    print('(c) tracking residual (de-drifted XY): median=%.3f m' % res_med)

if __name__ == '__main__':
    main()
