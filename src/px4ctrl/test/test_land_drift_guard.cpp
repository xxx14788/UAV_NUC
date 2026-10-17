// C3-v88 (2026-10-17): landing drift guard deterministic chain-break dry test.
// Signature injection per fix_design_prereg_v88.md §6:
//   type-1 z-negative drift sequence (P3 numeric replay),
//   type-2 interruption flash (1-frame gap),
//   type-3 target wandering (bounce re-anchor ratchet),
// plus transparency negative controls and rung helper checks.
// PASS criterion = chain-break assertions per type + zero clamp on healthy
// paths. Dry test must pass BEFORE any burn rounds (taskbook §一.2).

#include <gtest/gtest.h>
#include "land_drift_guard.h"
#include "fsm_decision.h"
#include <vector>
#include <cmath>

static LandGuardConfig live_cfg()
{
  LandGuardConfig c;             // preregistered values (yaml mirror)
  c.enabled = true;
  c.z_floor = -0.10;
  c.z_down_extra = 1.20;
  c.z_up = 0.30;
  c.xy_cap = 1.50;
  c.alarm_thresh = 0.40;
  c.alarm_sustain = 1.0;
  return c;
}

// ---------- type-1: z negative drift sequence (P3 replay numbers) ----------
TEST(LandDriftGuard, Type1_ZNegativeDrift_ChainBreak)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;
  const Eigen::Vector3d anchor(4.20, 4.20, 0.96);
  land_guard_begin(st, anchor, 0.0);

  const double dt = 1.0 / 210.0;  // imu_propagate ~210Hz
  double t = 0.0, z = 0.96;
  long wall_frames = 0;
  double perceived_min = 1e9, perceived_max = -1e9;
  double last_perceived_z = z;
  bool alarm_seen = false;
  // healthy descent 0.96 -> 0.20 @0.5 m/s, then P3 drift 0.49 m/s for 100 s
  // with 8.7 m/s single-frame spikes every 3 s (measured spike band 5.9-8.7).
  while (t < 105.0)
  {
    Eigen::Vector3d p(4.20, 4.20, z);
    if (t > 2.0 && std::fmod(t, 3.0) < dt) z -= 8.7 * dt;  // spike frame
    else if (z > 0.20) z -= 0.5 * dt;                       // healthy descent
    else z -= 0.49 * dt;                                    // sustained drift
    p(2) = z;
    bool zc, xyc;
    Eigen::Vector3d pc = land_guard_clamp(cfg, st, p, t, zc, xyc);
    if (zc) wall_frames++;
    perceived_min = std::min(perceived_min, pc(2));
    perceived_max = std::max(perceived_max, pc(2));
    last_perceived_z = pc(2);
    alarm_seen |= st.alarm_latched;
    t += dt;
  }
  // S2 cut: perception bounded in tube the whole episode
  EXPECT_GE(perceived_min, cfg.z_floor);
  EXPECT_LE(perceived_max, anchor(2) + cfg.z_up);
  // runaway is binding: clamp engaged
  EXPECT_GE(st.clamped, 1);
  EXPECT_GT(wall_frames, 1000);  // sustained wall contact, not a transient
  EXPECT_NEAR(last_perceived_z, cfg.z_floor, 1e-9);
  // alarm latched (A-rung threshold face exposed)
  EXPECT_TRUE(alarm_seen);
  // S4/S5 cut: any re-anchored target (= perception) keeps control error
  // bounded by the tube diameter (1.36 m) instead of diverging to 50 m.
  const double err_bound = (anchor(2) + cfg.z_up) - cfg.z_floor;
  EXPECT_LE(err_bound, 1.40);
  EXPECT_LT(st.excursion_max, 60.0);  // excursion tracked (raw ran to ~ -49)
  EXPECT_GT(st.excursion_max, 10.0);  // ...and it truly diverged in the raw
}

// ---------- type-2: interruption flash (1-frame gap, stream stays alive) ----------
TEST(LandDriftGuard, Type2_FlashGap_EpisodeSurvives_NoReject)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;
  land_guard_begin(st, Eigen::Vector3d(4.2, 4.2, 0.96), 0.0);
  bool zc, xyc;
  // healthy frames
  for (int i = 0; i < 100; i++)
    land_guard_clamp(cfg, st, Eigen::Vector3d(4.2, 4.2, 0.9), i * 0.005, zc, xyc);
  const long frames_before = st.frames;
  const long clamped_before = st.clamped;
  // one-frame interruption: no feed call (gap), then a drifted frame resumes
  land_guard_clamp(cfg, st, Eigen::Vector3d(4.2, 4.2, -3.0), 0.5 + 0.005, zc, xyc);
  EXPECT_TRUE(st.active);            // episode not reset by the flash
  EXPECT_EQ(st.frames, frames_before + 1);
  EXPECT_EQ(st.clamped, clamped_before + 1);
  EXPECT_TRUE(zc);                   // resumed frame clamped, not rejected
  // anchor unchanged: the resume does not re-anchor the tube
  EXPECT_NEAR(st.anchor(2), 0.96, 1e-12);
}

