#ifndef __PX4CTRL_ATTITUDE_UTILS_H
#define __PX4CTRL_ATTITUDE_UTILS_H
/*
 * px4ctrl 姿态合成纯函数（T3-W9 抽取，供 gtest 单测与控制器共用）。
 *
 * 期望加速度向量直接构造姿态（几何控制器法）。原实现先按当前 yaw_odom
 * 把 des_acc 折算成 roll/pitch，再与目标 des.yaw 组欧拉角四元数：yaw 误差
 * 大时（返程掉头 >90deg）PX4 按最短路径追该四元数会穿倒扣姿态，且倾角
 * 方向瞬时错向——2026-09-26 两次障碍区侧起飞返程坠机的根因（数值证据
 * sitl_sim/t3_experiments.md W1；docs/analysis/t3w1_*.png；2026-09-27 V1
 * 轮独立复现；W9 全历史轮回放定罪：老式失败腿倾角方向中位夹角 154-170deg，
 * 本式 0.2deg）。本式倾角只由加速度矢量决定，yaw 以连续 (cos,sin) 参与，
 * 无 ±180deg 绕环奇异。
 *
 * zb.z 下限护栏（0.1g）：des_acc.z<0（向下加速需求超重力，如强过冲）时
 * 老式小角度公式退化为近水平姿态，本式若不钳制会构造倒扣姿态。
 *
 * NaN 防护（W9 加固）：des_acc 非有限时返回单位姿态（悬停），绝不向
 * PX4 发 NaN 四元数。
 */
#include <Eigen/Dense>

namespace px4ctrl_att
{

inline Eigen::Quaterniond attitudeFromAccel(const Eigen::Vector3d &des_acc,
                                            double yaw, double gra)
{
  if (!des_acc.allFinite())
    return Eigen::Quaterniond::Identity();

  Eigen::Vector3d zb = des_acc;
  if (zb(2) < 0.1 * gra)
    zb(2) = 0.1 * gra;
  zb.normalize();
  Eigen::Vector3d xc(std::cos(yaw), std::sin(yaw), 0.0);
  Eigen::Vector3d yb = zb.cross(xc);
  if (yb.norm() < 1e-3) // 倾角近 90deg 且朝向航向的退化情形，兜底防 NaN
    yb = zb.cross(Eigen::Vector3d::UnitX());
  yb.normalize();
  Eigen::Matrix3d R_des;
  R_des.col(0) = yb.cross(zb);
  R_des.col(1) = yb;
  R_des.col(2) = zb;
  Eigen::Quaterniond q(R_des);
  return q;
}

/* 老式（c4f8c4e 及之前）欧拉构造，仅存于单测做等价性回归锚点，勿用于控制。 */
inline Eigen::Quaterniond attitudeLegacyEuler(const Eigen::Vector3d &des_acc,
                                              double yaw_des, double yaw_odom,
                                              double gra)
{
  double s = std::sin(yaw_odom), c = std::cos(yaw_odom);
  double roll = (des_acc(0) * s - des_acc(1) * c) / gra;
  double pitch = (des_acc(0) * c + des_acc(1) * s) / gra;
  Eigen::Matrix3d R =
      (Eigen::AngleAxisd(yaw_des, Eigen::Vector3d::UnitZ()) *
       Eigen::AngleAxisd(pitch, Eigen::Vector3d::UnitY()) *
       Eigen::AngleAxisd(roll, Eigen::Vector3d::UnitX()))
          .toRotationMatrix();
  return Eigen::Quaterniond(R);
}

} // namespace px4ctrl_att

#endif
