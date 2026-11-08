#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录包收尾审计：关键话题到底有没有录到（2026-11-08）。

只读 bag 索引，很快。判据按"有没有数据"，不按帧率（起飞前有些话题本来就该是空的）。
退出码：0 全有；1 有关键话题缺数据。
"""
import os
import sys

# 话题 -> 至少几条才算"录到了"
CRITICAL = {
    "/camera/depth/image_rect_raw": 10,
    "/vins_estimator/imu_propagate": 10,
    "/debugPx4ctrl": 10,
    "/position_cmd": 10,          # 只有规划器真发轨迹才有；没有=这轮没飞成
    "/drone_0_planning/bspline": 1,
    "/flight_v1/planned_path": 1,
    "/flight_v1/goal_gate": 1,
    "/drone_0_ego_planner_node/grid_map/occupancy_inflate": 1,   # P1-6：离线判目标是否在膨胀层
}


def main():
    if len(sys.argv) < 2:
        print("用法: record_audit.py <bag>")
        return 2
    bag = sys.argv[1]
    try:
        import rosbag
        with rosbag.Bag(bag) as b:
            topics = b.get_type_and_topic_info().topics
            counts = {k: v.message_count for k, v in topics.items()}
    except Exception as exc:
        print("AUDIT: 读不了索引 %r" % (exc,))
        return 2
    missing = []
    rows = []
    for t, need in CRITICAL.items():
        n = counts.get(t, 0)
        ok = n >= need
        rows.append("%-42s %8d %s" % (t, n, "OK" if ok else "缺"))
        if not ok:
            missing.append(t)
    print("== 录包审计 %s（共 %d 个话题）" % (os.path.basename(bag), len(counts)))
    for r in rows:
        print("   " + r)
    if missing:
        print("!! 关键话题没录到：%s" % ", ".join(missing))
        print("!! 这轮若真飞了，说明录制链路有问题，别拿这袋下结论。")
        return 1
    print("== 审计通过：关键话题都在")
    return 0


if __name__ == "__main__":
    sys.exit(main())
