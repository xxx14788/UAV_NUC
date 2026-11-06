/*************************************************************/
/* Acknowledgement: github.com/uzh-rpg/rpg_quadrotor_control */
/*************************************************************/

#ifndef __CONTROLLER_H
#define __CONTROLLER_H

#include <mavros_msgs/AttitudeTarget.h>
#include <quadrotor_msgs/Px4ctrlDebug.h>
#include <queue>

#include "input.h"
#include "ctrl_core.h"   // W4/W5/W6: 纯函数控制核心（gtest: test_ctrl_core）
#include <Eigen/Dense>

struct Desired_State_t
{
	Eigen::Vector3d p;
	Eigen::Vector3d v;
	Eigen::Vector3d a;
	Eigen::Vector3d j;
	Eigen::Quaterniond q;
	double yaw;
	double yaw_rate;
	// double thrust;


	Desired_State_t(){};

	Desired_State_t(Odom_Data_t &odom)
		: p(odom.p),
		  v(Eigen::Vector3d::Zero()),
		  a(Eigen::Vector3d::Zero()),
		  j(Eigen::Vector3d::Zero()),
		  q(odom.q),
		  yaw(uav_utils::get_yaw_from_quaternion(odom.q)),
		  yaw_rate(0){};
};

struct Controller_Output_t
{

	// Orientation of the body frame with respect to the world frame
	Eigen::Quaterniond q;

	// Body rates in body frame
	Eigen::Vector3d bodyrates; // [rad/s]

	// Collective mass normalized thrust
	double thrust;

	//Eigen::Vector3d des_v_real;
};


class LinearControl
{
public:
  LinearControl(Parameter_t &);
  quadrotor_msgs::Px4ctrlDebug calculateControl(const Desired_State_t &des,
      const Odom_Data_t &odom,
      const Imu_Data_t &imu, 
      Controller_Output_t &u,
      const double tilt_max_deg = -1.0);
  bool estimateThrustModel(const Eigen::Vector3d &est_v,
      const Parameter_t &param);
  void resetThrustMapping(void);

  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

private:
  Parameter_t param_;
  quadrotor_msgs::Px4ctrlDebug debug_msg_;
  std::queue<std::pair<ros::Time, double>> timed_thrust_;
  static constexpr double kMinNormalizedCollectiveThrust_ = 3.0;

  // Thrust-accel mapping params
  const double rho2_ = 0.998; // do not change
  double thr2acc_;
  double P_;

  double computeDesiredCollectiveThrustSignal(const Eigen::Vector3d &des_acc);
  double fromQuaternion2yaw(Eigen::Quaterniond q);

  // ---- W4/W5/W6: 控制核心 v2 状态（enabled=false 时从不参与运算）----
  px4ctrl_core::AxisCfg cfg_x_, cfg_y_, cfg_z_;
  px4ctrl_core::AxisMem mem_x_, mem_y_, mem_z_;
  ros::Time last_step_t_;
  bool v2_primed_ = false;
  double last_u_ = 0.0;          // 上一拍发出的推力（无扰切换用）
  double last_cos_tilt_ = 1.0;
  void applyV2Config();          // 把 param_.ctrl_v2 灌进 cfg_*
  double stepDt();               // 实测 dt（钳位 [dt_min, dt_max]）

  // FIX-20261022r2: 帧偏置保持状态（判读 v5 复查升级）
  Eigen::Quaterniond off_filt_ = Eigen::Quaterniond::Identity();
  bool off_valid_ = false;
  bool off_relock_armed_ = false;
  double off_fresh_t0_ = -1.0;
};


#endif
