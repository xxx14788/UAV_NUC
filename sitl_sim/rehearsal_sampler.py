#!/usr/bin/env python3
# rehearsal_sampler.py v1.0 — 1Hz fsm/armed/mode/odom_hz/z 采样器（外置版）
# 由 rehearsal.sh v7 sampler_start() 调用；替代 heredoc 内嵌形态（六轮零输出根因=heredoc python
# 进程组被 ssh 会话吞，坑账在案）。对冲三坑：setsid 脱会话+nohup 忽略 HUP+stdin/stdout/stderr 全重定向。
# 输出：argv[1]=tsv 路径（时序正源，列=ts fsm armed mode odom_hz z）+stdout 每秒摘要行（进 sampler.out，
# 供发射后短窗验证 tail log 有行）。
import sys, rospy, threading, collections, time, datetime
from std_msgs.msg import String
from mavros_msgs.msg import State
from nav_msgs.msg import Odometry

if len(sys.argv) < 2:
    sys.stderr.write("usage: rehearsal_sampler.py <sampler.tsv>\n"); sys.exit(2)

out = open(sys.argv[1], 'a', buffering=1)
st = {'fsm': '', 'armed': None, 'mode': '', 'odom_hz': 0, 'z': None}
lock = threading.Lock()
times = collections.deque()

def on_fsm(m): st['fsm'] = m.data
def on_state(m): st['armed'] = m.armed; st['mode'] = m.mode
def on_odom(m):
    t = time.time(); times.append(t)
    while times and t - times[0] > 2: times.popleft()
    st['odom_hz'] = len(times) / 2.0
    st['z'] = m.pose.pose.position.z

rospy.init_node('rehearsal_sampler', anonymous=True)
rospy.Subscriber('/debugPx4ctrl/fsm_state', String, on_fsm)
rospy.Subscriber('/mavros/state', State, on_state)
rospy.Subscriber('/vins_estimator/imu_propagate', Odometry, on_odom)
r = rospy.Rate(1)
while not rospy.is_shutdown():
    line = "%s\t%s\t%s\t%s\t%.1f\t%s" % (
        datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3],
        st['fsm'], st['armed'], st['mode'], st['odom_hz'],
        '' if st['z'] is None else '%.3f' % st['z'])
    with lock:
        out.write(line + "\n")
    print(line, flush=True)   # stdout 摘要行 → sampler.out（短窗验证面）
    r.sleep()
