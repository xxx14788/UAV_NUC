/**
 * T1-W4 depth camera_info 合成转发(v2:零 gazebo 侧额外订阅)。
 *
 * v1 订阅 rgb/camera_info 会在 openni 插件里激活 RGB 相机渲染,飞行中引入额外渲染负载
 * (smoke5/6 失败的唯一链路差异,二分归因中)。v2 改为内参全来自参数(launch 里本就有
 * cx/cy/fx/fy,同源 SDF hfov 推算,B 线交叉验证过),只订阅深度图。
 *
 * 根因背景:gazebo_ros_openni_kinect 的 DepthInfoConnect 不调 SetActive(true),
 * 仅订阅 depth/camera_info 时零消息(分析:sitl_sim/t1_evidence/w4_caminfo_analysis.md)。
 */
#include <string>

#include <ros/ros.h>
#include <sensor_msgs/CameraInfo.h>
#include <sensor_msgs/Image.h>

int main(int argc, char **argv)
{
  ros::init(argc, argv, "depth_caminfo_relay");
  ros::NodeHandle nh;
  ros::NodeHandle pnh("~");

  std::string depth_topic, out_topic;
  double fx, fy, cx, cy;
  pnh.param<std::string>("depth_image", depth_topic,
                         "/iris_depth_camera/camera/depth/image_raw");
  pnh.param<std::string>("out", out_topic,
                         "/iris_depth_camera/camera/depth/camera_info");
  // 内参默认值 = run_planner_sitl.launch 同源(SDF hfov=1.5009831567 @848x480 推算)
  pnh.param("fx", fx, 454.6857718666893);
  pnh.param("fy", fy, 454.6857718666893);
  pnh.param("cx", cx, 424.5);
  pnh.param("cy", cy, 240.5);

  ros::Publisher pub = nh.advertise<sensor_msgs::CameraInfo>(out_topic, 10);
  ROS_INFO("[depth_caminfo_relay] %s -> %s (fx=%.3f cx=%.1f cy=%.1f, from params)",
           depth_topic.c_str(), out_topic.c_str(), fx, cx, cy);

  ros::Subscriber sub = nh.subscribe<sensor_msgs::Image>(
      depth_topic, 10, [&](const sensor_msgs::ImageConstPtr &depth) {
        sensor_msgs::CameraInfo msg;
        msg.header = depth->header;
        msg.height = depth->height;
        msg.width = depth->width;
        msg.distortion_model = "plumb_bob";
        msg.D = {0.0, 0.0, 0.0, 0.0, 0.0};
        msg.K = {fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0};
        msg.R = {1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0};
        msg.P = {fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0};
        msg.binning_x = 0; msg.binning_y = 0;
        pub.publish(msg);
      });

  ros::spin();
  return 0;
}
