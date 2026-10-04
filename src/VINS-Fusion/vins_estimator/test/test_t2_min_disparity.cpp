#include <gtest/gtest.h>
#include <eigen3/Eigen/Dense>
#include "estimator/feature_manager.h"
#include "estimator/parameters.h"

// T2-R2F gtest: disparity observability screen (far_drop) on stereo triangulation.
// Fixture mirrors test_t2_depth_gate.cpp: identity window, 0.1m x-baseline.
// Normalized disp = 0.1/Z; px = disp * FOCAL_LENGTH (460).
//   Z=5.0 -> 9.2px (far), Z=2.0 -> 23px (far), Z=1.0 -> 46px (near), Z=0.5 -> 92px (near)

using namespace Eigen;

static Matrix3d Rs_arr[WINDOW_SIZE + 1];
static Vector3d Ps_arr[WINDOW_SIZE + 1];
static Vector3d tic_arr[2];
static Matrix3d ric_arr[2];

struct DispFixture : public ::testing::Test
{
    FeatureManager fm;
    DispFixture() : fm(Rs_arr)
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
        T2_DEPTH_GATE = 0;          // isolate the disparity axis
        T2_MIN_DISPARITY = 0;       // default off per test
        T2_FARDROP_MIN_NEAR = 30;
        fm.t2_near_supply_last = 0;
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
    const FeaturePerId *find(int id)
    {
        for (auto &f : fm.feature)
            if (f.feature_id == id) return &f;
        return nullptr;
    }
};

TEST_F(DispFixture, DefaultOffBitIdentical)
{
    T2_MIN_DISPARITY = 0;
    fm.t2_near_supply_last = 100;  // supply sufficient: gate must still not act
    addStereoFeature(1, 0.5, 0.2, 5.0);   // far (9.2px)
    addStereoFeature(2, 0.1, 0.0, 0.5);   // near (92px)
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(1));
    EXPECT_NEAR(find(1)->estimated_depth, 5.0, 1e-6);   // legacy path wrote it
    ASSERT_TRUE(find(2));
    EXPECT_NEAR(find(2)->estimated_depth, 0.5, 1e-6);
}

TEST_F(DispFixture, GateOnDropsFarKeepsNear)
{
    T2_MIN_DISPARITY = 30;
    fm.t2_near_supply_last = 100;  // guard satisfied
    addStereoFeature(3, 0.5, 0.2, 5.0);   // far 9.2px
    addStereoFeature(4, 0.4, 0.0, 2.0);   // far 23px
    addStereoFeature(5, 0.2, 0.0, 1.0);   // near 46px
    addStereoFeature(6, 0.1, 0.0, 0.5);   // near 92px
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    // far: track kept, no measurement produced (depth stays unset = -1)
    ASSERT_TRUE(find(3));
    EXPECT_DOUBLE_EQ(find(3)->estimated_depth, -1.0);
    ASSERT_TRUE(find(4));
    EXPECT_DOUBLE_EQ(find(4)->estimated_depth, -1.0);
    // near: depth written
    ASSERT_TRUE(find(5));
    EXPECT_NEAR(find(5)->estimated_depth, 1.0, 1e-6);
    ASSERT_TRUE(find(6));
    EXPECT_NEAR(find(6)->estimated_depth, 0.5, 1e-6);
    // near supply counted for this frame = 2
    // (t2_near_supply_last updated at end of triangulate)
}

TEST_F(DispFixture, StarvationGuardBlocksFarDrop)
{
    T2_MIN_DISPARITY = 30;
    fm.t2_near_supply_last = 0;  // below guard floor -> far must NOT be dropped
    addStereoFeature(7, 0.5, 0.2, 5.0);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(7));
    EXPECT_NEAR(find(7)->estimated_depth, 5.0, 1e-6);  // legacy write despite low disp
}

TEST_F(DispFixture, SupplyMemoryUpdatesAcrossFrames)
{
    T2_MIN_DISPARITY = 30;
    fm.t2_near_supply_last = 100;
    addStereoFeature(8, 0.2, 0.0, 1.0);   // near
    addStereoFeature(9, 0.5, 0.2, 5.0);   // far (dropped)
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    EXPECT_EQ(fm.t2_near_supply_last, 1);  // one near passed the gate
    // next frame: supply=1 < 30 -> starvation guard engages, far keeps legacy path
    for (auto &f : fm.feature) f.feature_per_frame[0].point[2] = 1.0;  // keep obs valid
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    ASSERT_TRUE(find(9));
    EXPECT_NEAR(find(9)->estimated_depth, 5.0, 1e-6);  // not dropped this time
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
