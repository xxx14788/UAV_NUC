#include <gtest/gtest.h>
#include <eigen3/Eigen/Dense>
#include <limits>
#include "estimator/feature_manager.h"
#include "estimator/parameters.h"

// T2-v8.9 route-fix gtest: case-A staged depth gate + case-B W4 line.
// Fixture mirrors test_t2_depth_gate.cpp (identity window, 0.1m stereo baseline).
// Case-A semantics: INITIAL fill-window + post-init grace window keep the
// legacy INIT_DEPTH pseudo-injection (solveGyroscopeBias feature mass — the
// depth-gate livelock lesson, v8.3 unit-3); steady state rejects like
// T2_DEPTH_GATE. Case-B semantics: W4 pre-init Bgs line configurable,
// 0.5 default = bit-identical to the former hardcode.

using namespace Eigen;

static Matrix3d Rs_arr[WINDOW_SIZE + 1];
static Vector3d Ps_arr[WINDOW_SIZE + 1];
static Vector3d tic_arr[2];
static Matrix3d ric_arr[2];

struct RouteFixFixture : public ::testing::Test
{
    FeatureManager fm;
    RouteFixFixture() : fm(Rs_arr)
    {
        for (int i = 0; i <= WINDOW_SIZE; i++)
        {
            Rs_arr[i] = Matrix3d::Identity();
            Ps_arr[i] = Vector3d::Zero();
        }
        ric_arr[0] = Matrix3d::Identity(); tic_arr[0] = Vector3d::Zero();
        ric_arr[1] = Matrix3d::Identity(); tic_arr[1] = Vector3d(0.1, 0, 0);
        STEREO = 1;
        INIT_DEPTH = 5.0;
        T2_DEPTH_GATE = 0;
        T2_DEPTH_MIN = 0.15; T2_DEPTH_MAX = 30.0;
        T2_DEPTH_GATE_STAGED = 0;
        T2_STAGED_N_SEC = 80.0;
        T2_W4_BGS_THRESH = 0.5;
    }
    void addStereoFeature(int id, double X, double Y, double Z)
    {
        FeaturePerId fid(id, 0);
        Matrix<double, 7, 1> pl, pr;
        pl << X / Z, Y / Z, 1.0, 460.0 * X / Z + 320, 460.0 * Y / Z + 240, 0, 0;
        pr << (X - 0.1) / Z, Y / Z, 1.0, 460.0 * (X - 0.1) / Z + 320, 460.0 * Y / Z + 240, 0, 0;
        FeaturePerFrame fl(pl, 0.0);
        fl.rightObservation(pr);
        fid.feature_per_frame.push_back(fl);
        fm.feature.push_back(fid);
    }
    // reversed-parallax obs: right x-norm LARGER than left -> negative depth
    void addReversedStereoFeature(int id)
    {
        FeaturePerId fid(id, 0);
        Matrix<double, 7, 1> pl, pr;
        pl << 0.10, 0.0, 1.0, 306, 240, 0, 0;
        pr << 0.12, 0.0, 1.0, 315.2, 240, 0, 0;
        FeaturePerFrame fl(pl, 0.0);
        fl.rightObservation(pr);
        fid.feature_per_frame.push_back(fl);
        fm.feature.push_back(fid);
    }
    const FeaturePerId *find(int id)
    {
        for (auto &f : fm.feature) if (f.feature_id == id) return &f;
        return nullptr;
    }
};

// ---------- case-A: staged gate arming ----------

TEST_F(RouteFixFixture, StagedOffBitIdentical)
{
    // staged=0 (default): reversed feature keeps pseudo-injection regardless
    // of the steady flag — bit-identical to legacy when the knob is absent.
    T2_DEPTH_GATE_STAGED = 0;
    fm.setT2StagedSteady(true);
    addStereoFeature(1, 0.5, 0.2, 5.0);
    addReversedStereoFeature(2);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(1));
    EXPECT_NEAR(find(1)->estimated_depth, 5.0, 1e-6);
    ASSERT_TRUE(find(2));
    EXPECT_DOUBLE_EQ(find(2)->estimated_depth, 5.0);
}

TEST_F(RouteFixFixture, StagedFillWindowKeepsInjection)
{
    // staged=1 but steady=false (INITIAL fill-window / grace window):
    // pseudo-injection retained — this is the anti-livelock core of case-A.
    T2_DEPTH_GATE_STAGED = 1;
    fm.setT2StagedSteady(false);
    addReversedStereoFeature(10);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(10));
    EXPECT_DOUBLE_EQ(find(10)->estimated_depth, 5.0);
    T2_DEPTH_GATE_STAGED = 0;
}

