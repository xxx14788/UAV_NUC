#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U4 bag 拼接: 按 stamp 时间轴顺延拼接两个 bag(A|D 旋转韧性实验用)。

b1 原样保留; b2 的所有消息 stamp(与 bag 到达时间)整体平移, 使 b2 首帧
排在 b1 末帧 + gap 之后。两 bag 须各自域内一致(b2 若跨域先跑 shift 工具)。
输出共同话题并集(b1 有 b2 无或反之的话题: 只保留 b1 段的, 忽略 b2 独有——
拼接语义以 b1 为基座)。

用法: python3 t2_bag_concat.py <b1.bag> <b2.bag> <out.bag> [--gap 0.5]
"""
import argparse

import rosbag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("b1")
    ap.add_argument("b2")
    ap.add_argument("out")
    ap.add_argument("--gap", type=float, default=0.5)
    a = ap.parse_args()

    with rosbag.Bag(a.b1, "r") as b1, rosbag.Bag(a.b2, "r") as b2:
        t1s, t1e = b1.get_start_time(), b1.get_end_time()
        t2s = b2.get_start_time()
        topics1 = set(b1.get_type_and_topic_info().topics)
        topics2 = set(b2.get_type_and_topic_info().topics)
        common = topics1 & topics2
        print("b1 [%.2f, %.2f] 话题%d; b2 起点 %.2f 话题%d; 共同 %d" %
              (t1s, t1e, len(topics1), t2s, len(topics2), len(common)))
        off = t2s - (t1e + a.gap)
        print("b2 平移 %+.3f s(全部 stamp 与到达时间)" % -off)

        n1 = n2 = 0
        with rosbag.Bag(a.out, "w") as bo:
            for tp, m, t in b1.read_messages(topics=list(common)):
                bo.write(tp, m, t)
                n1 += 1
            for tp, m, t in b2.read_messages(topics=list(common)):
                if hasattr(m, "header"):
                    m.header.stamp = rospy_Time_rel(m.header.stamp, -off)
                bo.write(tp, m, t.from_sec(t.to_sec() - off))
                n2 += 1
    print("写出 b1=%d + b2=%d 条 → %s" % (n1, n2, a.out))


def rospy_Time_rel(stamp, delta):
    import rospy
    return rospy.Time(stamp.to_sec() + delta)


if __name__ == "__main__":
    main()
