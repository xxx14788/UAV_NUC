#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成受控正样本单测(T3 v8.7 池件②;判读器 v1.1 PASS-CONTROLLED 路径+L1b 反例)。
v1.3 扩展(2026-10-04;T3 v9.3 单元1):任一门拦截三夹具——
  SYN_LEG    : legacy fire@50(早于onset)+jump@52 起点标记+健康复流/恢复
               → 期望 state=controlled, verdict=PASS-CONTROLLED(035509 同型)
  SYN_FALSE  : legacy fire@50+零事故证据(无jump/无diag/健康流)
               → 期望 state=uncontrolled-fail(§2.6-h 误触发处置,裁定②"误触发不算")
  SYN_LEG_A1 : legacy fire@49.212+触发前 diag Bas=3.17(真实性面ii)+odom 流止于触发点
               → 期望 state=triggered-no-recovery(A1 正型:真触发+无恢复)
判读走 wa_gate --online --skip-forensics(合成件无 forensics,smj=None→cf_smj_ok=True)。"""
import os
import math
import subprocess
import sys

BASE = os.path.expanduser("~/sitl_sim/t3_results/x11_dryrun_v11")

try:
    import rosbag
    import rospy
    from nav_msgs.msg import Odometry
    from gazebo_msgs.msg import ModelStates
    from geometry_msgs.msg import Pose, Point, Quaternion
except ImportError:
    sys.exit("need ROS env: source /opt/ros/noetic/setup.bash")


def make_bag(path, fire_t, jump_t=None, t_end=130.0):
    """odom 10Hz t=40..t_end;truth=odom+0.02m 级噪声;jump_t 处 odom 单帧跳 1.0m(起点标记)。"""
    if os.path.exists(path):
        return
    with rosbag.Bag(path, 'w') as b:
        t = 40.0
        while t <= t_end:
            # 健康轨迹: 缓慢圆弧
            x, y, z = 0.5 * math.sin(0.05 * (t - 40)), 0.3 * (t - 40) / 90.0, 0.75
            if jump_t is not None and abs(t - jump_t) < 0.05:
                y += 1.0  # 单帧 1.0m 跳=起点标记(>0.5 口径)
            odo = Odometry()
            odo.pose.pose.position = Point(x, y, z)
            b.write('/vins_estimator/odometry', odo, rospy.Time(t))
            ms = ModelStates()
            ms.name = ['iris_stereo_vins']
            p = Pose()
            p.position = Point(x + 0.01, y + 0.02 * math.sin(t), z + 0.01)
            ms.pose = [p]
            b.write('/gazebo/model_states', ms, rospy.Time(t))
            t += 0.1


def make_run(name, fire_t, jump_t):
    d = os.path.join(BASE, name)
    os.makedirs(d, exist_ok=True)
    make_bag(os.path.join(d, 'flight.bag'), fire_t, jump_t)
    with open(os.path.join(d, 'simvins.log'), 'w') as f:
        f.write("[33m[WARN] [1790880000.000000000, %.3f000000]: "
                "cost gate: streak=5 over 10.0x short-window median, reboot[0m\n" % fire_t)
    with open(os.path.join(d, 'round.log'), 'w') as f:
        f.write("[00:00:01] SITL up (sitl_world_obstacles)\n")
    with open(os.path.join(d, 'RESULT.txt'), 'w') as f:
        f.write("anchor(goal+5s窗): (1.000, 0.980, 0.100) | 帧稳定性 |pre-post|=0.083 m\n")
        f.write("leg1 到位(真值) min=0.312 m (<0.75,场景门 world=sitl_world_obstacles)->1 "
                "| leg1(VINS自报) min=0.401 m\n")
        f.write("避障 min_dist=1.530 m (>0.349)->1\n")
        f.write("poscmd 98.0 Hz (>=50)->1\n")
        f.write("auto_disarm->1\n")
        f.write("RESULT=PASS  (证据: synthetic)\n")
    return d


def make_leg_run(name, fire_t, jump_t=None, t_end=130.0, diag_bas=None):
    """v1.3 legacy 触发夹具:failure detection! 行(±可选触发前 diag 偏置行)。"""
    d = os.path.join(BASE, name)
    os.makedirs(d, exist_ok=True)
    make_bag(os.path.join(d, 'flight.bag'), fire_t, jump_t, t_end)
    with open(os.path.join(d, 'simvins.log'), 'w') as f:
        if diag_bas is not None:
            f.write("[T2diag] t=%.4f P=[0.0 0.0 0.1] V=[0.0 0.0 0.0] |Bas|=%.6f "
                    "|Bgs|=0.1486274 Bas=[-0.4 -0.6 -1.8] Bgs=[-0.1 0.05 0.1] "
                    "tic0=[0.0 0.0] track=120\n" % (fire_t - 0.048, diag_bas))
        f.write("[33m[WARN] [1790880000.000000000, %.3f000000]: failure detection![0m\n"
                % fire_t)
    with open(os.path.join(d, 'round.log'), 'w') as f:
        f.write("[00:00:01] SITL up (sitl_world_obstacles)\n")
    with open(os.path.join(d, 'RESULT.txt'), 'w') as f:
        f.write("anchor(goal+5s窗): (1.000, 0.980, 0.100) | 帧稳定性 |pre-post|=0.083 m\n")
        f.write("leg1 到位(真值) min=0.312 m (<0.75,场景门 world=sitl_world_obstacles)->1 "
                "| leg1(VINS自报) min=0.401 m\n")
        f.write("避障 min_dist=1.530 m (>0.349)->1\n")
        f.write("poscmd 98.0 Hz (>=50)->1\n")
        f.write("auto_disarm->1\n")
        f.write("RESULT=PASS  (证据: synthetic)\n")
    return d


if __name__ == '__main__':
    a = make_run('SYN_CTRL', 50.0, None)
    b_ = make_run('SYN_LATE', 100.0, 50.0)
    # v1.3 任一门三夹具
    c = make_leg_run('SYN_LEG', 50.0, jump_t=52.0)                    # 真触发(onset面)→controlled
    e = make_leg_run('SYN_FALSE', 50.0)                               # 零证据→误触发处置
    f_ = make_leg_run('SYN_LEG_A1', 49.212, t_end=49.3, diag_bas=3.172506)  # diag面真触发+流死→TNR
    for d in (a, b_, c, e, f_):
        r = subprocess.run([sys.executable,
                            os.path.expanduser('~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py'),
                            '--online', '--skip-forensics', d],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:])
    import json
    want = (('SYN_CTRL', ('controlled', 'PASS-CONTROLLED')),
            ('SYN_LATE', ('triggered-no-recovery', 'FAIL')),
            ('SYN_LEG', ('controlled', 'PASS-CONTROLLED')),
            ('SYN_FALSE', ('uncontrolled-fail', 'FAIL')),
            ('SYN_LEG_A1', ('triggered-no-recovery', 'FAIL')))
    fails = 0
    for n, w in want:
        j = json.load(open(os.path.join(BASE, n, 'wa_gate_online.json')))
        cf, x = j['controlled'], j['xline']
        got = (cf['state'], j['verdict'])
        ok = got == w
        fails += 0 if ok else 1
        print('%s: state=%s verdict=%s counting=%s l1b=%s onset=%s real=%s(%s) trig=%s@%s -> %s'
              % (n, cf['state'], j['verdict'], x['counting_pass'], cf['l1b_pass'],
                 cf['onset_t'], cf['trig_real'], cf['real_face'],
                 cf['trig_first_kind'], cf['trig_first_t'],
                 'MATCH' if ok else 'MISMATCH-EXPECT-%s' % (w,)))
    print('SYN battery: %s (%d/%d)' % ('ALL-GREEN' if fails == 0 else 'FAIL', len(want)-fails, len(want)))
    sys.exit(0 if fails == 0 else 1)
