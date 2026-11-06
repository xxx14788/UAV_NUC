#include "controller.h"
#include "attitude_utils.h"

using namespace std;



double LinearControl::fromQuaternion2yaw(Eigen::Quaterniond q)
{
  double yaw = atan2(2 * (q.x()*q.y() + q.w()*q.z()), q.w()*q.w() + q.x()*q.x() - q.y()*q.y() - q.z()*q.z());
  return yaw;
}

LinearControl::LinearControl(Parameter_t &param) : param_(param)
{
  resetThrustMapping();
  applyV2Config();
}

// W4/W5/W6：把参数灌进控制核心配置（垂直照 PX4 ωn=2.0/ζ=1.0/Ti=2.0，水平照 ζ=0.90）
void LinearControl::applyV2Config()
{
  const Parameter_t::CtrlV2_t &v = param_.ctrl_v2;
  cfg_z_.kp_p = v.kp_p_z;  cfg_z_.kp_v = v.kp_v_z;  cfg_z_.ki_v = v.ki_v_z;
  cfg_z_.i_lim = v.i_lim_z; cfg_z_.vel_max_up = v.vel_max_up; cfg_z_.vel_max_dn = v.vel_max_dn;
  cfg_z_.cos_tilt_min = v.cos_tilt_min; cfg_z_.u_min = v.u_min; cfg_z_.u_max = v.u_max;
  cfg_x_ = cfg_y_ = cfg_z_;
  cfg_x_.kp_p = cfg_y_.kp_p = v.kp_p_xy;
  cfg_x_.kp_v = cfg_y_.kp_v = v.kp_v_xy;
  cfg_x_.ki_v = cfg_y_.ki_v = v.ki_v_xy;
  cfg_x_.i_lim = cfg_y_.i_lim = v.i_lim_xy;
  cfg_x_.vel_max_up = cfg_x_.vel_max_dn = v.vel_max_xy;
  cfg_y_.vel_max_up = cfg_y_.vel_max_dn = v.vel_max_xy;
}

// 实测 dt（用 WallRate 驱动的真实间隔，钳位照 PX4 `MulticopterPositionControl.cpp:396`）
double LinearControl::stepDt()
{
  const ros::Time now = ros::Time::now();
  if (!v2_primed_) { v2_primed_ = true; last_step_t_ = now; return 0.01; }
  double dt = (now - last_step_t_).toSec();
  last_step_t_ = now;
  const Parameter_t::CtrlV2_t &v = param_.ctrl_v2;
  if (!(dt > 0.0)) dt = 0.01;
  return std::max(v.dt_min, std::min(v.dt_max, dt));
}

