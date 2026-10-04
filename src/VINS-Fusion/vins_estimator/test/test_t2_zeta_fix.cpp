#include <gtest/gtest.h>
#include <eigen3/Eigen/Dense>
#include "estimator/feature_manager.h"
#include "estimator/parameters.h"

// T2 zeta-fix gtest: pseudo-depth marking + starvation predicate.
// Semantics under test (prereg_pseudo_drop.md):
//   1. Features whose depth came from the INIT_DEPTH pseudo-injection path are
//      marked t2_pseudo=true (stereo / motion2 / svd-degenerate sources);
//      genuinely-triangulated features stay false. Marking is permanent
//      (depth>0 blocks re-triangulation) = quarantine semantics.
//   2. t2_starve_now truth table: armed only in NON_LINEAR, floor>0, and
//      track_num strictly below floor.

using namespace Eigen;

static Matrix3d Rs_arr[WINDOW_SIZE + 1];
static Vector3d Ps_arr[WINDOW_SIZE + 1];
static Vector3d tic_arr[2];
static Matrix3d ric_arr[2];

struct ZetaFixture : public ::testing::Test
{
    FeatureManager fm;
    ZetaFixture() : fm(Rs_arr)
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
        T2_DEPTH_GATE_STAGED = 0;
        T2_DEPTH_MIN = 0.15; T2_DEPTH_MAX = 30.0;
        T2_MIN_DISPARITY = 0.0;
        T2_MOTION2_MIN_BASE = 0.0;
        T2_PSEUDO_DROP = 0;
        T2_STARVE_FLOOR = 0;
        T2_STARVE_ALPHA = 1.0;
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
    FeaturePerId *find(int id)
    {
        for (auto &f : fm.feature) if (f.feature_id == id) return &f;
        return nullptr;
    }
};

TEST_F(ZetaFixture, PseudoMarkingStereoNegative)
{
    // legacy path (all gates off): reversed-parallax stereo -> INIT_DEPTH
    // pseudo-injection must mark t2_pseudo=true
    addReversedStereoFeature(1);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    FeaturePerId *f = find(1);
    ASSERT_TRUE(f);
    EXPECT_DOUBLE_EQ(f->estimated_depth, 5.0);
    EXPECT_TRUE(f->t2_pseudo);
}

TEST_F(ZetaFixture, GenuineDepthNotMarked)
{
    // in-band genuine stereo depth -> no marking
    addStereoFeature(2, 0.5, 0.2, 5.0);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    FeaturePerId *f = find(2);
    ASSERT_TRUE(f);
    EXPECT_NEAR(f->estimated_depth, 5.0, 1e-6);
    EXPECT_FALSE(f->t2_pseudo);
}

TEST_F(ZetaFixture, QuarantineIsPermanent)
{
    // re-triangulation does not clear the mark: estimated_depth>0 short-circuits
    // the triangulate loop, so a quarantined feature stays quarantined.
    addReversedStereoFeature(3);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    EXPECT_TRUE(find(3)->t2_pseudo);
    EXPECT_DOUBLE_EQ(find(3)->estimated_depth, 5.0);
}

TEST_F(ZetaFixture, GateOnBranchNotMarked)
{
    // depth-gate branch assigns genuine depths only; nothing marked
    T2_DEPTH_GATE = 1;
    addStereoFeature(4, 0.5, 0.2, 5.0);
    fm.t2_cur_t = 1.0;
    fm.triangulate(0, Ps_arr, Rs_arr, tic_arr, ric_arr);
    EXPECT_FALSE(find(4)->t2_pseudo);
    EXPECT_NEAR(find(4)->estimated_depth, 5.0, 1e-6);
    T2_DEPTH_GATE = 0;
}

TEST_F(ZetaFixture, StarvePredicateTruthTable)
{
    EXPECT_FALSE(t2_starve_now(true, 10, 0));    // floor 0 = off
    EXPECT_FALSE(t2_starve_now(false, 10, 40));  // INITIAL never armed
    EXPECT_FALSE(t2_starve_now(true, 40, 40));   // at floor = not starved (strict <)
    EXPECT_TRUE(t2_starve_now(true, 39, 40));    // just below floor
    EXPECT_TRUE(t2_starve_now(true, 9, 40));     // deep starvation (X1prime burst band)
    EXPECT_TRUE(t2_starve_now(true, 130, 150));  // hypothetical high floor
}

TEST_F(ZetaFixture, DefaultsAreOff)
{
    // absent keys = legacy bit-identical: knobs default off
    T2_PSEUDO_DROP = 0; T2_STARVE_FLOOR = 0; T2_STARVE_ALPHA = 1.0;
    EXPECT_EQ(T2_PSEUDO_DROP, 0);
    EXPECT_EQ(T2_STARVE_FLOOR, 0);
    EXPECT_DOUBLE_EQ(T2_STARVE_ALPHA, 1.0);
    EXPECT_FALSE(t2_starve_now(true, 9, T2_STARVE_FLOOR));
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
