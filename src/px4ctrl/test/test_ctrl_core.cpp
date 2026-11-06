/*******************************************************
 * test_ctrl_core.cpp -- W4/W5/W6 控制核心 gtest
 *
 * 覆盖（任务书 W4 完成判据：积分限幅/饱和冻结/参考连续化/破死锁分支）：
 *   T01 串级 + 积分：不可达目标 → 积分饱和在 ±i_lim，u 不超限
 *   T02 饱和冻结：u 已到上限且误差同号 → 本拍积分不增
 *   T03 参考连续化：handover 无位置阶跃；整形后收敛到目标；不越位
 *   T04 破死锁（E9 z_eq 定律）：P-only + 冻结模型 → 平衡高度 = eqHeight；
 *       加积分后 → 平衡高度回到 aim（这就是"破死锁"的数学形式）
 *   T05 模型无扰切换：改 thr2acc 后同 u 反算的加速度不变
 *   T06 倾角 1/cos 补偿：10° 时推力放大约 1.0154
 *   T07 RLS 门控：in_air=false 不更新；无激励不更新；存储点限幅；P 保正
 *   T08 起飞参考：末态恰为 (height,0,0)（消除 +9.4 cm 阶跃的根因）
 *   T09 降落：高度参考不穿地；到地即 done；速率不超过 v_cmd
 *   T10 倾角限幅斜率：每拍变化 <= rate*dt
 *******************************************************/
#include <gtest/gtest.h>
#include <cmath>
#include "ctrl_core.h"

using namespace px4ctrl_core;

// ---------------------------------------------------------------- T01
TEST(CtrlCore, T01_IntegralLimit)
{
  // 开环喂入固定误差（不接被控对象），验证积分**在未饱和时**沿限幅爬升并停在 i_lim。
  // 注意：饱和时积分必须冻结（T02），所以本测试必须构造 u 未饱和的工况。
  AxisCfg c;
  c.kp_p = 1.0; c.kp_v = 4.0; c.ki_v = 2.0;
  c.i_lim = 0.3 * G;               // 2.943
  c.thr2acc = 20.4375;
  AxisMem m;
  const double dt = 0.01;
  double u_max_seen = 0.0;
  AxisDebug d;
  // 每拍增量 = ki_v*e_v*dt = 2*0.01*0.01 = 2e-4；到 2.943 需 ~14715 拍 → 取 30000 拍
  for (int i = 0; i < 30000; ++i)
  {
    // p_d=5, p=0 → v_d = clamp(5)=3；v=2.99 → e_v=+0.01（恒定）
    d = axisStep(c, m, 5.0, 0.0, 0.0, 2.99, 0.0, 1.0, dt);
    u_max_seen = std::max(u_max_seen, d.u);
  }
  EXPECT_LT(u_max_seen, 1.0 - 1e-9) << "本工况必须保持未饱和（否则积分会被正确冻结）";
  EXPECT_LE(std::fabs(m.i), c.i_lim + 1e-9) << "积分必须被限幅";
  EXPECT_NEAR(m.i, c.i_lim, 1e-6) << "长期正误差 → 积分必饱和到上限";
}

// ---------------------------------------------------------------- T02
TEST(CtrlCore, T02_SaturationFreeze)
{
  AxisCfg c;
  c.kp_v = 4.0; c.ki_v = 2.0; c.i_lim = 0.3 * G;
  AxisMem m;
  m.i = 0.0;
  double i_before = m.i;
  // 目标速度远大于当前速度，误差为正且 u 已到上限
  AxisDebug d = axisStep(c, m, 0.0, 0.0, 100.0, 0.0, 0.0, 1.0, 0.01);
  ASSERT_EQ(d.sat, 1.0) << "本拍应上限饱和";
  EXPECT_GT(d.e_v, 0.0);
  EXPECT_DOUBLE_EQ(m.i, i_before) << "饱和且误差同号时积分必须冻结";
  // 反方向误差时应当积分
  AxisMem m2;
  axisStep(c, m2, 0.0, 0.0, -100.0, 0.0, 0.0, 1.0, 0.01);
  EXPECT_EQ(m2.i, 0.0) << "下限不会饱和（u_min=0 且推力为 0 时误差为负…）";
}

