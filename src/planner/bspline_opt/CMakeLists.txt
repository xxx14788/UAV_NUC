cmake_minimum_required(VERSION 2.8.3)
project(bspline_opt)

set(CMAKE_BUILD_TYPE "Release")
ADD_COMPILE_OPTIONS(-std=c++11 )
ADD_COMPILE_OPTIONS(-std=c++14 )
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall -g")

find_package(Eigen3 REQUIRED)
find_package(PCL 1.7 REQUIRED)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  visualization_msgs
  plan_env
  cv_bridge
  traj_utils
  path_searching
)

catkin_package(
 INCLUDE_DIRS include
 LIBRARIES bspline_opt
 CATKIN_DEPENDS plan_env 
#  DEPENDS system_lib
)

include_directories( 
    SYSTEM 
    include 
    ${catkin_INCLUDE_DIRS}
    ${Eigen3_INCLUDE_DIRS} 
    ${PCL_INCLUDE_DIRS}
)

add_library( bspline_opt 
    src/uniform_bspline.cpp 
    src/bspline_optimizer.cpp 
    src/gradient_descent_optimizer.cpp
    )
target_link_libraries( bspline_opt
    ${catkin_LIBRARIES} 
    )  

# 2026-11-12 质量修复 C：P2/P5 不变量自检（catkin build 后可直接运行：
#   devel/.private/bspline_opt/lib/bspline_opt/bspline_selfcheck）
enable_testing()
add_executable(bspline_selfcheck test/bspline_selfcheck.cpp)
target_link_libraries(bspline_selfcheck bspline_opt )
add_test(NAME bspline_selfcheck COMMAND bspline_selfcheck)
