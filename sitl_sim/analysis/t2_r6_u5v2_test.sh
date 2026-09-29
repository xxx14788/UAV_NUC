#!/usr/bin/env bash
# T2-R6 U5v2 三工况验收: ground/hover 零误报 + p2b 漂移拦截
set -u
export ROS_DISTRO=${ROS_DISTRO:-noetic}
export ROS_MASTER_URI=http://localhost:11401  # T2-R6修复:无条件私有master(条件导出在继承环境时泄漏到默认11311——04:33 T3中毒轮事故根源之一)
export ROS_VERSION=${ROS_VERSION:-1}
export ROS_PACKAGE_PATH=${ROS_PACKAGE_PATH:-}
source /opt/ros/noetic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
OUT=$HOME/sitl_sim/t2_results/R6_u5v2
mkdir -p "$OUT"

for BAG in "$@"; do
  NAME=$(basename "$BAG" .bag)
  roscore -p 11401 >/dev/null 2>&1 &
  COREPID=$!
  sleep 3
  rosparam set use_sim_time true
  rosrun vins_to_mavros vins_to_mavros_node _imu_check_enabled:=true \
      > "$OUT/${NAME}.log" 2>&1 &
  NODEPID=$!
  sleep 3
  rosbag play "$BAG" --clock /vins_estimator/odometry:=/vins_estimator/odometry \
      > "$OUT/${NAME}.play" 2>&1 &
  PLAYPID=$!
  wait $PLAYPID
  sleep 3
  kill -INT $NODEPID 2>/dev/null; sleep 1; kill -KILL $NODEPID 2>/dev/null
  kill $COREPID 2>/dev/null
  sleep 2
  C2=$(pgrep -f 'roscore -p 11401') && kill $C2 2>/dev/null
  sleep 1
  echo "== $NAME"
  grep -c 'SMOOTH DRIFT intercepted' "$OUT/${NAME}.log" | sed 's/^/  拦截次数: /'
  grep -m2 'SMOOTH DRIFT intercepted' "$OUT/${NAME}.log" | head -2
  grep -c 'window dev' "$OUT/${NAME}.log" | sed 's/^/  违例窗: /'
  grep -m1 'bias updated' "$OUT/${NAME}.log" | sed 's/^/  /'
  grep -c 'imu-check: rel_dev' "$OUT/${NAME}.log" | sed 's/^/  v2配置行: /'
done
echo ALLDONE
