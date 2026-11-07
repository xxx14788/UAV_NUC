// 2026-11-07 起飞地面锁定（GROUND_LOCK，判读 v1 §3）离地判定纯函数测试
// 被测：ctrl_core.h::groundLockStep —— 双门(dz/vz) + 确认窗 + 滞回
#include <gtest/gtest.h>
#include "ctrl_core.h"

using namespace px4ctrl_core;

namespace
{
GroundLockCfg cfgOn()
{
  GroundLockCfg c;
  c.enable = true;
  c.z_release = 0.06;
  c.vz_release = 0.05;
  c.confirm_s = 0.15;
  return c;
}
} // namespace

// 1) enable=false：永不锁定（= 旧行为；代码默认值必须是这个）
TEST(GroundLock, DisabledNeverLocks)
{
  GroundLockCfg c = cfgOn();
  c.enable = false;
  GroundLockState s;
  GroundLockOut o = groundLockStep(true, 0.0, 0.0, 0.0, c, s);
  EXPECT_FALSE(o.locked);
  EXPECT_FALSE(o.next.airborne);
}

// 2) 非起飞态：复位，保证下一次起飞重新判定
TEST(GroundLock, NotInTakeoffResets)
{
  GroundLockCfg c = cfgOn();
  GroundLockState s;
  s.airborne = true;
  s.since = 3.0;
  GroundLockOut o = groundLockStep(false, 1.0, 1.0, 10.0, c, s);
  EXPECT_FALSE(o.locked);
  EXPECT_FALSE(o.next.airborne);
  EXPECT_LT(o.next.since, 0.0);
}

// 3) 地面静止：恒锁（这是"起飞前姿态指令必须是水平"的前提）
TEST(GroundLock, GroundedStaysLocked)
{
  GroundLockCfg c = cfgOn();
  GroundLockState s;
  for (double t = 0.0; t < 3.0; t += 0.01)
  {
    GroundLockOut o = groundLockStep(true, 0.005, 0.0, t, c, s);
    ASSERT_TRUE(o.locked) << "t=" << t;
    ASSERT_FALSE(o.just_airborne);
    s = o.next;
  }
}

// 4) 双门必须同时成立；确认窗未满不放锁
TEST(GroundLock, NeedsBothGatesAndWindow)
{
  GroundLockCfg c = cfgOn();
  GroundLockState s;
  GroundLockOut o = groundLockStep(true, 0.10, 0.0, 0.0, c, s); // 只有 dz 过门
  ASSERT_TRUE(o.locked);
  EXPECT_LT(o.next.since, 0.0);
  s = o.next;
  o = groundLockStep(true, 0.0, 0.20, 0.05, c, s); // 只有 vz 过门
  ASSERT_TRUE(o.locked);
  EXPECT_LT(o.next.since, 0.0);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 1.00, c, s); // 双门成立，1.00 起计时
  ASSERT_TRUE(o.locked);
  ASSERT_GT(o.next.since, 0.0);
  s = o.next;
  o = groundLockStep(true, 0.12, 0.20, 1.14, c, s); // 窗内
  ASSERT_TRUE(o.locked);
  ASSERT_FALSE(o.just_airborne);
  s = o.next;
  // 窗满（用 1.16 而非 1.15：1.15-1.00=0.1499999999999999 < 0.15，FP 边界）
  o = groundLockStep(true, 0.12, 0.20, 1.16, c, s);
  ASSERT_FALSE(o.locked);
  ASSERT_TRUE(o.just_airborne);
  ASSERT_TRUE(o.next.airborne);
}

// 5) 放锁只发生一次；之后 dz 掉回地面值也不再锁（本次起飞不回退）
TEST(GroundLock, ReleasesOnceThenStaysAirborne)
{
  GroundLockCfg c = cfgOn();
  GroundLockState s;
  GroundLockOut o = groundLockStep(true, 0.10, 0.20, 0.0, c, s);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 0.20, c, s);
  ASSERT_TRUE(o.just_airborne);
  s = o.next;
  for (double t = 0.30; t < 2.0; t += 0.05)
  {
    o = groundLockStep(true, 0.0, -0.10, t, c, s);
    ASSERT_FALSE(o.locked) << "t=" << t;
    ASSERT_FALSE(o.just_airborne) << "t=" << t;
    s = o.next;
  }
}

// 6) 确认窗中途任一门掉落：重计时（防"抖一下就算离地"）
TEST(GroundLock, GateDropRestartsWindow)
{
  GroundLockCfg c = cfgOn();
  GroundLockState s;
  GroundLockOut o = groundLockStep(true, 0.10, 0.20, 0.00, c, s); // since=0
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 0.10, c, s); // 0.10<0.15 仍锁
  ASSERT_TRUE(o.locked);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.01, 0.12, c, s); // vz 掉落 -> 重计时
  ASSERT_TRUE(o.locked);
  ASSERT_LT(o.next.since, 0.0);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 0.13, c, s); // 重新从 0.13 计时
  ASSERT_TRUE(o.locked);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 0.27, c, s); // 0.14<0.15 仍锁（未重计时会误放）
  ASSERT_TRUE(o.locked);
  s = o.next;
  o = groundLockStep(true, 0.10, 0.20, 0.29, c, s); // 0.16>=0.15 放开
  ASSERT_TRUE(o.just_airborne);
}

// 7) takeoffRef 斜坡剖面（ref_accel 用）自检：单调、速度/加速度有界、末态到位
TEST(TakeoffRefRamp, ProfileBoundedAndArrives)
{
  TakeoffCfg c;
  c.height = 0.75;
  c.speed = 0.45;
  c.acc = 0.8;
  c.spinup = 0.0;
  double prev_p = -1.0;
  for (double t = 0.0; t <= 5.0; t += 0.005)
  {
    const Ref r = takeoffRef(t, c);
    EXPECT_GE(r.v, -1e-9) << "t=" << t;
    EXPECT_LE(r.v, c.speed + 1e-9) << "t=" << t;
    EXPECT_LE(std::fabs(r.a), c.acc + 1e-9) << "t=" << t;
    EXPECT_GE(r.p, prev_p - 1e-9) << "t=" << t;
    prev_p = r.p;
  }
  const Ref end = takeoffRef(5.0, c);
  EXPECT_NEAR(end.p, c.height, 1e-9);
  EXPECT_NEAR(end.v, 0.0, 1e-9);
  EXPECT_NEAR(end.a, 0.0, 1e-9);
}

// 8) takeoffRef 三角剖面（高度太矮）自检
TEST(TakeoffRefRamp, TriangleProfileArrives)
{
  TakeoffCfg c;
  c.height = 0.20; // < 2*d_acc=0.45 -> 三角
  c.speed = 0.45;
  c.acc = 0.8;
  c.spinup = 0.0;
  const Ref end = takeoffRef(5.0, c);
  EXPECT_NEAR(end.p, c.height, 1e-9);
  EXPECT_NEAR(end.v, 0.0, 1e-9);
}

int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
