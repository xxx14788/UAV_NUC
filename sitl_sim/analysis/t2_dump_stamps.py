#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump bag 各话题首/尾帧 stamp,裁决跨域"""
import sys
import rosbag

bag_path = sys.argv[1]
bag = rosbag.Bag(bag_path, "r")
seen = {}
for topic, msg, t in bag.read_messages():
    if topic in seen:
        continue
    hs = None
    if hasattr(msg, "header") and msg.header.stamp.to_sec() > 0:
        hs = msg.header.stamp.to_sec()
    seen[topic] = (hs, t.to_sec())
for topic in sorted(seen):
    hs, arrival = seen[topic]
    print("%-45s hdr=%s arrival=%.3f" % (topic, ("%.3f" % hs) if hs else "NONE", arrival))
bag.close()