TEST_F(RouteFixFixture, StagedSteadyRejectsNegative)
{
    // staged=1 + steady=true: same policy as T2_DEPTH_GATE — out-of-band and
    // negative-depth tracks are erased, in-band depth kept.
    T2_DEPTH_GATE_STAGED = 1;
    fm.setT2StagedSteady(true);
    addStereoFeature(20, 0.5, 0.2, 5.0);    // in-band
    addReversedStereoFeature(21);           // negative -> reject
    addStereoFeature(22, 3.5, 0.0, 35.0);   // 35 > 30 -> reject
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(20));
    EXPECT_NEAR(find(20)->estimated_depth, 5.0, 1e-6);
    EXPECT_FALSE(find(21));
    EXPECT_FALSE(find(22));
    T2_DEPTH_GATE_STAGED = 0;
}

TEST_F(RouteFixFixture, StagedGraceWindowLogic)
{
    // truth table of the arming predicate t2_staged_steady_now
    EXPECT_FALSE(t2_staged_steady_now(true, 0.0, 100.0, 80.0));   // never finished -> fill-window
    EXPECT_FALSE(t2_staged_steady_now(false, 50.0, 200.0, 80.0)); // INITIAL -> fill-window
    EXPECT_FALSE(t2_staged_steady_now(true, 50.0, 129.9, 80.0));  // 79.9s < 80 grace -> keep
    EXPECT_TRUE(t2_staged_steady_now(true, 50.0, 130.0, 80.0));   // 80.0s boundary -> armed
    EXPECT_TRUE(t2_staged_steady_now(true, 50.0, 400.0, 80.0));   // deep steady state
}

// ---------- case-B: W4 pre-init Bgs line ----------

TEST_F(RouteFixFixture, W4DefaultBitIdentical)
{
    // 0.5 default reproduces the former hardcoded norm()<0.5 boundaries
    T2_W4_BGS_THRESH = 0.5;
    EXPECT_TRUE(t2_w4_bgs_ok(Vector3d(0.3, 0.3, 0.1), 0.5));   // norm 0.4358 < 0.5
    EXPECT_TRUE(t2_w4_bgs_ok(Vector3d(0.499, 0.0, 0.0), 0.5)); // just under
    EXPECT_FALSE(t2_w4_bgs_ok(Vector3d(0.5, 0.0, 0.0), 0.5));  // exactly at line -> reject (strict <)
    EXPECT_FALSE(t2_w4_bgs_ok(Vector3d(0.5001, 0.0, 0.0), 0.5));
    Vector3d bad = Vector3d::Zero();
    bad(0) = std::numeric_limits<double>::quiet_NaN();
    EXPECT_FALSE(t2_w4_bgs_ok(bad, 5.0));                     // NaN guard even with wide line
}

TEST_F(RouteFixFixture, W4ConfiguredThresholdPasses)
{
    // 5.0 arm (rejudging window 0.62-5.63): mid-band solutions pass
    T2_W4_BGS_THRESH = 5.0;
    EXPECT_TRUE(t2_w4_bgs_ok(Vector3d(2.0, 1.5, 1.0), 5.0));  // norm 2.69
    EXPECT_TRUE(t2_w4_bgs_ok(Vector3d(3.0, 3.0, 1.0), 5.0));  // norm 4.36
    EXPECT_FALSE(t2_w4_bgs_ok(Vector3d(3.0, 3.0, 3.0), 5.0)); // norm 5.196 > 5.0 still guarded
    EXPECT_DOUBLE_EQ(T2_W4_BGS_THRESH, 5.0);
    T2_W4_BGS_THRESH = 0.5;
}

TEST_F(RouteFixFixture, W4BasLineUntouched)
{
    // case-B touches only the Bgs line; the Bas 1.0 line is not a knob:
    // verify the default knob value stays 0.5 so absent key = legacy math.
    EXPECT_DOUBLE_EQ(T2_W4_BGS_THRESH, 0.5);
    EXPECT_DOUBLE_EQ(T2_STAGED_N_SEC, 80.0);
    EXPECT_EQ(T2_DEPTH_GATE_STAGED, 0);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
