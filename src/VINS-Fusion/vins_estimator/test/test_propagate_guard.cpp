// T1-E2 (2026-09-30): gtest for PropagateGuard (C03 A3/A4 pure-value logic).
#include "estimator/propagate_guard.h"
#include "estimator/reanchor_smoother.h"
#include <gtest/gtest.h>
#include <limits>

TEST(PropagateGuard, DtInvalidBoundaries)
{
    EXPECT_FALSE(PropagateGuard::dt_invalid(0.0));
    EXPECT_FALSE(PropagateGuard::dt_invalid(0.5));
    EXPECT_FALSE(PropagateGuard::dt_invalid(1e-9));
    EXPECT_FALSE(PropagateGuard::dt_invalid(0.008));
    EXPECT_TRUE(PropagateGuard::dt_invalid(0.5001));
    EXPECT_TRUE(PropagateGuard::dt_invalid(-0.001));
    EXPECT_TRUE(PropagateGuard::dt_invalid(std::numeric_limits<double>::quiet_NaN()));
    EXPECT_TRUE(PropagateGuard::dt_invalid(std::numeric_limits<double>::infinity()));
}

TEST(PropagateGuard, ClampRaisesHoldAndCounts)
{
    PropagateGuard g;
    EXPECT_FALSE(g.pub_hold);
    g.on_clamp();
    EXPECT_TRUE(g.pub_hold);
    EXPECT_EQ(g.clamp_count, 1);
    g.on_clamp();
    EXPECT_EQ(g.clamp_count, 2);
}

TEST(PropagateGuard, AnchorClearsHold)
{
    PropagateGuard g;
    g.on_clamp();
    EXPECT_TRUE(g.pub_hold);
    g.on_anchor();
    EXPECT_FALSE(g.pub_hold);
}

TEST(PropagateGuard, SingleDomainSwitchWithSolverAlive)
{
    // P4 scenario (i): one domain jump -> clamp -> hold -> ULS anchors -> recover.
    PropagateGuard g;
    int published = 0, withheld = 0;
    for (int i = 0; i < 5; ++i) { if (!g.should_hold_publish()) published++; else withheld++; }
    EXPECT_EQ(published, 5);
    g.on_clamp();                       // domain-jump frame arrives
    for (int i = 0; i < 3; ++i) { if (!g.should_hold_publish()) published++; else withheld++; }
    g.on_anchor();                      // next steady ULS
    for (int i = 0; i < 5; ++i) { if (!g.should_hold_publish()) published++; else withheld++; }
    EXPECT_EQ(withheld, 3);
    EXPECT_EQ(g.clamp_count, 1);
    EXPECT_EQ(g.held_frames, 3);
    EXPECT_FALSE(g.pub_hold);
}

TEST(PropagateGuard, SolverDeadHoldsForever)
{
    // P4 scenario (ii): smooth3-type (no ULS ever) -> permanent hold, no
    // silent healthy-rate wrong-position stream.
    PropagateGuard g;
    g.on_clamp();
    for (int i = 0; i < 1000; ++i)
        EXPECT_TRUE(g.should_hold_publish());
    EXPECT_EQ(g.held_frames, 1000);
}

TEST(PropagateGuard, HealthyStreamNeverHolds)
{
    PropagateGuard g;
    for (int i = 0; i < 1000; ++i)
    {
        ASSERT_FALSE(PropagateGuard::dt_invalid(0.008));
        EXPECT_FALSE(g.should_hold_publish());
    }
    EXPECT_EQ(g.clamp_count, 0);
    EXPECT_EQ(g.held_frames, 0);
}

TEST(PropagateGuard, GapSkipThresholdBoundary)
{
    EXPECT_FALSE(PropagateGuard::gap_skip_needed(100.0, 100.0));     // 0.0
    EXPECT_FALSE(PropagateGuard::gap_skip_needed(100.0, 100.3));     // exactly 0.3
    EXPECT_FALSE(PropagateGuard::gap_skip_needed(100.0, 100.03));    // healthy pipe
    EXPECT_TRUE(PropagateGuard::gap_skip_needed(100.0, 100.31));     // just over
    EXPECT_TRUE(PropagateGuard::gap_skip_needed(100.0, 95.0));       // cross-second
}

TEST(PropagateGuard, GapSkipCountsButHoldUntouched)
{
    PropagateGuard g;
    g.on_gap_skip();
    g.on_gap_skip();
    EXPECT_EQ(g.gap_skips, 2);
    EXPECT_FALSE(g.pub_hold);   // gap skip is capture-side, not publish-side
}

// C03 A6 composite: consecutive jumps folded + a gap-skip interleaved --
// smoother conservation interacts with guard counters without interference.
TEST(PropagateGuard, CompositeJumpsAndGapSkip)
{
    ReanchorSmoother sm;
    PropagateGuard g;
    const Eigen::Vector3d J1(0.06, 0.0, 0.0), J2(0.2, 0.0, -0.17);
    sm.addJump(J1, Eigen::Vector3d::Zero());
    Eigen::Vector3d released = Eigen::Vector3d::Zero();
    for (int i = 0; i < 15; ++i) { released += sm.step_P; sm.step(); }
    EXPECT_NEAR(released.x(), 0.06, 1e-12);
    // 47s-type big jump captured (beta path), then a cross-second gap skip.
    sm.addJump(J2, Eigen::Vector3d::Zero());
    EXPECT_NEAR(sm.offset_P.x(), 0.2, 1e-12);   // J1 fully released, only J2 left
    g.on_gap_skip();
    EXPECT_EQ(g.gap_skips, 1);
    // release completes over 15 frames
    released.setZero();
    for (int i = 0; i < 15; ++i) { released += sm.step_P; sm.step(); }
    EXPECT_NEAR(released.x(), 0.2, 1e-12);
    EXPECT_NEAR(sm.offset_P.x(), 0.0, 1e-12);
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
