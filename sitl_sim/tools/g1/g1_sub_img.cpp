// G1 arm-3: roscpp long-lived subscriber of sensor_msgs/Image (large payload,
// isomorphic to vins image stream). Prints GOT per frame.
#include <ros/ros.h>
#include <sensor_msgs/Image.h>
#include <cstdio>
int main(int argc, char** argv) {
  ros::init(argc, argv, "g1_sub_img");
  ros::NodeHandle nh;
  ros::Subscriber sub = nh.subscribe<sensor_msgs::Image>("/g1/img", 2,
    [](const sensor_msgs::Image::ConstPtr& m) {
      fprintf(stdout, "GOT %u\n", m->header.stamp.sec); fflush(stdout);
    }, ros::VoidConstPtr(), ros::TransportHints().tcpNoDelay());
  ros::spin();
  return 0;
}
