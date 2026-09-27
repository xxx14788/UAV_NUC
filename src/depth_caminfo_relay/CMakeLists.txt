cmake_minimum_required(VERSION 3.0.2)
project(depth_caminfo_relay)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  sensor_msgs
  message_filters
)

catkin_package()

include_directories(
  ${catkin_INCLUDE_DIRS}
)

add_executable(depth_caminfo_relay_node src/depth_caminfo_relay_node.cpp)
target_link_libraries(depth_caminfo_relay_node ${catkin_LIBRARIES})
