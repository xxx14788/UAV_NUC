#include <gtest/gtest.h>
#include <eigen3/Eigen/Dense>
#include "estimator/feature_manager.h"
#include "estimator/parameters.h"

// T2-WA1G gtest: depth-domain gate on triangulation.
// Fixture: identity-pose window, stereo rig with 0.1m x-baseline (sim_stereo geometry).
// A world point (X,Y,Z) yields left obs (X/Z, Y/Z) and right obs ((X-0.1)/Z, Y/Z)
// in normalized coords; triangulate() must recover depth = Z (left-camera frame).

using namespace Eigen;

static Matrix3d Rs_arr[WINDOW_SIZE + 1];
static Vector3d Ps_arr[WINDOW_SIZE + 1];
static Vector3d tic_arr[2];
static Matrix3d ric_arr[2];

struct GateFixture : public ::testing::Test
{
    FeatureManager fm;
    GateFixture() : fm(Rs_arr)
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

TEST_F(GateFixture, GateOnKeepsInBandRejectsOutBand)
{
    T2_DEPTH_GATE = 1; T2_DEPTH_MIN = 0.15; T2_DEPTH_MAX = 30.0;
    addStereoFeature(1, 0.5, 0.2, 5.0);    // in-band
    addStereoFeature(2, 0.05, 0.0, 0.05);  // 0.05 < 0.15 -> reject
    addStereoFeature(3, 3.5, 0.0, 35.0);   // 35 > 30 -> reject
    addReversedStereoFeature(4);           // negative -> reject (no INIT_DEPTH)
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(1));
    EXPECT_NEAR(find(1)->estimated_depth, 5.0, 1e-6);
    EXPECT_FALSE(find(2));
    EXPECT_FALSE(find(3));
    EXPECT_FALSE(find(4));  // silent INIT_DEPTH path abolished when gate on
    T2_DEPTH_GATE = 0;
}

TEST_F(GateFixture, GateBoundariesInclusive)
{
    T2_DEPTH_GATE = 1; T2_DEPTH_MIN = 0.15; T2_DEPTH_MAX = 30.0;
    addStereoFeature(10, 0.015015, 0, 0.15015);  // just above min -> keep
    addStereoFeature(11, 3.0, 0, 29.9);          // just below max -> keep
    addStereoFeature(12, 0.014985, 0, 0.14985);  // just below min -> reject
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(10));
    EXPECT_NEAR(find(10)->estimated_depth, 0.15015, 1e-4);
    ASSERT_TRUE(find(11));
    EXPECT_NEAR(find(11)->estimated_depth, 29.9, 1e-4);
    EXPECT_FALSE(find(12));
    T2_DEPTH_GATE = 0;
}

TEST_F(GateFixture, GateOffLegacyBitIdentical)
{
    T2_DEPTH_GATE = 0;
    addStereoFeature(20, 0.5, 0.2, 5.0);
    addReversedStereoFeature(21);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(20));
    EXPECT_NEAR(find(20)->estimated_depth, 5.0, 1e-6);
    ASSERT_TRUE(find(21));                    // legacy keeps it with pseudo depth
    EXPECT_DOUBLE_EQ(find(21)->estimated_depth, 5.0);  // INIT_DEPTH fallback = upstream behavior
}

TEST_F(GateFixture, EmptyAndAllRejected)
{
    T2_DEPTH_GATE = 1; T2_DEPTH_MIN = 0.15; T2_DEPTH_MAX = 30.0;
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);  // empty list: no crash
    EXPECT_TRUE(fm.feature.empty());
    addStereoFeature(30, 0.05, 0, 0.05);
    addStereoFeature(31, 3.5, 0, 35.0);
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    EXPECT_TRUE(fm.feature.empty());  // all rejected -> empty, no crash
    T2_DEPTH_GATE = 0;
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
