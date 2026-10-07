// T2NANDEF (v11.17 2.1): NaN 防线四件判定纯函数 gtest(prereg nan_defense_v1)。
#include "estimator/t2_nan_defense.h"
#include <gtest/gtest.h>
#include <limits>

static const double kInf = std::numeric_limits<double>::infinity();
static const double kNaN = std::numeric_limits<double>::quiet_NaN();

TEST(NanDefD3, InitSolveOk)
{
    // 健康解:有限 cost+非 FAILURE+至少 1 迭代
    EXPECT_TRUE(t2nandef::init_solve_ok(123.4, 0, 3));
    EXPECT_TRUE(t2nandef::init_solve_ok(123.4, 1, 1));
    EXPECT_TRUE(t2nandef::init_solve_ok(0.0, 1, 2));   // cost=0 合法(有限即可,prereg 口径)
    // 非有限 cost 拒
    EXPECT_FALSE(t2nandef::init_solve_ok(kNaN, 0, 3));
    EXPECT_FALSE(t2nandef::init_solve_ok(kInf, 0, 3));
    EXPECT_FALSE(t2nandef::init_solve_ok(-kInf, 0, 3));
    // FAILURE 拒(C.1 风暴轮 1051 FAILURE 帧族)
    EXPECT_FALSE(t2nandef::init_solve_ok(123.4, t2nandef::CERES_FAILURE, 3));
    // 零迭代拒(未真解)
    EXPECT_FALSE(t2nandef::init_solve_ok(123.4, 0, 0));
    // 负迭代拒(防御)
    EXPECT_FALSE(t2nandef::init_solve_ok(123.4, 0, -1));
}

TEST(NanDefD4, MedianDegenerate)
{
    // 健康中位数(正有限)不触发
    EXPECT_FALSE(t2nandef::med_degenerate(65.0));
    EXPECT_FALSE(t2nandef::med_degenerate(1e-9));
    // -1 帧族(cost 未收敛期)/零/非有限触发(VRFY1 假触发机理)
    EXPECT_TRUE(t2nandef::med_degenerate(-1.0));
    EXPECT_TRUE(t2nandef::med_degenerate(0.0));
    EXPECT_TRUE(t2nandef::med_degenerate(kNaN));
    EXPECT_TRUE(t2nandef::med_degenerate(kInf));
    EXPECT_TRUE(t2nandef::med_degenerate(-kInf));
}

TEST(NanDefD5, BlockFinite)
{
    Eigen::VectorXd r(3);
    r << 1.0, -2.0, 0.5;
    using JM = Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;
    std::vector<JM> J{JM::Random(2, 2), JM::Random(3, 1)};
    EXPECT_TRUE(t2nandef::block_finite(r, J));          // 全有限过
    r[1] = kNaN;
    EXPECT_FALSE(t2nandef::block_finite(r, J));         // residual NaN 拒
    r[1] = kInf;
    EXPECT_FALSE(t2nandef::block_finite(r, J));         // residual Inf 拒
    r[1] = -2.0;
    J[0](1, 1) = kNaN;
    EXPECT_FALSE(t2nandef::block_finite(r, J));         // jacobian NaN 拒
    J[0](1, 1) = 1.0;
    J[1](2, 0) = kInf;
    EXPECT_FALSE(t2nandef::block_finite(r, J));         // 第二块 jacobian Inf 拒
    // 空输入=有限(首帧无 prior 块不拦)
    EXPECT_TRUE(t2nandef::block_finite(Eigen::VectorXd(0), {}));
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
