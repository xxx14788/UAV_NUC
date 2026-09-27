#include <gtest/gtest.h>
#include <cmath>
#include "attitude_utils.h"

using px4ctrl_att::attitudeFromAccel;
using px4ctrl_att::attitudeLegacyEuler;

static double quatAngleDeg(const Eigen::Quaterniond &a, const Eigen::Quaterniond &b)
{
  return std::acos(std::min(1.0, std::abs(a.dot(b)))) * 2.0 * 180.0 / M_PI;
}

static Eigen::Vector3d rotateZ(const Eigen::Quaterniond &q)
{ // 机体 zb 轴在世界系的指向
  return q * Eigen::Vector3d::UnitZ();
}

static double yawOf(const Eigen::Quaterniond &q)
{
  return std::atan2(2 * (q.x() * q.y() + q.w() * q.z()),
                    q.w() * q.w() + q.x() * q.x() - q.y() * q.y() - q.z() * q.z());
}

static const double G = 9.81;

// 1. 悬停恒等：期望加速度 = 纯重力补偿、yaw=0 → 单位姿态
TEST(Attitude, HoverIdentity)
{
  Eigen::Quaterniond q = attitudeFromAccel(Eigen::Vector3d(0, 0, G), 0.0, G);
  EXPECT_LT(quatAngleDeg(q, Eigen::Quaterniond::Identity()), 1e-6);
}

// 2. 四向倾角：+x 期望加速度 → zb 偏向 +x（<30deg 夹角），其余三向同理
TEST(Attitude, TiltFourDirections)
{
  const double a = 3.0;
  struct
  {
    Eigen::Vector3d acc;
    Eigen::Vector3d dir;
  } cases[] = {
      {{a, 0, G}, {1, 0, 0}},
      {{-a, 0, G}, {-1, 0, 0}},
      {{0, a, G}, {0, 1, 0}},
      {{0, -a, G}, {0, -1, 0}},
  };
  for (auto &c : cases)
  {
    Eigen::Quaterniond q = attitudeFromAccel(c.acc, 0.0, G);
    Eigen::Vector3d zb = rotateZ(q);
    double cosang = zb.head<2>().normalized().dot(c.dir.head<2>().normalized());
    EXPECT_GT(cosang, std::cos(30.0 * M_PI / 180)) << "zb=" << zb.transpose();
    EXPECT_GT(zb(2), 0.0); // 绝不倒扣
  }
}

// 3. 护栏：des_acc.z < 0 仍须给出 zb.z>0 的姿态（不倒扣），且可微倾
TEST(Attitude, DesAccZNegativeGuard)
{
  Eigen::Quaterniond q = attitudeFromAccel(Eigen::Vector3d(1.0, 0.5, -2.0), 0.5, G);
  Eigen::Vector3d zb = rotateZ(q);
  EXPECT_GT(zb(2), 0.0);
  EXPECT_LT(zb(2), 1.0); // 确实发生了倾斜而非纯垂直
  EXPECT_TRUE(std::isfinite(q.w()) && std::isfinite(q.x()) &&
              std::isfinite(q.y()) && std::isfinite(q.z()));
}

// 4. 退化保护：zb 反平行 xc（yb=zb×xc≈0）时兜底，输出仍正交且有限
TEST(Attitude, DegenerateZbAntiParallelXc)
{
  // zb 近水平朝 -x、yaw=π → xc=(-1,0,0)，zb≈-xc → yb 范数近 0
  Eigen::Quaterniond q = attitudeFromAccel(Eigen::Vector3d(-30.0, 0.0, 0.05),
                                           M_PI, G);
  Eigen::Matrix3d R = q.toRotationMatrix();
  EXPECT_TRUE(R.allFinite());
  EXPECT_LT((R * R.transpose() - Eigen::Matrix3d::Identity()).norm(), 1e-6);
  EXPECT_NEAR(R.determinant(), 1.0, 1e-6);
}

