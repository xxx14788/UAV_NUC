// T1-P2 (v11.4 unit 3): gtest for cmdresp_gate.h + fsm_decision RJ wiring.
// Frozen v1 semantics: eps_static 0.5 m / drift_rate 0.21 m/s / win 10 s.
#include <gtest/gtest.h>

#include "cmdresp_gate.h"
#include "fsm_decision.h"

#include <Eigen/Dense>
#include <cmath>
#include <functional>

namespace
{
Eigen::Vector3d v3(double x, double y, double z) { return Eigen::Vector3d(x, y, z); }

// Feed a synthetic stream at 100 Hz. p_des/v_des hover at the origin by
// default; the odom side follows a scripted trajectory.
struct FeedResult
{
  bool latched = false;
  bool warn_edge = false;
};

FeedResult run_stream(const CmdRespConfig &cfg, CmdRespState &st, double dur_sec,
                      const std::function<Eigen::Vector3d(double)> &p_odom_fn,
                      const std::function<Eigen::Vector3d(double)> &v_odom_fn,
                      const std::function<Eigen::Vector3d(double)> &p_des_fn =
                          [](double) { return v3(0, 0, 0); },
                      const std::function<Eigen::Vector3d(double)> &v_des_fn =
                          [](double) { return v3(0, 0, 0); },
                      double t0 = 100.0)
{
  FeedResult r;
  const double dt = 0.01; // 100 Hz
  for (double t = t0; t < t0 + dur_sec; t += dt)
  {
    bool warn = false;
    r.latched = cmdresp_feed(cfg, st, &warn, t, p_des_fn(t), v_des_fn(t),
                             p_odom_fn(t), v_odom_fn(t));
    if (warn)
      r.warn_edge = true;
  }
  return r;
}
} // namespace

// enabled=false -> exact passthrough, never latches even on gross drift
TEST(CmdRespGate, DisabledPassthrough)
{
  CmdRespConfig cfg; // enabled=false
  CmdRespState st;
  auto r = run_stream(cfg, st, 30.0,
                      [](double t) { return v3(0.3 * (t - 100.0), 0, 0); },
                      [](double) { return v3(0.3, 0, 0); });
  EXPECT_FALSE(r.latched);
  EXPECT_FALSE(st.fired_ever);
}

// window not full (< win_sec) -> no evaluation even for obvious divergence
TEST(CmdRespGate, WindowNotFullNoEval)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  auto r = run_stream(cfg, st, 8.0, // < 10 s win
                      [](double t) { return v3(0.21 * (t - 100.0), 0, 0); },
                      [](double) { return v3(0.21, 0, 0); });
  EXPECT_FALSE(r.latched);
  EXPECT_EQ(st.fired_count, 0);
}

// healthy hover: residual 0.4 m flat (inside 0.48-0.5 healthy band), dv ~ 0.05
TEST(CmdRespGate, HealthyHoverNoFire)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  auto r = run_stream(cfg, st, 40.0,
                      [](double) { return v3(0.4, 0.05, 0.0); },
                      [](double) { return v3(0.02, 0.02, 0.0); });
  EXPECT_FALSE(r.latched);
  EXPECT_FALSE(st.fired_ever);
}

// u3/VR3 event form: des_v=0, odom drifts at constant 0.21 m/s -> residual
// grows to 2.1 m per 10 s > 4*eps (2.0 m); median dv = 0.21 >= threshold.
TEST(CmdRespGate, VR3DriftFires)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  // t starts at 100; drift starts at t=110 after a 10 s calm lead-in
  auto p_fn = [](double t) {
    double dt = std::max(0.0, t - 110.0);
    return v3(0.21 * dt, 0, 0);
  };
  auto v_fn = [](double t) { return t < 110.0 ? v3(0, 0, 0) : v3(0.21, 0, 0); };
  auto r = run_stream(cfg, st, 35.0, p_fn, v_fn);
  EXPECT_TRUE(r.latched);      // fires while drift persists
  EXPECT_TRUE(r.warn_edge);    // rising-edge banner reported
  EXPECT_EQ(st.fired_count, 1);
}

// static overshoot without divergence increment (residual parked at 3 m,
// dv ~ 0): cond_div false -> no fire (anti-false-positive face)
TEST(CmdRespGate, StaticOvershootNoFire)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  auto r = run_stream(cfg, st, 30.0,
                      [](double) { return v3(3.0, 0, 0); },
                      [](double) { return v3(0.01, 0, 0); });
  EXPECT_FALSE(r.latched);
  EXPECT_FALSE(st.fired_ever);
}

