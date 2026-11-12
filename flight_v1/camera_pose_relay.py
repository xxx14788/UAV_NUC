#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry


def main():
    rospy.init_node("planner_camera_pose_relay")
    pub = rospy.Publisher("/planner/camera_pose", PoseStamped, queue_size=10)

    def callback(msg):
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose
        pub.publish(pose)

    rospy.Subscriber("/vins_estimator/camera_pose", Odometry, callback, queue_size=10)
    rospy.loginfo("Relaying VINS T_world_cam0 to /planner/camera_pose")
    rospy.spin()


if __name__ == "__main__":
    main()
