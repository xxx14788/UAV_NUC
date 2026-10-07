// T1-v1125 M2 腿B gtest: t2_iqg_should_reject 纯逻辑(INPUTFACE-SCREEN)
// 覆盖: 默认关/staging(init 放行/宽限期放行/稳态启用)/三键各自触发/边界值/fail-open 语义
#include <gtest/gtest.h>
#include "estimator/parameters.h"

class IQGTest : public ::testing::Test
{
protected:
    int saved_gate, saved_corners, saved_consec;
    double saved_dr, saved_band, saved_sr, saved_n;
    void SetUp() override
    {
        saved_gate = T2_IQG_GATE; saved_corners = T2_IQG_MIN_CORNERS;
        saved_dr = T2_IQG_MIN_DEPTH_RATIO; saved_band = T2_IQG_MAX_DEPTH_M;
        saved_sr = T2_IQG_MIN_STEREO_RATIO; saved_n = T2_IQG_STAGED_N_SEC;
        saved_consec = T2_IQG_MAX_CONSEC_REJECT;
        T2_IQG_MIN_CORNERS = 80; T2_IQG_MIN_DEPTH_RATIO = 0.5;
        T2_IQG_MAX_DEPTH_M = 100.0; T2_IQG_MIN_STEREO_RATIO = 0.3;
        T2_IQG_MAX_CONSEC_REJECT = 30;
    }
    void TearDown() override
    {
        T2_IQG_GATE = saved_gate; T2_IQG_MIN_CORNERS = saved_corners;
        T2_IQG_MIN_DEPTH_RATIO = saved_dr; T2_IQG_MAX_DEPTH_M = saved_band;
        T2_IQG_MIN_STEREO_RATIO = saved_sr; T2_IQG_STAGED_N_SEC = saved_n;
        T2_IQG_MAX_CONSEC_REJECT = saved_consec;
    }
    T2IQGMetrics mk(int corners, double dr, double sr)
    {
        T2IQGMetrics m; m.corners = corners; m.depth_ok_ratio = dr;
        m.stereo_pair_ratio = sr; return m;
    }
};

TEST_F(IQGTest, StagingInitPassesAll)
{  // init 期(非稳态):坏帧也放行(保 Bgs 解)
    EXPECT_FALSE(t2_iqg_should_reject(false, mk(0, 0.0, 0.0), 0, nullptr));
}

TEST_F(IQGTest, StagingSteadyRejectsBadSupply)
{  // 稳态:角点数低于下限→拒
    EXPECT_TRUE(t2_iqg_should_reject(true, mk(79, 0.9, 0.9), 0, nullptr));
    EXPECT_FALSE(t2_iqg_should_reject(true, mk(80, 0.9, 0.9), 0, nullptr));  // 边界=过
}

TEST_F(IQGTest, DepthRatioKey)
{
    EXPECT_TRUE(t2_iqg_should_reject(true, mk(150, 0.49, 0.9), 0, nullptr));
    EXPECT_FALSE(t2_iqg_should_reject(true, mk(150, 0.50, 0.9), 0, nullptr));
}

TEST_F(IQGTest, StereoPairKey)
{
    EXPECT_TRUE(t2_iqg_should_reject(true, mk(150, 0.9, 0.29), 0, nullptr));
    EXPECT_FALSE(t2_iqg_should_reject(true, mk(150, 0.9, 0.30), 0, nullptr));
}

TEST_F(IQGTest, HealthyFramePasses)
{
    EXPECT_FALSE(t2_iqg_should_reject(true, mk(150, 0.95, 0.8), 0, nullptr));
}

TEST_F(IQGTest, FailOpenAfterConsecCap)
{  // 连续拒收达上限→放行(防门致盲飞);计数清零后门重新武装
    const char *r = nullptr;
    EXPECT_FALSE(t2_iqg_should_reject(true, mk(0, 0.0, 0.0), 30, &r));
    EXPECT_STREQ(r, "fail-open");
    EXPECT_TRUE(t2_iqg_should_reject(true, mk(0, 0.0, 0.0), 29, &r));
}

TEST_F(IQGTest, ReasonReporting)
{
    const char *r = nullptr;
    t2_iqg_should_reject(true, mk(10, 0.9, 0.9), 0, &r);
    EXPECT_STREQ(r, "corners");
    t2_iqg_should_reject(true, mk(150, 0.1, 0.9), 0, &r);
    EXPECT_STREQ(r, "depth");
    t2_iqg_should_reject(true, mk(150, 0.9, 0.1), 0, &r);
    EXPECT_STREQ(r, "stereo");
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
