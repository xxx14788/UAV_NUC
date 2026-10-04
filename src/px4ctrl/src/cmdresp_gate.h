#ifndef __CMDRESP_GATE_H
#define __CMDRESP_GATE_H

#include <Eigen/Dense>
#include <algorithm>
#include <array>
#include <cmath>

/*******************************************************
 * T1-P2 (2026-10-05, v11.4 unit 3): command-response
 * divergence gate — 消费侧第三层"清醒度"防线
 * (D2 帧值毒拒 -> P1 rebirth 错位拒 -> P2 指令-响应拒).
 *
 * Forensics (u3_hover_drift_verdict.md, VR3 hover-8.5m event):
 * VINS imu_propagate stream lies smoothly-pinned (des_v = 0
 * while GT drifts at constant 0.21 m/s -> 2.1 m per 10 s;
 * healthy hover des-odom residual band 0.48-0.5 m flat).
 * The odom stream stays FRESH and value-sane, so D2 does not
 * fire; no rebirth, so P1 does not fire. Data "looks healthy"
 * but the vehicle does not follow commands — the only
 * measurable face of birth-lie / actuator-loss / model
 * mismatch classes, which the first two gates cannot cover.
 *
 * Gate semantics (FROZEN v1: eps 0.5 m / drift 0.21 m/s /
 * win 10 s — u3 verdict §32 caliber):
 *   e(t)  = ||p_odom - p_des||      (residual)
 *   dv(t) = ||v_odom - v_des||      (response deficit)
 *   FIRE (AND, fire_beats consecutive beats):
 *     e_now - min(e in win) >= 4*eps_static_m
 *        (frozen: 0.21 m/s * 10 s = 2.1 m > 4*0.5 m)
 *     median(dv in win)    >= drift_rate_mps
 *        (response deficit dominates the window)
 *   RECOVER: stable_beats consecutive beats with either
 *     condition false (D2 recovery semantics).
 *   Samples are fed by the caller only on armed non-MANUAL
 *   beats (call-site discipline); window not full -> no
 *   evaluation, latch state unchanged.
 * Default OFF = exact legacy behavior (real-machine yaml
 * carries no key).
 *
 * Consumed by: PX4CtrlFSM::process (STEP5.5), blocks
 * fsm_decision decide_manual enter_hover / takeoff via
 * RJ_CMDRESP (P1-symmetric wiring). Latched state is
 * published via banner (rate-limited) for upstream gates.
 *******************************************************/

struct CmdRespConfig
{
  bool enabled = false;         // default OFF = legacy
  double win_sec = 10.0;        // frozen: judgment window
  double eps_static_m = 0.5;    // frozen: healthy residual band upper edge
  double drift_rate_mps = 0.21; // frozen: response-deficit velocity threshold
  int fire_beats = 10;          // consecutive satisfying beats to fire (100Hz -> 0.1s)
  int stable_beats = 100;       // consecutive calm beats to recover (100Hz -> 1s)
  int warn_every = 100;         // rate-limit for latched warnings (100Hz -> 1Hz)
};

// Ring capacity: 10 s * 100 Hz + headroom. Fixed array = no
// steady-state allocation (probe-budget discipline).
static constexpr int CMDRESP_WIN_CAP = 1100;

struct CmdRespState
{
  bool latched = false;
  bool fired_ever = false;
  int fire_streak = 0;
  int stable_streak = 0;
  long samples = 0;
  long fired_count = 0;
  long beats_since_warn = 0;
  std::array<double, CMDRESP_WIN_CAP> t{}, e{}, dv{};
  int head = 0;
  int count = 0;

  void clear()
  {
    latched = false;
    fire_streak = stable_streak = 0;
    samples = fired_count = 0;
    beats_since_warn = 0;
    head = count = 0;
  }

  double latest_e() const { return count ? e[(head + CMDRESP_WIN_CAP - 1) % CMDRESP_WIN_CAP] : 0.0; }
};

