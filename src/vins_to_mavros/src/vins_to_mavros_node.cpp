#include <ros/ros.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseStamped.h>

ros::Publisher pose_pub;

void vins_callback(const nav_msgs::Odometry::ConstPtr& msg)
{
    geometry_msgs::PoseStamped pose;

    pose.header.stamp = msg->header.stamp;
    pose.header.frame_id = "map";

    // 直接转发位姿
    pose.pose.position.x = msg->pose.pose.position.x;
    pose.pose.position.y = msg->pose.pose.position.y;
    pose.pose.position.z = msg->pose.pose.position.z;

    pose.pose.orientation.x = msg->pose.pose.orientation.x;
    pose.pose.orientation.y = msg->pose.pose.orientation.y;
    pose.pose.orientation.z = msg->pose.pose.orientation.z;
    pose.pose.orientation.w = msg->pose.pose.orientation.w;

    pose_pub.publish(pose);
}

int main(int argc, char** argv)
{
    ros::init(argc, argv, "vins_to_mavros");
    ros::NodeHandle nh;

    // 订阅 VINS-Fusion 的里程计输出
    ros::Subscriber vins_sub = nh.subscribe("/vins_estimator/odometry", 10, vins_callback);

    // 发布到 MAVROS 的视觉位姿输入
    pose_pub = nh.advertise<geometry_msgs::PoseStamped>("/mavros/vision_pose/pose", 10);

    ROS_INFO("vins_to_mavros bridge started");
    ros::spin();
    return 0;
}
