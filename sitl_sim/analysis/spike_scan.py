#!/usr/bin/env python3
"""D1-1 reanchor spike forensics: imu_propagate spike census + odometry keyframe alignment.

Reads ONLY /vins_estimator/imu_propagate + /vins_estimator/odometry (+ truth opt).
For each spike (|v| above vth, or inter-frame position jump above jumpth):
  - t, |v|, direction (unit vec), position jump dP, dP/dt equivalent velocity
  - alignment: nearest odometry frame within +win s (odometry = optimizer-solution update)
  - reanchor-delta check: dP_jump vs (odo_frame.pos - prop_pos_just_before)
Causality verdict: spike list alignment rate -> is "spike == optimizer update instant".

Usage:
  spike_scan.py BAG [--vth 0.3] [--jumpth 0.02] [--win 0.05] [--out JSON]
"""
import argparse, json, math, sys
import rosbag

def vlen(x, y, z):
    return math.sqrt(x * x + y * y + z * z)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bag')
    ap.add_argument('--vth', type=float, default=0.3, help='|v| spike threshold m/s (absolute)')
    ap.add_argument('--vjump', type=float, default=0.5, help='frame-to-frame |dv| spike threshold m/s')
    ap.add_argument('--jumpth', type=float, default=0.02, help='frame-to-frame position jump threshold m')
    ap.add_argument('--win', type=float, default=0.05, help='alignment window s around odometry frame')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    prop, odo = [], []
    with rosbag.Bag(args.bag) as b:
        bag_t0, bag_t1 = b.get_start_time(), b.get_end_time()
        for topic, msg, ts in b.read_messages(topics=['/vins_estimator/imu_propagate',
                                                      '/vins_estimator/odometry']):
            t = msg.header.stamp.to_sec()
            p = msg.pose.pose.position
            v = msg.twist.twist.linear
            rec = (t, p.x, p.y, p.z, v.x, v.y, v.z)
            if topic.endswith('imu_propagate'):
                prop.append(rec)
            else:
                odo.append(rec)

    if len(prop) < 10:
        print('RESULT=FAIL too few imu_propagate frames: %d' % len(prop)); sys.exit(1)
    prop.sort(); odo.sort()

    # domain sanity (t2b lesson: dump domains)
    print('prop: n=%d t=[%.3f..%.3f] span=%.1fs' % (len(prop), prop[0][0], prop[-1][0], prop[-1][0] - prop[0][0]))
    print('odo : n=%d t=[%.3f..%.3f] span=%.1fs' % (len(odo), odo[0][0], odo[-1][0], odo[-1][0] - odo[0][0]))
    print('bag : t=[%.3f..%.3f]' % (bag_t0, bag_t1))
    if abs(prop[0][0] - bag_t0) > 3600:
        print('WARN: prop header domain differs from bag domain by >1h (cross-domain suspicion)')

    odo_ts = [r[0] for r in odo]
    import bisect
    def nearest_odo(t):
        i = bisect.bisect_left(odo_ts, t)
        best, bd = None, 1e18
        for j in (i - 1, i):
            if 0 <= j < len(odo_ts):
                d = abs(odo_ts[j] - t)
                if d < bd: bd, best = d, j
        return best, bd

    spikes = []
    n_v, n_dv, n_dp = 0, 0, 0
    for i in range(1, len(prop)):
        t0, x0, y0, z0, vx0, vy0, vz0 = prop[i - 1]
        t1, x1, y1, z1, vx1, vy1, vz1 = prop[i]
        dt = t1 - t0
        if dt <= 0 or dt > 0.5: continue
        sp = vlen(vx1, vy1, vz1)
        dv = vlen(vx1 - vx0, vy1 - vy0, vz1 - vz0)
        dp = vlen(x1 - x0, y1 - y0, z1 - z0)
        is_spike = (sp > args.vth) or (dp > args.jumpth) or (dv > args.vjump)
        if not is_spike: continue
        if sp > args.vth: n_v += 1
        if dp > args.jumpth: n_dp += 1
        if dv > args.vjump: n_dv += 1
        # alignment: is there an odometry frame just at/after this spike within win?
        j, d = nearest_odo(t1)
        aligned = (j is not None and 0 <= odo_ts[j] - t1 <= args.win) or (j is not None and abs(odo_ts[j] - t1) <= args.win)
        # reanchor delta: odo frame pos minus prop pos just before the jump
        reanchor = None
        if j is not None and abs(odo_ts[j] - t1) <= args.win:
            ox, oy, oz = odo[j][1], odo[j][2], odo[j][3]
            reanchor = (ox - x0, oy - y0, oz - z0)
        jumps = (x1 - x0, y1 - y0, z1 - z0)
        spikes.append(dict(
            t=round(t1 - prop[0][0], 3), sp=round(sp, 3), dv=round(dv, 3), dp=round(dp, 4),
            jump=[round(e, 4) for e in jumps],
            vdir=[round(vx1 / sp, 2) if sp > 1e-6 else 0, round(vy1 / sp, 2) if sp > 1e-6 else 0,
                  round(vz1 / sp, 2) if sp > 1e-6 else 0] if sp > 1e-6 else [0, 0, 0],
            dt_ms=round(dt * 1000, 1),
            odo_dt_ms=round((odo_ts[j] - t1) * 1000, 1) if j is not None else None,
            aligned=bool(aligned),
            reanchor_delta=[round(e, 4) for e in reanchor] if reanchor else None,
        ))

    n_al = sum(1 for s in spikes if s['aligned'])
    # magnitude match: |jump| vs |reanchor_delta| for aligned spikes
    match_n = match_bad = 0
    for s in spikes:
        if s['aligned'] and s['reanchor_delta']:
            a = vlen(*s['jump']); b = vlen(*s['reanchor_delta'])
            if a > args.jumpth:
                if b > 1e-9 and 0.5 <= a / b <= 2.0: match_n += 1
                else: match_bad += 1
    print('spikes: n=%d (|v|>%.2f: %d, dP>%.3f: %d, |dv|>%.2f: %d) | aligned to odo frame: %d (%.0f%%)'
          % (len(spikes), args.vth, n_v, args.jumpth, n_dp, args.vjump, n_dv, n_al,
             100.0 * n_al / len(spikes) if spikes else 0))
    print('reanchor-delta magnitude match (|jump| within [0.5,2]x of |odo-prop|): %d ok / %d bad' % (match_n, match_bad))
    print('%-9s %-7s %-7s %-8s %-9s %-6s %-11s %s' % ('t(s)', '|v|', '|dv|', 'dP', 'dt_ms', 'align', 'odo_dt_ms', 'jump(x,y,z) | reanchor_delta'))
    for s in spikes[:60]:
        ra = '(%+.3f,%+.3f,%+.3f)' % tuple(s['reanchor_delta']) if s['reanchor_delta'] else '-'
        print('%-9.3f %-7.3f %-7.3f %-8.4f %-9.1f %-6s %-11s (%+.3f,%+.3f,%+.3f) | %s'
              % (s['t'], s['sp'], s['dv'], s['dp'], s['dt_ms'], 'Y' if s['aligned'] else 'N',
                 s['odo_dt_ms'], *s['jump'], ra))
    if len(spikes) > 60: print('... %d more' % (len(spikes) - 60))

    # per-odo-frame residual series head (for reanchor ladder inspection)
    if args.out:
        with open(args.out, 'w') as f:
            json.dump(dict(bag=args.bag, n_prop=len(prop), n_odo=len(odo),
                           thresholds=vars(args), spikes=spikes,
                           odo_t=[round(r[0] - prop[0][0], 3) for r in odo[:500]]), f)
        print('JSON -> %s' % args.out)

if __name__ == '__main__':
    main()
