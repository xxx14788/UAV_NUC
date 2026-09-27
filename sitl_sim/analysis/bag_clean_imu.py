#!/usr/bin/env python3
"""bag IMU 流净化重写（T2-W3 E14b，H-D 裁决的对照实验工具）。

背景: 2026-09-26 崩溃 bag 实测 /mavros/imu/data 有 20.3% 重复 stamp +
4.3% 倒退（-4~-8ms），VINS getIMUInterval 假定队列单调、预积分对 dt 异常
敏感（"numerical unstable" 现场）。本工具把指定 IMU 话题重写为严格单调递增
流（丢重复、丢倒退），其余话题原样拷贝 → 重放对比 ATE 即可裁决 H-D。

用法: python3 bag_clean_imu.py <in.bag> <out.bag> [--imu-topic T（可多次）]
输出: 终端统计（原始/净化后帧数、丢弃数、丢弃率）。
依赖: ROS Noetic python3 (rosbag)
"""
import argparse

import rosbag


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inbag")
    ap.add_argument("outbag")
    ap.add_argument("--imu-topic", action="append", default=[
        "/mavros/imu/data_raw", "/mavros/imu/data"])
    args = ap.parse_args()

    last = {t: None for t in args.imu_topic}
    kept = {t: 0 for t in args.imu_topic}
    dropped = {t: 0 for t in args.imu_topic}
    other = 0
    with rosbag.Bag(args.inbag, "r") as bi, \
            rosbag.Bag(args.outbag, "w") as bo:
        for topic, msg, t in bi.read_messages(raw=True):
            if topic in last:
                ts = msg.header.stamp if hasattr(msg, "header") else None
                sec = ts.to_sec() if ts else t.to_sec()
                if last[topic] is not None and sec <= last[topic]:
                    dropped[topic] += 1
                    continue
                last[topic] = sec
                kept[topic] += 1
            else:
                other += 1
            bo.write(topic, msg, t, raw=True)

    print("=" * 60)
    print(f"净化完成: {args.outbag}")
    for t in args.imu_topic:
        tot = kept[t] + dropped[t]
        rate = 100.0 * dropped[t] / max(tot, 1)
        print(f"  {t}: 保留 {kept[t]} / {tot}（丢弃 {dropped[t]}，{rate:.2f}%）")
    print(f"  其余话题消息: {other}")
    print("=" * 60)


if __name__ == "__main__":
    main()
