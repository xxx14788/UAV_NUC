#!/usr/bin/env python3
# t1_landing_line.py — 早退收束路径 LANDING 行补算器（2026-10-11 软件收官册单元5）
# 用法: python3 t1_landing_line.py <flight.bag>
# 机理: round_result.sh L165 的 LANDING 行(z_end=truth 尾 50 帧 iris z 均值<0.15)只在正常
#       收束路径打印;早退路径(STOPLOSS-ABORT/GATE-INTERCEPT/NEVER-FLEW/GOAL-POLLUTION-ABORT)
#       直写 RESULT 退出 → 判读器 t1_rejudge_hafix_v1140.py L102 正则落空 → landed=NA。
#       本工具以同一口径(truth 尾 50 帧 z 均值)从 bag 补算 LANDING 行,供早退路径 append。
# 输出: "LANDING: z_end=X.XXX m (<0.15)->N"（stdout;bag 不可读时输出 NA 行保持记录面存在）
import sys

import rosbag


def main():
    bag_path = sys.argv[1]
    zs = []
    try:
        with rosbag.Bag(bag_path, "r") as b:
            for topic, msg, ts in b.read_messages(topics=["/gazebo/model_states"]):
                try:
                    i = msg.name.index("iris_stereo_vins")
                except ValueError:
                    continue
                zs.append(msg.pose[i].position.z)
    except Exception as e:
        print("LANDING: z_end=NA m (bag unreadable: %s)->NA" % type(e).__name__)
        return 0
    if not zs:
        print("LANDING: z_end=NA m (no truth frames)->NA")
        return 0
    tail = zs[-50:]
    z_end = sum(tail) / len(tail)
    print("LANDING: z_end=%.3f m (<0.15)->%d" % (z_end, 1 if z_end < 0.15 else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
