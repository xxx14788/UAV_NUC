#include <ros/ros.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseStamped.h>
#include <sensor_msgs/Imu.h>
#include <deque>
#include <vector>
#include <cmath>

ros::Publisher pose_pub;

// ---- 健康门控（T2-W4，2026-09-26 翻机事故防线）----
// 相邻帧位置跳变或隐含速度超阈 → 停止向 /mavros/vision_pose/pose 转发并告警；
// 连续 gate_stable_frames 帧平稳后自动恢复。阈值走私有 rosparam。
class HealthGate
{
public:
  HealthGate(ros::NodeHandle& pnh)
  {
    pnh.param("gate_enabled", enabled_, true);
    pnh.param("gate_pos_jump", pos_jump_m_, 1.0);      // 单帧位移阈值 (m)
    pnh.param("gate_vel", vel_max_, 5.0);              // 隐含速度阈值 (m/s)
    pnh.param("gate_stable_frames", stable_need_, 20); // 恢复所需连续平稳帧数
    ROS_INFO("vins_to_mavros gate: pos_jump=%.2f m, vel=%.1f m/s, stable=%d, "
             "enabled=%d", pos_jump_m_, vel_max_, stable_need_,
             (int)enabled_);
    blocked_ = false;
    stable_cnt_ = 0;
    have_last_ = false;
    viol_total_ = 0;
  }

  // 输入一帧 odom 位姿与时间戳，返回是否允许转发
  bool allow(const geometry_msgs::Point& p, const ros::Time& stamp)
  {
    if (!enabled_)
      return true;
    if (!have_last_)
    {
      last_p_ = p;
      last_t_ = stamp;
      have_last_ = true;
      stable_cnt_ = 1;
      return !blocked_;
    }
    double dt = (stamp - last_t_).toSec();
    if (dt <= 0.0)
      dt = 0.02;  // 时间戳异常时的保守假设（50Hz）
    double dx = p.x - last_p_.x, dy = p.y - last_p_.y, dz = p.z - last_p_.z;
    double jump = std::sqrt(dx * dx + dy * dy + dz * dz);
    double spd = jump / dt;
    if (jump > pos_jump_m_ || spd > vel_max_)
    {
      stable_cnt_ = 0;
      blocked_ = true;
      ++viol_total_;
      ROS_ERROR("vins_to_mavros gate: divergent odom (jump %.2f m, %.1f m/s) "
                "- vision_pose forwarding SUSPENDED (violation #%d)",
                jump, spd, viol_total_);
    }
    else
    {
      ++stable_cnt_;
      if (blocked_ && stable_cnt_ >= stable_need_)
      {
        blocked_ = false;
        ROS_INFO("vins_to_mavros gate: %d stable frames, forwarding RESUMED",
                 stable_cnt_);
      }
    }
    last_p_ = p;
    last_t_ = stamp;
    return !blocked_;
  }

  bool blocked() const { return blocked_; }

private:
  bool enabled_;
  double pos_jump_m_;
  double vel_max_;
  int stable_need_;
  bool blocked_;
  bool have_last_;
  int stable_cnt_;
  int viol_total_;
  geometry_msgs::Point last_p_;
  ros::Time last_t_;
};

