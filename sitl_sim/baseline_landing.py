#!/usr/bin/env python3
"""Report takeoff/landing evidence without judging a nonexistent hover goal."""
import json
import sys
from collections import deque


def main():
    import rosbag
    z_tail = deque(maxlen=50)
    z_max = None
    armed = []
    with rosbag.Bag(sys.argv[1]) as bag:
        for topic, msg, _ in bag.read_messages(topics=['/gazebo/model_states', '/mavros/state']):
            if topic == '/mavros/state':
                armed.append(msg.armed)
            elif 'iris_stereo_vins' in msg.name:
                z = msg.pose[msg.name.index('iris_stereo_vins')].position.z
                z_tail.append(z)
                z_max = z if z_max is None else max(z, z_max)
    z_end = sum(z_tail) / len(z_tail) if z_tail else None
    result = {'z_max_m': z_max, 'z_end_m': z_end, 'truth_tail_count': len(z_tail),
              'armed_seen': any(armed), 'disarmed_at_end': not armed[-1] if armed else None,
              'takeoff_observed': z_max is not None and z_max > .3 and any(armed),
              'landed': z_end is not None and z_end < .15 and len(z_tail) == 50}
    print(json.dumps(result, indent=2))
    return 0 if result['takeoff_observed'] and result['landed'] and result['disarmed_at_end'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
