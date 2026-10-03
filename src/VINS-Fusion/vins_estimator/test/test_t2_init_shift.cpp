// T2-v8.3 unit-1b gtest (prereg_gatereset_initshift.md): shift-path INIT_DEPTH
// injection counter. removeBackShiftDepth with dep_j<=0 must (a) inject
// INIT_DEPTH, (b) increment t2_init_shift_total; a positive transfer must do
// neither. Backs the [T2gate] ir_shift= delta consumed by unit-2 forensics.
#include "estimator/feature_manager.h"
#include <gtest/gtest.h>
#include <cmath>

using namespace Eigen;

static Matrix3d Rs_arr[WINDOW_SIZE + 1];

namespace
{
Matrix3d RxPi()
{
    Matrix3d R = Matrix3d::Identity();
    R(1, 1) = -1; R(2, 2) = -1;  // 180 deg about x: flips z
    return R;
}

void addFeature(FeatureManager &fm, int id, double depth)
{
    FeaturePerId fid(id, 0);
    for (int k = 0; k < 3; k++)  // >=3 frames: slide erases frame[0], needs >=2 alive
    {
        double x = 0.1 * (k + 1), y = -0.05 * (k + 1);  // normalized image point (z=1)
        Matrix<double, 7, 1> pl;
        pl << x, y, 1.0, 460.0 * x + 320, 460.0 * y + 240, 0, 0;
        FeaturePerFrame f(pl, 0.0);
        fid.feature_per_frame.push_back(f);
    }
    fid.estimated_depth = depth;
    fm.feature.push_back(fid);
}
} // namespace

TEST(T2InitShift, NegativeTransferCountsAndInjects)
{
    FeatureManager fm(Rs_arr);
    addFeature(fm, 7, 3.0);
    long before = fm.t2_init_shift_total;
    // marg pose identity, new pose flipped: repro z = -3.0 <= 0
    fm.removeBackShiftDepth(Matrix3d::Identity(), Vector3d::Zero(), RxPi(), Vector3d::Zero());
    EXPECT_EQ(fm.t2_init_shift_total, before + 1);
    ASSERT_FALSE(fm.feature.empty());
    EXPECT_NEAR(fm.feature.front().estimated_depth, INIT_DEPTH, 1e-12);
}

TEST(T2InitShift, PositiveTransferDoesNotCount)
{
    FeatureManager fm(Rs_arr);
    addFeature(fm, 8, 3.0);
    long before = fm.t2_init_shift_total;
    // both poses identity: repro z = +3.0 (transfer keeps measured depth)
    fm.removeBackShiftDepth(Matrix3d::Identity(), Vector3d::Zero(),
                            Matrix3d::Identity(), Vector3d::Zero());
    EXPECT_EQ(fm.t2_init_shift_total, before);
    ASSERT_FALSE(fm.feature.empty());
    EXPECT_NEAR(fm.feature.front().estimated_depth, 3.0, 1e-12);
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