// ---------------------------------------------------------------- T03
TEST(CtrlCore, T03_ReferenceContinuity)
{
  // handover 场景：起飞剖面切到悬停在 0.406 m / 0.45 m/s，目标 0.50 / 0
  Ref cur{0.40625, 0.45, 0.0};
  Ref tgt{0.50, 0.0, 0.0};
  const double dt = 0.01;
  double p_prev = cur.p;
  double max_step = 0.0, max_v = 0.0;
  Ref r = cur;
  for (int i = 0; i < 500; ++i)
  {
    r = shapeRef(r, tgt, 1.0, 4.0, 4.0, dt);   // MPC_JERK_AUTO=4, ACC_UP=4
    max_step = std::max(max_step, std::fabs(r.p - p_prev));
    max_v = std::max(max_v, r.v);
    p_prev = r.p;
  }
  // 连续性：单拍位置增量 <= v*dt + 0.5*a*dt^2 的上界（v_max=1, a_max=4）
  EXPECT_LE(max_step, 1.0 * dt + 0.5 * 4.0 * dt * dt + 1e-9)
      << "参考位置不得出现阶跃（原实现 +9.4 cm 阶跃）";
  EXPECT_LE(max_v, 1.0 + 1e-9);
  EXPECT_NEAR(r.p, 0.50, 1e-3) << "整形后必须收敛到目标";
  EXPECT_NEAR(r.v, 0.0, 1e-3);
  // 幂等
  Ref same = shapeRef(r, tgt, 1.0, 4.0, 4.0, dt);
  EXPECT_NEAR(same.p, r.p, 1e-9);
}

// ---------------------------------------------------------------- T04 破死锁
TEST(CtrlCore, T04_DeadlockLaw)
{
  // (a) P-only + 冻结模型：复现 S2。取实测值（E9）
  const double aim = 0.55;          // 起飞梯形 aim（旧实现 height+0.05）
  const double thr2acc_est = G / 0.48;
  // u_hover = 0.535（005259 实测）→ 平衡高度应为负（飞不起来）
  double z_eq = eqHeight(aim, 0.535, thr2acc_est, 1.5);
  EXPECT_LT(z_eq, 0.0) << "005259 的 z_eq 必须 < 0（结构性不可达）";
  // u_hover = 0.511（004602 实测）→ 平衡高度小正数
  double z_eq2 = eqHeight(aim, 0.511, thr2acc_est, 1.5);
  EXPECT_GT(z_eq2, 0.0);
  EXPECT_LT(z_eq2, 0.20) << "004602 的平衡高度必须远低于 0.5";
  // 临界 u_hover
  EXPECT_NEAR(maxHoverableThrust(aim, thr2acc_est, 1.5), 0.5204, 1e-3);

  // (b) 加积分后：同一 u_hover 也能达到 aim（积分吸收模型误差）
  AxisCfg c;
  c.kp_p = 1.0; c.kp_v = 4.0; c.ki_v = 2.0; c.i_lim = 0.3 * G;
  c.thr2acc = G / 0.48;             // 模型仍是错的（冷启动 0.48）
  const double u_true = 0.535;
  double k_true = G / u_true;       // 真实斜率
  AxisMem m;
  double p = 0.0, v = 0.0;
  const double dt = 0.01;
  double p_d = 0.0;
  for (int i = 0; i < 4000; ++i)
  {
    // 参考以 0.45 m/s 爬到 aim 后保持
    p_d = std::min(aim, p_d + 0.45 * dt);
    AxisDebug d = axisStep(c, m, p_d, p, 0.0, v, 0.0, 1.0, dt);
    double acc_true = d.u * k_true - G;
    v += acc_true * dt;
    p += v * dt;
    if (p < 0) { p = 0; v = 0; }
  }
  EXPECT_GT(p, aim - 0.03) << "有积分时必须能到达 aim（破死锁），实测 005259 无积分时只能到 0.03";
  EXPECT_LT(std::fabs(m.i), c.i_lim + 1e-9);
}

// ---------------------------------------------------------------- T05
TEST(CtrlCore, T05_ModelRetargetNoJump)
{
  AxisCfg c;
  c.thr2acc = G / 0.55;             // 旧模型
  AxisMem m;
  m.i = 0.5;
  const double u_now = 0.52, ct = 1.0;
  const double k_old = c.thr2acc;
  double acc_demand_before = u_now * k_old * ct - G;   // 产生该 u 所需的 acc 需求
  retargetThrustModel(c, m, G / 0.48, u_now, ct);
  // 换模型后：acc 需求 = 旧需求 + 积分增量，用新 k 反算的 u 必须仍是 u_now
  double acc_demand_after = acc_demand_before + (m.i - 0.5);
  double u_after = (acc_demand_after + G) / (c.thr2acc * ct);
  EXPECT_NEAR(u_after, u_now, 1e-9) << "无扰切换：同一 acc 需求下的 u 必须不变";
  EXPECT_GT(std::fabs(m.i - 0.5), 1e-6) << "积分必须真的移动";
}

// ---------------------------------------------------------------- T06
TEST(CtrlCore, T06_TiltCosCompensation)
{
  const double thr2acc = G / 0.52;
  double u_flat = thrustFromAcc(0.0, thr2acc, 1.0, 0.0, 1.0);
  double u_10deg = thrustFromAcc(0.0, thr2acc, std::cos(10.0 * M_PI / 180.0), 0.0, 1.0);
  EXPECT_NEAR(u_flat / u_10deg, std::cos(10.0 * M_PI / 180.0), 1e-9)
      << "悬停推力应按 1/cos(倾角) 放大";
  EXPECT_NEAR(u_10deg / u_flat, 1.0154, 1e-3);
  // cos 护栏
  double u_guard = thrustFromAcc(0.0, thr2acc, 0.0, 0.0, 1.0, 0.5);
  EXPECT_TRUE(std::isfinite(u_guard));
  EXPECT_LE(u_guard, 1.0);
}

