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
		// C3-B2 H4-FIX（B1 预注册）：起飞控制包络三参数
		double thrust_cap;    // >0：AUTO_TAKEOFF 包络内推力上限（0=关闭=旧行为）
		double tilt_max_deg;  // >0：AUTO_TAKEOFF 姿态倾角限幅（-1=关闭=旧行为）
		double cap_release_z; // odom_z 高出起飞锚该值后释放包络
		// C3-B2 H4-F3（设计文档 §11 回炉增补预注册）：姿态门控推力
		double att_gate_deg;  // >0：实际倾角超此值期间推力压到平衡档（-1=关闭）
		double gated_thrust;  // 门控期推力上限（0=关闭）
		double land_speed;    // 2026-11-04 用户指令：降落速度（0=沿用 takeoff_land_speed）
		// 2026-11-05 用户指令：悬停锚点锁定起飞点 xy（false=旧行为：锁进入悬停瞬间位置）
		bool hover_at_takeoff_xy;
		// 2026-11-07（判读 v1 §5 批2，默认关）：起飞参考整形。
		// >0：用 ctrl_core::takeoffRef 的"加速-匀速-减速"剖面替换"速度阶跃到 speed"；
		// 取值 = 加减速度 [m/s^2]。0 = 关闭 = 旧行为（速度阶跃，实测推力尖峰
		// 0.15->0.675 = 1.26~1.36x 悬停，是离地冲击的能量源）。
		// **本批只落地不启用**：与 ground_lock 一起开会分不清是谁的效果。
		double ref_accel;
	};

	// 2026-11-07 起飞地面锁定（GROUND_LOCK，判读 v1 §3，本批主修）
	// 地面阶段：不产生任何水平力需求 + 姿态指令走执行器侧(PX4)估计姿态；
	// 离地确认那一拍把起飞锚点 xy/yaw 重捕为此刻。enable=false 等价旧行为。
	struct GroundLock
	{
		bool enable = false;         // 实机 yaml 置 true
		double z_release = 0.06;     // 离地判据 dz [m]
		double vz_release = 0.05;    // 离地判据 vz [m/s]
		double confirm_s = 0.15;     // 双门同时成立需持续 [s]
		double blend_s = 0.25;       // 释放后姿态指令交叉 [s]
		double guard_tilt_deg = 5.0; // 锁定期间实测倾角超此值打 ERROR（只告警不动作）
	};
	// W4/W5/W6（2026-11-06）：控制核心 v2（串级+积分+参考整形+1/cos+无扰切换）。
	// **默认 enabled=false = 逐位保留 legacy 行为**；参数全为 optional（缺键用默认）。
	// 2026-11-06 砍旋钮：原 CtrlV2_t 有 13 个键，全部收进 ctrl_core.h 的 PX4 参考常量。
	// 这里只留总开关。yaml 的 ctrl_v2 段现在只有一个 enabled。
	struct CtrlV2_t
	{
		bool enabled = false;
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
	GroundLock ground_lock;   // 2026-11-07 起飞地面锁定
	OdomSanityGate_t odom_gate;
	CtrlV2_t ctrl_v2;
	// FIX-20261022r2: 帧偏置保持（true=修复；false=legacy 实时搬运）
	bool frame_off_hold;
	// F-1 (2026-10-22 判读v5): REINIT_RESET 分支开关（false=状态机零行为变化）
	bool reinit_reset_enabled;
	double frame_off_dev_max_deg;

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