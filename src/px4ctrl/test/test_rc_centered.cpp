// 2026-11-10（整改 F-01）: RC 居中判据回归锚。
//
// 被测: RC_Data_t::check_centered()（input.cpp）
// 背景: 旧实现写的是 `abs(ch[0]) < 1e-5 && abs(ch[0]) < 1e-5 && ...` 四遍 ——
//       四次都判 ch[0](roll)，pitch/throttle/yaw 三个杆从未参与。该函数是
//       AUTO_TAKEOFF 的唯一 RC 护栏（fsm_decision::decide_manual 的 RJ_RC_GUARD）。
// 本文件里 OffCenterPitch / OffCenterThrottle / OffCenterYaw 三个用例在旧实现上**必红**，
// 是"改前红、改后绿"的注入证据（见 tools/ci/inject_tests/）。
#include <gtest/gtest.h>

#include "input.h"

namespace
{
// ch[] 只在 feed() 里被写；本测直接摆归一化后的杆量（死区已折算，见 input.h 注释）。
RC_Data_t make_rc(double ch0, double ch1, double ch2, double ch3)
{
    RC_Data_t rc;
    rc.ch[0] = ch0;
    rc.ch[1] = ch1;
    rc.ch[2] = ch2;
    rc.ch[3] = ch3;
    return rc;
}
}  // namespace

// 全中位 -> 允许起飞
TEST(RcCentered, AllCentered)
{
    RC_Data_t rc = make_rc(0.0, 0.0, 0.0, 0.0);
    EXPECT_TRUE(rc.check_centered());
}

// 回归锚: 只有 roll 偏 —— 新旧实现都应拒绝（这条不是区分用例）
TEST(RcCentered, OffCenterRoll)
{
    RC_Data_t rc = make_rc(0.4, 0.0, 0.0, 0.0);
    EXPECT_FALSE(rc.check_centered());
}

// 回归锚: 只有 pitch 偏 —— 旧实现返回 true（漏检），新实现必须 false
TEST(RcCentered, OffCenterPitch)
{
    RC_Data_t rc = make_rc(0.0, 0.4, 0.0, 0.0);
    EXPECT_FALSE(rc.check_centered());
}

// 回归锚: 只有 throttle 偏 —— 旧实现返回 true，新实现必须 false
TEST(RcCentered, OffCenterThrottle)
{
    RC_Data_t rc = make_rc(0.0, 0.0, 0.4, 0.0);
    EXPECT_FALSE(rc.check_centered());
}

// 回归锚: 只有 yaw 偏 —— 旧实现返回 true，新实现必须 false
TEST(RcCentered, OffCenterYaw)
{
    RC_Data_t rc = make_rc(0.0, 0.0, 0.0, 0.4);
    EXPECT_FALSE(rc.check_centered());
}

// 微小偏移（仍在死区外的最小可表示量）也必须判"不居中"：判据是严格相等语义
TEST(RcCentered, TinyOffsetIsNotCentered)
{
    RC_Data_t rc = make_rc(0.0, 1e-3, 0.0, 0.0);
    EXPECT_FALSE(rc.check_centered());
}

// 负方向偏同样拒绝（防止只判正向的对称性漏洞）
TEST(RcCentered, NegativeOffset)
{
    RC_Data_t rc = make_rc(0.0, 0.0, -0.4, 0.0);
    EXPECT_FALSE(rc.check_centered());
}

// 四杆同时偏也拒绝（不应因为"第一个就返回"而漏判后面）
TEST(RcCentered, AllSticksOffCenter)
{
    RC_Data_t rc = make_rc(0.4, -0.4, 0.4, -0.4);
    EXPECT_FALSE(rc.check_centered());
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
