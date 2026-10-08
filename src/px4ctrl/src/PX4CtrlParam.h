#ifndef __PX4CTRLPARAM_H
#define __PX4CTRLPARAM_H

#include <ros/ros.h>

class Parameter_t
{
public:
	struct Gain
	{
		double Kp0, Kp1, Kp2;
		double Kv0, Kv1, Kv2;
		double Kvi0, Kvi1, Kvi2;
		double Kvd0, Kvd1, Kvd2;
		double KAngR, KAngP, KAngY;
	};

	struct RotorDrag
	{
		double x, y, z;
		double k_thrust_horz;
	};

	struct MsgTimeout
	{
		double odom;
		double rc;
		double cmd;
		double imu;
		double bat;
	};

	struct ThrustMapping
	{
		bool print_val;
		double K1;
		double K2;
		double K3;
		bool accurate_thrust_model;
		double hover_percentage;
			bool enable_rls;
	};

	struct RCReverse
	{
		bool roll;
		bool pitch;
		bool yaw;
		bool throttle;
	};

	struct AutoTakeoffLand
	{
		bool enable;
		bool enable_auto_arm;
		bool no_RC;
		double height;
		double speed;

	};

	struct OdomSanityGate_t
	{
		// T1-D2 (2026-09-29): odom value-sanity gate. Defaults keep legacy
		// behavior when keys are absent (real-machine yaml untouched).
		bool enabled = false;
		double max_vel = 5.0;
		double max_acc = 10.0;
		double max_jump = 1.0;
		// Z1.2 (v11.17 2.2 接线本体): v2 总开关参数面贯通——默认 false=v1 行为
		// 逐位不变;SITL yaml 显式置位翻入运行时(三步常规化 77/77 绿在册后置件)。
		bool enabled_v2 = false;
	};

	Gain gain;
	RotorDrag rt_drag;
	MsgTimeout msg_timeout;
	RCReverse rc_reverse;
	ThrustMapping thr_map;
	AutoTakeoffLand takeoff_land;
	OdomSanityGate_t odom_gate;

	// T1-v1125-4b HAFIX (D1 演练实证:飞行期 VINS 死亡=盲飞+disarm=0 炸机路径)
	struct HaFix_t
	{
		bool enabled;
		double dead_s;   // odom 流死亡持续阈值(触发梯① AUTO_LAND)
		double kill_s;   // 梯①后再经此窗仍 armed → KILL+disarm 兜底
		double p3_max_recovery_s; // T1 v11.31 2f P3: 计划内恢复窗(reboot_notify 后 HAFIX 挂起窗)
	};
	HaFix_t ha_fix;
	// T1-P1 (v11.0 unit 2): rebirth birth-offset gate params
	struct
	{
		bool enabled;
		double gap_sec;
		double birth_thresh;
	} p1_rebirth;
	// T1-P2 (v11.4 unit 3): cmd-response divergence gate params
	// (frozen v1: eps_static 0.5 m / drift_rate 0.21 m/s / win 10 s —
	// u3_hover_drift_verdict.md caliber; SITL yaml only, default OFF)
	struct
	{
		bool enabled;
		double win_sec;
		double eps_static_m;
		double drift_rate_mps;
	} p2_cmdresp;

	int pose_solver;
	double mass;
	double gra;
	double max_angle;
	double ctrl_freq_max;
	double max_manual_vel;
	double low_voltage;

	bool use_bodyrate_ctrl;
	// bool print_dbg;

	Parameter_t();
	void config_from_ros_handle(const ros::NodeHandle &nh);
	void config_full_thrust(double hov);

private:
	template <typename TName, typename TVal>
	void read_essential_param(const ros::NodeHandle &nh, const TName &name, TVal &val)
	{
		if (nh.getParam(name, val))
		{
			// pass
		}
		else
		{
			ROS_ERROR_STREAM("Read param: " << name << " failed.");
			ROS_BREAK();
		}
	};
};

#endif