// 5. yaw wrap 连续性：yaw 扫描 -180→180，相邻输出夹角必须平滑（<1deg/步）
TEST(Attitude, YawWrapContinuity)
{
  Eigen::Quaterniond prev = attitudeFromAccel(Eigen::Vector3d(2.0, 1.0, G),
                                              -M_PI, G);
  for (int i = -179; i <= 180; ++i)
  {
    double yaw = i * M_PI / 180.0;
    Eigen::Quaterniond q = attitudeFromAccel(Eigen::Vector3d(2.0, 1.0, G), yaw, G);
    // 容差 1.5deg：倾角 22.9deg 下 1deg 方位步进的测地距离被锥面几何
    // 放大到 ~1.02deg；wrap 跳变（若存在）会是几十~180deg 量级。
    EXPECT_LT(quatAngleDeg(q, prev), 1.5) << "yaw=" << i;
    prev = q;
  }
  // ±179.9deg 两端：zb 相同、倾角方向相同（差 ≈0 而非 2*倾角）
  Eigen::Quaterniond qp = attitudeFromAccel(Eigen::Vector3d(2.0, 1.0, G),
                                            179.9 * M_PI / 180.0, G);
  Eigen::Quaterniond qm = attitudeFromAccel(Eigen::Vector3d(2.0, 1.0, G),
                                            -179.9 * M_PI / 180.0, G);
  EXPECT_LT((rotateZ(qp).head<2>() - rotateZ(qm).head<2>()).norm(), 1e-3);
}

// 6. 与老式等价回归锁：yaw 误差为 0 且小倾角（老式 a_xy/g 为小角线性化，
//    倾角 >15deg 时两式差为线性化误差、非实现差异）时两式夹角 < 0.5deg
TEST(Attitude, LegacyEquivalenceZeroYawError)
{
  // 网格 ±0.5（倾角≤4.1deg）：两式差 O(倾角²)，实测 0.59deg@8.2deg、
  // ~0.15deg@4deg，故 0.5deg 锚点配 ±0.5 网格。
  for (double ax = -0.5; ax <= 0.5; ax += 0.25)
    for (double ay = -0.5; ay <= 0.5; ay += 0.25)
      for (double yaw = -M_PI; yaw <= M_PI; yaw += M_PI / 6)
      {
        Eigen::Vector3d acc(ax, ay, G);
        Eigen::Quaterniond qn = attitudeFromAccel(acc, yaw, G);
        Eigen::Quaterniond ql = attitudeLegacyEuler(acc, yaw, yaw, G);
        EXPECT_LT(quatAngleDeg(qn, ql), 0.5)
            << "acc=" << acc.transpose() << " yaw=" << yaw;
      }
}

// 7. NaN/Inf 输入不产生 NaN 输出（W9 加固：返回单位姿态）
TEST(Attitude, NaNInputSafe)
{
  double nan = std::numeric_limits<double>::quiet_NaN();
  double inf = std::numeric_limits<double>::infinity();
  Eigen::Vector3d bad1(nan, 0, G);
  Eigen::Vector3d bad2(0, nan, G);
  Eigen::Vector3d bad3(inf, 0, G);
  Eigen::Vector3d bad4(0, 0, nan);
  for (auto *acc : {&bad1, &bad2, &bad3, &bad4})
  {
    Eigen::Quaterniond q = attitudeFromAccel(*acc, 0.0, G);
    EXPECT_TRUE(q.coeffs().allFinite());
    EXPECT_LT(quatAngleDeg(q, Eigen::Quaterniond::Identity()), 1e-9);
  }
}

// 8. 全网格正交性/有限性/倾角方向合理性（性质测试兜底）
TEST(Attitude, GridProperties)
{
  for (double ax = -8; ax <= 8; ax += 2.0)
    for (double ay = -8; ay <= 8; ay += 2.0)
      for (double az = -5; az <= 5; az += 2.5)
        for (double yaw = -M_PI; yaw <= M_PI; yaw += M_PI / 4)
        {
          Eigen::Vector3d acc(ax, ay, az);
          if (acc.norm() < 1e-9)
            continue;
          Eigen::Quaterniond q = attitudeFromAccel(acc, yaw, G);
          ASSERT_TRUE(q.coeffs().allFinite());
          Eigen::Matrix3d R = q.toRotationMatrix();
          ASSERT_LT((R * R.transpose() - Eigen::Matrix3d::Identity()).norm(), 1e-6);
          Eigen::Vector3d zb = rotateZ(q);
          ASSERT_GT(zb(2), 0.0); // 护栏保证任何输入都不倒扣
          // 倾角合理性：az≥0（护栏未触发）时 zb 落在 acc 方向与 +z 之间；
          // az<0（护栏触发）时只要求不倒扣且离水平至少 0.1g 当量
          double zb_tilt = std::acos(std::min(1.0, zb(2)));
          if (az >= 0)
          {
            double acc_tilt = std::acos(std::min(1.0, az / acc.norm()));
            ASSERT_LE(zb_tilt, acc_tilt + 1e-9);
          }
          else
          {
            ASSERT_LT(zb_tilt, 89.0 * M_PI / 180.0);
          }
        }
}

int main(int argc, char **argv)
{
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
