#ifndef __PX4CTRLFSM_H
#define __PX4CTRLFSM_H

#include <ros/ros.h>
#include <ros/assert.h>
#include <std_msgs/UInt32.h>

#include <geometry_msgs/PoseStamped.h>
#include <nav_msgs/Odometry.h>
#include <mavros_msgs/SetMode.h>
#include <mavros_msgs/CommandLong.h>
#include <mavros_msgs/CommandBool.h>
#include <mavros_msgs/PositionTarget.h>

#include "input.h"
// #include "ThrustCurve.h"
#include "controller.h"
#include "cmdresp_gate.h" // T1-P2: cmd-response divergence gate (v11.4 unit 3)

struct AutoTakeoffLand_t
{
	bool landed{true};
	ros::Time toggle_takeoff_land_time;
	std::pair<bool, ros::Time> delay_trigger{std::pair<bool, ros::Time>(false, ros::Time(0))};
	Eigen::Vector4d start_pose;
	
	static constexpr double MOTORS_SPEEDUP_TIME = 3.0; // motors idle running for 3 seconds before takeoff
	static constexpr double DELAY_TRIGGER_TIME = 2.0;  // Time to be delayed when reach at target height
	static constexpr double TAKEOFF_ABORT_TIMEOUT = 10.0; // T1-W1: 电机加速后仍 disarmed 且未离地这么久则放弃起飞
};

class PX4CtrlFSM
{
public:
	Parameter_t &param;

	RC_Data_t rc_data;
	State_Data_t state_data;
	ExtendedState_Data_t extended_state_data;
	Odom_Data_t odom_data;
	Imu_Data_t imu_data;
	Command_Data_t cmd_data;
	Battery_Data_t bat_data;
	Takeoff_Land_Data_t takeoff_land_data;

	LinearControl &controller;

	// T1-v1125-4b HAFIX: odom 死亡看门状态(0=监视/1=watch/2=LAND/3=KILL 已发)
	ros::Time ha_dead_since;
	// T1-v1139 P-1/P-2: 梯②KILL 与梯③disarm 1Hz 限频重试时戳
	ros::Time ha_kill_trial;
	ros::Time ha_disarm_trial;
	// T1 v11.31 2f P3: 计划内 reboot 通告消费面(p3_contract_design_v1)
	ros::Time p3_notify_time;
	uint32_t p3_last_msg = 0;
	bool p3_notify_seen = false;
	int ha_stage = 0;
	// F-1 (2026-10-22 判读v5): VINS 空中重初始化守卫状态（详 PX4CtrlFSM.cpp STEP0.6）
	bool reinit_poisoned_{false};      // reboot(ev=1) 置位；disarm 清除（resume 不清——世界系可能已换）
	bool reinit_handover_done_{false}; // 已交还手动（抑制 HAFIX auto_land 抢回）；disarm 清除
public:
	void p3NotifyFeed(const std_msgs::UInt32::ConstPtr &msg);

	ros::Publisher traj_start_trigger_pub;
	ros::Publisher ctrl_FCU_pub;
	ros::Publisher ctrl_FCU_pos_pub; // PositionTarget publisher for PX4 internal control
	ros::Publisher debug_pub; //debug
	ros::Publisher fsm_state_pub; // T1-W1: 1Hz FSM 状态自监视

	bool use_px4_position_ctrl{true}; // true: send PositionTarget (PX4 runs pos/vel PID), false: send AttitudeTarget (px4ctrl runs pos/vel PID)
	ros::ServiceClient set_FCU_mode_srv;
	ros::ServiceClient arming_client_srv;
	ros::ServiceClient reboot_FCU_srv;

	quadrotor_msgs::Px4ctrlDebug debug_msg; //debug

