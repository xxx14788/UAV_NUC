#!/usr/bin/env python3
"""Passive header/arrival/clock baseline; never publishes control commands."""
import argparse
import bisect
import csv
import json
import math
from pathlib import Path
import signal
import struct
import threading
import time

LEFT = '/iris_stereo_vins/vins_cam_left/image_raw'
RIGHT = '/iris_stereo_vins/vins_cam_right/image_raw'
IMU = '/mavros/imu/data_raw'
PROP = '/vins_estimator/imu_propagate'
ODOM = '/vins_estimator/odometry'
TRUTH = '/gazebo/model_states'
STATE = '/mavros/state'
CLOCK = '/clock'
TOPICS = (LEFT, RIGHT, IMU, PROP, ODOM, TRUTH, STATE, CLOCK)
FIELDS = ('topic', 'stamp_ns', 'arrival_ns', 'clock_ns', 'seq', 'x', 'y', 'z', 'armed')


def header(data):
    """sensor_msgs/Image and Imu start with a ROS1 serialized Header."""
    if len(data) < 16:
        raise ValueError('truncated ROS Header')
    seq, sec, nsec, size = struct.unpack_from('<IIII', data)
    if nsec >= 1000000000 or 16 + size > len(data):
        raise ValueError('invalid ROS Header')
    return sec * 1000000000 + nsec, seq


def quantile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def distribution(values):
    return {'p50': quantile(values, .5), 'p95': quantile(values, .95),
            'max': max(values) if values else None}


def stream_stats(rows, nominal_hz=None):
    arrivals = [r['arrival_ns'] for r in rows]
    stamps = [r['stamp_ns'] for r in rows if r['stamp_ns'] is not None]
    da = [(b - a) / 1e6 for a, b in zip(arrivals, arrivals[1:])]
    ds = [(b - a) / 1e6 for a, b in zip(stamps, stamps[1:])]
    span = (arrivals[-1] - arrivals[0]) / 1e9 if len(arrivals) > 1 else None
    stamp_span = (stamps[-1] - stamps[0]) / 1e9 if len(stamps) > 1 else None
    seq = [r['seq'] for r in rows if r['seq'] is not None]
    seq_missing = sum(max(0, b - a - 1) for a, b in zip(seq, seq[1:]) if b > a)
    seq_resets = sum(b < a for a, b in zip(seq, seq[1:]))
    missing = None
    if nominal_hz and ds:
        missing = sum(max(0, int(dt * nominal_hz / 1000 + .5) - 1) for dt in ds if dt > 0)
    ages = [(r['clock_ns'] - r['stamp_ns']) / 1e6 for r in rows
            if r['clock_ns'] is not None and r['stamp_ns'] is not None]
    return {'count': len(rows), 'arrival_span_s': span, 'stamp_span_s': stamp_span,
            'wall_hz': (len(arrivals) - 1) / span if span and span > 0 else None,
            'sim_stamp_hz': (len(stamps) - 1) / stamp_span if stamp_span and stamp_span > 0 else None,
            'arrival_dt_ms': distribution(da), 'stamp_dt_ms': distribution(ds),
            'stamp_duplicates': sum(d == 0 for d in ds),
            'stamp_regressions': sum(d < 0 for d in ds),
            'seq_missing': seq_missing, 'seq_resets': seq_resets,
            'nominal_missing_estimate': missing,
            'nominal_missing_fraction': missing / (missing + len(ds)) if missing is not None and ds else None,
            'observed_clock_minus_stamp_ms': distribution(ages)}


def stereo_stats(left, right):
    a = sorted(r['stamp_ns'] for r in left if r['stamp_ns'] is not None)
    b = sorted(r['stamp_ns'] for r in right if r['stamp_ns'] is not None)
    # Multiset intersection, so duplicate stamps do not inflate matched pairs.
    i = j = exact = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            exact += 1
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    delta = []
    for stamp in a:
        k = bisect.bisect_left(b, stamp)
        candidates = b[max(0, k - 1):min(len(b), k + 1)]
        if candidates:
            delta.append(min(abs(stamp - s) for s in candidates) / 1e6)
    return {'exact_pairs': exact, 'left_exact_fraction': exact / len(a) if a else None,
            'right_exact_fraction': exact / len(b) if b else None,
            'left_to_nearest_right_abs_ms': distribution(delta)}


