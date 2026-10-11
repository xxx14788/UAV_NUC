#!/usr/bin/env python3
# t1_goal_pollution_watch.py — /move_base_simple/goal 全程污染监听（S8P UTM 签名；2026-10-11 任务书单元3）
# 用法: t1_goal_pollution_watch.py --out <EV>/goal_pollution_watch.jsonl \
#        [--topic /move_base_simple/goal] [--thresh 10000]
# 判据: 任一 |coord|>thresh(默认1e4)=UTM 污染签名（TK_S8P_B 实证形态 (642716,5.72e6,0);
#       正常 goal 坐标 ≤1e2 量级,阈值分离≥3 个数量级,无误报面）。
# 记录: 污染帧全量 jsonl 行 {t, seq, x, y, z}+首帧+末帧(采样留痕);
#       退出时写 summary 行 {type: summary, polluted_n, frames_n}。
# 消费: 判读面污染伪影注记（与 TK_S8P_B 剔除条款同口径）+毒域溯源素材（污染帧时序/频率/seq 域）。
import argparse
import json
import sys

import rospy
from geometry_msgs.msg import PoseStamped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--topic', default='/move_base_simple/goal')
    ap.add_argument('--thresh', type=float, default=1e4)
    args = ap.parse_args()

    state = {'n': 0, 'polluted': 0, 'first_done': False}

    def cb(msg):
        state['n'] += 1
        p = msg.pose.position
        bad = max(abs(p.x), abs(p.y), abs(p.z)) > args.thresh
        if bad:
            state['polluted'] += 1
        if bad or not state['first_done']:
            state['first_done'] = True
            try:
                with open(args.out, 'a') as f:
                    f.write(json.dumps({
                        'type': 'polluted' if bad else 'first',
                        't': rospy.get_time(),
                        'seq': msg.header.seq,
                        'x': p.x, 'y': p.y, 'z': p.z}) + '\n')
            except Exception:
                pass

    rospy.init_node('t1_goal_pollution_watch', anonymous=True, disable_signals=True)
    rospy.Subscriber(args.topic, PoseStamped, cb, queue_size=50)
    rospy.on_shutdown(lambda: None)
    try:
        rospy.spin()
    except (KeyboardInterrupt, SystemExit):
        pass
    with open(args.out, 'a') as f:
        f.write(json.dumps({'type': 'summary', 'frames_n': state['n'],
                            'polluted_n': state['polluted']}) + '\n')


if __name__ == '__main__':
    sys.exit(main())
