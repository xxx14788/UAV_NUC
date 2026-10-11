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
import subprocess
import sys

import rospy
from geometry_msgs.msg import PoseStamped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--topic', default='/move_base_simple/goal')
    ap.add_argument('--thresh', type=float, default=1e4)
    ap.add_argument('--snap-publishers', action='store_true',
                    help='v1.1 L2a: 污染帧在场时拍 rostopic info publishers 快照(发布者定位)')
    args = ap.parse_args()

    state = {'n': 0, 'polluted': 0, 'first_done': False, 'snapped': False}

    def snap_publishers(t, seq):
        # 污染帧在场时拍 publishers 面(L2a 定位; 每轮一次)
        # v1.2: rostopic info 非交互空输出坑→改 rosgraph MasterApi.getSystemState
        # 直取 topic→publishers 节点映射(零 subprocess)
        out = {'type': 'publishers_snap', 't': t, 'seq': seq}
        try:
            import rosgraph
            m = rosgraph.Master(rosgraph.get_master_uri())
            code, _, syst = m.getSystemState()
            # v1.3: 防御性解析(实测 'too many values to unpack' 形态)
            pubs, subs = [], []
            for item in syst[0]:
                if item and item[0] == args.topic:
                    pubs = list(item[1]) if len(item) >= 2 else []
            for item in syst[1]:
                if item and item[0] == args.topic:
                    subs = list(item[1]) if len(item) >= 2 else []
            out['system_state_publishers'] = pubs
            out['system_state_subscribers'] = subs
        except Exception as e:
            out['rosgraph_error'] = repr(e)
        # v1.3: rostopic 进程命令行快照(节点 /rostopic_<pid>_* → args 定位谁在发)
        try:
            ps = subprocess.run(['bash', '-c', 'pgrep -a rostopic || true'],
                                capture_output=True, text=True, timeout=5).stdout
            out['rostopic_procs'] = [l.strip() for l in ps.splitlines() if l.strip()]
        except Exception as e:
            out['rostopic_procs_error'] = repr(e)
        try:
            nodes = subprocess.run(
                ['rosnode', 'list'], capture_output=True, text=True,
                timeout=6).stdout
            out['nodes'] = nodes.split()
        except Exception as e:
            out['nodes_error'] = repr(e)
        # v1.4: TCP 连接层取证——监听器(subscriber)的每个 publisher 连接对端
        # 在 /proc/net 级可见:ss -tnp 全快照(发布者必与订阅端口有 ESTABLISHED 连接)
        try:
            ss = subprocess.run(['bash', '-c', 'ss -tnp 2>/dev/null || true'],
                                capture_output=True, text=True, timeout=5).stdout
            out['tcp_conns'] = [l.strip() for l in ss.splitlines()
                                if l.strip() and 'ESTAB' in l][:60]
        except Exception as e:
            out['tcp_conns_error'] = repr(e)
        try:
            with open(args.out, 'a') as f:
                f.write(json.dumps(out) + '\n')
        except Exception:
            pass

    def cb(msg):
        state['n'] += 1
        p = msg.pose.position
        bad = max(abs(p.x), abs(p.y), abs(p.z)) > args.thresh
        if bad:
            state['polluted'] += 1
            if args.snap_publishers and not state['snapped']:
                state['snapped'] = True
                snap_publishers(rospy.get_time(), msg.header.seq)
        if bad or not state['first_done']:
            state['first_done'] = True
            try:
                ch = getattr(msg, '_connection_header', {}) or {}
                with open(args.out, 'a') as f:
                    f.write(json.dumps({
                        'type': 'polluted' if bad else 'first',
                        't': rospy.get_time(),
                        'seq': msg.header.seq,
                        'callerid': ch.get('callerid', 'NA'),
                        'latching': ch.get('latching', 'NA'),
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
