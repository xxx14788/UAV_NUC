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
    pnh.param("imu_check_enabled", enabled_, true);
    pnh.param("imu_rel_dev_thresh", rel_thresh_, 0.5);
    pnh.param("imu_dev_need", dev_need_, 5);
    pnh.param("imu_win_frames", win_frames_, 20);   // 1s @20Hz
    have_last_ = false;
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
    if (!have_last_)
    {
      last_t_ = t1;
      // 首帧: 锚定 IMU 速度状态 = vision twist(物理初值, 此后独立演化)
      v_[0] = msg->twist.twist.linear.x;
      v_[1] = msg->twist.twist.linear.y;
      v_[2] = msg->twist.twist.linear.z;
      last_p_[0] = msg->pose.pose.position.x;
      last_p_[1] = msg->pose.pose.position.y;
      last_p_[2] = msg->pose.pose.position.z;
      anchor_p_[0] = last_p_[0]; anchor_p_[1] = last_p_[1]; anchor_p_[2] = last_p_[2];
      have_last_ = true;
      return true;
    }
    // 取 [last_t_, t1] 区间 IMU 死推算
    bool integrated = integrate(last_t_, t1, msg);
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
      double diff[3] = {dv[0] - dp_imu_[0], dv[1] - dp_imu_[1], dv[2] - dp_imu_[2]};
      double nd = std::sqrt(diff[0] * diff[0] + diff[1] * diff[1] + diff[2] * diff[2]);
      double denom = std::max(std::max(nv, ni), 0.15);  // 悬停下限, 防微小数值误报
      double rel = nd / denom;
      ++frame_idx_;
      if (frame_idx_ >= (size_t)win_frames_)
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
        // 重锚: 窗口起点重置(IMU 死推不长期裸奔), 速度状态重新锚定 vision
        v_[0] = msg->twist.twist.linear.x;
        v_[1] = msg->twist.twist.linear.y;
        v_[2] = msg->twist.twist.linear.z;
        dp_imu_[0] = dp_imu_[1] = dp_imu_[2] = 0;
        anchor_p_[0] = msg->pose.pose.position.x;
        anchor_p_[1] = msg->pose.pose.position.y;
        anchor_p_[2] = msg->pose.pose.position.z;
      }
      ok = dev_cnt_ < dev_need_;
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