// ---- IMU 一致性校验(T2b-U5, 2026-09-28 平滑漂移第二道防线)----
// W4 跳变门挡得住单帧爆炸, 挡不住 p2b 型平滑漂移(60m/240s, 帧帧平稳)。
// 机制: IMU 死推算速度状态独立演化(仅首帧锚定 vision twist), 每帧区间
// 积分去重力加速度推进; 每 win_frames 帧比较窗口内 vision 位移 vs IMU
// 预测位移, 相对偏差 > thresh 且连续 need 窗 → 拦截+ROS_ERROR。
// 漂移形态下 VINS 假速度不被共同信任(IMU 独立), 0.25m/s 级缓漂在 1s
// 窗口暴露为 >60% 偏差; 真实机动(6g 尖峰)两侧一致不误报。
class ImuConsistency
{
public:
  ImuConsistency(ros::NodeHandle& pnh)
  {
    // T2-v3 W1.1 (2026-09-28): 默认改为 false。地面静态实测误报根因:
    // 窗口锚定速度取自 vision twist(静态噪声 ~0.05-0.3 m/s)+姿态残余
    // 倾角的重力投影残差(≈g·sinθ),1s 窗内死推位移即超 0.15m 下限的
    // 50% 阈值——健康静态 VINS 被连续误判 SMOOTH DRIFT 并挂起
    // vision_pose(悬停工况会饿死 EKF2 EV 融合,飞行关键级危害)。
    // v2 重设计要点(未实现): ①窗口位移比较改速度增量+低通 ②窗口级
    // 最小二乘加速度偏置在线估计(吸收倾角/零偏) ③起评延迟至起飞后。
    // 跳变门(W4 第一道)不受影响,保持启用。
    pnh.param("imu_check_enabled", enabled_, false);
    pnh.param("imu_rel_dev_thresh", rel_thresh_, 0.5);
    pnh.param("imu_dev_need", dev_need_, 5);
    pnh.param("imu_win_frames", win_frames_, 20);   // 1s @20Hz
    // T2-R6 v2 (2026-09-29): 三改造参数
    pnh.param("imu_start_windows", start_windows_, 14);  // 起评延迟(v2b): 21s 覆盖 EMA 收敛期(τ10s, 静止重力残余吸收)
    pnh.param("imu_lpf_tau", lpf_tau_, 0.5);             // 锚定速度低通 [s]
    pnh.param("imu_bias_window", bias_win_, 10.0);       // 偏置 EMA 时间常数 [s](v2b)
    pnh.param("imu_win_sec", win_sec_, 1.5);             // 窗口时长, 时间基(v2b)
    have_last_ = false;
    have_lpf_ = false;
    win_count_ = 0;
    acc_T_ = 0.0;
    for (int i = 0; i < 3; i++) { b_hat_[i] = 0; acc_dv_[i] = 0; v_lpf_[i] = 0; v_lpf_win0_[i] = 0; }
    dev_cnt_ = 0;
    viol_total_ = 0;
    frame_idx_ = 0;
    for (int i = 0; i < 3; i++) { v_[i] = 0; dp_imu_[i] = 0; a_prev_[i] = 0; }
    have_acc_ = false;
    ROS_INFO("vins_to_mavros imu-check: rel_dev=%.2f need=%d win=%d enabled=%d",
             rel_thresh_, dev_need_, win_frames_, (int)enabled_);
  }

  void pushImu(const sensor_msgs::Imu::ConstPtr& m)
  {
    imu_.push_back(*m);
    if (imu_.size() > 6000)  // ~48s @125Hz
      imu_.pop_front();
  }

