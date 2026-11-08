#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看最新回传轨迹与真实占据（未膨胀）的关系：最近距离 / 穿障点数。"""
import math
import sys, time
import rospy
import sensor_msgs.point_cloud2 as pc2
from nav_msgs.msg import Path
from sensor_msgs.msg import PointCloud2

occ = {"pts": None}
path = {"m": None}


def main():
    rospy.init_node("path_clearance_check", anonymous=True, disable_signals=True)
    rospy.Subscriber("/drone_0_ego_planner_node/grid_map/occupancy", PointCloud2,
                     lambda m: occ.__setitem__("pts", list(pc2.read_points(m, field_names=("x", "y", "z"), skip_nans=True))[:200000]), queue_size=2)
    rospy.Subscriber("/flight_v1/planned_path", Path, lambda m: path.__setitem__("m", m), queue_size=2)
    t0 = time.time()
    while time.time() - t0 < 6 and (occ["pts"] is None or path["m"] is None):
        rospy.sleep(0.2)
    if not occ["pts"] or not path["m"]:
        print("!! 没拿到 occupancy 或路径"); return 2
    pts = occ["pts"]
    seg = path["m"].poses
    # 只检查航线中段（首尾贴近自身气泡/目标）
    mid = [p.pose.position for p in seg]
    best = 1e9
    inside = 0
    cell = 0.075  # 认为落在同一体素内即"穿障"
    for q in mid:
        for p in pts:
            d = math.sqrt((p[0]-q.x)**2 + (p[1]-q.y)**2 + (p[2]-q.z)**2)
            if d < best:
                best = d
            if d <= cell:
                inside += 1
                break
    print("占据点 %d，路径点 %d，路径到最近占据体素中心 = %.3f m，落体素内点数 = %d"
          % (len(pts), len(mid), best, inside))
    ok = inside == 0 and best > 0.15
    print("==== 净空 %s ====" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
