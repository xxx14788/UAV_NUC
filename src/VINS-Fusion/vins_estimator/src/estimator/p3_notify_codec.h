// T1 v11.31 2f P3: reboot_notify 载荷编码单一来源(p3_contract_design_v1)
// 契约: /vins_estimator/reboot_notify (std_msgs/UInt32, latched)
//   高16位=事件类型(1=reboot, 2=resume), 低16位=累计计数(截断)
#pragma once
#include <cstdint>

namespace p3_codec
{
constexpr uint32_t EV_REBOOT = 1;
constexpr uint32_t EV_RESUME = 2;

inline uint32_t encode(uint32_t ev, uint32_t cnt)
{
    return ((ev & 0xFFFFu) << 16) | (cnt & 0xFFFFu);
}
inline uint32_t event_of(uint32_t v) { return v >> 16; }
inline uint32_t count_of(uint32_t v) { return v & 0xFFFFu; }
}
