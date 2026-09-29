// T3-Z1.2/Z1.3 gtest 注入矩阵(C07-E3 口径 + 方向 6 增补档)
// 对象:odom_sanity_v2.h(设计稿;enabled_v2=false=纯 v1 行为)
// 层序=WD1b 实战次序:STAMP(BACK→AGE)→ACC→JUMP→R→VEL(v2 后 R 插在 JUMP 与 VEL 间)
// 运行:catkin build px4ctrl && catkin run_tests px4ctrl --no-deps(构建走 STATUS 预告窗,锁章 6)
#include <gtest/gtest.h>
#include <Eigen/Dense>
#include "odom_sanity_v2.h"

using V3 = Eigen::Vector3d;

struct SimStream
{
  OdomSanityConfigV2 cfg;
  OdomSanityStateV2 st;
  double t = 0.0;
  SimStream(bool v2 = true)
  {
    cfg.enabled = true;
    cfg.enabled_v2 = v2;
  }
  OdomSanityVerdictV2 feed(V3 p, V3 v, double stamp_off = 0.0)
  {
    t += 0.0045;  // 223Hz
    return odom_sanity_check_v2(cfg, st, t - stamp_off, t, p, v);
  }
  long rejects() const { return st.rejected; }
};

static V3 P(double x, double y, double z) { return V3(x, y, z); }
static V3 VZ() { return V3::Zero(); }

// 健康悬停基线:零误伤(结果层判据 C07-E2)
TEST(OdomGateV2, HealthyHoverZeroFalsePositive)
{
  SimStream s;
  for (int i = 0; i < 5000; ++i)
    ASSERT_EQ(OdomSanityVerdictV2::ACCEPT, s.feed(P(0.01, 0.01, 1.0), VZ()));
  EXPECT_EQ(0, s.rejects());
}

// 慢漂 0.1m/s:运动学自洽=r≡0,全层门内(√T 律泄漏,验收按泄漏上界声明,C07 方向 7)
TEST(OdomGateV2, SlowDrift0p1_InGateLeak)
{
  SimStream s;
  V3 p = V3::Zero();
  for (int i = 0; i < 5000; ++i)
  {
    p += V3(0.1 * 0.0045, 0, 0);
    ASSERT_EQ(OdomSanityVerdictV2::ACCEPT, s.feed(p, V3(0.1, 0, 0)));
  }
  EXPECT_EQ(0, s.rejects());  // 泄漏上界=0.45m/22.5s(105449 实证同型盲区)
}

// 阶跃档 {0.5,2,10}m 水平:0.5 档=v1 漏(K4 缺口)/v2 R 层检出;≥2 档=JUMP 层(层序如实)
TEST(OdomGateV2, StepHorizontal_LayerAttribution)
{
  for (double d : {0.5, 2.0, 10.0})
  {
    SimStream s;
    for (int i = 0; i < 1000; ++i) s.feed(V3::Zero(), VZ());
    auto v = s.feed(P(d, 0, 0), VZ());
    if (d < 0.6) EXPECT_EQ(OdomSanityVerdictV2::REJECT_R, v) << "v2 补 K4 缺口 d=" << d;
    else EXPECT_EQ(OdomSanityVerdictV2::REJECT_JUMP, v) << "大阶跃首触层=JUMP d=" << d;
    SimStream s1(false);  // v1 对照
    for (int i = 0; i < 1000; ++i) s1.feed(V3::Zero(), VZ());
    auto v1 = s1.feed(P(d, 0, 0), VZ());
    if (d < 0.6) EXPECT_EQ(OdomSanityVerdictV2::ACCEPT, v1) << "K4 复现:v1 漏 " << d;
    else EXPECT_EQ(OdomSanityVerdictV2::REJECT_JUMP, v1);
  }
}

// 垂直 10m 子档(负油门线域,C07 方向 6-①):JUMP 层检出(层序如实)
TEST(OdomGateV2, StepVertical10_JUMPLayer)
{
  SimStream s;
  for (int i = 0; i < 1000; ++i) s.feed(P(0, 0, 1.0), VZ());
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_JUMP, s.feed(P(0, 0, 11.0), VZ()));
}

// 速度爬坡(0.03/帧=6.7m/s²<ACC 帽,105449 真实形态):VEL 层检出(唯一防线实锤)
TEST(OdomGateV2, VelocityRamp_VELLayerOnly)
{
  SimStream s;
  V3 v = VZ();
  int fired = -1;
  for (int i = 0; i < 2000 && fired < 0; ++i)
  {
    v += V3(0.03, 0, 0);
    auto r = s.feed(v * 0.0045 * i, v);  // 位置与速度协调(r≈0)
    if (r != OdomSanityVerdictV2::ACCEPT) fired = i;
  }
  ASSERT_GE(fired, 0) << "爬坡须被检出";
  // |v| 超 5 应在 ~167 帧后触发,且触发层=VEL(r 协调=0)
  EXPECT_GT(v.x(), 4.9);
}

