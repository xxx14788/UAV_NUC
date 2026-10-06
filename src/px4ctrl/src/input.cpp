#include "input.h"

RC_Data_t::RC_Data_t()
{
    rcv_stamp = ros::Time(0);

    last_mode = -1.0;
    last_gear = -1.0;

    // Parameter initilation is very important in RC-Free usage!
    is_hover_mode = true;
    enter_hover_mode = false;
    is_command_mode = true;
    enter_command_mode = false;
    toggle_reboot = false;
    for (int i = 0; i < 4; ++i)
    {
        ch[i] = 0.0;
    }
}

void RC_Data_t::feed(mavros_msgs::RCInConstPtr pMsg)
{
    msg = *pMsg;
    rcv_stamp = ros::Time::now();

    for (int i = 0; i < 4; i++)
    {
        ch[i] = ((double)msg.channels[i] - 1500.0) / 500.0;
        if (ch[i] > DEAD_ZONE)
            ch[i] = (ch[i] - DEAD_ZONE) / (1 - DEAD_ZONE);
        else if (ch[i] < -DEAD_ZONE)
            ch[i] = (ch[i] + DEAD_ZONE) / (1 - DEAD_ZONE);
        else
            ch[i] = 0.0;
    }

    mode = ((double)msg.channels[4] - 1000.0) / 1000.0;
    gear = ((double)msg.channels[5] - 1000.0) / 1000.0;
    reboot_cmd = ((double)msg.channels[7] - 1000.0) / 1000.0;

    check_validity();

    if (!have_init_last_mode)
    {
        have_init_last_mode = true;
        last_mode = mode;
    }
    if (!have_init_last_gear)
    {
        have_init_last_gear = true;
        last_gear = gear;
    }
    if (!have_init_last_reboot_cmd)
    {
        have_init_last_reboot_cmd = true;
        last_reboot_cmd = reboot_cmd;
    }

    // 1
    if (last_mode < API_MODE_THRESHOLD_VALUE && mode > API_MODE_THRESHOLD_VALUE)
        enter_hover_mode = true;
    else
        enter_hover_mode = false;

    if (mode > API_MODE_THRESHOLD_VALUE)
        is_hover_mode = true;
    else
        is_hover_mode = false;

    // 2
    if (is_hover_mode)
    {
        if (last_gear < GEAR_SHIFT_VALUE && gear > GEAR_SHIFT_VALUE)
            enter_command_mode = true;
        else if (gear < GEAR_SHIFT_VALUE)
            enter_command_mode = false;

        if (gear > GEAR_SHIFT_VALUE)
            is_command_mode = true;
        else
            is_command_mode = false;
    }

    // 3
    if (!is_hover_mode && !is_command_mode)
    {
        if (last_reboot_cmd < REBOOT_THRESHOLD_VALUE && reboot_cmd > REBOOT_THRESHOLD_VALUE)
            toggle_reboot = true;
        else
            toggle_reboot = false;
    }
    else
        toggle_reboot = false;

    last_mode = mode;
    last_gear = gear;
    last_reboot_cmd = reboot_cmd;
}

void RC_Data_t::check_validity()
{
    if (mode >= -1.1 && mode <= 1.1 && gear >= -1.1 && gear <= 1.1 && reboot_cmd >= -1.1 && reboot_cmd <= 1.1)
    {
        // pass
    }
    else
    {
        ROS_ERROR("RC data validity check fail. mode=%f, gear=%f, reboot_cmd=%f", mode, gear, reboot_cmd);
    }
}

bool RC_Data_t::check_centered()
{
    bool centered = abs(ch[0]) < 1e-5 && abs(ch[0]) < 1e-5 && abs(ch[0]) < 1e-5 && abs(ch[0]) < 1e-5;
    return centered;
}

Odom_Data_t::Odom_Data_t()
{
    rcv_stamp = ros::Time(0);
    q.setIdentity();
    recv_new_msg = false;
};

