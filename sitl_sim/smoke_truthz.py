#!/usr/bin/env python3
# smoke_truthz.py — H-4b fix: read iris_stereo_vins z from /gazebo/model_states
# BY MODEL NAME (the never-flew gate's old `rostopic echo pose[0]` read
# ground_plane, which is models[0] in every gazebo world -> z==0.0 always ->
# every round since 04:2x false-killed at 37s; F3B3/F3B4 truth z max was
# actually 0.93/0.95m). Prints one float or NA.
import rospy
from gazebo_msgs.msg import ModelStates

MODEL = 'iris_stereo_vins'

rospy.init_node('smoke_truthz', anonymous=True, disable_signals=True)
got = {}


def cb(m):
    if MODEL in m.name:
        got['z'] = m.pose[m.name.index(MODEL)].position.z


rospy.Subscriber('/gazebo/model_states', ModelStates, cb, queue_size=1)
rate = rospy.Rate(20)
deadline = rospy.Time.now().to_sec() + 5.0
while 'z' not in got and rospy.Time.now().to_sec() < deadline and not rospy.is_shutdown():
    rate.sleep()
print('%.4f' % got['z'] if 'z' in got else 'NA')
