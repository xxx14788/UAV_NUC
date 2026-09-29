// T1-G1 minimal reproducer: long-lived roscpp subscriber (px4ctrl-isomorphic,
// tcpNoDelay, queue 10). Prints one line per received message to stdout.
// Build (manual, outside catkin):
//   g++ -std=c++14 t1_g1_repro_sub.cpp -o /tmp/g1_sub -I/opt/ros/noetic/include \
//     -L/opt/ros/noetic/lib -lroscpp -lroscpp_serialization -lrosconsole \
//     -lrosconsole_log4cxx -llog4cxx -lroscpp_serialization -lrostime -lcpp_common \
//     -lroslib -lrospack -ltinyxml2 -lboost_system -lboost_thread -lboost_filesystem
#include <ros/ros.h>
#include <std_msgs/String.h>
#include <cstdio>
int main(int argc, char** argv) {
  ros::init(argc, argv, "g1_sub");
  ros::NodeHandle nh;
  ros::SubscribeOptions ops;
  auto cb = [](const std_msgs::String::ConstPtr& m) {
    fprintf(stdout, "GOT %s\n", m->data.c_str());
    fflush(stdout);
  };
  ros::TransportHints th = ros::TransportHints().tcpNoDelay();
  ros::Subscriber sub = nh.subscribe<std_msgs::String>("/g1/test", 10, cb, ros::VoidConstPtr(), th);
  ros::spin();
  return 0;
}
