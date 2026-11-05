#include <gtest/gtest.h>
#include <ros/time.h>
#include <nav_msgs/Odometry.h>
#include "input.h"

// F-1 (2026-10-22 判读v5) gtest: REINIT_RESET 毒化锁存的 choke point 回归——
// feed() 首行拒收（msg/rcv_stamp 保持末好帧→新鲜度走既有超时路径=断流语义，
// 与 T1-D2 同构）；解毒（disarm 流程）后恢复接收。
// 锁存置位/清除/交还的状态机时序在 PX4CtrlFSM.cpp STEP0.6（ROS 回调依赖，
// 由静态审查+呈裁后飞行验证计划覆盖；本测只锚定数据面语义不漂移）。

TEST(ReinitReset, PoisonedFeedRejectsAndKeepsLastGood)
{
  ros::Time::init();
  Odom_Data_t odom;
  nav_msgs::Odometry msg;
  msg.pose.pose.position.x = 1.0;
  msg.pose.pose.position.y = 0.0;
  msg.pose.pose.position.z = 0.5;
  odom.feed(nav_msgs::OdometryConstPtr(new nav_msgs::Odometry(msg)));
  EXPECT_TRUE(odom.recv_new_msg);      // 基线：正常接收
  EXPECT_DOUBLE_EQ(odom.p(0), 1.0);
  ros::Time stamp_before = odom.rcv_stamp;

  odom.recv_new_msg = false;
  odom.poisoned = true;                // F-1: VINS 空中重初始化毒化
  nav_msgs::Odometry msg2;
  msg2.pose.pose.position.x = 99.0;    // 重锚后的新世界帧（大跳变值）
  msg2.pose.pose.position.y = -50.0;
  msg2.pose.pose.position.z = 2.0;
  odom.feed(nav_msgs::OdometryConstPtr(new nav_msgs::Odometry(msg2)));
  EXPECT_FALSE(odom.recv_new_msg);     // 拒收：无新帧
  EXPECT_DOUBLE_EQ(odom.p(0), 1.0);    // 状态保持末好帧
  EXPECT_DOUBLE_EQ(odom.p(1), 0.0);
  EXPECT_EQ(odom.rcv_stamp.toSec(), stamp_before.toSec()); // 新鲜度不被毒帧续命

  odom.poisoned = false;               // disarm 清毒后恢复接收
  odom.feed(nav_msgs::OdometryConstPtr(new nav_msgs::Odometry(msg2)));
  EXPECT_TRUE(odom.recv_new_msg);
  EXPECT_DOUBLE_EQ(odom.p(0), 99.0);
}

int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
