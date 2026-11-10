// 2026-11-10（整改 N-02）: camera_pose 跳变判据 gtest。
//
// 被测: px4ctrl_gate::poseJumpCheck()（pose_jump_gate.h，纯函数、无 ROS）
// 背景: 旧实现 dt = msg->header.stamp - 到达墙钟 -> 恒 ≤0 -> `dt > 1e-3` 恒假
//       -> "位置跳变 >3 m/s" 这一面从上线起从未生效。
// 本文件的 StampGoesBackwards / DtZero 两个用例锚定"时间戳异常必须显式上报"，
// 这是旧实现静默跳过的地方。
#include <gtest/gtest.h>

#include <limits>

#include "pose_jump_gate.h"

using px4ctrl_gate::PoseJumpCfg;
using px4ctrl_gate::poseJumpCheck;

namespace
{
const Eigen::Vector3d kOrigin = Eigen::Vector3d::Zero();
PoseJumpCfg cfg() { return PoseJumpCfg(); }  // min_dt 1e-3, max 3.0 m/s
}  // namespace

// 正常帧：1 cm / 10 ms = 1 m/s -> 不触发
TEST(PoseJump, HealthyFrame)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0.01, 0, 0), 0.010, cfg());
    EXPECT_FALSE(o.bad);
    EXPECT_FALSE(o.stamp_anomaly);
    EXPECT_NEAR(o.v_implied, 1.0, 1e-9);
}

// 真实跳变：0.5 m / 10 ms = 50 m/s -> 触发
TEST(PoseJump, RealJumpTrips)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0.5, 0, 0), 0.010, cfg());
    EXPECT_TRUE(o.bad);
    EXPECT_NEAR(o.v_implied, 50.0, 1e-9);
}

// 阈值边界：恰好 3 m/s -> 不触发（判据是严格大于）
TEST(PoseJump, BoundaryIsExclusive)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0.03, 0, 0), 0.010, cfg());
    EXPECT_FALSE(o.bad);
}

// 回归锚: 时间戳回退（旧实现里这条路径静默跳过，永不告警）
// 物理含义: 同一帧的 header.stamp 比上一帧还早 -> dt<0 -> 判据不可用，必须上报
TEST(PoseJump, StampGoesBackwards)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0.5, 0, 0), -0.05, cfg());
    EXPECT_TRUE(o.stamp_anomaly);
    EXPECT_FALSE(o.bad);  // 判据不可用时不许"凭空判跳变"，只上报
}

// 回归锚: dt=0（消息戳停住/重复）同样必须上报
TEST(PoseJump, DtZero)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0.5, 0, 0), 0.0, cfg());
    EXPECT_TRUE(o.stamp_anomaly);
}

// 非有限位置：必须判 bad（含 NaN 的位置绝不能进控制）
TEST(PoseJump, NonFinitePositionIsBad)
{
    Eigen::Vector3d nan_p(0.0, std::numeric_limits<double>::quiet_NaN(), 0.0);
    const auto o = poseJumpCheck(kOrigin, nan_p, 0.010, cfg());
    EXPECT_TRUE(o.bad);
    EXPECT_TRUE(o.non_finite);
}

// 负方向跳变同样触发（对称性）
TEST(PoseJump, NegativeJumpTrips)
{
    const auto o = poseJumpCheck(kOrigin, Eigen::Vector3d(0, -0.5, 0), 0.010, cfg());
    EXPECT_TRUE(o.bad);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