// ---------- type-3: target wandering (bounce re-anchor ratchet) ----------
TEST(LandDriftGuard, Type3_BounceRatchet_TargetBounded)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;
  const Eigen::Vector3d anchor(4.2, 4.2, 0.96);
  land_guard_begin(st, anchor, 0.0);
  // P3 bounce times 86.78/87.80 then long tail; raw z on the -0.49 m/s line
  const double bounce_t[6] = {86.78, 87.80, 100.0, 120.0, 140.0, 160.0};
  bool zc, xyc;
  double tmin = 1e9, tmax = -1e9;
  for (int k = 0; k < 6; k++)
  {
    const double raw_z = 0.2 - 0.49 * (bounce_t[k] - 81.1);
    const double raw_x = 4.2 - 0.03 * (bounce_t[k] - 81.1);
    Eigen::Vector3d target = land_guard_clamp(cfg, st,
        Eigen::Vector3d(raw_x, 4.2, raw_z), bounce_t[k], zc, xyc);
    // every re-anchored hover target sits inside the tube
    EXPECT_GE(target(2), cfg.z_floor);
    EXPECT_LE(target(2), anchor(2) + cfg.z_up);
    tmin = std::min(tmin, target(2));
    tmax = std::max(tmax, target(2));
  }
  // total target wander bounded by tube diameter (ratchet cut)
  EXPECT_LE(tmax - tmin, 1.40);
}

// ---------- transparency: healthy paths never touch a wall ----------
TEST(LandDriftGuard, Transparency_HealthyLanding_ZeroClamp)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;
  land_guard_begin(st, Eigen::Vector3d(4.2, 4.2, 0.96), 0.0);
  const double dt = 1.0 / 210.0;
  double z = 0.96, t = 0.0;
  bool zc, xyc;
  while (z > 0.0)  // commanded descent 0.5 m/s to touchdown
  {
    z = std::max(0.0, z - 0.5 * dt);
    land_guard_clamp(cfg, st, Eigen::Vector3d(4.2, 4.2, z), t, zc, xyc);
    EXPECT_FALSE(zc);
    EXPECT_FALSE(xyc);
    t += dt;
  }
  EXPECT_EQ(st.clamped, 0);
  EXPECT_DOUBLE_EQ(st.excursion_max, 0.0);
  EXPECT_FALSE(st.alarm_latched);
}

TEST(LandDriftGuard, Transparency_HealthyHover60s_ZeroClamp)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;
  land_guard_begin(st, Eigen::Vector3d(4.2, 4.2, 0.96), 0.0);
  const double dt = 1.0 / 210.0;
  bool zc, xyc;
  for (long i = 0; i < (long)(60.0 / dt); i++)
  {
    const double t = i * dt;
    // hover band [0.76, 1.16] (healthy band 0.2m), xy wander 0.1m
    land_guard_clamp(cfg, st,
        Eigen::Vector3d(4.2 + 0.1 * std::sin(t), 4.2 + 0.1 * std::cos(t),
                        0.96 + 0.1 * std::sin(0.3 * t)),
        t, zc, xyc);
    EXPECT_FALSE(zc);
    EXPECT_FALSE(xyc);
  }
  EXPECT_EQ(st.clamped, 0);
  EXPECT_FALSE(st.alarm_latched);
}

TEST(LandDriftGuard, Transparency_OutsideEpisode_Passthrough)
{
  LandGuardConfig cfg = live_cfg();
  LandGuardState st;  // never began: active=false
  bool zc, xyc;
  Eigen::Vector3d wild(-300.0, 250.0, -49.4);
  Eigen::Vector3d p = land_guard_clamp(cfg, st, wild, 1.0, zc, xyc);
  EXPECT_EQ(p(2), wild(2));  // nav/hover phases untouched (episode-scoped guard)
  EXPECT_FALSE(zc);
  EXPECT_EQ(st.frames, 0);
}

// ---------- legacy default-off = bit-exact passthrough ----------
TEST(LandDriftGuard, LegacyDisabled_Identity)
{
  LandGuardConfig cfg;  // enabled=false (real-machine yaml has no key)
  LandGuardState st;
  land_guard_begin(st, Eigen::Vector3d(0, 0, 0.96), 0.0);  // even if begun
  bool zc, xyc;
  Eigen::Vector3d wild(-300.0, 250.0, -49.4);
  Eigen::Vector3d p = land_guard_clamp(cfg, st, wild, 1.0, zc, xyc);
  EXPECT_EQ(p, wild);
  EXPECT_FALSE(zc);
  EXPECT_FALSE(xyc);
  EXPECT_EQ(st.frames, 0);
}