  // 返回是否允许转发; 内部无论放行与否都持续演化状态(观察+恢复)
  bool allow(const nav_msgs::Odometry::ConstPtr& msg)
  {
    if (!enabled_)
      return true;
    double t1 = msg->header.stamp.toSec();
    // T2-R6 v2①: 锚定速度 LPF(twist 噪声 0.05-0.3 m/s 压制; 静态误报根因之一)
    if (!have_lpf_)
    {
      v_lpf_[0] = msg->twist.twist.linear.x;
      v_lpf_[1] = msg->twist.twist.linear.y;
      v_lpf_[2] = msg->twist.twist.linear.z;
      have_lpf_ = true;
    }
    else if (have_last_)
    {
      double dtl = t1 - last_t_;
      if (dtl > 0)
      {
        double alpha = std::min(dtl / lpf_tau_, 1.0);
        v_lpf_[0] += alpha * (msg->twist.twist.linear.x - v_lpf_[0]);
        v_lpf_[1] += alpha * (msg->twist.twist.linear.y - v_lpf_[1]);
        v_lpf_[2] += alpha * (msg->twist.twist.linear.z - v_lpf_[2]);
      }
    }
    if (!have_last_)
    {
      last_t_ = t1;
      anchor_t_ = t1;
      v_lpf_win0_[0] = v_lpf_[0]; v_lpf_win0_[1] = v_lpf_[1]; v_lpf_win0_[2] = v_lpf_[2];
      // 首帧: 锚定 IMU 速度状态 = LPF 后 vision twist(v2①)
      v_[0] = v_lpf_[0];
      v_[1] = v_lpf_[1];
      v_[2] = v_lpf_[2];
      last_p_[0] = msg->pose.pose.position.x;
      last_p_[1] = msg->pose.pose.position.y;
      last_p_[2] = msg->pose.pose.position.z;
      anchor_p_[0] = last_p_[0]; anchor_p_[1] = last_p_[1]; anchor_p_[2] = last_p_[2];
      have_last_ = true;
      return true;
    }
    // 取 [last_t_, t1] 区间 IMU 死推算
    double v_before[3] = {v_[0], v_[1], v_[2]};
    bool integrated = integrate(last_t_, t1, msg);
    // T2-R6 v2②: 长窗偏置累积(窗内 IMU raw 速度增量 vs vision LPF 速度增量;
    // 满_bias_win_ 才更新 b_hat_——恒定倾角/零偏被吸收,缓漂不被追赶)
    if (integrated)
    {
      double Tw = t1 - last_t_;
      for (int k = 0; k < 3; k++)
        acc_dv_[k] += (v_[k] - v_before[k]) + b_hat_[k] * Tw
                      - (v_lpf_[k] - v_lpf_win0_[k]);
      acc_T_ += Tw;
      if (acc_T_ >= 0.5)
      {
        // T2-R6 v2b: EMA 每窗更新(替代 20s 批量——批量首次更新前 ~36s 裸奔,
        // 静止重力残余 g·sinθ 期间 IMU 死推 0.1-0.28m/窗是三工况误报主源之二;
        // EMA α=win/τ_bias, 静止首窗收敛大半, 机动瞬态被平滑)
        double bw[3];
        for (int k = 0; k < 3; k++) bw[k] = acc_dv_[k] / acc_T_;
        double alpha_b = std::min(acc_T_ / bias_win_, 1.0);
        for (int k = 0; k < 3; k++) b_hat_[k] += alpha_b * (bw[k] - b_hat_[k]);
        ROS_INFO("vins_to_mavros imu-check v2: bias ema |b|=%.3f win_obs=%.3f",
                 std::sqrt(b_hat_[0]*b_hat_[0]+b_hat_[1]*b_hat_[1]+b_hat_[2]*b_hat_[2]),
                 std::sqrt(bw[0]*bw[0]+bw[1]*bw[1]+bw[2]*bw[2]));
        for (int k = 0; k < 3; k++) acc_dv_[k] = 0;
        acc_T_ = 0.0;
      }
      v_lpf_win0_[0] = v_lpf_[0]; v_lpf_win0_[1] = v_lpf_[1]; v_lpf_win0_[2] = v_lpf_[2];
    }
    // vision 窗口位移
    double dv[3] = {msg->pose.pose.position.x - anchor_p_[0],
                    msg->pose.pose.position.y - anchor_p_[1],
                    msg->pose.pose.position.z - anchor_p_[2]};
    double nv = std::sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]);
    double ni = std::sqrt(dp_imu_[0] * dp_imu_[0] + dp_imu_[1] * dp_imu_[1] +
                          dp_imu_[2] * dp_imu_[2]);
    bool ok = true;
    if (integrated)
    {
      // T2-R6 v2③: 起评延迟(init 质量依赖期不判,静态误报根因之三)
      win_count_++;
      if (win_count_ <= start_windows_)
        ok = true;
      else
      {
      double diff[3] = {dv[0] - dp_imu_[0], dv[1] - dp_imu_[1], dv[2] - dp_imu_[2]};
      double nd = std::sqrt(diff[0] * diff[0] + diff[1] * diff[1] + diff[2] * diff[2]);
      double denom = std::max(std::max(nv, ni), 0.15);  // 悬停下限, 防微小数值误报
      double rel = nd / denom;
      ++frame_idx_;
      // T2-R6 v2b: 窗口判定改时间基(odometry 实际 10Hz, 20 帧语义=2s 死推窗,
      // 位移噪声底放大 4x 是三工况误报主源之一; 时间基回归设计语义)
      if (t1 - anchor_t_ >= win_sec_)
      {
        frame_idx_ = 0;
        if (rel > rel_thresh_)
        {
          ++dev_cnt_;
          ROS_WARN("vins_to_mavros imu-check: window dev %.2f (vins %.3f m vs imu "
                   "%.3f m, rel %.0f%%) #%d", nd, nv, ni, rel * 100, dev_cnt_);
          if (dev_cnt_ >= dev_need_)
          {
            ++viol_total_;
            ROS_ERROR("vins_to_mavros imu-check: SMOOTH DRIFT intercepted "
                      "(%d windows > %.0f%%, violation #%d) - vision_pose SUSPENDED",
                      dev_cnt_, rel_thresh_ * 100, viol_total_);
          }
        }
        else
        {
          if (dev_cnt_ > 0)
            ROS_INFO("vins_to_mavros imu-check: window consistent (rel %.0f%%), "
                     "counter %d -> 0", rel * 100, dev_cnt_);
          dev_cnt_ = 0;
        }
        // 重锚: 窗口起点重置(IMU 死推不长期裸奔), 速度状态锚定 LPF 后 vision(v2①)
        anchor_t_ = t1;
        v_[0] = v_lpf_[0];
        v_[1] = v_lpf_[1];
        v_[2] = v_lpf_[2];
        dp_imu_[0] = dp_imu_[1] = dp_imu_[2] = 0;
        anchor_p_[0] = msg->pose.pose.position.x;
        anchor_p_[1] = msg->pose.pose.position.y;
        anchor_p_[2] = msg->pose.pose.position.z;
      }
      ok = dev_cnt_ < dev_need_;
      }
    }
    last_t_ = t1;
    last_p_[0] = msg->pose.pose.position.x;
    last_p_[1] = msg->pose.pose.position.y;
    last_p_[2] = msg->pose.pose.position.z;
    return ok;
  }

