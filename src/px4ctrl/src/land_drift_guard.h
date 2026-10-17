#ifndef __LAND_DRIFT_GUARD_H
#define __LAND_DRIFT_GUARD_H

#include <Eigen/Dense>
#include <cmath>
#include <algorithm>

/*******************************************************
 * C3-v88 (2026-10-17): landing-episode perception drift guard.
 *
 * Root cause (tuning_v82/runaway_root_cause.md, frame-level): during
 * AUTO_LAND near-ground the VINS z drifts negative at ~0.5 m/s sustained
 * (P3 bag: 0.2 -> -49m; per-frame jumps ~0.03m << max_jump 0.6 = every
 * frame-level gate blind), FSM bounces re-anchor hover targets to the
 * drifting odom (chase link S4) and the growing error runs the vehicle
 * away (S5, physical z_max 95m).
 *
 * This guard clamps the perceived pose into a tube anchored at AUTO_LAND
 * entry -- CLAMP, NOT REJECT (rejection would re-create the setpoint-gap
 * bounce S3). Single interception in Odom_Data_t::feed (after the P1
 * rebirth check, before store): FSM targets, controller feedback and the
 * land detector all see the clamped perception. Wall-contact frames zero
 * the poisoned axis velocity (the drift's -0.49 m/s vz would otherwise
 * keep a 0.74 m/s^2 climb command alive through the Kv term).
 *
 * Rung ladder (red-42 single-variable; preregistration =
 * tuning_v82/fix_design_prereg_v88.md):
 *   B1 tube clamp + wall velocity zeroing (live rung)
 *   B2 near-ground re-anchor xy freeze      (config-gated, default OFF)
 *   B3 near-ground descent speed cap        (config-gated, default OFF)
 *   A  drift alarm -> HOLD-freeze + HAFIX blind-land handover (default OFF)
 *      alarm threshold 0.40m = hover-band upper 0.2m x margin 2.
 * Defaults (enabled=false) keep legacy behavior bit-exact; the real-machine
 * yaml carries no key = OFF there (red-40: sim-domain fix, no auto deploy).
 *******************************************************/

struct LandGuardConfig
{
  bool enabled = false;        // master switch (SITL yaml only)
  double z_floor = -0.10;      // absolute floor: ground plane + odom z noise margin
  double z_down_extra = 1.20;  // relative down travel from anchor
  double z_up = 0.30;          // relative up travel from anchor (0.2m hover band + margin)
  double xy_cap = 1.50;        // per-axis horizontal tube half-width
  double alarm_thresh = 0.40;  // A-rung excursion latch threshold
  double alarm_sustain = 1.0;  // A-rung sustained seconds above threshold
  bool rung_b2_land_xy_freeze = false;
  bool rung_b3_descent_cap = false;
  double b3_cap_mps = 0.35;
  bool rung_a_drift_hold = false;
};

struct LandGuardState
{
  bool active = false;
  Eigen::Vector3d anchor = Eigen::Vector3d::Zero();
  double episode_t0 = 0.0;
  long frames = 0;
  long clamped = 0;
  double excursion_max = 0.0;
  double over_since = -1.0;
  bool alarm = false;          // latch crossing reported this frame
  bool alarm_latched = false;  // sticky until episode end
};

// Per-frame clamp. t = arrival clock seconds. Outputs which axis group hit a wall.
inline Eigen::Vector3d land_guard_clamp(const LandGuardConfig &cfg,
                                        LandGuardState &st,
                                        const Eigen::Vector3d &p_raw,
                                        double t,
                                        bool &z_clamped, bool &xy_clamped)
{
  z_clamped = false;
  xy_clamped = false;
  if (!cfg.enabled || !st.active)
    return p_raw;
  st.frames++;

  Eigen::Vector3d p = p_raw;
  const double zlo = std::max(cfg.z_floor, st.anchor(2) - cfg.z_down_extra);
  const double zhi = st.anchor(2) + cfg.z_up;
  if (p(2) < zlo) { p(2) = zlo; z_clamped = true; }
  else if (p(2) > zhi) { p(2) = zhi; z_clamped = true; }
  for (int i = 0; i < 2; ++i)
  {
    const double lo = st.anchor(i) - cfg.xy_cap;
    const double hi = st.anchor(i) + cfg.xy_cap;
    if (p(i) < lo) { p(i) = lo; xy_clamped = true; }
    else if (p(i) > hi) { p(i) = hi; xy_clamped = true; }
  }
  if (z_clamped || xy_clamped)
    st.clamped++;

  const double exc = (p_raw - p).norm();
  if (exc > st.excursion_max)
    st.excursion_max = exc;
  if (exc > cfg.alarm_thresh)
  {
    if (st.over_since < 0.0)
      st.over_since = t;
    if (!st.alarm_latched && (t - st.over_since) >= cfg.alarm_sustain)
    {
      st.alarm = true;
      st.alarm_latched = true;
    }
  }
  else
  {
    st.over_since = -1.0;
  }
  return p;
}

// B2: freeze re-anchor xy to the episode anchor (z keeps clamped perception).
// Cuts the horizontal target ratchet at FSM bounces (link S4-xy).
inline void land_guard_b2_freeze_xy(const LandGuardConfig &cfg,
                                    const LandGuardState &st,
                                    Eigen::Vector3d &hover_p)
{
  if (!cfg.enabled || !cfg.rung_b2_land_xy_freeze || !st.active)
    return;
  hover_p(0) = st.anchor(0);
  hover_p(1) = st.anchor(1);
}

// B3: near-ground descent cap, target-continuous: capped target never below
// the engage-point descent line (gentler final approach, no target jump).
inline double land_guard_b3_target_z(double target_z_uncapped,
                                     double z_engage, double t_engage,
                                     double t_now, double cap_mps)
{
  const double line = z_engage - cap_mps * (t_now - t_engage);
  return std::max(target_z_uncapped, line);
}

inline void land_guard_begin(LandGuardState &st, const Eigen::Vector3d &anchor, double t)
{
  st.active = true;
  st.anchor = anchor;
  st.episode_t0 = t;
  st.frames = 0;
  st.clamped = 0;
  st.excursion_max = 0.0;
  st.over_since = -1.0;
  st.alarm = false;
  st.alarm_latched = false;
}

inline void land_guard_end(LandGuardState &st)
{
  st.active = false;
}

#endif  // __LAND_DRIFT_GUARD_H