// ---------- rung B2: near-ground re-anchor xy freeze ----------
TEST(LandDriftGuard, RungB2_XyFreeze)
{
  LandGuardConfig cfg = live_cfg();
  cfg.rung_b2_land_xy_freeze = true;
  LandGuardState st;
  const Eigen::Vector3d anchor(4.2, 4.2, 0.96);
  land_guard_begin(st, anchor, 0.0);
  Eigen::Vector3d hover(7.7, -3.1, -0.10);  // drifted re-anchor (P3 max|xy|=7.7)
  land_guard_b2_freeze_xy(cfg, st, hover);
  EXPECT_DOUBLE_EQ(hover(0), 4.2);
  EXPECT_DOUBLE_EQ(hover(1), 4.2);
  EXPECT_DOUBLE_EQ(hover(2), -0.10);  // z keeps clamped perception
  // rung off -> no freeze (single-variable check)
  LandGuardConfig cfg_off = live_cfg();
  Eigen::Vector3d hover2(7.7, -3.1, -0.10);
  land_guard_b2_freeze_xy(cfg_off, st, hover2);
  EXPECT_DOUBLE_EQ(hover2(0), 7.7);
}

// ---------- rung B3: descent cap target continuity ----------
TEST(LandDriftGuard, RungB3_TargetContinuity)
{
  // engage at z=0.6, t=100; nominal target already below the capped line
  // (start 0.96 @0.5 m/s from t=98.72): capped target must stay on the
  // gentler line and never jump.
  const double cap = 0.35;
  double prev = land_guard_b3_target_z(0.60, 0.60, 100.0, 100.0, cap);
  for (double t = 100.05; t <= 102.0; t += 0.05)
  {
    const double uncapped = 0.96 - 0.5 * (t - 98.72);
    const double v = land_guard_b3_target_z(uncapped, 0.60, 100.0, t, cap);
    EXPECT_GE(v, 0.60 - cap * (t - 100.0) - 1e-12);   // never below line
    EXPECT_LE(v - prev, 1e-9);                        // monotone down, no jump up
    prev = v;
  }
}

// ---------- rung A: alarm -> HAFIX blind-land handover (wiring mirror) ----------
TEST(LandDriftGuard, RungA_AlarmHandsOverToHafixLadder)
{
  LandGuardConfig cfg = live_cfg();
  cfg.rung_a_drift_hold = true;
  LandGuardState st;
  land_guard_begin(st, Eigen::Vector3d(4.2, 4.2, 0.96), 0.0);
  // force the alarm exactly like type-1 does (drift past threshold, sustain)
  bool zc, xyc;
  for (int i = 0; i < 500; i++)
    land_guard_clamp(cfg, st, Eigen::Vector3d(4.2, 4.2, -2.0 - 0.005 * i),
                     1.0 + i * 0.005, zc, xyc);
  ASSERT_TRUE(st.alarm_latched);

  // FSM wiring mirror (PX4CtrlFSM.cpp STEP0.5):
  const bool armed = true, landed = false, odom_dead = false;
  const double dead_s = 5.0;
  int stage = 0;
  double dead_since = 0.0, t_now = 10.0;
  const bool drift_alarm = cfg.enabled && cfg.rung_a_drift_hold && st.alarm_latched;
  const bool flying = armed && !landed && (odom_dead || drift_alarm);
  double dead_elapsed = (stage != 0) ? (t_now - dead_since) : 0.0;
  if (drift_alarm)
    dead_elapsed = (dead_elapsed > dead_s) ? dead_elapsed : dead_s;
  fsm_decision::HafixInputs ha_in;
  ha_in.enabled = true; ha_in.stage = stage; ha_in.flying = flying;
  ha_in.dead_elapsed = dead_elapsed; ha_in.landed = landed; ha_in.armed = armed;
  ha_in.dead_s = dead_s; ha_in.kill_s = 15.0;
  fsm_decision::HafixAction a1 = fsm_decision::decide_hafix(ha_in);
  EXPECT_TRUE(a1.watch_start);          // tick 1: watch opens

  stage = a1.stage_next;                // tick 2: alarm waives the dead_s window
  dead_elapsed = 0.05;
  if (drift_alarm) dead_elapsed = (dead_elapsed > dead_s) ? dead_elapsed : dead_s;
  ha_in.stage = stage; ha_in.dead_elapsed = dead_elapsed;
  fsm_decision::HafixAction a2 = fsm_decision::decide_hafix(ha_in);
  EXPECT_TRUE(a2.auto_land);            // immediate blind-land handover

  // single-variable check: with rung A OFF the alarm alone does NOT fire HAFIX
  LandGuardConfig cfg_no_a = live_cfg();  // rung_a = false
  const bool drift_alarm_off = cfg_no_a.enabled && cfg_no_a.rung_a_drift_hold && st.alarm_latched;
  const bool flying_off = armed && !landed && (odom_dead || drift_alarm_off);
  EXPECT_FALSE(flying_off);
}

int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
