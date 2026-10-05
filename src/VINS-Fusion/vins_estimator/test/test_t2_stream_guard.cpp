#include <gtest/gtest.h>
#include <Eigen/Dense>
#include "estimator/stream_guard_logic.h"
#include "estimator/reanchor_smoother.h"

// T2-v9.5 gtest (prereg_reanchor_fix): sane-gate boundaries, resume-gap
// detection, adaptive ramp conservation and per-frame step cap.

TEST(StreamGuard, SaneGateBoundaries)
{
    EXPECT_TRUE(StreamGuardLogic::publish_sane(10.0, 5.0, 50.0, 15.0));
    EXPECT_FALSE(StreamGuardLogic::publish_sane(50.0, 5.0, 50.0, 15.0));   // |P| at bound -> hold
    EXPECT_FALSE(StreamGuardLogic::publish_sane(10.0, 15.0, 50.0, 15.0));  // |V| at bound -> hold
    EXPECT_TRUE(StreamGuardLogic::publish_sane(49.9, 14.9, 50.0, 15.0));
    EXPECT_TRUE(StreamGuardLogic::publish_sane(999.0, 49.0, 1e3, 50.0));   // legacy defaults keep legacy behavior
}

TEST(StreamGuard, ResumeGapDetection)
{
    EXPECT_FALSE(StreamGuardLogic::resume_needed(false, 10.0));  // never published -> nothing to continue from
    EXPECT_FALSE(StreamGuardLogic::resume_needed(true, 0.008));  // 125Hz normal cadence
    EXPECT_FALSE(StreamGuardLogic::resume_needed(true, 0.15));   // at threshold -> not a gap
    EXPECT_TRUE(StreamGuardLogic::resume_needed(true, 0.151));   // just over
    EXPECT_TRUE(StreamGuardLogic::resume_needed(true, 1.3));     // MACH1-class reboot blackout
}

TEST(StreamGuard, AdaptiveFramesCapPerFrameStep)
{
    EXPECT_EQ(StreamGuardLogic::resume_frames(0.0), 15);
    EXPECT_EQ(StreamGuardLogic::resume_frames(6.0), 15);    // 6/15 = 0.4 exactly
    EXPECT_EQ(StreamGuardLogic::resume_frames(2.6), 15);    // constant family: 0.173/frame
    EXPECT_EQ(StreamGuardLogic::resume_frames(5.4), 15);    // MACH1-class resume w/ sane-hold: 0.36/frame
    int fr = StreamGuardLogic::resume_frames(294.0);        // monster delta (guard-bypassed path)
    EXPECT_EQ(fr, 735);
    EXPECT_LE(294.0 / fr, 0.4 + 1e-12);
    EXPECT_EQ(StreamGuardLogic::resume_frames(400.0), 750); // clamped
}

TEST(StreamGuard, ResumeRampConservationWithSmoother)
{
    // wire-up contract: feeding the resume delta through the smoother with the
    // adaptive frame count releases the delta exactly once, every per-frame
    // released step stays under the 0.4 m cap, and the offset zeroes out.
    ReanchorSmoother s;
    Eigen::Vector3d last_pub(5.0, -1.5, 0.3), now(0.0, 0.0, 0.0);
    Eigen::Vector3d dP = last_pub - now;
    s.frames = StreamGuardLogic::resume_frames(dP.norm());
    s.addJump(dP, Eigen::Vector3d::Zero());
    Eigen::Vector3d prev_off = s.offset_P;
    Eigen::Vector3d released = Eigen::Vector3d::Zero();
    double max_step = 0.0;
    for (int i = 0; i < 800; i++)
    {
        s.step();
        Eigen::Vector3d stp = prev_off - s.offset_P;
        if (stp.norm() > max_step) max_step = stp.norm();
        released += stp;
        prev_off = s.offset_P;
    }
    EXPECT_LT((released - dP).norm(), 1e-12);
    EXPECT_LE(max_step, 0.4 + 1e-12);
    EXPECT_DOUBLE_EQ(s.offset_P.norm(), 0.0);
}

TEST(StreamGuard, OverlappingResumeFoldsConservation)
{
    ReanchorSmoother s;
    Eigen::Vector3d d1(2.6, 0.0, 0.0), d2(0.0, -1.0, 0.5);
    s.frames = StreamGuardLogic::resume_frames(d1.norm());
    s.addJump(d1, Eigen::Vector3d::Zero());
    Eigen::Vector3d prev = s.offset_P, released = Eigen::Vector3d::Zero();
    for (int i = 0; i < 3; i++)     // partial release, then a second resume folds in
    {
        s.step();
        released += prev - s.offset_P;
        prev = s.offset_P;
    }
    s.frames = StreamGuardLogic::resume_frames(d2.norm());
    s.addJump(d2, Eigen::Vector3d::Zero());
    prev = s.offset_P;   // re-anchor the accounting to the folded offset
    for (int i = 0; i < 2000; i++)
    {
        s.step();
        released += prev - s.offset_P;
        prev = s.offset_P;
    }
    EXPECT_LT((released - (d1 + d2)).norm(), 1e-12);
    EXPECT_DOUBLE_EQ(s.offset_P.norm(), 0.0);
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
