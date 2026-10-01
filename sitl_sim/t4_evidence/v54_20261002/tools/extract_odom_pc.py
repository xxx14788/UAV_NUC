#!/usr/bin/env python3
# t4_v54 tool: read-only extraction from 7 existing jr3_replay_* features.bag
# - /vins_estimator/odometry   (nav_msgs/Odometry, t=header.stamp, world/world per data_dictionary.md SS2)
#     -> <name>_odom.csv: t,px,py,pz,qx,qy,qz,qw
# - /vins_estimator/point_cloud (sensor_msgs/PointCloud, geometry_msgs/Point32 list, t=header.stamp)
#     -> <name>_pc.csv: t,n_points
# No bag is modified; output CSVs go to /tmp/t4_v54_tools/out/.
import csv
import json
import os
import rosbag

BAGS = ["U3PG_210307", "U3PO_211438", "U3PR2_213717",
        "WC2OBS1_030927", "WC2OBS1_032005",
        "X1img_015950", "X1img2_020706"]
BASE = os.path.expanduser("~/sitl_sim/vision_inputs")
OUT = "/tmp/t4_v54_tools/out"
T_ODOM = "/vins_estimator/odometry"
T_PC = "/vins_estimator/point_cloud"


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = []
    for name in BAGS:
        path = os.path.join(BASE, "jr3_replay_" + name, "features.bag")
        bag = rosbag.Bag(path)
        t0 = bag.get_start_time()
        t1 = bag.get_end_time()
        n_odom = 0
        n_pc = 0
        other = {}
        odom_bad_frame = 0
        pc_bad_frame = 0
        odom_probe = None
        pc_probe = None
        first_odom_t = last_odom_t = None
        first_pc_t = last_pc_t = None
        odom_path = os.path.join(OUT, "jr3_replay_%s_odom.csv" % name)
        pc_path = os.path.join(OUT, "jr3_replay_%s_pc.csv" % name)
        f_odom = open(odom_path, "w", newline="")
        f_pc = open(pc_path, "w", newline="")
        w_odom = csv.writer(f_odom)
        w_pc = csv.writer(f_pc)
        w_odom.writerow(["t", "px", "py", "pz", "qx", "qy", "qz", "qw"])
        w_pc.writerow(["t", "n_points"])
        for topic, msg, ts in bag.read_messages():
            if topic == T_ODOM:
                st = msg.header.stamp.to_sec()
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                w_odom.writerow([repr(st), repr(p.x), repr(p.y), repr(p.z),
                                 repr(q.x), repr(q.y), repr(q.z), repr(q.w)])
                if n_odom == 0:
                    odom_probe = {
                        "type": getattr(msg, "_type", None),
                        "frame_id": msg.header.frame_id,
                        "child_frame_id": msg.child_frame_id,
                    }
                if msg.header.frame_id != "world" or msg.child_frame_id != "world":
                    odom_bad_frame += 1
                if first_odom_t is None:
                    first_odom_t = st
                last_odom_t = st
                n_odom += 1
            elif topic == T_PC:
                st = msg.header.stamp.to_sec()
                w_pc.writerow([repr(st), len(msg.points)])
                if n_pc == 0:
                    pc_probe = {
                        "type": getattr(msg, "_type", None),
                        "frame_id": msg.header.frame_id,
                        "first_msg_n_points": len(msg.points),
                        "point_class": (type(msg.points[0]).__name__
                                        if msg.points else None),
                    }
                if msg.header.frame_id != "world":
                    pc_bad_frame += 1
                if first_pc_t is None:
                    first_pc_t = st
                last_pc_t = st
                n_pc += 1
            else:
                other[topic] = other.get(topic, 0) + 1
        f_odom.close()
        f_pc.close()
        bag.close()
        rec = {
            "name": name,
            "bag": path,
            "bag_duration_s": round(t1 - t0, 6),
            "bag_start": t0,
            "bag_end": t1,
            "n_odom": n_odom,
            "n_pc": n_pc,
            "n_other_msgs": sum(other.values()),
            "other_topics": other,
            "odom_frame_mismatch": odom_bad_frame,
            "pc_frame_mismatch": pc_bad_frame,
            "odom_probe": odom_probe,
            "pc_probe": pc_probe,
            "first_odom_t": first_odom_t,
            "last_odom_t": last_odom_t,
            "first_pc_t": first_pc_t,
            "last_pc_t": last_pc_t,
            "odom_csv": odom_path,
            "pc_csv": pc_path,
        }
        summary.append(rec)
        print("DONE %s odom=%d pc=%d other=%d span=%.3f..%.3f" % (
            name, n_odom, n_pc, sum(other.values()), t0, t1), flush=True)
    with open(os.path.join(OUT, "extract_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print("ALL_DONE")


if __name__ == "__main__":
    main()
