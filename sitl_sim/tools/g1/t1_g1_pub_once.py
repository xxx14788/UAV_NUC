#!/usr/bin/env python3
# T1-G1 reproducer: fresh publisher process per round (new node = new
# negotiation dice, isomorphic to U3's rostopic-pub / vins-restart shape).
import sys, time
import rospy
from std_msgs.msg import String
rid = sys.argv[1]
rospy.init_node('g1_pub_%s' % rid, anonymous=True)
p = rospy.Publisher('/g1/test', String, queue_size=5)
# wait for sub connection per rospy convention (advertise+sleep)
time.sleep(0.6)
for i in range(20):
    if rospy.is_shutdown(): break
    p.publish(String(data='r%s_%d' % (rid, i)))
    time.sleep(0.05)
time.sleep(0.2)
