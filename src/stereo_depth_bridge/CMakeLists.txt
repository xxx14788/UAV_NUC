cmake_minimum_required(VERSION 3.0.2)
project(stereo_depth_bridge)

find_package(catkin REQUIRED)

catkin_package()

catkin_install_python(
  PROGRAMS scripts/stereo_depth_bridge_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