private:
  // 四元数(body->world)旋转向量, 手写避免 Eigen 依赖
  static void rot(double out[3], const double q[4], const double v[3])
  {
    double w = q[3], x = q[0], y = q[1], z = q[2];
    // R = I + 2w[k] + 2k^2, k=(x,y,z)
    double kx = x, ky = y, kz = z;
    double kv[3] = {ky * v[2] - kz * v[1], kz * v[0] - kx * v[2], kx * v[1] - ky * v[0]};
    double kkv = kx * v[0] + ky * v[1] + kz * v[2];
    out[0] = v[0] + 2 * (w * kv[0] + kx * kkv);
    out[1] = v[1] + 2 * (w * kv[1] + ky * kkv);
    out[2] = v[2] + 2 * (w * kv[2] + kz * kkv);
  }

  // 区间 [t0,t1] 去重力积分; 姿态用 msg 四元数(区间内常值近似, 1s 窗口可接受)
  bool integrate(double t0, double t1, const nav_msgs::Odometry::ConstPtr& msg)
  {
    double q[4] = {msg->pose.pose.orientation.x, msg->pose.pose.orientation.y,
                   msg->pose.pose.orientation.z, msg->pose.pose.orientation.w};
    std::vector<const sensor_msgs::Imu*> seg;
    for (auto& m : imu_)
    {
      double t = m.header.stamp.toSec();
      if (t > t1)
        break;
      if (t >= t0 - 1e-6)
        seg.push_back(&m);
    }
    if (seg.size() < 2 || seg.front()->header.stamp.toSec() > t0 + 0.05 ||
        seg.back()->header.stamp.toSec() < t1 - 0.05)
      return false;  // IMU 覆盖不足(断流/域分裂): 不判, 交由原跳变门
    double tprev = t0;
    for (size_t i = 0; i < seg.size(); i++)
    {
      double t = seg[i]->header.stamp.toSec();
      double dt = t - tprev;
      if (dt > 0 && dt < 0.5)
      {
        double ab[3] = {seg[i]->linear_acceleration.x, seg[i]->linear_acceleration.y,
                        seg[i]->linear_acceleration.z};
        double aw[3];
        rot(aw, q, ab);
        aw[2] -= 9.81;  // 去重力(ENU, 静止比力 +z)
        // T2-R6 v2②: 减长窗偏置(吸收倾角重力投影残差/acc 零偏)
        for (int k = 0; k < 3; k++) aw[k] -= b_hat_[k];
        double am[3];
        if (have_acc_)
          for (int k = 0; k < 3; k++) am[k] = 0.5 * (aw[k] + a_prev_[k]);
        else
          for (int k = 0; k < 3; k++) am[k] = aw[k];
        for (int k = 0; k < 3; k++)
        {
          v_[k] += am[k] * dt;
          dp_imu_[k] += v_[k] * dt;  // 一阶积分足够(窗口 1s)
          a_prev_[k] = aw[k];
        }
        have_acc_ = true;
      }
      tprev = t;
    }
    return true;
  }

  bool enabled_;
  double rel_thresh_;
  int dev_need_;
  int win_frames_;
  bool have_last_;
  bool have_acc_;
  int dev_cnt_;
  bool have_lpf_;
  int win_count_;
  int start_windows_;
  double lpf_tau_, bias_win_;
  double v_lpf_[3], v_lpf_win0_[3];
  double b_hat_[3], acc_dv_[3], acc_T_;
  double win_sec_;
  double anchor_t_ = 0;
  int viol_total_;
  size_t frame_idx_;
  double last_t_;
  double last_p_[3];
  double anchor_p_[3];
  double v_[3];
  double dp_imu_[3];
  double a_prev_[3];
  std::deque<sensor_msgs::Imu> imu_;
};

