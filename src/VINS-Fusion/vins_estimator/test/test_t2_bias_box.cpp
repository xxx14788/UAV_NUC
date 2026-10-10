#include <gtest/gtest.h>
#include <cmath>
#include <cstring>
#include "estimator/t2_bias_box.h"

// T2-v10.10 ②a gtest (prereg bias_constraint2_design_v1.md, md5 c16f59c1):
//  1) frozen-domain lock — layout indices + half-widths match the design
//  2) off path (default 0) applies ZERO bounds and is bit-identical to a bare
//     problem (regression zero-drift lock — arm-batch B-side iron rule)
//  3) on path clamps Ba to ±0.5 m/s² and Bg to ±0.05 rad/s, V(0..2) free
//  4) on path leaves interior targets untouched (box inactive inside domain)

namespace {
// deterministic separable quadratic: r_k = w_k * (sb_k - target_k)
struct PullToTarget {
    double target[9], w[9];
    template <typename T>
    bool operator()(const T *const sb, T *r) const
    {
        for (int k = 0; k < 9; k++) r[k] = T(w[k]) * (sb[k] - T(target[k]));
        return true;
    }
};

// build + solve the tiny problem; returns bounds set by the helper (if used)
int solve_tiny(double *x, const double *target, bool use_helper)
{
    ceres::Problem problem;
    problem.AddParameterBlock(x, 9);
    ceres::CostFunction *cf = new ceres::AutoDiffCostFunction<PullToTarget, 9, 9>(
        new PullToTarget{/*target*/ {target[0], target[1], target[2], target[3], target[4],
                                      target[5], target[6], target[7], target[8]},
                         /*w*/ {1.0, 1.0, 1.0, 10.0, 10.0, 10.0, 100.0, 100.0, 100.0}});
    problem.AddResidualBlock(cf, nullptr, x);
    int bounds = use_helper ? T2BiasBox::apply(problem, x) : 0;
    ceres::Solver::Options opts;
    opts.minimizer_progress_to_stdout = false;
    opts.max_num_iterations = 200;
    opts.num_threads = 1;              // determinism for the bit-identity test
    opts.linear_solver_type = ceres::DENSE_QR;
    ceres::Solver::Summary summ;
    ceres::Solve(opts, &problem, &summ);
    EXPECT_TRUE(summ.IsSolutionUsable());
    return bounds;
}
} // namespace

TEST(T2BiasBox, FrozenDomainLock)
{
    EXPECT_EQ(T2BiasBox::BA0, 3);
    EXPECT_EQ(T2BiasBox::BG0, 6);
    EXPECT_DOUBLE_EQ(T2BiasBox::BA_HALF, 0.5);   // m/s^2, design ②a frozen
    EXPECT_DOUBLE_EQ(T2BiasBox::BG_HALF, 0.05);  // rad/s, design ②a frozen
}

TEST(T2BiasBox, OffPathNoOpBitIdentical)
{
    T2_BIAS_BOX = 0;  // default value in parameters.cpp must stay 0
    double target[9] = {2.0, -3.0, 0.5, 0.8, -0.9, 0.7, 0.06, -0.07, 0.2};
    double xA[9], xB[9];
    for (int k = 0; k < 9; k++) { xA[k] = xB[k] = 0.0; }  // identical starts
    int bA = solve_tiny(xA, target, /*use_helper*/ false);  // bare problem
    int bB = solve_tiny(xB, target, /*use_helper*/ true);   // helper on, switch off
    EXPECT_EQ(bA, 0);
    EXPECT_EQ(bB, 0);                       // off switch sets zero bounds
    EXPECT_EQ(0, std::memcmp(xA, xB, sizeof(xA)));  // bit-identical solutions
    // sanity: both actually solved to the free optimum (far outside the box domain)
    for (int k = 0; k < 9; k++) EXPECT_NEAR(xA[k], target[k], 1e-8);
}

TEST(T2BiasBox, OnPathClampsBiasDomain)
{
    T2_BIAS_BOX = 1;
    // targets far outside: V free stays; Ba clamps ±0.5; Bg clamps ±0.05
    double target[9] = {2.0, -3.0, 0.5, 10.0, -10.0, 3.0, 1.0, -1.0, 0.3};
    double x[9];
    for (int k = 0; k < 9; k++) x[k] = 0.0;
    int bounds = solve_tiny(x, target, true);
    EXPECT_EQ(bounds, 12);                  // 3 comps x (lower+upper) x (Ba+Bg)
    double want[9] = {2.0, -3.0, 0.5, 0.5, -0.5, 0.5, 0.05, -0.05, 0.05};
    for (int k = 0; k < 9; k++) EXPECT_NEAR(x[k], want[k], 5e-3);  // solver tol at active bound
    // hard guarantee: never beyond the box (exact bound respect, no tol)
    for (int k = 3; k < 6; k++) EXPECT_LE(std::fabs(x[k]), 0.5 + 1e-9);
    for (int k = 6; k < 9; k++) EXPECT_LE(std::fabs(x[k]), 0.05 + 1e-9);
}

TEST(T2BiasBox, OnPathInteriorUnchanged)
{
    T2_BIAS_BOX = 1;
    // targets strictly inside the domain: box must not distort the optimum
    double target[9] = {0.1, 0.0, -0.2, 0.2, -0.1, 0.05, 0.01, -0.02, 0.005};
    double x[9];
    for (int k = 0; k < 9; k++) x[k] = 0.0;
    int bounds = solve_tiny(x, target, true);
    EXPECT_EQ(bounds, 12);
    for (int k = 0; k < 9; k++) EXPECT_NEAR(x[k], target[k], 1e-8);
}

// ---- T2-v10.10 ②b transit relative lock ----

TEST(T2BiasTlock, WindowPredicateFrozen)
{
    EXPECT_DOUBLE_EQ(T2BiasTlockLogic::ENGAGE_V, 0.3);
    EXPECT_DOUBLE_EQ(T2BiasTlockLogic::RELEASE_V, 0.2);
}

TEST(T2BiasTlock, Transitions)
{
    EXPECT_EQ(T2BiasTlockLogic::transition(false, 0.05), 0);  // ground: no change
    EXPECT_EQ(T2BiasTlockLogic::transition(false, 0.3), 0);   // at threshold: not over
    EXPECT_EQ(T2BiasTlockLogic::transition(false, 0.31), 1);  // engage
    EXPECT_EQ(T2BiasTlockLogic::transition(true, 0.25), 0);   // transit coast: hold
    EXPECT_EQ(T2BiasTlockLogic::transition(true, 0.19), -1);  // release below
    EXPECT_EQ(T2BiasTlockLogic::transition(true, 0.4), 0);    // armed stays armed
}

TEST(T2BiasTlock, DefaultsLock)
{
    // parameters.cpp in-library defaults: 2b master off = legacy; W = gradient mid
    EXPECT_EQ(T2_BIAS_TLOCK, 0);
    EXPECT_DOUBLE_EQ(T2_BIAS_TLOCK_W, 10.0);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