// transient velocity spikes only (median dv below threshold, no residual
// divergence) -> no fire
TEST(CmdRespGate, VelocitySpikesNoFire)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  // 1 Hz spikes of 0.5 m/s for 0.2 s each: ~2% of beats, median unaffected
  auto v_fn = [](double t) {
    double ph = std::fmod(t, 1.0);
    return ph < 0.02 ? v3(0.5, 0, 0) : v3(0.02, 0, 0);
  };
  auto r = run_stream(cfg, st, 30.0,
                      [](double t) { return v3(0.1 * std::sin(t), 0, 0); }, v_fn);
  EXPECT_FALSE(r.latched);
}

// recovery: after the drift stops and tracking resumes (dv small, residual
// flat), the latch releases after stable_beats
TEST(CmdRespGate, RecoveryAfterDrift)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  // phase 1: drift 0.21 m/s for 15 s (window fills at ~10 s, fires ~10.1 s)
  {
    auto p_fn = [](double t) { return v3(0.21 * (t - 100.0), 0, 0); };
    auto v_fn = [](double) { return v3(0.21, 0, 0); };
    auto r = run_stream(cfg, st, 15.0, p_fn, v_fn);
    ASSERT_TRUE(r.latched);
  }
  // phase 2: tracking resumes; residual parks at the drifted offset (3.15 m,
  // static overshoot form) -> no divergence increment + dv small -> recover
  double parked = 0.21 * 15.0;
  auto p2 = [parked](double) { return v3(parked, 0, 0); };
  auto v2 = [](double) { return v3(0.01, 0, 0); };
  // stale window initially still holds drift samples: keep feeding 25 s to
  // let the window fully rotate onto calm samples, well past stable_beats
  auto r2 = run_stream(cfg, st, 25.0, p2, v2, [](double) { return v3(0, 0, 0); },
                       [](double) { return v3(0, 0, 0); }, 115.0);
  (void)r2; // feed-only phase; assertions read st directly
  EXPECT_FALSE(st.latched);
}

// clear() resets everything (disarm path)
TEST(CmdRespGate, DisarmClearResets)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  auto p_fn = [](double t) { return v3(0.21 * (t - 100.0), 0, 0); };
  auto v_fn = [](double) { return v3(0.21, 0, 0); };
  auto r = run_stream(cfg, st, 15.0, p_fn, v_fn);
  ASSERT_TRUE(r.latched);
  st.clear();
  EXPECT_FALSE(st.latched);
  EXPECT_EQ(st.count, 0);
  EXPECT_EQ(st.fired_count, 0);
}

// poison beat (NaN) is skipped without corrupting state
TEST(CmdRespGate, PoisonBeatSkipped)
{
  CmdRespConfig cfg;
  cfg.enabled = true;
  CmdRespState st;
  bool warn = false;
  EXPECT_FALSE(cmdresp_feed(cfg, st, &warn, 100.0, v3(0, 0, 0), v3(NAN, 0, 0),
                            v3(0, 0, 0), v3(0, 0, 0)));
  EXPECT_EQ(st.count, 0);
  // healthy beat accepted (feed returns LATCH state = false, not acceptance)
  EXPECT_FALSE(cmdresp_feed(cfg, st, &warn, 101.0, v3(0, 0, 0), v3(0, 0, 0),
                            v3(0.1, 0, 0), v3(0, 0, 0)));
  EXPECT_EQ(st.count, 1);
  // non-monotonic stamp skipped
  EXPECT_FALSE(cmdresp_feed(cfg, st, &warn, 100.5, v3(0, 0, 0), v3(0, 0, 0),
                            v3(0.1, 0, 0), v3(0, 0, 0)));
  EXPECT_EQ(st.count, 1);
}

// ---- fsm_decision RJ_CMDRESP wiring (P1-symmetric) ----

TEST(CmdRespGate, RJBlocksHoverEntry)
{
  fsm_decision::Inputs in; // defaults: enter_hover=false...
  in.enter_hover = true;
  in.odom_ok = true;
  in.cmdresp_divergent = true; // P2 latched
  auto o = fsm_decision::decide_manual(in);
  EXPECT_TRUE(o.reject);
  EXPECT_EQ(o.reason, fsm_decision::RJ_CMDRESP);
}

TEST(CmdRespGate, RJBlocksTakeoff)
{
  fsm_decision::Inputs in;
  in.takeoff_trigger = true;
  in.odom_ok = true;
  in.cmdresp_divergent = true;
  auto o = fsm_decision::decide_manual(in);
  EXPECT_TRUE(o.reject);
  EXPECT_EQ(o.reason, fsm_decision::RJ_CMDRESP);
}

TEST(CmdRespGate, RJIdleWhenNotDivergent)
{
  fsm_decision::Inputs in;
  in.enter_hover = true;
  in.odom_ok = true;
  in.cmdresp_divergent = false;
  auto o = fsm_decision::decide_manual(in);
  EXPECT_FALSE(o.reject);
  EXPECT_EQ(o.next, fsm_decision::AUTO_HOVER);
}

int main(int argc, char **argv)
{
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
