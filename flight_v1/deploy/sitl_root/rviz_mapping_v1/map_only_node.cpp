// Standalone viewer using the installed EGO GridMap library. No trajectory server.
#include <plan_env/grid_map.h>
#include <ros/message_event.h>
#include <std_msgs/String.h>
#include <cmath>
#include <iomanip>
#include <sstream>

class MapViewer {
  using Policy = message_filters::sync_policies::ApproximateTime<sensor_msgs::Image, nav_msgs::Odometry>;
  ros::NodeHandle nh_{"~"};
  GridMap grid_;
  message_filters::Subscriber<sensor_msgs::Image> depth_;
  message_filters::Subscriber<nav_msgs::Odometry> odom_;
  std::shared_ptr<message_filters::Synchronizer<Policy>> sync_;
  ros::Subscriber ext_;
  ros::Publisher image_pub_, pose_pub_, status_pub_;
  ros::WallTimer timer_;
  Eigen::Isometry3d imu_from_cam_ = Eigen::Isometry3d::Identity();
  ros::Time ext_stamp_;
  ros::Time last_stamp_;
  ros::WallTime last_pair_;
  Eigen::Isometry3d last_imu_ = Eigen::Isometry3d::Identity();
  std::string depth_frame_, world_frame_;
  bool have_ext_ = false;
  bool restart_required_ = false;
  uint64_t accepted_ = 0, rejected_ = 0;
  double max_age_ = 0.5, max_skew_ = 0.04;