def clock_stats(rows):
    valid = [r for r in rows if r['clock_ns'] is not None]
    ratios = []
    anchor = valid[0] if valid else None
    regressions = 0
    for previous, row in zip(valid, valid[1:]):
        if row['clock_ns'] < previous['clock_ns']:
            regressions += 1
            anchor = row
        if row['arrival_ns'] - anchor['arrival_ns'] >= 1e9:
            ratios.append((row['clock_ns'] - anchor['clock_ns']) /
                          (row['arrival_ns'] - anchor['arrival_ns']))
            anchor = row
    wall = ((valid[-1]['arrival_ns'] - valid[0]['arrival_ns']) / 1e9) if len(valid) > 1 else None
    sim = ((valid[-1]['clock_ns'] - valid[0]['clock_ns']) / 1e9) if len(valid) > 1 else None
    return {'sim_span_s': sim, 'wall_span_s': wall, 'regressions': regressions,
            'overall_rtf': sim / wall if wall and not regressions else None,
            'rtf_1s_windows': distribution(ratios)}


def positions(rows):
    return [r for r in rows if r['x'] is not None]


def displacement(rows):
    rows = positions(rows)
    if not rows:
        return None
    origin = rows[0]
    distances = [math.sqrt(sum((r[k] - origin[k]) ** 2 for k in ('x', 'y', 'z'))) for r in rows]
    return {'relative_displacement_m': distribution(distances), 'end_displacement_m': distances[-1],
            'z_min_m': min(r['z'] for r in rows), 'z_max_m': max(r['z'] for r in rows)}


def relative_error(prop, truth):
    prop, truth = positions(prop), positions(truth)
    if not prop or not truth:
        return None
    times = [r['arrival_ns'] for r in truth]
    paired = []
    for p in prop:
        i = bisect.bisect_left(times, p['arrival_ns'])
        candidates = truth[max(0, i - 1):min(len(truth), i + 1)]
        t = min(candidates, key=lambda r: abs(r['arrival_ns'] - p['arrival_ns']))
        if abs(t['arrival_ns'] - p['arrival_ns']) <= 50000000:
            paired.append([p[k] - t[k] for k in ('x', 'y', 'z')])
    if not paired:
        return None
    residuals = [math.sqrt(sum((v - o) ** 2 for v, o in zip(pair, paired[0]))) for pair in paired]
    return {'pairs_within_50ms_arrival': len(paired),
            'translation_only_delta_m': distribution(residuals),
            'note': 'receiver-time pairing; no rotation/scale fit; not SE3 ATE'}


def summarize(rows, seconds, mode, elapsed_s=None, errors=0):
    by_topic = {topic: [] for topic in TOPICS}
    for row in rows:
        by_topic[row['topic']].append(row)
    stats = {topic: stream_stats(samples, 30 if topic in (LEFT, RIGHT) else None)
             for topic, samples in by_topic.items()}
    required = (LEFT, RIGHT, IMU, PROP, ODOM, TRUTH, CLOCK, STATE)
    incomplete = [topic for topic in required if stats[topic]['count'] < 2 or
                  (stats[topic]['arrival_span_s'] or 0) < .9 * seconds]
    anomalies = [topic for topic in (LEFT, RIGHT, IMU, PROP, ODOM)
                 if stats[topic]['stamp_regressions'] or stats[topic]['stamp_duplicates']]
    rtf = clock_stats(by_topic[CLOCK])
    armed = [r['armed'] for r in by_topic[STATE] if r['armed'] is not None]
    truth = displacement(by_topic[TRUTH])
    window_ok = not incomplete and not errors and elapsed_s is not None and elapsed_s >= seconds - .05
    flight_ok = bool(armed) and all(armed) and truth is not None and truth['z_min_m'] > .3
    return {'schema': 1, 'mode': mode, 'requested_wall_s': seconds, 'elapsed_wall_s': elapsed_s,
            'measurement_complete': window_ok, 'incomplete_topics': incomplete,
            'header_decode_errors': errors, 'timestamp_anomaly_topics': anomalies,
            'clock': rtf, 'streams': stats,
            'stereo': stereo_stats(by_topic[LEFT], by_topic[RIGHT]),
            'truth': truth, 'vins': displacement(by_topic[PROP]),
            'vins_truth_relative_error': relative_error(by_topic[PROP], by_topic[TRUTH]),
            'armed_samples': len(armed), 'all_armed': bool(armed) and all(armed),
            'hover_window_valid': window_ok and flight_ok if mode == 'hover' else None,
            'static_unarmed': bool(armed) and not any(armed) if mode == 'static' else None,
            'notes': ['Passive observer adds transport/scheduling load.',
                      'Nominal missing is a period-based estimate, not proven transport packet loss.',
                      'Clock-minus-stamp is not physical end-to-end latency.']}


