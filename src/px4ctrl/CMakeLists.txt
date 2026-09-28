cmake_minimum_required(VERSION 2.8.3)
project(px4ctrl)

set(CMAKE_VERBOSE_MAKEFILE "false")

set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS "-std=c++11")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall -g")

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  quadrotor_msgs
  geometry_msgs
  sensor_msgs
  uav_utils
  mavros
)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
find_package(Eigen3 REQUIRED) 

catkin_package(
)

include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN_INCLUDE_DIRS}
  include/${PROJECT_NAME}
  include
)

add_executable(px4ctrl_node 
  src/px4ctrl_node.cpp
  src/PX4CtrlFSM.cpp
  src/PX4CtrlParam.cpp
  src/controller.cpp
  src/input.cpp
)

add_dependencies(px4ctrl_node quadrotor_msgs)

target_link_libraries(px4ctrl_node
  ${catkin_LIBRARIES}
)

catkin_install_python(PROGRAMS thrust_calibrate_scrips/thrust_calibrate.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# T3-W9: 姿态合成纯函数 gtest 单测（attitude_utils.h，无 ROS 依赖）
if(CATKIN_ENABLE_TESTING)
  include_directories(${CMAKE_CURRENT_LIST_DIR}/src)
  catkin_add_gtest(test_controller_attitude
    test/test_controller_attitude.cpp)
  target_link_libraries(test_controller_attitude ${catkin_LIBRARIES})

  # T1-D2: odom value-sanity gate gtest (odom_sanity.h, no ROS dependency)
  catkin_add_gtest(test_odom_sanity
    test/test_odom_sanity.cpp)
  target_link_libraries(test_odom_sanity ${catkin_LIBRARIES})
endif()
