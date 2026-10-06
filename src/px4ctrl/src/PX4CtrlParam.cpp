#include "PX4CtrlParam.h"

Parameter_t::Parameter_t()
{
}

void Parameter_t::config_from_ros_handle(const ros::NodeHandle &nh)
{
	read_essential_param(nh, "gain/Kp0", gain.Kp0);
	read_essential_param(nh, "gain/Kp1", gain.Kp1);
	read_essential_param(nh, "gain/Kp2", gain.Kp2);
	read_essential_param(nh, "gain/Kv0", gain.Kv0);
	read_essential_param(nh, "gain/Kv1", gain.Kv1);
	read_essential_param(nh, "gain/Kv2", gain.Kv2);
	read_essential_param(nh, "gain/Kvi0", gain.Kvi0);
	read_essential_param(nh, "gain/Kvi1", gain.Kvi1);
	read_essential_param(nh, "gain/Kvi2", gain.Kvi2);
	read_essential_param(nh, "gain/KAngR", gain.KAngR);
	read_essential_param(nh, "gain/KAngP", gain.KAngP);
	read_essential_param(nh, "gain/KAngY", gain.KAngY);

	read_essential_param(nh, "rotor_drag/x", rt_drag.x);
	read_essential_param(nh, "rotor_drag/y", rt_drag.y);
	read_essential_param(nh, "rotor_drag/z", rt_drag.z);
	read_essential_param(nh, "rotor_drag/k_thrust_horz", rt_drag.k_thrust_horz);

	read_essential_param(nh, "msg_timeout/odom", msg_timeout.odom);
	read_essential_param(nh, "msg_timeout/rc", msg_timeout.rc);
	read_essential_param(nh, "msg_timeout/cmd", msg_timeout.cmd);
	read_essential_param(nh, "msg_timeout/imu", msg_timeout.imu);
	read_essential_param(nh, "msg_timeout/bat", msg_timeout.bat);

	// T1-D2 (2026-09-29): non-essential -- absent keys keep code defaults
	// (enabled=false -> legacy). SITL yaml sets them explicitly.
	nh.param("odom_gate/enabled", odom_gate.enabled, false);
	nh.param("odom_gate/max_vel", odom_gate.max_vel, 5.0);
	nh.param("odom_gate/max_acc", odom_gate.max_acc, 10.0);
	nh.param("odom_gate/max_jump", odom_gate.max_jump, 1.0);
	// Z1.2 (v11.17 2.2): v2 总开关参数读取(缺键=false=v1 行为逐位不变)
	nh.param("odom_gate/enabled_v2", odom_gate.enabled_v2, false);
	ROS_WARN("[px4ctrl] odom sanity gate: enabled=%d v2=%d max_vel=%.1f max_acc=%.1f max_jump=%.2f",
	         (int)odom_gate.enabled, (int)odom_gate.enabled_v2,
	         odom_gate.max_vel, odom_gate.max_acc, odom_gate.max_jump);

	// T1-P1 (v11.0 unit 2): rebirth birth-offset gate (default OFF = legacy;
	// SITL yaml enables). gap_sec 2.0 >> healthy 223Hz gaps (ms-level) and
	// << VINS restart window; birth_thresh 0.75 splits healthy cm-level
	// gap drift from the U9 rebirth family 1.42-1.46m (~20x separation).
	nh.param("p1_rebirth/enabled", p1_rebirth.enabled, false);
	nh.param("p1_rebirth/gap_sec", p1_rebirth.gap_sec, 2.0);
	nh.param("p1_rebirth/birth_thresh", p1_rebirth.birth_thresh, 0.75);
	ROS_WARN("[px4ctrl] P1 rebirth gate: enabled=%d gap_sec=%.1f birth_thresh=%.2f",
	         (int)p1_rebirth.enabled, p1_rebirth.gap_sec, p1_rebirth.birth_thresh);

	// T1-P2 (v11.4 unit 3): cmd-response divergence gate (default OFF =
	// legacy; SITL yaml enables). Frozen v1 thresholds from u3 verdict:
	// eps_static 0.5 m = healthy hover des-odom band upper edge (0.48-0.5);
	// drift_rate 0.21 m/s = event drift velocity (des_v=0 family); win 10 s
	// (0.21*10=2.1 m > 4*eps=2.0 m separation).
	nh.param("p2_cmdresp/enabled", p2_cmdresp.enabled, false);
	nh.param("p2_cmdresp/win_sec", p2_cmdresp.win_sec, 10.0);
	nh.param("p2_cmdresp/eps_static_m", p2_cmdresp.eps_static_m, 0.5);
	nh.param("p2_cmdresp/drift_rate_mps", p2_cmdresp.drift_rate_mps, 0.21);
	ROS_WARN("[px4ctrl] P2 cmdresp gate: enabled=%d win=%.1fs eps_static=%.2fm drift_rate=%.2fm/s",
	         (int)p2_cmdresp.enabled, p2_cmdresp.win_sec, p2_cmdresp.eps_static_m,
	         p2_cmdresp.drift_rate_mps);

	read_essential_param(nh, "pose_solver", pose_solver);
	read_essential_param(nh, "mass", mass);
	read_essential_param(nh, "gra", gra);
	read_essential_param(nh, "ctrl_freq_max", ctrl_freq_max);
	read_essential_param(nh, "use_bodyrate_ctrl", use_bodyrate_ctrl);
	read_essential_param(nh, "max_manual_vel", max_manual_vel);
	read_essential_param(nh, "max_angle", max_angle);
	read_essential_param(nh, "low_voltage", low_voltage);

	read_essential_param(nh, "rc_reverse/roll", rc_reverse.roll);
	read_essential_param(nh, "rc_reverse/pitch", rc_reverse.pitch);
	read_essential_param(nh, "rc_reverse/yaw", rc_reverse.yaw);
	read_essential_param(nh, "rc_reverse/throttle", rc_reverse.throttle);

	read_essential_param(nh, "auto_takeoff_land/enable", takeoff_land.enable);
    read_essential_param(nh, "auto_takeoff_land/enable_auto_arm", takeoff_land.enable_auto_arm);
    read_essential_param(nh, "auto_takeoff_land/no_RC", takeoff_land.no_RC);
	read_essential_param(nh, "auto_takeoff_land/takeoff_height", takeoff_land.height);
	read_essential_param(nh, "auto_takeoff_land/takeoff_land_speed", takeoff_land.speed);

	read_essential_param(nh, "thrust_model/print_value", thr_map.print_val);
	read_essential_param(nh, "thrust_model/K1", thr_map.K1);
	read_essential_param(nh, "thrust_model/K2", thr_map.K2);
	read_essential_param(nh, "thrust_model/K3", thr_map.K3);
	read_essential_param(nh, "thrust_model/accurate_thrust_model", thr_map.accurate_thrust_model);
	read_essential_param(nh, "thrust_model/hover_percentage", thr_map.hover_percentage);
	// T3 2026-09-27: RLS 推力映射自适应在 SITL 快速机动段可被加速度伪影喂爆致油门塌 0
	// (V2f/V2g 实证)。可选参数默认 true(实机零改动);SITL yaml 置 false 冻结估计器
	// (SITL 推力曲线恒定,名义 hover_percentage 即足够)。
	nh.param("thrust_model/enable_rls", thr_map.enable_rls, true);
	

	max_angle /= (180.0 / M_PI);

	if ( takeoff_land.enable_auto_arm && !takeoff_land.enable )
	{
		takeoff_land.enable_auto_arm = false;
		ROS_ERROR("\"enable_auto_arm\" is only allowd with \"auto_takeoff_land\" enabled.");
	}
	if ( takeoff_land.no_RC && (!takeoff_land.enable_auto_arm || !takeoff_land.enable) )
	{
		takeoff_land.no_RC = false;
		ROS_ERROR("\"no_RC\" is only allowd with both \"auto_takeoff_land\" and \"enable_auto_arm\" enabled.");
	}

	if ( thr_map.print_val )
	{
		ROS_WARN("You should disable \"print_value\" if you are in regular usage.");
	}
};

// void Parameter_t::config_full_thrust(double hov)
// {
// 	full_thrust = mass * gra / hov;
// };
