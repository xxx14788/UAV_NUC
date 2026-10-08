cmake_minimum_required(VERSION 2.8.3)
project(vins)

set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS "-std=c++11")
#-DEIGEN_USE_MKL_ALL")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall -g")

find_package(catkin REQUIRED COMPONENTS
    roscpp
    std_msgs
    geometry_msgs
    nav_msgs
    tf
    cv_bridge
    camera_models
    image_transport)

find_package(OpenCV REQUIRED)

# message(WARNING "OpenCV_VERSION: ${OpenCV_VERSION}")

find_package(Ceres REQUIRED)

include_directories(${catkin_INCLUDE_DIRS} ${CERES_INCLUDE_DIRS})

set(CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)
find_package(Eigen3)
include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
)

catkin_package()

add_library(vins_lib
    src/estimator/parameters.cpp
    src/estimator/estimator.cpp
    src/estimator/feature_manager.cpp
    src/factor/pose_local_parameterization.cpp
    src/factor/projectionTwoFrameOneCamFactor.cpp
    src/factor/projectionTwoFrameTwoCamFactor.cpp
    src/factor/projectionOneFrameTwoCamFactor.cpp
    src/factor/marginalization_factor.cpp
    src/utility/utility.cpp
    src/utility/visualization.cpp
    src/utility/CameraPoseVisualization.cpp
    src/initial/solve_5pts.cpp
    src/initial/initial_aligment.cpp
    src/initial/initial_sfm.cpp
    src/initial/initial_ex_rotation.cpp
    src/featureTracker/feature_tracker.cpp)
target_link_libraries(vins_lib ${catkin_LIBRARIES} ${OpenCV_LIBS} ${CERES_LIBRARIES})


add_executable(vins_node src/rosNodeTest.cpp)

if(CATKIN_ENABLE_TESTING)
  catkin_add_gtest(test_reanchor_smoother test/test_reanchor_smoother.cpp)
  target_include_directories(test_reanchor_smoother PRIVATE src)
  catkin_add_gtest(test_t2_stream_guard test/test_t2_stream_guard.cpp)
  catkin_add_gtest(test_p3_notify test/test_p3_notify.cpp)
  target_include_directories(test_t2_stream_guard PRIVATE src)
  catkin_add_gtest(test_propagate_guard test/test_propagate_guard.cpp)
  target_include_directories(test_propagate_guard PRIVATE src)
  catkin_add_gtest(test_t2_depth_gate test/test_t2_depth_gate.cpp)
  catkin_add_gtest(test_t2_input_quality_gate test/test_t2_input_quality_gate.cpp)
  target_include_directories(test_t2_input_quality_gate PRIVATE src)
  target_link_libraries(test_t2_input_quality_gate vins_lib)
  target_include_directories(test_t2_depth_gate PRIVATE src)
  target_link_libraries(test_t2_depth_gate vins_lib)
  catkin_add_gtest(test_t2_min_disparity test/test_t2_min_disparity.cpp)
  target_include_directories(test_t2_min_disparity PRIVATE src)
  target_link_libraries(test_t2_min_disparity vins_lib)
  catkin_add_gtest(test_t2_imu_factor test/test_t2_imu_factor.cpp)
  target_include_directories(test_t2_imu_factor PRIVATE src)
  target_link_libraries(test_t2_imu_factor vins_lib)
  catkin_add_gtest(test_t2_nan_defense test/test_t2_nan_defense.cpp)
  target_include_directories(test_t2_nan_defense PRIVATE src)
  catkin_add_gtest(test_a1_reboot_fix test/test_a1_reboot_fix.cpp)
  target_include_directories(test_a1_reboot_fix PRIVATE src)
  catkin_add_gtest(test_t2_init_shift test/test_t2_init_shift.cpp)
  target_include_directories(test_t2_init_shift PRIVATE src)
  target_link_libraries(test_t2_init_shift vins_lib)
  catkin_add_gtest(test_t2_route_fix test/test_t2_route_fix.cpp)
  target_include_directories(test_t2_route_fix PRIVATE src)
  target_link_libraries(test_t2_route_fix vins_lib)
  catkin_add_gtest(test_t2_zeta_fix test/test_t2_zeta_fix.cpp)
  target_include_directories(test_t2_zeta_fix PRIVATE src)
  target_link_libraries(test_t2_zeta_fix vins_lib)
endif()
target_link_libraries(vins_node vins_lib) 

add_executable(kitti_odom_test src/KITTIOdomTest.cpp)
target_link_libraries(kitti_odom_test vins_lib) 

add_executable(kitti_gps_test src/KITTIGPSTest.cpp)
target_link_libraries(kitti_gps_test vins_lib) 