	// 2026-11-09（P0-5）：VINS 位姿健康守门。只看 VINS 健康，不看速度/倾角。
	// camera_pose 断流 >0.4 s 或位置跳变 >3 m/s -> 判"不健康"，切 AUTO_HOVER。
	ros::Time vins_pose_stamp_;
	ros::Time vins_bad_until_;
	Eigen::Vector3d vins_last_p_{Eigen::Vector3d::Zero()};
	bool vins_guard_enable_{true};
	// 2026-11-10（用户令）：0=关 1=影子(只记日志) 2=生效（刹车 0.8 s -> 开环悬停）
	int vins_guard_mode_{1};
	bool vins_guard_active_{false};
	ros::Time vins_guard_t0_;
	Eigen::Vector3d vins_stop_pt_{Eigen::Vector3d::Zero()};
	Eigen::Quaterniond vins_hold_q_{Eigen::Quaterniond::Identity()};
	double vins_hold_thrust_{-1.0};
	// P1-7：撞击检测计数（只报不做）
	long impact_cnt_{0};
	void vinsPoseFeed(const nav_msgs::Odometry::ConstPtr &msg);
	bool vinsBad() const
	{
		if (vins_pose_stamp_.isZero()) return false;   // 从未收到 -> fail-open，不误判
		return ros::Time::now() < vins_bad_until_;
	}

	Eigen::Vector4d hover_pose;
	ros::Time last_set_hover_pose_time;

	// T1-P2 (v11.4 unit 3): cmd-response divergence gate state.
	// Config injected from params in node main (default OFF = legacy);
	// fed each process() beat after des is final (armed non-MANUAL only);
	// latched flag feeds fsm_decision Inputs.cmdresp_divergent (RJ_CMDRESP).
	CmdRespConfig p2_cfg;
	CmdRespState p2_st;

	enum State_t
	{
		MANUAL_CTRL = 1, // px4ctrl is deactived. FCU is controled by the remote controller only
		AUTO_HOVER, // px4ctrl is actived, it will keep the drone hover from odom measurments while waiting for commands from PositionCommand topic.
		CMD_CTRL,	// px4ctrl is actived, and controling the drone.
		AUTO_TAKEOFF,
		AUTO_LAND
	};

	PX4CtrlFSM(Parameter_t &, LinearControl &);
	void process();
	bool rc_is_received(const ros::Time &now_time);
	bool cmd_is_received(const ros::Time &now_time);
	bool odom_is_received(const ros::Time &now_time);
	bool imu_is_received(const ros::Time &now_time);
	State_t get_state() { return state; }
	bool get_landed() { return takeoff_land.landed; }
	static std::string state2str(State_t s); // T1-W1: 状态名输出,自监视用

private:
	State_t state; // Should only be changed in PX4CtrlFSM::process() function!
	AutoTakeoffLand_t takeoff_land;
	// 2026-11-07 起飞地面锁定（GROUND_LOCK，判读 v1 §3）
	px4ctrl_core::GroundLockState gl_state_;
	double gl_kick_max_deg_ = 0.0;     // 锁定期间实测倾角峰值（guard + 判读量）
	bool gl_locked_this_tick_ = false;
	bool updateGroundLock(const ros::Time &now); // 返回本拍是否锁定

	// ---- control related ----
	Desired_State_t get_hover_des();
	Desired_State_t get_cmd_des();

	// ---- auto takeoff/land ----
	void motors_idling(const Imu_Data_t &imu, Controller_Output_t &u);
	void land_detector(const State_t state, const Desired_State_t &des, const Odom_Data_t &odom); // Detect landing 
	void set_start_pose_for_takeoff_land(const Odom_Data_t &odom);
	Desired_State_t get_rotor_speed_up_des(const ros::Time now);
	Desired_State_t get_takeoff_land_des(const double speed);

	// ---- tools ----
	void set_hov_with_odom();
	void set_hov_at_takeoff_xy(const Odom_Data_t &odom);
	void set_hov_with_rc();

	bool toggle_offboard_mode(bool on_off); // It will only try to toggle once, so not blocked.
	bool toggle_arm_disarm(bool arm); // It will only try to toggle once, so not blocked.
	void reboot_FCU();

	void publish_bodyrate_ctrl(const Controller_Output_t &u, const ros::Time &stamp);
	void publish_attitude_ctrl(const Controller_Output_t &u,const Desired_State_t &des, const ros::Time &stamp);
	void publish_position_ctrl(const Desired_State_t &des, const ros::Time &stamp);
	void publish_trigger(const nav_msgs::Odometry &odom_msg);
};

#endif