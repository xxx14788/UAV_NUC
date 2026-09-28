#include <gtest/gtest.h>
#include <Eigen/Dense>
#include "odom_sanity.h"

// T1-D2 gtest: threshold boundaries / slow-drift not killed / steps killed /
// explosion signature timeline / acceleration gate / reboot window / disabled
// pass-through / NaN defense.

static OdomSanityConfig gate_on()
{
  OdomSanityConfig c;
  c.enabled = true;
  c.max_vel = 5.0;
  c.max_acc = 10.0;
  c.max_jump = 1.0;
  c.reboot_dt = 1.0;
  return c;
}

TEST(OdomSanity, ThresholdBoundaryVel)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  // exactly at threshold: accept (strict >); just above: reject
  EXPECT_EQ(odom_sanity_check(c, st, 1.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d(5.0, 0, 0)),
            OdomSanityVerdict::ACCEPT);
  OdomSanityState st2;
  EXPECT_EQ(odom_sanity_check(c, st2, 1.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d(5.01, 0, 0)),
            OdomSanityVerdict::REJECT_VEL);
}

TEST(OdomSanity, ThresholdBoundaryJump)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  ASSERT_EQ(odom_sanity_check(c, st, 10.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::ACCEPT);
  // 1.0 m in 0.008 s -> exactly at cap: accept
  EXPECT_EQ(odom_sanity_check(c, st, 10.008, Eigen::Vector3d(1.0, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::ACCEPT);
  // 1.1 m jump: reject
  EXPECT_EQ(odom_sanity_check(c, st, 10.016, Eigen::Vector3d(2.1, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::REJECT_JUMP);
}

TEST(OdomSanity, SlowDriftNotKilled)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  // sustained 4.9 m/s cruise with matching position rate (0.0392 m / 8 ms)
  Eigen::Vector3d p(0, 0, 0), v(4.9, 0, 0);
  for (int i = 0; i < 500; i++)
  {
    p += Eigen::Vector3d(4.9 * 0.008, 0, 0);
    ASSERT_EQ(odom_sanity_check(c, st, 10.0 + i * 0.008, p, v), OdomSanityVerdict::ACCEPT)
        << "frame " << i;
  }
  EXPECT_EQ(st.accepted, 500);
  EXPECT_EQ(st.rejected, 0);
}

TEST(OdomSanity, AccGateKillsSpike)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  ASSERT_EQ(odom_sanity_check(c, st, 10.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::ACCEPT);
  // dv=0.2 m/s in 8 ms = 25 m/s^2 > 10 (position consistent, jump small)
  EXPECT_EQ(odom_sanity_check(c, st, 10.008, Eigen::Vector3d(0.002, 0, 0), Eigen::Vector3d(0.2, 0, 0)),
            OdomSanityVerdict::REJECT_ACC);
}

TEST(OdomSanity, ExplosionSignatureTimeline)
{
  // replay of the measured ramp (route7/X1): healthy 0.3 -> ramp -> 25 m/s.
  // Gate must engage during the ramp, then keep rejecting (frozen reference).
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  Eigen::Vector3d p(0, 0, 0);
  double t = 0.0;
  // healthy hover: 1 s of 0.3 m/s
  for (int i = 0; i < 125; i++) { t += 0.008; p += Eigen::Vector3d(0.3 * 0.008, 0, 0);
    ASSERT_EQ(odom_sanity_check(c, st, t, p, Eigen::Vector3d(0.3, 0, 0)), OdomSanityVerdict::ACCEPT); }
  // explosion ramp: accel 1.5 m/s^2 for 4 s -> 6.3 m/s (crosses 5.0 mid-way);
  // position follows the (garbage) velocity: jump stays under 1.0 until v>~9
  double v = 0.3;
  OdomSanityVerdict last = OdomSanityVerdict::ACCEPT;
  int rejected_frames = 0;
  for (int i = 0; i < 500; i++)
  {
    t += 0.008; v += 1.5 * 0.008;
    p += Eigen::Vector3d(v * 0.008, 0, 0);
    last = odom_sanity_check(c, st, t, p, Eigen::Vector3d(v, 0, 0));
    if (last != OdomSanityVerdict::ACCEPT) rejected_frames++;
  }
  EXPECT_EQ(rejected_frames, 109) << "gate should engage once v crosses 5.0 (frame 392 of 500)";
  EXPECT_EQ(last, OdomSanityVerdict::REJECT_VEL);
  // and a later milder frame is still compared against the frozen healthy ref:
  EXPECT_EQ(odom_sanity_check(c, st, t + 0.008, Eigen::Vector3d(0.5, 0, 0), Eigen::Vector3d(0.4, 0, 0)),
            OdomSanityVerdict::REJECT_JUMP);
}

TEST(OdomSanity, RebootWindowSkipsContinuity)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  ASSERT_EQ(odom_sanity_check(c, st, 10.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::ACCEPT);
  // stream gap of 5 s (VINS re-init / re-anchor at origin): position far from
  // stale reference but dt >= reboot_dt -> magnitude gate only -> accept
  EXPECT_EQ(odom_sanity_check(c, st, 15.0, Eigen::Vector3d(3.0, -2.0, 1.0), Eigen::Vector3d(0.1, 0, 0)),
            OdomSanityVerdict::ACCEPT);
}

TEST(OdomSanity, DisabledPassThrough)
{
  OdomSanityConfig c;  // enabled = false
  OdomSanityState st;
  EXPECT_EQ(odom_sanity_check(c, st, 1.0, Eigen::Vector3d(740, -458, 0), Eigen::Vector3d(1250000, 0, 0)),
            OdomSanityVerdict::ACCEPT);  // legacy behavior: garbage passes untouched
  EXPECT_EQ(st.accepted, 1);
}

TEST(OdomSanity, NanRejected)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  double nan = std::numeric_limits<double>::quiet_NaN();
  EXPECT_EQ(odom_sanity_check(c, st, 1.0, Eigen::Vector3d(nan, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::REJECT_NAN);
  EXPECT_EQ(odom_sanity_check(c, st, 1.0, Eigen::Vector3d::Zero(), Eigen::Vector3d(0, nan, 0)),
            OdomSanityVerdict::REJECT_NAN);
}

TEST(OdomSanity, ReferenceNotPoisonedBySingleReject)
{
  OdomSanityConfig c = gate_on();
  OdomSanityState st;
  ASSERT_EQ(odom_sanity_check(c, st, 10.0, Eigen::Vector3d(0, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::ACCEPT);
  // one violating frame (jump 5 m)
  EXPECT_EQ(odom_sanity_check(c, st, 10.008, Eigen::Vector3d(5, 0, 0), Eigen::Vector3d::Zero()),
            OdomSanityVerdict::REJECT_JUMP);
  // next healthy frame (relative to frozen ref) accepted again -> no lockout.
  // NOTE: recovery speed must stay under the acc gate w.r.t. the FROZEN ref
  // (0.05 m/s step over 8 ms = 6.25 m/s^2 < 10); a 0.2 m/s step (25 m/s^2)
  // would be legitimately REJECT_ACC.
  EXPECT_EQ(odom_sanity_check(c, st, 10.016, Eigen::Vector3d(0.03, 0, 0), Eigen::Vector3d(0.05, 0, 0)),
            OdomSanityVerdict::ACCEPT);
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
