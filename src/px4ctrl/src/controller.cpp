#include "controller.h"

using namespace std;



double LinearControl::fromQuaternion2yaw(Eigen::Quaterniond q)
{
  double yaw = atan2(2 * (q.x()*q.y() + q.w()*q.z()), q.w()*q.w() + q.x()*q.x() - q.y()*q.y() - q.z()*q.z());
  return yaw;
}

LinearControl::LinearControl(Parameter_t &param) : param_(param)
{
  resetThrustMapping();
}

/* 
  compute u.thrust and u.q, controller gains and other parameters are in param_ 
*/
quadrotor_msgs::Px4ctrlDebug
LinearControl::calculateControl(const Desired_State_t &des,
    const Odom_Data_t &odom,
    const Imu_Data_t &imu, 
    Controller_Output_t &u)
{
  /* WRITE YOUR CODE HERE */
      //compute disired acceleration
      Eigen::Vector3d des_acc(0.0, 0.0, 0.0);
      Eigen::Vector3d Kp,Kv;
      Kp << param_.gain.Kp0, param_.gain.Kp1, param_.gain.Kp2;
      Kv << param_.gain.Kv0, param_.gain.Kv1, param_.gain.Kv2;
      des_acc = des.a + Kv.asDiagonal() * (des.v - odom.v) + Kp.asDiagonal() * (des.p - odom.p);
      des_acc += Eigen::Vector3d(0,0,param_.gra);

      u.thrust = computeDesiredCollectiveThrustSignal(des_acc);
      /* 姿态目标改为期望加速度向量直接构造（几何控制器法）。原实现先按当前
         yaw_odom 把 des_acc 折算成 roll/pitch，再与目标 des.yaw 组欧拉角四元数：
         yaw 误差大时（返程掉头 >90deg）PX4 按最短路径追该四元数会穿倒扣姿态，
         且倾角方向瞬时错向——2026-09-26 两次障碍区侧起飞返程坠机的根因（数值
         证据 sitl_sim/t3_experiments.md W1，docs/analysis/t3w1_*.png；2026-09-27
         V1 轮独立复现）。本式倾角只由加速度矢量决定，yaw 以连续 (cos,sin)
         参与，无 ±180deg 绕环奇异。
         zb.z 下限护栏（0.1g）：des_acc.z<0（向下加速需求超重力，如强过冲）时
         老式小角度公式退化为近水平姿态，本式若不钳制会构造倒扣姿态。 */
      Eigen::Vector3d zb = des_acc;
      if (zb(2) < 0.1 * param_.gra)
        zb(2) = 0.1 * param_.gra;
      zb.normalize();
      Eigen::Vector3d xc(std::cos(des.yaw), std::sin(des.yaw), 0.0);
      Eigen::Vector3d yb = zb.cross(xc);
      if (yb.norm() < 1e-3) // 倾角近 90deg 且朝向航向的退化情形，兜底防 NaN
        yb = zb.cross(Eigen::Vector3d::UnitX());
      yb.normalize();
      Eigen::Matrix3d R_des;
      R_des.col(0) = yb.cross(zb);
      R_des.col(1) = yb;
      R_des.col(2) = zb;
      Eigen::Quaterniond q(R_des);
      u.q = imu.q * odom.q.inverse() * q;


  /* WRITE YOUR CODE HERE */

  //used for debug
  // debug_msg_.des_p_x = des.p(0);
  // debug_msg_.des_p_y = des.p(1);
  // debug_msg_.des_p_z = des.p(2);
  
  debug_msg_.des_v_x = des.v(0);
  debug_msg_.des_v_y = des.v(1);
  debug_msg_.des_v_z = des.v(2);
  
  debug_msg_.des_a_x = des_acc(0);
  debug_msg_.des_a_y = des_acc(1);
  debug_msg_.des_a_z = des_acc(2);
  
  debug_msg_.des_q_x = u.q.x();
  debug_msg_.des_q_y = u.q.y();
  debug_msg_.des_q_z = u.q.z();
  debug_msg_.des_q_w = u.q.w();
  
  debug_msg_.des_thr = u.thrust;
  
  // Used for thrust-accel mapping estimation
  timed_thrust_.push(std::pair<ros::Time, double>(ros::Time::now(), u.thrust));
  while (timed_thrust_.size() > 100)
  {
    timed_thrust_.pop();
  }
  return debug_msg_;
}

/*
  compute throttle percentage 
*/
double 
LinearControl::computeDesiredCollectiveThrustSignal(
    const Eigen::Vector3d &des_acc)
{
  double throttle_percentage(0.0);
  
  /* compute throttle, thr2acc has been estimated before。
     T3 2026-09-27: RLS 估计器在快速自旋段会被旋转加速度伪影喂爆(悬停名义
     ~13.8 m/s^2，病态时发散到无穷使油门恒 0，V2f 实证 des_a_z 正常而 thr=0)。
     使用点钳位到 [5,40]:健康估计不受影响，病态时油门下限 ~0.25 保持可控，
     健康反馈下 RLS 可自行收敛回。 */
  double thr2acc = std::max(5.0, std::min(40.0, thr2acc_));
  throttle_percentage = des_acc(2) / thr2acc;
  throttle_percentage = std::max(0.0, std::min(1.0, throttle_percentage));

  return throttle_percentage;
}

bool 
LinearControl::estimateThrustModel(
    const Eigen::Vector3d &est_a,
    const Parameter_t &param)
{
  if (!param_.thr_map.enable_rls) // SITL 冻结模式:名义映射恒定
    return false;
  ros::Time t_now = ros::Time::now();
  while (timed_thrust_.size() >= 1)
  {
    // Choose data before 35~45ms ago
    std::pair<ros::Time, double> t_t = timed_thrust_.front();
    double time_passed = (t_now - t_t.first).toSec();
    if (time_passed > 0.045) // 45ms
    {
      // printf("continue, time_passed=%f\n", time_passed);
      timed_thrust_.pop();
      continue;
    }
    if (time_passed < 0.035) // 35ms
    {
      // printf("skip, time_passed=%f\n", time_passed);
      return false;
    }

    /***********************************************************/
    /* Recursive least squares algorithm with vanishing memory */
    /***********************************************************/
    double thr = t_t.second;
    timed_thrust_.pop();
    
    /***********************************/
    /* Model: est_a(2) = thr1acc_ * thr */
    /***********************************/
    double gamma = 1 / (rho2_ + thr * P_ * thr);
    double K = gamma * P_ * thr;
    thr2acc_ = thr2acc_ + K * (est_a(2) - thr * thr2acc_);
    P_ = (1 - K * thr) * P_ / rho2_;
    //printf("%6.3f,%6.3f,%6.3f,%6.3f\n", thr2acc_, gamma, K, P_);
    //fflush(stdout);

    // debug_msg_.thr2acc = thr2acc_;
    return true;
  }
  return false;
}

void 
LinearControl::resetThrustMapping(void)
{
  thr2acc_ = param_.gra / param_.thr_map.hover_percentage;
  P_ = 1e6;
}







