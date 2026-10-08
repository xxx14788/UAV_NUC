#include <gtest/gtest.h>
#include "estimator/p3_notify_codec.h"

// T1 v11.31 2f gtest: P3 计划内 reboot 通告契约编码(p3_contract_design_v1)
// 单一来源=p3_notify_codec.h; 生产侧(estimator.cpp)与消费侧文档共用此编码。

TEST(P3NotifyCodec, EventCodesFrozen)
{
    EXPECT_EQ(1u, p3_codec::EV_REBOOT);
    EXPECT_EQ(2u, p3_codec::EV_RESUME);
}

TEST(P3NotifyCodec, EncodeDecodeRoundTrip)
{
    for (uint32_t cnt : {0u, 1u, 2u, 7u, 0xFFFEu, 0xFFFFu})
    {
        uint32_t v = p3_codec::encode(p3_codec::EV_REBOOT, cnt);
        EXPECT_EQ(p3_codec::EV_REBOOT, p3_codec::event_of(v));
        EXPECT_EQ(cnt, p3_codec::count_of(v));
        v = p3_codec::encode(p3_codec::EV_RESUME, cnt);
        EXPECT_EQ(p3_codec::EV_RESUME, p3_codec::event_of(v));
        EXPECT_EQ(cnt, p3_codec::count_of(v));
    }
}

TEST(P3NotifyCodec, CountWrapsAt16Bit)
{
    // 0x10000 & 0xFFFF == 0: 契约=低16位截断(计数以 65536 为周期, 消费侧只看变化)
    EXPECT_EQ(0u, p3_codec::count_of(p3_codec::encode(p3_codec::EV_REBOOT, 0x10000u)));
}

TEST(P3NotifyCodec, MonotonicWithinPeriod)
{
    uint32_t last = 0;
    for (uint32_t i = 1; i <= 1000; ++i)
    {
        uint32_t v = p3_codec::encode(p3_codec::EV_REBOOT, i);
        EXPECT_GT(v, last); // 同事件下编码随计数单调(发布侧变化检测依赖)
        last = v;
    }
}

TEST(P3NotifyCodec, InitialValueContract)
{
    // 话题无事件时零值=未通告(消费侧 p3_notify_seen 门)
    EXPECT_EQ(0u, p3_codec::encode(0, 0));
    EXPECT_EQ(0u, p3_codec::event_of(0));
    EXPECT_EQ(0u, p3_codec::count_of(0));
}
