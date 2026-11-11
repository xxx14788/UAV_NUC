#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录包降频副本（2026-11-11）：定标 15/15/10 Hz。

为什么不用 topic_tools throttle：实测它输入 30 Hz / 目标 15 Hz 只给 11.4-12.8 Hz、
目标 10 只给 8.1 Hz（CPU 仅 1.5%，是它的丢帧相位算法问题）。这里用固定周期定时器：
每个周期如果有新帧就发最新一帧，否则跳过 —— 速率精确 = min(输入, 目标)。

VINS 仍消费原始 30 Hz 流；本节点只服务录包。
"""
import rospy
from sensor_msgs.msg import Image

STREAMS = [
    ("/camera/infra1/image_rect_raw", "/record/infra1", 15.0),
    ("/camera/infra2/image_rect_raw", "/record/infra2", 15.0),
    ("/camera/depth/image_rect_raw", "/record/depth", 10.0),
]


class Throttle(object):
    def __init__(self, src, dst, hz):
        self._msg = None
        self._new = False
        self._pub = rospy.Publisher(dst, Image, queue_size=2)
        rospy.Subscriber(src, Image, self._cb, queue_size=1)
        rospy.Timer(rospy.Duration(1.0 / hz), self._tick)

    def _cb(self, msg):
        self._msg = msg
        self._new = True

    def _tick(self, _evt):
        if self._msg is not None and self._new:
            self._pub.publish(self._msg)
            self._new = False


def main():
    rospy.init_node("record_throttle", anonymous=False, disable_signals=True)
    for src, dst, hz in STREAMS:
        Throttle(src, dst, hz)
        rospy.loginfo("[record_throttle] %s -> %s @ %.0f Hz", src, dst, hz)
    rospy.spin()


if __name__ == "__main__":
    main()
