#!/usr/bin/env python3
"""T1-D2 forensics: route7 (t2v3_route_215016.bag, 23GB) coarse sweep.

Discipline: topic-filtered + time-window reads only (no full-dump).
Pass 1 (this script): low-rate skeleton -- armed timeline, truth track (decimated),
fsm_state, odom magnitude timeline in 10s buckets -> locate the flyaway window.
Pass 2 (later): full-rate dump of the located window only.

Usage: d2_route_scan.py BAG [--bucket 10]
"""
import argparse, math, sys
import rosbag

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bag')
    ap.add_argument('--bucket', type=float, default=10.0)
    args = ap.parse_args()

    topics = ['/mavros/state',
              '/debugPx4ctrl/fsm_state',
              '/vins_estimator/imu_propagate',
              '/gazebo/model_states',
              '/mavros/setpoint_raw/attitude']

    t0 = None
    # bucket accumulators
    B = {}
    def bkt(t):
        nonlocal t0
        if t0 is None: t0 = t
        return int((t - t0) // args.bucket)

    n_state = n_fsm = n_odo = n_truth = n_cmd = 0
    armed_changes = []
    fsm_changes = []
    last_armed = None
    last_fsm = None
    truth_decim = []

    with rosbag.Bag(args.bag) as b:
        bt0 = b.get_start_time()
        for topic, msg, ts in b.read_messages(topics=topics):
            t = ts.to_sec() if hasattr(ts, 'to_sec') else ts  # bag-time domain (sim clock)
            if topic == '/mavros/state':
                n_state += 1
                if msg.armed != last_armed:
                    armed_changes.append((round(t - bt0, 1), bool(msg.armed)))
                    last_armed = msg.armed
            elif topic == '/debugPx4ctrl/fsm_state':
                n_fsm += 1
                if msg.data != last_fsm:
                    fsm_changes.append((round(t - bt0, 1), msg.data[:40]))
                    last_fsm = msg.data
            elif topic == '/vins_estimator/imu_propagate':
                n_odo += 1
                p = msg.pose.pose.position; v = msg.twist.twist.linear
                k = bkt(t)
                d = B.setdefault(k, dict(n=0, vmax=0.0, pmax=0.0, vsum=0.0, jmax=0.0,
                                          plast=None, first_t=None, last_t=None))
                vn = math.sqrt(v.x**2 + v.y**2 + v.z**2)
                pn = math.sqrt(p.x**2 + p.y**2 + p.z**2)
                d['n'] += 1
                d['vmax'] = max(d['vmax'], vn)
                d['vsum'] += vn
                d['pmax'] = max(d['pmax'], pn)
                if d['plast'] is not None:
                    j = math.sqrt((p.x-d['plast'][0])**2 + (p.y-d['plast'][1])**2 + (p.z-d['plast'][2])**2)
                    d['jmax'] = max(d['jmax'], j)
                d['plast'] = (p.x, p.y, p.z)
                if d['first_t'] is None: d['first_t'] = t - bt0
                d['last_t'] = t - bt0
            elif topic == '/gazebo/model_states':
                n_truth += 1
                if n_truth % 25 == 0:  # decimate 250Hz -> 10Hz
                    try:
                        i = msg.name.index('iris_stereo_vins')
                        p = msg.pose[i].position
                        truth_decim.append((round(t - bt0, 1), round(p.x,2), round(p.y,2), round(p.z,2)))
                    except ValueError:
                        pass
            elif topic == '/mavros/setpoint_raw/attitude':
                n_cmd += 1
                k = bkt(t)
                th = abs(msg.thrust)
                d = B.setdefault(k, dict(n=0, vmax=0.0, pmax=0.0, vsum=0.0, jmax=0.0, plast=None, first_t=None, last_t=None, thr_max=0.0))
                d['thr_max'] = max(d.get('thr_max', 0.0), th)

    print('bag span %.1fs | msgs: state=%d fsm=%d odo=%d truth=%d cmd=%d' % (0, n_state, n_fsm, n_odo, n_truth, n_cmd))
    print('armed changes (t_rel, armed):', armed_changes[:20])
    print('fsm changes:')
    for t, f in fsm_changes[:25]: print('  %8.1f  %s' % (t, f))
    print('--- odom buckets (%gs) ---' % args.bucket)
    print('%-6s %-7s %-9s %-9s %-9s %-9s %-8s' % ('bucket', 'n', 'v_max', 'v_mean', 'p_max', 'jump_max', 'thr_max'))
    for k in sorted(B):
        d = B[k]
        if d['n'] == 0:
            print('%-6d %-7s %-9s %-9s %-9s %-9s %-8.2f' % (k, '-', '-', '-', '-', '-', d.get('thr_max', 0)))
            continue
        print('%-6d %-7d %-9.2f %-9.2f %-9.2f %-9.3f %-8.2f' % (k, d['n'], d['vmax'], d['vsum']/d['n'], d['pmax'], d['jmax'], d.get('thr_max', 0)))
    print('--- truth (decimated 10Hz) ---')
    line = []
    for row in truth_decim:
        line.append('%7.1f:(%6.2f,%6.2f,%5.2f)' % row)
        if len(line) == 5:
            print(' '.join(line)); line = []
    if line: print(' '.join(line))

if __name__ == '__main__':
    main()