void Odom_Data_t::feed(nav_msgs::OdometryConstPtr pMsg)
{
    ros::Time now = ros::Time::now();

    // T1-D2 (2026-09-29): value-sanity gate. Violating frames are REJECTED
    // before touching state: msg/rcv_stamp keep the last accepted frame, so
    // sustained garbage expires the existing freshness timeout
    // (odom_is_received) and degrades via the EXISTING MANUAL_CTRL path --
    // identical to a real odom dropout, no new behavior class. Disabled by
    // default (real-machine yaml has no key) = exact legacy behavior.
    {
        Eigen::Vector3d p_in, v_in, w_in;
        Eigen::Quaterniond q_in;
        uav_utils::extract_odometry(pMsg, p_in, v_in, q_in, w_in);
        double t_in = pMsg->header.stamp.isZero() ? now.toSec()
                                                  : pMsg->header.stamp.toSec();
        OdomSanityVerdict verdict = odom_sanity_check(sanity_cfg, sanity_st, t_in, p_in, v_in);
        if (verdict != OdomSanityVerdict::ACCEPT)
        {
            if (sanity_st.rejected % sanity_cfg.warn_every == 1)
                ROS_ERROR("[px4ctrl] odom sanity gate REJECTED frame (v=%d): |v|=%.2f |p|=%.2f |dv|ref, total_rejected=%ld",
                          (int)verdict, v_in.norm(), p_in.norm(), sanity_st.rejected);
            return;  // state untouched: freshness clock runs on last healthy frame
        }
        // Z1.2 (v11.17 2.2 接线本体): v2 增强层——v1 ACCEPT 后叠加(运动学残差 R/
        // 戳龄/时戳回退);enabled_v2=false 时零调用=v1 行为逐位不变(回归口径)
        if (sanity_cfg_v2.enabled && sanity_cfg_v2.enabled_v2)
        {
            OdomSanityVerdictV2 v2 = odom_sanity_check_v2(sanity_cfg_v2, sanity_st_v2,
                                                          pMsg->header.stamp.toSec(), now.toSec(), p_in, v_in);
            if (v2 != OdomSanityVerdictV2::ACCEPT)
            {
                if (sanity_st_v2.rejected % sanity_cfg_v2.warn_every == 1)
                    ROS_ERROR("[px4ctrl] odom sanity v2 REJECTED frame (v=%d): |v|=%.2f |p|=%.2f, total=%ld",
                              (int)v2, v_in.norm(), p_in.norm(), sanity_st_v2.rejected);
                return;
            }
        }
        // T1-P1 (v11.0 unit 2): rebirth birth-offset check. Gap counted
        // on ACCEPTED frames only (poison frames expire freshness, so a
        // gap here = true supply loss e.g. VINS restart). Uses p (last
        // accepted pose) BEFORE it is overwritten by p_in below.
        if (p1_cfg.enabled && !rcv_stamp.isZero() &&
            (now - rcv_stamp).toSec() > p1_cfg.gap_sec)
        {
            double p1_off = (p_in - p).norm();
            if (p1_off > p1_cfg.birth_thresh)
            {
                birth_mismatch = true;
                ROS_ERROR("[px4ctrl] P1: odom REBIRTH birth-offset %.2fm > %.2fm (gap %.1fs) - frame misaligned (U9 1.42m family); AUTO_HOVER entry gated until disarm.",
                          p1_off, p1_cfg.birth_thresh, (now - rcv_stamp).toSec());
            }
            else
                ROS_INFO("[px4ctrl] P1: odom gap-rebirth re-aligned (offset %.2fm <= %.2fm).",
                         p1_off, p1_cfg.birth_thresh);
        }
        msg = *pMsg;
        rcv_stamp = now;
        recv_new_msg = true;
        p = p_in; v = v_in; q = q_in; w = w_in;
    }


// #define VEL_IN_BODY
#ifdef VEL_IN_BODY /* Set to 1 if the velocity in odom topic is relative to current body frame, not to world frame.*/
    Eigen::Quaternion<double> wRb_q(msg.pose.pose.orientation.w, msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z);
    Eigen::Matrix3d wRb = wRb_q.matrix();
    v = wRb * v;

    static int count = 0;
    if (count++ % 500 == 0)
        ROS_WARN("VEL_IN_BODY!!!");
#endif

    // check the frequency
    static int one_min_count = 9999;
    static ros::Time last_clear_count_time = ros::Time(0.0);
    if ( (now - last_clear_count_time).toSec() > 1.0 )
    {
        if ( one_min_count < 100 )
        {
            ROS_WARN("ODOM frequency seems lower than 100Hz, which is too low!");
        }
        one_min_count = 0;
        last_clear_count_time = now;
    }
    one_min_count ++;
}

Imu_Data_t::Imu_Data_t()
{
    rcv_stamp = ros::Time(0);
}