/* 
  compute u.thrust and u.q, controller gains and other parameters are in param_ 
*/
quadrotor_msgs::Px4ctrlDebug
LinearControl::calculateControl(const Desired_State_t &des,
    const Odom_Data_t &odom,
    const Imu_Data_t &imu, 
    Controller_Output_t &u,
    const double tilt_max_deg)
{
  /* WRITE YOUR CODE HERE */
      //compute disired acceleration
      Eigen::Vector3d des_acc(0.0, 0.0, 0.0);
      Eigen::Vector3d Kp,Kv;
      Kp << param_.gain.Kp0, param_.gain.Kp1, param_.gain.Kp2;
      Kv << param_.gain.Kv0, param_.gain.Kv1, param_.gain.Kv2;
      if (param_.ctrl_v2.enabled)
      {
        /* W4/W5/W6 控制核心 v2：
           - 三轴串级（位置 P → 速度 PI）+ 积分限幅/条件积分
           - 竖直推力含 1/cos(倾角) 补偿（照 PX4 PositionControl.cpp:219-220）
           - 模型变更时用积分做无扰切换（照 PX4 updateHoverThrust）
           legacy 分支（下方）逐位保留，enabled=false 时零行为变化。 */
        const double dt = stepDt();
        // 2026-11-06 护栏（顾问加）：1/cos(倾角) 补偿依赖 imu.q，而 **imu_is_received()
        // 是死代码、从未被调用**（PX4CtrlFSM.cpp:925 定义无调用点）。若 imu.q 尚未被
        // 任何 IMU 消息写入（Eigen 默认构造不初始化）或是全零，zb(2)≈0 ->
        // cos_tilt 落到下限 -> u 被放大 2~10 倍并 clip 到 1.0 = 满推力。
        // 失效方向必须选"不补偿"（0~2% 误差），绝不能选"放大推力"。
        const double qn = imu.q.norm();
        const bool q_ok = (qn > 0.5 && qn < 1.5);
        const Eigen::Vector3d zb = q_ok ? (imu.q * Eigen::Vector3d::UnitZ())
                                        : Eigen::Vector3d::UnitZ();
        const double cos_tilt = std::max(0.1, std::fabs(zb(2)));
        if (!q_ok)
        {
          ROS_WARN_THROTTLE(5.0, "[px4ctrl] v2: imu.q 无效 (|q|=%.3f)，本拍按零倾角处理"
                            "（放弃 1/cos 补偿，不做推力放大）", qn);
        }
        // 模型变更检测：thr2acc_ 与 cfg_z_.thr2acc 不一致 → 无扰切换
        if (std::fabs(cfg_z_.thr2acc - thr2acc_) > 1e-9)
        {
          px4ctrl_core::retargetThrustModel(cfg_z_, mem_z_, thr2acc_, last_u_, cos_tilt,
                                            param_.ctrl_v2.cos_tilt_min);
        }
        px4ctrl_core::AxisDebug dz = px4ctrl_core::axisStep(
            cfg_z_, mem_z_, des.p(2), odom.p(2), des.v(2), odom.v(2), des.a(2), cos_tilt, dt);
        px4ctrl_core::AxisDebug dx = px4ctrl_core::axisStep(
            cfg_x_, mem_x_, des.p(0), odom.p(0), des.v(0), odom.v(0), des.a(0), cos_tilt, dt);
        px4ctrl_core::AxisDebug dy = px4ctrl_core::axisStep(
            cfg_y_, mem_y_, des.p(1), odom.p(1), des.v(1), odom.v(1), des.a(1), cos_tilt, dt);
        // 姿态用的加速度向量（含重力），与 legacy 的 des_acc 语义一致
        des_acc = Eigen::Vector3d(dx.acc, dy.acc, dz.acc + param_.gra);
        u.thrust = dz.u;
        last_u_ = u.thrust;
        last_cos_tilt_ = cos_tilt;
        debug_msg_.hover_percentage = param_.gra / cfg_z_.thr2acc;
        // 2026-11-06：把垂直环的内部状态发出来（msg 已加 i_z / v_d_z 两个字段）。
        // 没有这两个量，判读时只能猜"是积分没吃住还是模型没收敛"——上一轮就是这么猜错的。
        debug_msg_.i_z = mem_z_.i;
        debug_msg_.v_d_z = dz.v_d;
      }
      else
      {
        des_acc = des.a + Kv.asDiagonal() * (des.v - odom.v) + Kp.asDiagonal() * (des.p - odom.p);
        des_acc += Eigen::Vector3d(0,0,param_.gra);

        u.thrust = computeDesiredCollectiveThrustSignal(des_acc);
        last_u_ = u.thrust;
        debug_msg_.i_z = 0.0;          // legacy 无积分
        debug_msg_.v_d_z = des.v(2);   // legacy 的速度指令=前馈
      }
      /* C3-B2 H4-F2（B1 预注册）：起飞倾角限幅。thrust 只取 des_acc(2) 且
         已在上行算毕，此处横向缩放不影响推力信号（thrust 不变性单测锚定）。 */
      px4ctrl_att::clampAccelTilt(des_acc, tilt_max_deg);
      /* 姿态目标改为期望加速度向量直接构造（几何控制器法）。原实现先按当前
         yaw_odom 把 des_acc 折算成 roll/pitch，再与目标 des.yaw 组欧拉角四元数：
         yaw 误差大时（返程掉头 >90deg）PX4 按最短路径追该四元数会穿倒扣姿态，
         且倾角方向瞬时错向——2026-09-26 两次障碍区侧起飞返程坠机的根因（数值
         证据 sitl_sim/t3_experiments.md W1，docs/analysis/t3w1_*.png；2026-09-27
         V1 轮独立复现）。本式倾角只由加速度矢量决定，yaw 以连续 (cos,sin)
         参与，无 ±180deg 绕环奇异。
         zb.z 下限护栏（0.1g）：des_acc.z<0（向下加速需求超重力，如强过冲）时
         老式小角度公式退化为近水平姿态，本式若不钳制会构造倒扣姿态。 */
      // W9: 公式本体抽取到 attitude_utils.h（gtest 单测覆盖 + NaN 防护加固），
      // 行为与 0de090e 内联版一致（护栏/退化兜底/构造次序均不变）。
      Eigen::Quaterniond q =
          px4ctrl_att::attitudeFromAccel(des_acc, des.yaw, param_.gra);
      /* FIX-20261022（两轮翻机根因，判读v3/v4）: 原式 u.q = imu.q*odom.q⁻¹*q
       * 用双实时估计搬运坐标系——odom 冻结/发散时正反馈（机体转→imu.q 跟转→
       * 搬运项放大→指令更转，轮2实测 0.5s 自旋至倒扣）。直发模式：倾角对任意
       * 两重力对齐世界系不变（tilt 不变性），代价仅恒定 yaw 偏差（起降/悬停
       * 无害）。frame_offset/direct: false 回滚 legacy。 */
      if (param_.frame_off_hold)
      {
        ros::Time now_t = ros::Time::now();
        double odom_age = (now_t - odom.rcv_stamp).toSec();
        double imu_age = (now_t - imu.rcv_stamp).toSec();
        bool q_ok = odom.q.coeffs().allFinite() && imu.q.coeffs().allFinite();
        bool fresh = q_ok && odom_age >= 0.0 && odom_age < 0.2 && imu_age >= 0.0 && imu_age < 0.2;
        if (!fresh)
        {
          if (odom_age > 0.3) off_relock_armed_ = true; // 断流武装重锁（吸收 VINS 重启换世界系）
          off_fresh_t0_ = -1.0;
        }
        else
        {
          Eigen::Quaterniond off_now = imu.q * odom.q.inverse();
          if (!off_valid_)
          {
            off_filt_ = off_now; off_valid_ = true;
          }
          else if (off_relock_armed_)
          {
            double tn = now_t.toSec();
            if (off_fresh_t0_ < 0.0) off_fresh_t0_ = tn;
            if (tn - off_fresh_t0_ > 0.5)
            {
              off_filt_ = off_now; off_relock_armed_ = false; off_fresh_t0_ = -1.0;
              ROS_WARN("[FIX-1022r2] frame offset relocked (post-gap stable 0.5s)");
            }
          }
          else
          {
            // 偏离滤波值超 dev_max = 估计分叉（正反馈形态）→ 拒收本帧偏置（冻结）
            if (off_now.angularDistance(off_filt_) < param_.frame_off_dev_max_deg * M_PI / 180.0)
              off_filt_ = off_filt_.slerp(0.05, off_now); // 低通跟随慢漂（τ≈0.2s@100Hz）
          }
        }
        u.q = (off_valid_ ? off_filt_ : Eigen::Quaterniond::Identity()) * q;
      }
      else
      {
        u.q = imu.q * odom.q.inverse() * q; // legacy（frame_offset/hold:false 回滚）
      }


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
  
  {
    // 2026-11-05: 暴露实时推力模型；用与 computeDesiredCollectiveThrustSignal 相同的限幅值，
    // 保证这里看到的就是控制真正用到的等价 hover 比例
    const double thr2acc_used = std::max(5.0, std::min(40.0, thr2acc_));
    debug_msg_.hover_percentage = param_.gra / thr2acc_used;
  }
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
  // 2026-11-06 DEF-11：v2 下 NaN 门**无条件**生效（原实现只在 rls_air_gate=true 时才挡，
  // 而那个开关名字暗示的是"空中门"，名不副实）。legacy 路径仍未加（DEF-06 部分修）。
  // 注意：这里不做 z 空中门 —— RLS 本来就只在 AUTO_HOVER/CMD_CTRL 更新（FSM STEP2）。
  if (param_.ctrl_v2.enabled)
  {
    if (!(est_a.allFinite())) return false;
  }
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







