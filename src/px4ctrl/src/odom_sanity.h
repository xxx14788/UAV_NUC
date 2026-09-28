#ifndef __ODOM_SANITY_H
#define __ODOM_SANITY_H

#include <Eigen/Dense>

/*******************************************************
 * T1-D2 (2026-09-29): odom VALUE-sanity gate (flyaway line of defense).
 *
 * Forensics (route7 t2v3_route_215016.bag + X1 explosion rounds 232055/
 * 235025/001817): during VINS transient divergence the odometry stays FRESH
 * but insane -- v_mean ramps 0.3 -> 9 -> 25+ m/s, inter-frame position jumps
 * reach 5-66 m, position runs to 1e6 m -- while px4ctrl's only health check
 * is freshness (PX4CtrlFSM::odom_is_received). X1_232055: px4ctrl stayed in
 * CMD_CTRL following garbage for 68 s (truth parked at origin, odom at
 * 1000 m); route7: armed the whole time, truth flown 18 m away.
 *
 * Gate semantics: violating frames are REJECTED inside Odom_Data_t::feed.
 * State (msg/rcv_stamp/p/v/q/w) keeps the last ACCEPTED frame, so a stream
 * of garbage is indistinguishable from a real dropout once msg_timeout.odom
 * expires -- the EXISTING degradation path (AUTO_HOVER -> MANUAL_CTRL) fires
 * unchanged. No new behavior class; armed-disconnect behavior untouched.
 *
 * Thresholds calibrated against measured envelopes:
 *   healthy chain:  v_max 1.2-1.35 m/s, frame jump <= 0.05 m (hover/salvage)
 *   explosion ramp: jump 0.2-1.6 m, v_mean 1.4-9 m/s (10-20 s before peak)
 *   explosion peak: jump 5-66 m, v_mean 25+ m/s
 * Default OFF = exact legacy behavior (real-machine yaml carries no key).
 *******************************************************/

struct OdomSanityConfig
{
  bool enabled = false;    // default OFF = legacy (real-machine yaml has no key)
  double max_vel = 5.0;    // m/s, magnitude cap (mission envelope ~2 + margin)
  double max_acc = 10.0;   // m/s^2, frame-to-frame dv/dt cap
  double max_jump = 1.0;   // m, frame-to-frame position jump cap
  double reboot_dt = 1.0;  // s, gap >= this skips continuity checks (stale ref)
  int warn_every = 50;     // rate-limit for rejection warnings
};

struct OdomSanityState
{
  bool has_ref = false;
  Eigen::Vector3d last_p = Eigen::Vector3d::Zero();
  Eigen::Vector3d last_v = Eigen::Vector3d::Zero();
  double last_t = 0.0;
  long accepted = 0;
  long rejected = 0;
};

enum class OdomSanityVerdict
{
  ACCEPT = 0,
  REJECT_VEL = 1,
  REJECT_ACC = 2,
  REJECT_JUMP = 3,
  REJECT_NAN = 4
};

inline OdomSanityVerdict odom_sanity_check(const OdomSanityConfig &cfg, OdomSanityState &st,
                                           double t, const Eigen::Vector3d &p, const Eigen::Vector3d &v)
{
  if (!cfg.enabled)
  {
    st.has_ref = true; st.last_p = p; st.last_v = v; st.last_t = t;
    st.accepted++;
    return OdomSanityVerdict::ACCEPT;
  }
  if (!p.allFinite() || !v.allFinite())
  {
    st.rejected++;
    return OdomSanityVerdict::REJECT_NAN;
  }
  if (v.norm() > cfg.max_vel)
  {
    st.rejected++;
    return OdomSanityVerdict::REJECT_VEL;
  }
  if (st.has_ref && t > st.last_t)
  {
    double dt = t - st.last_t;
    if (dt < cfg.reboot_dt)
    {
      if ((p - st.last_p).norm() > cfg.max_jump)
      {
        st.rejected++;
        return OdomSanityVerdict::REJECT_JUMP;
      }
      if ((v - st.last_v).norm() / dt > cfg.max_acc)
      {
        st.rejected++;
        return OdomSanityVerdict::REJECT_ACC;
      }
    }
  }
  // accepted: refresh the reference (a single violating frame never poisons it)
  st.has_ref = true; st.last_p = p; st.last_v = v; st.last_t = t;
  st.accepted++;
  return OdomSanityVerdict::ACCEPT;
}

#endif
