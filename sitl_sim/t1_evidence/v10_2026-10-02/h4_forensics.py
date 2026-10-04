#!/usr/bin/env python3
# h4_forensics.py — H-4 never-flew discriminator: five faces per round bag.
# (a) truth z exact stats (physics alive? frozen? resting jitter?)
# (b) /mavros/state mode+armed transitions (did FCU enter OFFBOARD?)
# (c) EKF2 local_position z max (what does PX4 think?)
# (d) setpoint_raw/attitude thrust timeline (what did px4ctrl command?)
# (e) imu/data_raw rate + vins odom/prop z max (VINS phantom?)
import sys

import rosbag

IRIS = "iris_stereo_vins"


def main(bag_path):
    bag = rosbag.Bag(bag_path)
    truth = []
    states = []
    ekf = []
    sp = []       # (t, thrust, bodyrate_z)
    imu_n = 0
    imu_t0 = None
    imu_tN = None
    vins_odom_z = []
    vins_prop_z = []
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
            truth.append((ts, msg.pose[i].position.z, msg.pose[i].position.x))
        elif topic == '/mavros/state':
            states.append((ts, msg.mode, msg.armed))
        elif topic == '/mavros/local_position/odom':
            ekf.append((ts, msg.pose.pose.position.z))
        elif topic == '/mavros/setpoint_raw/attitude':
            sp.append((ts, msg.thrust, msg.body_rate.z))
        elif topic == '/mavros/imu/data_raw':
            imu_n += 1
            imu_t0 = ts if imu_t0 is None else imu_t0
            imu_tN = ts
        elif topic == '/vins_estimator/odometry':
            vins_odom_z.append((ts, msg.pose.pose.position.z))
        elif topic == '/vins_estimator/imu_propagate':
            vins_prop_z.append((ts, msg.pose.pose.position.z))
    bag.close()
    print('== %s' % bag_path.split('/')[-2])
    # (a) truth
    if truth:
        zs = [z for _, z, _ in truth]
        uniq = len(set(round(z, 6) for z in zs))
        print(' truth: n=%d span=%.1fs z[min=%.4f max=%.4f] uniq6=%d first=%.4f last=%.4f x[max=%.3f]' % (
            len(truth), truth[-1][0] - truth[0][0], min(zs), max(zs), uniq, zs[0], zs[-1],
            max(x for _, _, x in truth)))
    else:
        print(' truth: NONE')
    # (b) state transitions
    prev = None
    trans = []
    for ts, m, a in states:
        k = (m, a)
        if k != prev:
            trans.append((round(ts - states[0][0], 1), m, a))
            prev = k
    print(' state:', trans[:10])
    # (c) ekf
    if ekf:
        print(' ekf_z: n=%d max=%.3f last=%.3f' % (len(ekf), max(z for _, z in ekf), ekf[-1][1]))
    # (d) setpoints
    if sp:
        t0 = sp[0][0]
        thr = [s[1] for s in sp]
        # thrust bins: fraction of setpoints with thrust>0.1 in first/last thirds
        n3 = len(sp) // 3
        hi_frac = [sum(1 for s in sp[i * n3:(i + 1) * n3] if s[1] > 0.1) / max(n3, 1) for i in range(3)]
        print(' sp: n=%d thr[min=%.3f max=%.3f p50=%.3f] hi_frac_thirds=%s span=%.1fs' % (
            len(sp), min(thr), max(thr), sorted(thr)[len(thr) // 2],
            [round(f, 2) for f in hi_frac], sp[-1][0] - t0))
    # (e) imu + vins
    if imu_n:
        print(' imu: n=%d rate=%.1fHz' % (imu_n, imu_n / max(imu_tN - imu_t0, 1e-9)))
    if vins_odom_z:
        print(' vins_odom_z: n=%d max=%.3f' % (len(vins_odom_z), max(z for _, z in vins_odom_z)))
    if vins_prop_z:
        print(' vins_prop_z: n=%d max=%.3f' % (len(vins_prop_z), max(z for _, z in vins_prop_z)))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        try:
            main(p)
        except Exception as e:
            print('ERR', p, e)
