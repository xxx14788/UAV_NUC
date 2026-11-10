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
  catkin_add_gtest(test_fsm_decision
    test/test_fsm_decision.cpp)
  target_link_libraries(test_fsm_decision ${catkin_LIBRARIES})

  # T3-Z1.2: odom sanity gate v2 design-stage gtest (odom_sanity_v2.h, UNWIRED;
  # injection matrix per C07-E3 + direction-6 augmented cells)
  catkin_add_gtest(test_odom_sanity_v2
    test/test_odom_sanity_v2.cpp)
  target_link_libraries(test_odom_sanity_v2 ${catkin_LIBRARIES})

  # T1-P2 (v11.4 unit 3): cmd-response divergence gate gtest
  # (cmdresp_gate.h + fsm_decision RJ_CMDRESP wiring, no ROS dependency)
  catkin_add_gtest(test_cmdresp_gate
    test/test_cmdresp_gate.cpp)
  target_link_libraries(test_cmdresp_gate ${catkin_LIBRARIES})

  # W4/W5/W6 (2026-11-06): 控制核心 v2 纯函数 gtest（ctrl_core.h，无 ROS 依赖）
  catkin_add_gtest(test_ctrl_core
    test/test_ctrl_core.cpp)
  target_link_libraries(test_ctrl_core ${catkin_LIBRARIES})
  # 2026-11-07 起飞地面锁定（GROUND_LOCK，判读 v1）：离地判定纯函数 gtest
  catkin_add_gtest(test_ground_lock
    test/test_ground_lock.cpp)
  target_link_libraries(test_ground_lock ${catkin_LIBRARIES})

  # F-1 (2026-10-22 判读v5): REINIT_RESET 毒化拒收 gtest（input.cpp 数据面语义）
  catkin_add_gtest(test_reinit_reset
    test/test_reinit_reset.cpp src/input.cpp)
  target_link_libraries(test_reinit_reset ${catkin_LIBRARIES})

  # 2026-11-10（整改 F-01）: RC "四杆居中"判据回归锚。
  # 旧实现四次都判 ch[0]，pitch/throttle/yaw 漏检；本测三个用例在旧码上必红。
  catkin_add_gtest(test_rc_centered
    test/test_rc_centered.cpp src/input.cpp)
  target_link_libraries(test_rc_centered ${catkin_LIBRARIES})
endif()
