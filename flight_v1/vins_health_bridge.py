#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vins_health_bridge.py — 把 VINS 日志里的健康量发成 ROS 话题，进录包。

背景（2026-11-15）：VINS 日志的 T2diag 每帧已经打印 track/|Bas|/|Bgs|，T2slv 打印
final_cost/iters；但这些只在 NUC 的 log 文件里，bag 里没有，事后判读要靠"找日志"。
本节点 tail 最新的 vins_*.log，以 2 Hz 发 /vins_estimator/health（std_msgs/String）：
    "t=<sim时间> track=<特征数> bas=<|Bas|> bgs=<|Bgs|> cost=<final_cost> iters=<n> log=<文件名>"

不改 VINS 本体（避免重建估计器），只做只读解析。
"""
import glob
import os
import re
import time

import rospy
from std_msgs.msg import String

HOME = os.path.expanduser("~")
PATTERNS = [
    os.path.join(HOME, "sitl_realmachine", "vins_*.log"),
    os.path.join(HOME, "sitl_realmachine", "*", "vins_*.log"),
]
FRESH_S = 900.0          # 只认 15 分钟内还在写的日志（活日志每帧都写）
TAIL_BYTES = 65536
RE_DIAG = re.compile(r"\[T2diag\] t=([0-9.]+).*?\|Bas\|=([0-9.eE+-]+).*?\|Bgs\|=([0-9.eE+-]+).*?track=([0-9]+)")
RE_SLV = re.compile(r"\[T2slv\] t=([0-9.]+).*?final_cost=([0-9.eE+-]+).*?iters=([0-9]+)")


def newest_log():
    files = []
    for p in PATTERNS:
        files.extend(glob.glob(p))
    files = [f for f in files if os.path.getmtime(f) > time.time() - FRESH_S]
    return max(files, key=os.path.getmtime) if files else None


def tail_lines(path, nbytes=TAIL_BYTES):
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - nbytes))
        data = fh.read().decode("utf-8", "replace")
    return data.splitlines()


def parse(lines):
    diag = slv = None
    for ln in lines:
        m = RE_DIAG.search(ln)
        if m:
            diag = m
        m2 = RE_SLV.search(ln)
        if m2:
            slv = m2
    if not diag:
        return None
    s = "t=%s track=%s bas=%s bgs=%s" % (diag.group(1), diag.group(4), diag.group(2), diag.group(3))
    if slv:
        s += " cost=%s iters=%s" % (slv.group(2), slv.group(3))
    return s


def main():
    rospy.init_node("vins_health_bridge", anonymous=True)
    pub = rospy.Publisher("/vins_estimator/health", String, queue_size=10)
    rate = rospy.Rate(2.0)
    cur_path, cur_mtime = None, 0.0
    last_msg = None
    while not rospy.is_shutdown():
        # 日志按"最新且新鲜"选；VINS 重启会换文件，这里自动跟随
        if cur_path is None or not os.path.isfile(cur_path) or (time.time() - cur_mtime) > 5.0:
            p = newest_log()
            if p and p != cur_path:
                cur_path = p
                rospy.loginfo("vins_health_bridge: follow %s", p)
        if cur_path:
            try:
                cur_mtime = os.path.getmtime(cur_path)
                body = parse(tail_lines(cur_path))
                if body:
                    msg = String()
                    msg.data = "%s log=%s" % (body, os.path.basename(cur_path))
                    if msg.data != last_msg:
                        pub.publish(msg)
                        last_msg = msg.data
            except OSError:
                cur_path = None
        rate.sleep()


if __name__ == "__main__":
    main()
