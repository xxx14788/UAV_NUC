#include <ros/ros.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseStamped.h>

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

static HealthGate* g_gate = nullptr;

void vins_callback(const nav_msgs::Odometry::ConstPtr& msg)
{
    if (g_gate && !g_gate->allow(msg->pose.pose.position, msg->header.stamp))
        return;  // 发散期：不转发（EKF2 防线）

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

    // 订阅 VINS-Fusion 的里程计输出
    ros::Subscriber vins_sub = nh.subscribe("/vins_estimator/odometry", 10, vins_callback);

    // 发布到 MAVROS 的视觉位姿输入
    pose_pub = nh.advertise<geometry_msgs::PoseStamped>("/mavros/vision_pose/pose", 10);

    ros::spin();
    return 0;
}
