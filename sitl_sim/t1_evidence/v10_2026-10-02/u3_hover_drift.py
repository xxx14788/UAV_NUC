#!/usr/bin/env python3
# u3_hover_drift.py — unit-3 forensics: px4ctrl hover 8.5m physical drift
# profiling (VR3 bag vs E-4 R8 control). Reads: model_states (GT truth),
# mavros/local_position/odom (EKF2), debugPx4ctrl (control loop). Read-only.
import math
import sys

import rosbag

BAG = sys.argv[1]
IRIS = "iris_stereo_vins"


def rows(bag):
    gt = []      # (t, x, y, z)
    ekf = []     # (t, x, y, z)
    dbg = []     # dicts
    fsm = []
    for row in bag.read_messages():
        if hasattr(row[0], 'to_sec') or isinstance(row[0], float):
            t, topic, msg = row[0], row[1], row[2]
        else:
            topic, msg, t = row[0], row[1], row[2]
        ts = t.to_sec() if hasattr(t, 'to_sec') else float(t)
        if topic == '/gazebo/model_states':
            try:
                i = msg.name.index(IRIS)
            except ValueError:
                continue
            p = msg.pose[i].position
            gt.append((ts, p.x, p.y, p.z))
        elif topic == '/mavros/local_position/odom':
            p = msg.pose.pose.position
            ekf.append((ts, p.x, p.y, p.z))
        elif topic == '/debugPx4ctrl':
            dbg.append((ts, msg.des_v_x, msg.des_v_y, msg.des_v_z, msg.des_thr,
                        msg.hover_percentage, msg.err_axisang_ang,
                        msg.fb_a_x, msg.fb_a_y, msg.fb_a_z, msg.des_a_z))
        elif topic == '/debugPx4ctrl/fsm_state':
            fsm.append((ts, msg.data))
    return gt, ekf, dbg, fsm


def stats(a):
    if not a:
        return None
    s = sorted(a)
    return dict(n=len(s), p50=round(s[len(s) // 2], 4),
                p95=round(s[int(0.95 * len(s))], 4), mx=round(s[-1], 4))


def main():
    bag = rosbag.Bag(BAG)
    gt, ekf, dbg, fsm = rows(bag)
    bag.close()
    if not gt:
        print('no GT')
        return
    t0 = gt[0][0]
    # GT drift profile: displacement from first airborne-anchored point
    # find hover anchor = after takeoff (z > 0.8m first time)
    ai = next((i for i, r in enumerate(gt) if r[3] > 0.8), 0)
    ax, ay = gt[ai][1], gt[ai][2]
    print('anchor t=%.1f  span=%.1fs  n_gt=%d n_ekf=%d n_dbg=%d' %
          (gt[ai][0] - t0, gt[-1][0] - gt[ai][0], len(gt), len(ekf), len(dbg)))
    maxd = 0.0
    maxt = None
    per10 = []
    for r in gt[ai:]:
        d = math.hypot(r[1] - ax, r[2] - ay)
        if d > maxd:
            maxd, maxt = d, r[0] - t0
    for k in range(0, int(gt[-1][0] - gt[ai][0]), 10):
        w = [r for r in gt[ai:] if k <= r[0] - t0 - (gt[ai][0] - t0) < k + 10]
        if w:
            per10.append((k + 10, round(max(math.hypot(r[1] - ax, r[2] - ay) for r in w), 2)))
    print('gt_xy_drift_max=%.2fm @t=%.1fs' % (maxd, maxt))
    print('gt_drift_10s_bins:', per10)
    # z profile
    zs = [r[3] for r in gt[ai:]]
    print('gt_z: min=%.2f max=%.2f' % (min(zs), max(zs)))
    # EKF2 vs GT tracking (nearest-sample)
    if ekf:
        import bisect
        ets = [e[0] for e in ekf]
        derr = []
        for r in gt[ai:]:
            j = bisect.bisect_left(ets, r[0])
            if 0 < j < len(ets):
                e = ekf[j]
                derr.append(math.hypot(e[1] - r[1], e[2] - r[2]))
        print('ekf_vs_gt_xy:', stats(derr))
    # px4ctrl loop face
    if dbg:
        des_v_norm = [math.hypot(d[1], d[2], d[3]) for d in dbg]
        thr = [d[4] for d in dbg if d[4] > 0]
        hov = [d[5] for d in dbg if d[5] > 0]
        err_ang = [d[6] for d in dbg]
        fb_a_norm = [math.hypot(d[7], d[8], d[9]) for d in dbg]
        print('des_v_norm:', stats(des_v_norm))
        print('des_thr:', stats(thr))
        print('hover_pct:', stats(hov))
        print('err_axisang_ang(rad):', stats(err_ang))
        print('fb_a_norm:', stats(fb_a_norm))
    # fsm states
    seq = []
    prev = None
    for ts, s in fsm:
        key = s.split()[0]
        if key != prev:
            seq.append((round(ts - t0, 1), key))
            prev = key
    print('fsm:', seq[-6:] if len(seq) > 6 else seq)


if __name__ == '__main__':
    main()
