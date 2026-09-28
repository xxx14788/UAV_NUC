#include <gtest/gtest.h>
#include <Eigen/Dense>
#include "estimator/reanchor_smoother.h"

// T1-D1 gtest: conservation / no-idle-drift / immediate continuity / defenses.

TEST(ReanchorSmoother, ConservationSingleJump)
{
    // correct invariant: the SUM OF PER-FRAME RELEASED amounts == captured jump
    // (published stream = kernel + offset; offset decay releases exactly J once)
    ReanchorSmoother s; s.frames = 15;
    Eigen::Vector3d J(0.05, -0.08, 0.01), JV(0.3, -0.2, 0.0);
    s.addJump(J, JV);
    Eigen::Vector3d relP = Eigen::Vector3d::Zero(), relV = Eigen::Vector3d::Zero();
    Eigen::Vector3d prevP = s.offset_P, prevV = s.offset_V;
    for (int i = 0; i < 200; i++)
    {
        s.step();
        relP += prevP - s.offset_P; prevP = s.offset_P;
        relV += prevV - s.offset_V; prevV = s.offset_V;
    }
    EXPECT_LT((relP - J).norm(), 1e-12);
    EXPECT_LT((relV - JV).norm(), 1e-12);
    EXPECT_DOUBLE_EQ(s.offset_P.norm(), 0.0);
}

TEST(ReanchorSmoother, OverlappingJumpsConservation)
{
    ReanchorSmoother s; s.frames = 15;
    Eigen::Vector3d J1(0.02, 0.03, -0.01), J2(-0.04, 0.01, 0.02);
    s.addJump(J1, Eigen::Vector3d::Zero());
    Eigen::Vector3d rel = Eigen::Vector3d::Zero(), prev = s.offset_P;
    for (int i = 0; i < 5; i++) { s.step(); rel += prev - s.offset_P; prev = s.offset_P; }
    s.addJump(J2, Eigen::Vector3d::Zero());  // undigested folded into new schedule
    prev = s.offset_P;  // addJump changed the offset: refresh snapshot BEFORE stepping
    for (int i = 0; i < 300; i++) { s.step(); rel += prev - s.offset_P; prev = s.offset_P; }
    EXPECT_LT((rel - (J1 + J2)).norm(), 1e-12);
}

TEST(ReanchorSmoother, PublishedStreamHasNoStep)
{
    // end-to-end semantics: kernel stream steps 0.06 m at a reanchor; smoothed
    // published stream steps at most natural(0.004)+J/N(0.004)=0.008 per frame
    // and converges back onto the kernel stream.
    ReanchorSmoother s; s.frames = 15;
    double kernel = 0.0, prev_pub = 0.0, max_step = 0.0;
    for (int i = 0; i < 40; i++)
    {
        kernel += 0.004;                       // natural per-frame drift
        if (i == 10)
        {
            double anchored = kernel - 0.06;   // reanchor pulls kernel back
            s.addJump(Eigen::Vector3d(kernel - anchored, 0, 0), Eigen::Vector3d::Zero());
            kernel = anchored;
        }
        double pub = kernel + s.offset_P.x();
        if (i > 0) max_step = std::max(max_step, std::abs(pub - prev_pub));
        prev_pub = pub;
        s.step();
    }
    // released offset cancels the natural drift here (J/N == nat): the stream
    // pauses 15 frames then rejoins the kernel chain -- never steps 0.06.
    EXPECT_LT(max_step, 0.01);
    EXPECT_NEAR(max_step, 0.004, 0.001);
    EXPECT_NEAR(prev_pub, kernel, 1e-12);
}

TEST(ReanchorSmoother, FirstFrameHidesStep)
{
    // first post-reanchor publish carries the full offset -> stream continuity
    ReanchorSmoother s; s.frames = 15;
    Eigen::Vector3d J(0.06, -0.06, 0.0);
    s.addJump(J, Eigen::Vector3d::Zero());
    EXPECT_LT((s.offset_P - J).norm(), 1e-12);
}

TEST(ReanchorSmoother, LinearReleaseShape)
{
    ReanchorSmoother s; s.frames = 4;
    s.addJump(Eigen::Vector3d(0.4, 0, 0), Eigen::Vector3d::Zero());
    double o1 = s.offset_P.x(); s.step();
    double o2 = s.offset_P.x(); s.step();
    double o3 = s.offset_P.x(); s.step();
    double o4 = s.offset_P.x(); s.step();
    EXPECT_NEAR(o1 - o2, 0.1, 1e-12);   // uniform decrement
    EXPECT_NEAR(o2 - o3, 0.1, 1e-12);
    EXPECT_NEAR(o3 - o4, 0.1, 1e-12);
    EXPECT_DOUBLE_EQ(s.offset_P.x(), 0.0);
}

TEST(ReanchorSmoother, DisabledByZeroFrames)
{
    ReanchorSmoother s; s.frames = 0;
    s.addJump(Eigen::Vector3d(1, 1, 1), Eigen::Vector3d::Zero());
    EXPECT_DOUBLE_EQ(s.offset_P.norm(), 0.0);
    EXPECT_EQ(s.remaining, 0);
}

TEST(ReanchorSmoother, IdleStepIsNoop)
{
    ReanchorSmoother s; s.frames = 3;
    for (int i = 0; i < 50; i++) s.step();
    EXPECT_DOUBLE_EQ(s.offset_P.norm(), 0.0);  // idle stepping never drifts
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
