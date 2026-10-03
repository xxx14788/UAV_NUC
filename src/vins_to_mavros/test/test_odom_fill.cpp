#include <gtest/gtest.h>

#include <cmath>
#include <string>

#include <vins_to_mavros/odom_fill.h>

using vins_to_mavros::PubMode;
using vins_to_mavros::fill_odom_msg;
using vins_to_mavros::parse_pub_mode;
using vins_to_mavros::rotate_world_to_body;

namespace
{
const double EPS = 1e-9;

geometry_msgs::Quaternion yawQuat(double deg)
{
  const double half = deg * M_PI / 180.0 * 0.5;
  geometry_msgs::Quaternion q;
  q.x = 0.0;
  q.y = 0.0;
  q.z = std::sin(half);
  q.w = std::cos(half);
  return q;
}
}  // namespace

TEST(ParsePubMode, LegacyDefault)
{
  bool fell = true;
  EXPECT_EQ(PubMode::POSE, parse_pub_mode("pose", &fell));
  EXPECT_FALSE(fell);
  EXPECT_EQ(PubMode::ODOM, parse_pub_mode("odom", &fell));
  EXPECT_FALSE(fell);
}

TEST(ParsePubMode, GarbageFallsBackToPose)
{
  bool fell = false;
  EXPECT_EQ(PubMode::POSE, parse_pub_mode("Odometry", &fell));
  EXPECT_TRUE(fell);
  EXPECT_EQ(PubMode::POSE, parse_pub_mode("", &fell));
  EXPECT_TRUE(fell);
}

TEST(RotateWorldToBody, IdentityPassthrough)
{
  double x = 1.5, y = -2.0, z = 0.25;
  rotate_world_to_body(x, y, z, 0.0, 0.0, 0.0, 1.0);
  EXPECT_NEAR(1.5, x, EPS);
  EXPECT_NEAR(-2.0, y, EPS);
  EXPECT_NEAR(0.25, z, EPS);
}

TEST(RotateWorldToBody, Yaw90WorldXToBodyNegY)
{
  // body yawed +90 deg w.r.t. world: world +x == body -y
  double x = 1.0, y = 0.0, z = 0.0;
  const geometry_msgs::Quaternion q = yawQuat(90.0);
  rotate_world_to_body(x, y, z, q.x, q.y, q.z, q.w);
  EXPECT_NEAR(0.0, x, EPS);
  EXPECT_NEAR(-1.0, y, EPS);
  EXPECT_NEAR(0.0, z, EPS);
}

TEST(RotateWorldToBody, RoundTrip)
{
  // rotate then rotate back with conjugate must return original
  double x0 = 0.37, y0 = -1.2, z0 = 2.4;
  double x = x0, y = y0, z = z0;
  const double qx = 0.183, qy = -0.316, qz = 0.268;
  const double qw = std::sqrt(std::max(0.0, 1.0 - (qx * qx + qy * qy + qz * qz)));
  rotate_world_to_body(x, y, z, qx, qy, qz, qw);
  rotate_world_to_body(x, y, z, -qx, -qy, -qz, qw);
  EXPECT_NEAR(x0, x, EPS);
  EXPECT_NEAR(y0, y, EPS);
  EXPECT_NEAR(z0, z, EPS);
}

TEST(FillOdomMsg, FieldMappingAndTwistRotation)
{
  nav_msgs::Odometry vins;
  vins.header.stamp = ros::Time(123.456);
  vins.pose.pose.position.x = 1.0;
  vins.pose.pose.position.y = 2.0;
  vins.pose.pose.position.z = 3.0;
  vins.pose.pose.orientation = yawQuat(90.0);
  vins.twist.twist.linear.x = 1.0;  // world-frame velocity +x
  vins.twist.twist.linear.y = 0.0;
  vins.twist.twist.linear.z = 0.0;

  nav_msgs::Odometry out;
  fill_odom_msg(vins, out);

  EXPECT_EQ(123.456, out.header.stamp.toSec());
  EXPECT_STREQ("map", out.header.frame_id.c_str());
  EXPECT_STREQ("base_link", out.child_frame_id.c_str());
  EXPECT_NEAR(1.0, out.pose.pose.position.x, EPS);
  EXPECT_NEAR(2.0, out.pose.pose.position.y, EPS);
  EXPECT_NEAR(3.0, out.pose.pose.position.z, EPS);
  // world +x under body-yaw-90 -> body -y
  EXPECT_NEAR(0.0, out.twist.twist.linear.x, EPS);
  EXPECT_NEAR(-1.0, out.twist.twist.linear.y, EPS);
  EXPECT_NEAR(0.0, out.twist.twist.linear.z, EPS);
  // covariance stays zero (parameter-driven noise face)
  for (int i = 0; i < 36; ++i)
  {
    EXPECT_EQ(0.0, out.pose.covariance[i]);
    EXPECT_EQ(0.0, out.twist.covariance[i]);
  }
}

TEST(FillOdomMsg, OutputIsCleanSlate)
{
  // out pre-filled with junk must be fully overwritten (no stale fields)
  nav_msgs::Odometry vins;
  vins.pose.pose.orientation.w = 1.0;
  nav_msgs::Odometry out;
  out.child_frame_id = "junk";
  out.twist.twist.angular.z = 9.9;
  out.pose.covariance[0] = 5.0;
  fill_odom_msg(vins, out);
  EXPECT_STREQ("base_link", out.child_frame_id.c_str());
  EXPECT_EQ(0.0, out.twist.twist.angular.z);
  EXPECT_EQ(0.0, out.pose.covariance[0]);
}


TEST(PubThrottle, OffIsPassthrough)
{
  vins_to_mavros::PubThrottle th;
  th.configure(0.0);
  for (int i = 0; i < 100; ++i)
    EXPECT_TRUE(th.allow(1.0 + i * 0.005));
}

TEST(PubThrottle, RateTenOnFiftyHzStream)
{
  vins_to_mavros::PubThrottle th;
  th.configure(10.0);
  int passed = 0;
  double t = 100.0;
  for (int i = 0; i < 500; ++i, t += 0.02)
    if (th.allow(t))
      ++passed;
  EXPECT_GE(passed, 98);
  EXPECT_LE(passed, 102);
}

TEST(PubThrottle, FirstFrameAlwaysPasses)
{
  vins_to_mavros::PubThrottle th;
  th.configure(30.0);
  EXPECT_TRUE(th.allow(55.0));
  EXPECT_FALSE(th.allow(55.01));
  EXPECT_TRUE(th.allow(55.04));
}

TEST(PubThrottle, ReconfigureResets)
{
  vins_to_mavros::PubThrottle th;
  th.configure(10.0);
  EXPECT_TRUE(th.allow(1.0));
  EXPECT_FALSE(th.allow(1.05));
  th.configure(0.0);
  EXPECT_TRUE(th.allow(1.05));
}

int main(int argc, char** argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