def collect(output, seconds, mode):
    import rospy
    from gazebo_msgs.msg import ModelStates
    from mavros_msgs.msg import State
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    rows = []
    state = {'clock': None, 'errors': 0, 'accept': True, 'stop': False}
    raw = (output / 'timing.csv').open('x', newline='')
    writer = csv.DictWriter(raw, fieldnames=FIELDS)
    writer.writeheader()

    def append(topic, stamp=None, seq=None, point=None, armed=None, clock=None):
        arrival = time.monotonic_ns()
        with lock:
            if not state['accept']:
                return
            if clock is not None:
                state['clock'] = clock
            row = dict.fromkeys(FIELDS)
            row.update(topic=topic, stamp_ns=stamp, seq=seq, arrival_ns=arrival,
                       clock_ns=state['clock'], armed=armed)
            if point is not None:
                row.update(x=point.x, y=point.y, z=point.z)
            rows.append(row)
            writer.writerow(row)

    def receive_header(message, topic):
        try:
            stamp, seq = header(message._buff)
            append(topic, stamp=stamp, seq=seq)
        except (ValueError, struct.error):
            with lock:
                state['errors'] += 1

    def receive_odom(message, topic):
        append(topic, message.header.stamp.to_nsec(), message.header.seq, message.pose.pose.position)

    def receive_truth(message):
        if 'iris_stereo_vins' in message.name:
            append(TRUTH, point=message.pose[message.name.index('iris_stereo_vins')].position)

    rospy.init_node('baseline_observer', anonymous=True, disable_signals=True)
    signal.signal(signal.SIGTERM, lambda *_: state.update(stop=True))
    signal.signal(signal.SIGINT, lambda *_: state.update(stop=True))
    started = time.monotonic()
    subscribers = [rospy.Subscriber(t, rospy.AnyMsg, receive_header, callback_args=t,
                                    queue_size=100, buff_size=2**24) for t in (LEFT, RIGHT, IMU)]
    subscribers += [rospy.Subscriber(t, Odometry, receive_odom, callback_args=t, queue_size=100)
                    for t in (PROP, ODOM)]
    subscribers += [rospy.Subscriber(TRUTH, ModelStates, receive_truth, queue_size=100),
                    rospy.Subscriber(STATE, State, lambda m: append(STATE, armed=m.armed), queue_size=100),
                    rospy.Subscriber(CLOCK, Clock, lambda m: append(CLOCK, clock=m.clock.to_nsec()), queue_size=100)]
    while time.monotonic() - started < seconds and not state['stop'] and not rospy.is_shutdown():
        time.sleep(.05)
    elapsed = time.monotonic() - started
    with lock:
        state['accept'] = False
        raw.close()
    for sub in subscribers:
        sub.unregister()
    result = summarize(rows, seconds, mode, elapsed, state['errors'])
    (output / 'timing_summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'mode': mode, 'complete': result['measurement_complete'],
                      'rtf': result['clock']['overall_rtf'], 'output': str(output)}), flush=True)
    return 0 if result['measurement_complete'] else 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--mode', choices=('static', 'hover', 'nav'), required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 3600:
        parser.error('seconds must be finite and between 1 and 3600')
    return collect(args.output, args.seconds, args.mode)


if __name__ == '__main__':
    raise SystemExit(main())