void Imu_Data_t::feed(sensor_msgs::ImuConstPtr pMsg)
{
    ros::Time now = ros::Time::now();

    msg = *pMsg;
    rcv_stamp = now;

    w(0) = msg.angular_velocity.x;
    w(1) = msg.angular_velocity.y;
    w(2) = msg.angular_velocity.z;

    a(0) = msg.linear_acceleration.x;
    a(1) = msg.linear_acceleration.y;
    a(2) = msg.linear_acceleration.z;

    q.x() = msg.orientation.x;
    q.y() = msg.orientation.y;
    q.z() = msg.orientation.z;
    q.w() = msg.orientation.w;

    // check the frequency
    static int one_min_count = 9999;
    static ros::Time last_clear_count_time = ros::Time(0.0);
    if ( (now - last_clear_count_time).toSec() > 1.0 )
    {
        if ( one_min_count < 100 )
        {
            ROS_WARN("IMU frequency seems lower than 100Hz, which is too low!");
        }
        one_min_count = 0;
        last_clear_count_time = now;
    }
    one_min_count ++;
}

State_Data_t::State_Data_t()
{
}

void State_Data_t::feed(mavros_msgs::StateConstPtr pMsg)
{
    rcv_stamp = ros::Time::now(); // T1-W1: FCU 链路活性

    current_state = *pMsg;
}

ExtendedState_Data_t::ExtendedState_Data_t()
{
}

void ExtendedState_Data_t::feed(mavros_msgs::ExtendedStateConstPtr pMsg)
{
    current_extended_state = *pMsg;
}

Command_Data_t::Command_Data_t()
{
    rcv_stamp = ros::Time(0);
}

void Command_Data_t::feed(quadrotor_msgs::PositionCommandConstPtr pMsg)
{

    msg = *pMsg;
    rcv_stamp = ros::Time::now();

    // T3-E2 诊断: px4ctrl 侧消费点低频日志（与 traj_server 发布点对齐）
    ROS_INFO_THROTTLE(1.0,
        "[pmdiag] rcv p=(%.2f,%.2f,%.2f) v=(%.2f,%.2f,%.2f) yaw=%.1f id=%d",
        pMsg->position.x, pMsg->position.y, pMsg->position.z,
        pMsg->velocity.x, pMsg->velocity.y, pMsg->velocity.z,
        pMsg->yaw, pMsg->trajectory_id);

    p(0) = msg.position.x;
    p(1) = msg.position.y;
    p(2) = msg.position.z;

    v(0) = msg.velocity.x;
    v(1) = msg.velocity.y;
    v(2) = msg.velocity.z;

    a(0) = msg.acceleration.x;
    a(1) = msg.acceleration.y;
    a(2) = msg.acceleration.z;

    j(0) = msg.jerk.x;
    j(1) = msg.jerk.y;
    j(2) = msg.jerk.z;

    // std::cout << "j1=" << j.transpose() << std::endl;

    yaw = uav_utils::normalize_angle(msg.yaw);
    yaw_rate = msg.yaw_dot;
}

Battery_Data_t::Battery_Data_t()
{
    rcv_stamp = ros::Time(0);
}

void Battery_Data_t::feed(sensor_msgs::BatteryStateConstPtr pMsg)
{

    msg = *pMsg;
    rcv_stamp = ros::Time::now();

    double voltage = 0;
    for (size_t i = 0; i < pMsg->cell_voltage.size(); ++i)
    {
        voltage += pMsg->cell_voltage[i];
    }
    volt = 0.8 * volt + 0.2 * voltage; // Naive LPF, cell_voltage has a higher frequency

    // volt = 0.8 * volt + 0.2 * pMsg->voltage; // Naive LPF
    percentage = pMsg->percentage;

    static ros::Time last_print_t = ros::Time(0);
    if (percentage > 0.05)
    {
        if ((rcv_stamp - last_print_t).toSec() > 10)
        {
            ROS_INFO("[px4ctrl] Voltage=%.3f, percentage=%.3f", volt, percentage);
            last_print_t = rcv_stamp;
        }
    }
    else
    {
        if ((rcv_stamp - last_print_t).toSec() > 1)
        {
            // ROS_ERROR("[px4ctrl] Dangerous! voltage=%.3f, percentage=%.3f", volt, percentage);
            last_print_t = rcv_stamp;
        }
    }
}

Takeoff_Land_Data_t::Takeoff_Land_Data_t()
{
    rcv_stamp = ros::Time(0);
}

void Takeoff_Land_Data_t::feed(quadrotor_msgs::TakeoffLandConstPtr pMsg)
{

    msg = *pMsg;
    rcv_stamp = ros::Time::now();

    triggered = true;
    takeoff_land_cmd = pMsg->takeoff_land_cmd;
}