  static bool pose(const geometry_msgs::Pose &p, Eigen::Isometry3d &t) {
    Eigen::Quaterniond q(p.orientation.w, p.orientation.x, p.orientation.y, p.orientation.z);
    Eigen::Vector3d v(p.position.x, p.position.y, p.position.z);
    if (!v.allFinite() || !q.coeffs().allFinite() || std::abs(q.norm() - 1.0) > 0.01) return false;
    t = Eigen::Isometry3d::Identity();
    t.linear() = q.normalized().toRotationMatrix();
    t.translation() = v;
    return true;
  }
  bool fresh(const ros::Time &t) const {
    const double age = (ros::Time::now() - t).toSec();
    return !t.isZero() && age >= -0.05 && age <= max_age_;
  }
  void extrinsic(const nav_msgs::OdometryConstPtr &m) {
    Eigen::Isometry3d t;
    have_ext_ = fresh(m->header.stamp) && pose(m->pose.pose, t) && t.translation().norm() < 1.0;
    if (have_ext_) { imu_from_cam_ = t; ext_stamp_ = m->header.stamp; }
  }
  void pair(const sensor_msgs::ImageConstPtr &image, const nav_msgs::OdometryConstPtr &odom) {
    if (restart_required_) { ++rejected_; return; }
    Eigen::Isometry3d world_from_imu;
    const double skew = std::abs((image->header.stamp - odom->header.stamp).toSec());
    if (!have_ext_ || !fresh(ext_stamp_) || !fresh(image->header.stamp) || !fresh(odom->header.stamp) ||
        skew > max_skew_ || image->header.frame_id != depth_frame_ || odom->header.frame_id != world_frame_ ||
        image->width != 640 || image->height != 480 || image->encoding != "16UC1" ||
        image->step < image->width * 2 || image->data.size() != image->step * image->height ||
        !pose(odom->pose.pose, world_from_imu)) {
      ++rejected_;
      ROS_WARN_THROTTLE(2.0, "Map input rejected: check freshness, dimensions, frame, quaternion and extrinsic.");
      return;
    }
    if (accepted_ > 0) {
      const double dt = (odom->header.stamp - last_stamp_).toSec();
      const double displacement = (world_from_imu.translation() - last_imu_.translation()).norm();
      const Eigen::AngleAxisd rotation(last_imu_.linear().transpose() * world_from_imu.linear());
      if (dt <= 0 || dt > 1.0 || displacement > 0.5 || std::abs(rotation.angle()) > 0.5) {
        restart_required_ = true;
        ++rejected_;
        ROS_ERROR("Map latched: odometry discontinuity; stop/start mapper to clear old world map.");
        return;
      }
    }
    // Camera optical -> IMU -> VINS world. No FRD/FLU conversion is guessed here.
    const Eigen::Isometry3d world_from_cam = world_from_imu * imu_from_cam_;
    const Eigen::Quaterniond q(world_from_cam.linear());
    geometry_msgs::PoseStamped p;
    p.header.stamp = image->header.stamp;
    p.header.frame_id = world_frame_;
    p.pose.position.x = world_from_cam.translation().x();
    p.pose.position.y = world_from_cam.translation().y();
    p.pose.position.z = world_from_cam.translation().z();
    p.pose.orientation.x = q.x(); p.pose.orientation.y = q.y();
    p.pose.orientation.z = q.z(); p.pose.orientation.w = q.w();
    // GridMap pose_type=1 consumes this CAMERA pose, not a body pose.
    pose_pub_.publish(p);
    image_pub_.publish(image);
    last_pair_ = ros::WallTime::now();
    last_stamp_ = odom->header.stamp;
    last_imu_ = world_from_imu;
    ++accepted_;
  }
  void status(const ros::WallTimerEvent &) {
    const double age = last_pair_.isZero() ? -1.0 : (ros::WallTime::now() - last_pair_).toSec();
    if (accepted_ > 0 && (age > 1.0 || !fresh(ext_stamp_) || grid_.getOdomDepthTimeout()))
      restart_required_ = true;
    const bool live = !restart_required_ && age >= 0.0 && age <= max_age_ && fresh(ext_stamp_) && grid_.hasDepthObservation() && !grid_.getOdomDepthTimeout();
    std::ostringstream s;
    s << std::fixed << std::setprecision(3)
      << "{\"live\":" << (live ? "true" : "false") << ",\"pair_age_s\":" << age
      << ",\"accepted\":" << accepted_ << ",\"rejected\":" << rejected_
      << ",\"restart_required\":" << (restart_required_ ? "true" : "false")
      << ",\"resolution_m\":" << grid_.getResolution() << "}";
    std_msgs::String m; m.data = s.str(); status_pub_.publish(m);
  }
public:
  MapViewer() {
    std::string depth_topic, odom_topic, ext_topic;
    nh_.param<std::string>("input/depth_topic", depth_topic, "/camera/depth/image_rect_raw");
    nh_.param<std::string>("input/odom_topic", odom_topic, "/vins_estimator/imu_propagate");
    nh_.param<std::string>("input/extrinsic_topic", ext_topic, "/vins_estimator/extrinsic");
    nh_.param<std::string>("input/depth_frame", depth_frame_, "camera_depth_optical_frame");
    nh_.param<std::string>("grid_map/frame_id", world_frame_, "world");
    nh_.param("input/max_age", max_age_, 0.5);
    nh_.param("input/max_skew", max_skew_, 0.04);
    // Private loopback topics prevent other ROS nodes from consuming these inputs.
    nh_.setParam("grid_map/pose_type", 1);
    grid_.initMap(nh_);
    grid_.resetBuffer();
    image_pub_ = nh_.advertise<sensor_msgs::Image>("grid_map/depth", 3);
    pose_pub_ = nh_.advertise<geometry_msgs::PoseStamped>("grid_map/pose", 3);
    status_pub_ = nh_.advertise<std_msgs::String>("status", 1);
    ext_ = nh_.subscribe(ext_topic, 10, &MapViewer::extrinsic, this);
    depth_.subscribe(nh_, depth_topic, 5);
    odom_.subscribe(nh_, odom_topic, 100, ros::TransportHints().tcpNoDelay());
    sync_.reset(new message_filters::Synchronizer<Policy>(Policy(100), depth_, odom_));
    sync_->setMaxIntervalDuration(ros::Duration(max_skew_));
    sync_->registerCallback(boost::bind(&MapViewer::pair, this, _1, _2));
    timer_ = nh_.createWallTimer(ros::WallDuration(0.5), &MapViewer::status, this);
    ROS_INFO("MAP VIEWER: depth=%s, camera pose from VINS; no trajectory/control publishers.", depth_topic.c_str());
  }
};

int main(int argc, char **argv) {
  ros::init(argc, argv, "mapping_view");
  MapViewer viewer;
  ros::spin();
}