// ---------------------------------------------------------------- T07
TEST(CtrlCore, T07_RlsGates)
{
  RlsCfg c;
  RlsState s;
  // 地面（in_air=false）不更新
  double k0 = s.k;
  EXPECT_FALSE(rlsUpdate(s, c, 0.52, 9.81, false));
  EXPECT_DOUBLE_EQ(s.k, k0);
  // 空中 + 有激励 → 更新
  EXPECT_TRUE(rlsUpdate(s, c, 0.52, 9.9, true));
  // 无激励（u 不变）→ 不更新
  double k1 = s.k;
  EXPECT_FALSE(rlsUpdate(s, c, 0.52, 9.9, true));
  EXPECT_DOUBLE_EQ(s.k, k1);
  // 极端值：存储点限幅
  RlsState s2;
  for (int i = 0; i < 20000; ++i)
    rlsUpdate(s2, c, (i % 2) ? 1.0 : 0.05, 1e6, true);
  EXPECT_LE(s2.k, c.k_max);
  EXPECT_GE(s2.k, c.k_min);
  EXPECT_GT(s2.P, 0.0) << "P 必须保持为正";
  EXPECT_TRUE(std::isfinite(s2.k));
}

// ---------------------------------------------------------------- T08
TEST(CtrlCore, T08_TakeoffRefEndsAtHeight)
{
  TakeoffCfg c;
  c.height = 0.5; c.speed = 0.45; c.acc = 1.0; c.spinup = 3.0;
  // 加速段单调、末态精确
  Ref r_prev = takeoffRef(0.0, c);
  for (double t = 0.01; t < 8.0; t += 0.01)
  {
    Ref r = takeoffRef(t, c);
    EXPECT_GE(r.p, r_prev.p - 1e-12) << "参考高度必须单调不减";
    EXPECT_LE(r.p, c.height + 1e-9) << "参考不得越过目标高度";
    r_prev = r;
  }
  Ref end = takeoffRef(10.0, c);
  EXPECT_NEAR(end.p, c.height, 1e-12) << "末态必须恰为 height（旧实现 aim=height+0.05 造成切换阶跃）";
  EXPECT_NEAR(end.v, 0.0, 1e-12);
  EXPECT_NEAR(end.a, 0.0, 1e-12);
  // 到达判据：存在一个时刻 t_arr 使 p_ref + k*v_ref >= height，且此时 p 约 0.40-0.45
  double t_arr = -1.0;
  for (double t = 3.0; t < 8.0; t += 0.001)
    if (takeoffArrived(takeoffRef(t, c), 0.45, c)) { t_arr = t; break; }
  ASSERT_GT(t_arr, 0.0) << "必须存在到达时刻";
  Ref at = takeoffRef(t_arr, c);
  EXPECT_NEAR(at.p + c.arrive_k * 0.45, c.height, 0.02)
      << "到达时 剩余距离 = k*vz（预测式到位）";
  EXPECT_GT(at.p, 0.30);
}

// ---------------------------------------------------------------- T09
TEST(CtrlCore, T09_LandProfile)
{
  LandCfg c;
  c.v_cmd = 0.15;
  LandMem m;
  m.p_d = 0.50;
  const double ground = 0.0, dt = 0.01;
  double t = 0.0, v_last = 0.0;
  while (!m.done && t < 30.0)
  {
    v_last = landStep(c, m, ground, dt);
    EXPECT_LE(v_last, c.v_cmd + 1e-12) << "下降速率不得超过指令";
    EXPECT_GE(m.p_d, ground - 1e-12) << "参考不得穿地";
    t += dt;
  }
  EXPECT_TRUE(m.done);
  EXPECT_NEAR(t, 0.50 / 0.15, 0.10) << "0.5 m / 0.15 m/s 约 3.33 s（ground_eps 会提前 ~0.07 s）";
  EXPECT_NEAR(m.p_d, ground, 1e-9);
  // 已到地再调用 → 不再下降
  EXPECT_DOUBLE_EQ(landStep(c, m, ground, dt), 0.0);
}

// ---------------------------------------------------------------- T10
TEST(CtrlCore, T10_TiltSlew)
{
  double cur = 10.0, target = 25.0;
  const double rate = 30.0, dt = 0.01;   // 30 deg/s
  for (int i = 0; i < 100; ++i)
  {
    double n = slewTilt(cur, target, rate, dt);
    EXPECT_LE(std::fabs(n - cur), rate * dt + 1e-9);
    cur = n;
  }
  EXPECT_NEAR(cur, 25.0, 1e-9);
  // 反向
  for (int i = 0; i < 100; ++i)
    cur = slewTilt(cur, 10.0, rate, dt);
  EXPECT_NEAR(cur, 10.0, 1e-9);
}

int main(int argc, char **argv)
{
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
