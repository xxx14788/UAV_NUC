#ifndef VINS_TO_MAVROS_ODOM_FILL_H
#define VINS_TO_MAVROS_ODOM_FILL_H
// T1 E-5a (2026-10-03): L-odom publish arm support.
// vins_to_mavros publishes EITHER PoseStamped (L-pose, legacy) OR
// nav_msgs/Odometry (L-odom, adds twist) — mutually exclusive to prevent
// double-feeding EKF2 EV. Default pub_mode="pose" = legacy bit-behavior.

#include <string>

#include <nav_msgs/Odometry.h>

namespace vins_to_mavros
{

enum class PubMode
{
  POSE = 0,
  ODOM = 1
};

// "odom" -> ODOM; "pose" and anything else -> POSE (fallback, legacy-safe).
inline PubMode parse_pub_mode(const std::string& s, bool* fell_back = nullptr)
{
  if (fell_back)
    *fell_back = false;
  if (s == "odom")
    return PubMode::ODOM;
  if (s != "pose" && fell_back)
    *fell_back = true;
  return PubMode::POSE;
}

// v_body = R(q)^{-1} v_world = R(q_bar) v_world, q = body-to-world unit
// quaternion (x,y,z,w), q_bar = conjugate. Conjugate rotation equals the
// active-rotation formula with the cross terms' 2w(u x v) part negated:
//   v' = v - 2w(u x v) + 2u x (u x v),  u = (qx,qy,qz)
inline void rotate_world_to_body(double& x, double& y, double& z,
                                 double qx, double qy, double qz, double qw)
{
  const double tx = 2.0 * (qy * z - qz * y);
  const double ty = 2.0 * (qz * x - qx * z);
  const double tz = 2.0 * (qx * y - qy * x);
  const double rx = x - qw * tx + (qy * tz - qz * ty);
  const double ry = y - qw * ty + (qz * tx - qx * tz);
  const double rz = z - qw * tz + (qx * ty - qy * tx);
  x = rx;
  y = ry;
  z = rz;
}

// Fill the L-odom output from a VINS odometry msg.
// VINS twist is WORLD-frame (estimator Vs state); mavros /mavros/odometry/out
// expects twist in child_frame_id (body). Pose passes through unchanged.
// Covariances stay zero: PX4 EKF2 EV noise is parameter-driven (EKF2_EV_*_NSE)
// and zero-cov ODOMETRY keeps that path — same noise face as the L-pose arm.
inline void fill_odom_msg(const nav_msgs::Odometry& vins, nav_msgs::Odometry& out)
{
  out = nav_msgs::Odometry();
  out.header = vins.header;
  out.header.frame_id = "odom";      // U2.5 fix (2026-10-04): mavros odom plugin looks up TF
                                      // <odom_parent_id_des>_ned <- header.frame_id; "map" has no path to
                                      // odom_ned (two unconnected static trees) => ConnectivityException every
                                      // frame + uninitialized Eigen::Affine3d poisons pose (R3: 285 Ex lines,
                                      // J1 0.783 const-offset). "odom" reaches odom->odom_ned static TF =>
                                      // correct ENU->NED, same transform family as L-pose hardcoded path.
  out.child_frame_id = "base_link";  // twist frame = body FLU; mavros converts to FRD
  out.pose = vins.pose;
  double vx = vins.twist.twist.linear.x;
  double vy = vins.twist.twist.linear.y;
  double vz = vins.twist.twist.linear.z;
  const geometry_msgs::Quaternion& q = vins.pose.pose.orientation;
  rotate_world_to_body(vx, vy, vz, q.x, q.y, q.z, q.w);
  out.twist.twist.linear.x = vx;
  out.twist.twist.linear.y = vy;
  out.twist.twist.linear.z = vz;
}

// T1 E-4 (2026-10-03): EV supply-density face (D30/D60).
// pub_source: "odometry" (legacy 10Hz input) | "imu_prop" (223Hz high-rate input)
// pub_rate_hz: 0 = no throttle (bit-identical); >0 = min publish interval gate.
// Throttle sits AFTER the shared health gates (gates protect both arms and
// every rate) and stamps on header.stamp (sim domain, monotone per stream).
struct PubThrottle
{
  double rate_hz = 0.0;   // 0 = off
  double min_dt = 0.0;    // 1/rate, computed on set
  bool have_last = false;
  double last_pub_t = 0.0;

  void configure(double hz)
  {
    rate_hz = hz;
    min_dt = (hz > 0.0) ? (1.0 / hz) : 0.0;
    have_last = false;
    last_pub_t = 0.0;
  }

  // true = this frame may pass
  inline bool allow(double stamp)
  {
    if (rate_hz <= 0.0)
      return true;
    if (have_last && (stamp - last_pub_t) < min_dt - 1e-6)
      return false;
    have_last = true;
    last_pub_t = stamp;
    return true;
  }
};

}  // namespace vins_to_mavros

#endif  // VINS_TO_MAVROS_ODOM_FILL_H
