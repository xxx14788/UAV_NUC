import os
import rosbag
p = os.path.expanduser("~/sitl_sim/vision_inputs/jr3_replay_U3PG_210307/features.bag")
bag = rosbag.Bag(p)
n = 0
for topic, msg, ts in bag.read_messages(topics=["/vins_estimator/point_cloud"]):
    if len(msg.points) > 0:
        print("type=%s frame=%s stamp=%.9f n_points=%d point0_class=%s n_channels=%d" % (
            msg._type, msg.header.frame_id, msg.header.stamp.to_sec(), len(msg.points),
            type(msg.points[0]).__name__, len(msg.channels)))
        n += 1
        if n >= 2:
            break
bag.close()
