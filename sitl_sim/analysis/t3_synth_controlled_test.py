#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成受控正样本单测(T3 v8.7 池件②;判读器 v1.1 PASS-CONTROLLED 路径+L1b 反例)。
构造两个合成 run 目录(真 rosbag flight.bag+手写 simvins.log/RESULT.txt):
  SYN_CTRL   : t=50 cost 门触发,odom 流全程 10Hz 健康(毒窗后复流≥50,误差 p95≪0.5),
               无起点标记 → 期望 state=controlled, verdict=PASS-CONTROLLED
  SYN_LATE   : t=50 袋侧爆窗起点(1.0m 帧跳),cost 门 t=100 才触发(迟触发>onset+5s),
               其余健康 → 期望 state=triggered-no-recovery(L1b 面,§2.6-g)
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


def make_bag(path, fire_t, jump_t=None):
    """odom 10Hz t=40..130;truth=odom+0.02m 级噪声;jump_t 处 odom 单帧跳 1.0m(起点标记)。"""
    if os.path.exists(path):
        return
    with rosbag.Bag(path, 'w') as b:
        t = 40.0
        while t <= 130.0:
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


if __name__ == '__main__':
    a = make_run('SYN_CTRL', 50.0, None)
    b_ = make_run('SYN_LATE', 100.0, 50.0)
    for d in (a, b_):
        r = subprocess.run([sys.executable,
                            os.path.expanduser('~/catkin_ws/sitl_sim/analysis/t3_wa_gate.py'),
                            '--online', '--skip-forensics', d],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:])
    import json
    for n, want in (('SYN_CTRL', ('controlled', 'PASS-CONTROLLED')),
                    ('SYN_LATE', ('triggered-no-recovery', 'FAIL'))):
        j = json.load(open(os.path.join(BASE, n, 'wa_gate_online.json')))
        c, x = j['controlled'], j['xline']
        got = (c['state'], j['verdict'])
        ok = got == want
        print('%s: state=%s verdict=%s counting=%s l1b=%s onset=%s -> %s'
              % (n, c['state'], j['verdict'], x['counting_pass'], c['l1b_pass'],
                 c['onset_t'], 'MATCH' if ok else 'MISMATCH-EXPECT-%s' % (want,)))