// Pure evaluation over the time window [t-win_sec, t]. Exposed
// for gtest; the process loop uses cmdresp_feed() below.
inline bool cmdresp_conditions(const CmdRespConfig &cfg, const CmdRespState &st,
                               double now, double &e_min_win, double &dv_med_win)
{
  if (st.count < 2)
    return false;
  double oldest = st.t[st.head];
  if (now - oldest < cfg.win_sec * 0.99)
    return false; // window not full yet -> no evaluation
  // iterate physical order old->new over the ring
  double e_min = 1e18;
  static thread_local std::array<double, CMDRESP_WIN_CAP> dv_win;
  int n = 0;
  for (int k = 0; k < st.count; ++k)
  {
    int idx = (st.head + k) % CMDRESP_WIN_CAP;
    double dt = now - st.t[idx];
    if (dt > cfg.win_sec)
      continue; // aged out (pruning happens in feed; belt&braces)
    e_min = std::min(e_min, st.e[idx]);
    dv_win[n++] = st.dv[idx];
  }
  if (n < 2)
    return false;
  e_min_win = e_min;
  // median of dv over window (nth_element on a linear slice; even n needs
  // max of the lower half because nth_element does not order within halves)
  double *b = dv_win.data();
  std::nth_element(b, b + n / 2, b + n);
  dv_med_win = (n % 2) ? b[n / 2]
                       : 0.5 * (*std::max_element(b, b + n / 2) + b[n / 2]);
  double e_now = st.latest_e();
  bool cond_div = (e_now - e_min) >= 4.0 * cfg.eps_static_m;
  bool cond_resp = dv_med_win >= cfg.drift_rate_mps;
  return cond_div && cond_resp;
}

// Feed one beat (caller: armed non-MANUAL beats only). Returns
// current latch state. Banner decision (rate-limited warn) is
// reported via `warn_now` on the rising edge or every
// warn_every latched beats.
inline bool cmdresp_feed(const CmdRespConfig &cfg, CmdRespState &st, bool *warn_now,
                         double t, const Eigen::Vector3d &p_des, const Eigen::Vector3d &v_des,
                         const Eigen::Vector3d &p_odom, const Eigen::Vector3d &v_odom)
{
  if (warn_now)
    *warn_now = false;
  if (!cfg.enabled)
    return false;
  if (!std::isfinite(t) || !p_des.allFinite() || !v_des.allFinite() ||
      !p_odom.allFinite() || !v_odom.allFinite())
    return st.latched; // poison beat: skip sample, keep state

  // push
  double e = (p_odom - p_des).norm();
  double dv = (v_odom - v_des).norm();
  if (st.count && t <= st.t[(st.head + CMDRESP_WIN_CAP - 1) % CMDRESP_WIN_CAP])
    return st.latched; // non-monotonic stamp: skip
  st.t[st.head] = t;
  st.e[st.head] = e;
  st.dv[st.head] = dv;
  st.head = (st.head + 1) % CMDRESP_WIN_CAP;
  if (st.count < CMDRESP_WIN_CAP)
    ++st.count;
  ++st.samples;
  ++st.beats_since_warn;

  // prune aged samples from the ring head (amortized O(aged))
  while (st.count && (t - st.t[st.head]) > cfg.win_sec)
  {
    st.head = (st.head + 1) % CMDRESP_WIN_CAP;
    --st.count;
  }

  double e_min_win = 0.0, dv_med_win = 0.0;
  bool cond = cmdresp_conditions(cfg, st, t, e_min_win, dv_med_win);
  if (cond)
  {
    ++st.fire_streak;
    st.stable_streak = 0;
    if (!st.latched && st.fire_streak >= cfg.fire_beats)
    {
      st.latched = true;
      st.fired_ever = true;
      ++st.fired_count;
      st.beats_since_warn = 0;
      if (warn_now)
        *warn_now = true;
    }
  }
  else
  {
    ++st.stable_streak;
    st.fire_streak = 0;
    if (st.latched && st.stable_streak >= cfg.stable_beats)
      st.latched = false;
  }
  if (st.latched && st.beats_since_warn >= cfg.warn_every)
  {
    st.beats_since_warn = 0;
    if (warn_now)
      *warn_now = true;
  }
  return st.latched;
}

#endif // __CMDRESP_GATE_H