static HealthGate* g_gate = nullptr;
static ImuConsistency* g_imu = nullptr;

void imu_callback(const sensor_msgs::Imu::ConstPtr& msg)
{
    if (g_imu)
        g_imu->pushImu(msg);
}

void vins_callback(const nav_msgs::Odometry::ConstPtr& msg)
{
    if (g_gate && !g_gate->allow(msg->pose.pose.position, msg->header.stamp))
        return;  // 跳变/爆炸：不转发（EKF2 防线, 第一道）
    if (g_imu && !g_imu->allow(msg))
        return;  // 平滑漂移：不转发（IMU 一致性, 第二道, T2b-U5）

    geometry_msgs::PoseStamped pose;

    pose.header.stamp = msg->header.stamp;
    pose.header.frame_id = "map";

    // 直接转发位姿
    pose.pose.position.x = msg->pose.pose.position.x;
    pose.pose.position.y = msg->pose.pose.position.y;
    pose.pose.position.z = msg->pose.pose.position.z;

    pose.pose.orientation.x = msg->pose.pose.orientation.x;
    pose.pose.orientation.y = msg->pose.pose.orientation.y;
    pose.pose.orientation.z = msg->pose.pose.orientation.z;
    pose.pose.orientation.w = msg->pose.pose.orientation.w;

    pose_pub.publish(pose);
}

int main(int argc, char** argv)
{
    ros::init(argc, argv, "vins_to_mavros");
    ros::NodeHandle nh;
    ros::NodeHandle pnh("~");

    HealthGate gate(pnh);
    g_gate = &gate;
    ImuConsistency imucheck(pnh);
    g_imu = &imucheck;

    // 订阅 VINS-Fusion 的里程计输出
    ros::Subscriber vins_sub = nh.subscribe("/vins_estimator/odometry", 10, vins_callback);
    // IMU 缓存(第二道防线, T2b-U5)
    ros::Subscriber imu_sub = nh.subscribe("/mavros/imu/data_raw", 2000, imu_callback);

    // 发布到 MAVROS 的视觉位姿输入
    pose_pub = nh.advertise<geometry_msgs::PoseStamped>("/mavros/vision_pose/pose", 10);

    ros::spin();
    return 0;
}