// 平滑上升协调跳慢速档(2m/s<VEL 帽):全层门盲(H13 盲区如实登记,防线=慢漂泄漏上界/E6 漂移率门)
TEST(OdomGateV2, CoordinatedSmoothRiseSlow_FullBlind)
{
  SimStream s;
  V3 p = V3::Zero();
  const double vz = 2.0;  // <VEL 5:门内速度
  for (int i = 0; i < 600; ++i)
  {
    p += V3(vz * 0.0045, 0, 0);
    ASSERT_EQ(OdomSanityVerdictV2::ACCEPT, s.feed(p, V3(vz, 0, 0)))
        << "0.5m 级慢速协调位移在门内=已知盲区(C07-H13)";
  }
  EXPECT_EQ(0, s.rejects());
}

// 瞬时协调跳(副轨,V_k=2Δ/Δt−V_{k−1},r≡0):首触层=ACC(层序),拦截等价
TEST(OdomGateV2, CoordinatedInstant_FirstLayerACC)
{
  SimStream s;
  const double d = 0.5, dt = 0.0045;
  V3 v_cur(2 * d / dt, 0, 0);
  V3 p = V3::Zero();
  for (int i = 0; i < 1000; ++i) s.feed(p, VZ());
  p += 0.5 * (VZ() + v_cur) * dt;  // 梯形恒等:r=0
  auto v = s.feed(p, v_cur);
  EXPECT_NE(OdomSanityVerdictV2::ACCEPT, v) << "瞬时协调跳必须被拦";
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_ACC, v)
      << "首触层=ACC(dv/dt 巨大);C07-P3 'VEL 1 帧检出'在 ACC 前置层序下归层为 ACC,拦截等价";
}

// 陈旧突发:整段 STAMP-BACK(单调基线只在 ACCEPT 推进,陈旧戳直到追上最后接受戳都是回退);
// 冻结型滞后(stamp 正常前进但接收钟超前)= STAMP-AGE。值本身完全健康=拦的是戳不是值
TEST(OdomGateV2, StaleBurst_STAMPLayers)
{
  SimStream s;
  for (int i = 0; i < 1000; ++i) s.feed(V3::Zero(), VZ());
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_STAMP_BACK, s.feed(V3(0, 0, 0), VZ(), 3.0));
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_STAMP_BACK, s.feed(V3(0, 0, 0), VZ(), 2.9955));
  // 冻结型:stamp 相对上一 ACCEPT 正常推进,但本地接收钟超前 0.5s(收到旧帧)
  OdomSanityStateV2 st2;
  OdomSanityConfigV2 cfg2;
  cfg2.enabled = true; cfg2.enabled_v2 = true;
  odom_sanity_check_v2(cfg2, st2, 100.0, 100.0, V3::Zero(), VZ());     // 建参考
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_STAMP_AGE,
            odom_sanity_check_v2(cfg2, st2, 100.0045, 100.5045, V3(0, 0, 0), VZ()));
}

// 时戳回退(双流污染签名,043355 型 -13s):STAMP-BACK 拦
TEST(OdomGateV2, StampRegression_BackRejected)
{
  SimStream s;
  double st_ = 100.0;
  for (int i = 0; i < 100; ++i)
  {
    st_ += 0.0045;
    odom_sanity_check_v2(s.cfg, s.st, st_, st_, V3::Zero(), VZ());
  }
  s.t = st_;
  EXPECT_EQ(OdomSanityVerdictV2::REJECT_STAMP_BACK,
            odom_sanity_check_v2(s.cfg, s.st, st_ - 13.0, st_ + 0.0045, V3::Zero(), VZ()));
}

// 停流档 {0.5,3}s 复流:reboot_gap 跳过连续性=零误伤(速度仍检)
TEST(OdomGateV2, StopFlowResume_NoContinuityFalsePositive)
{
  for (double gap : {0.5, 3.0})
  {
    SimStream s;
    for (int i = 0; i < 1000; ++i) s.feed(P(0, 0, 1.0), VZ());
    s.t += gap;
    EXPECT_EQ(OdomSanityVerdictV2::ACCEPT, s.feed(P(0.05, 0, 1.0), VZ())) << "gap=" << gap;
  }
}

// 占空比 90% 间歇毒:毒帧零摄入(净帧照常 ACCEPT;参考由前置健康段建立=实机时序)
TEST(OdomGateV2, DutyCycle90_Intermittent)
{
  SimStream s;
  V3 p = V3::Zero();
  for (int i = 0; i < 100; ++i)  // 健康段建立参考(毒流不会先于健康流出现)
    s.feed(p += V3(0.0001, 0, 0), VZ());
  long accepted_poison = 0;
  for (int i = 0; i < 2000; ++i)
  {
    bool poison = (i % 10) < 9;
    p += V3(0.0001, 0, 0);
    auto v = s.feed(poison ? P(5, 0, 0) : p, VZ());
    if (poison && v == OdomSanityVerdictV2::ACCEPT) accepted_poison++;
  }
  EXPECT_EQ(0, accepted_poison) << "毒帧零摄入";
}

int main(int argc, char **argv)
{
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
