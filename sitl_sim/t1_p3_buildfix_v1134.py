#!/usr/bin/env python3
# T1 v11.34 单元0-③ — P3 build 失败修复（三处, 最小侵入+按仓库既有惯例）
# 1) vins CMakeLists: 主 include 组补 src 跃点(estimator.cpp 的 "estimator/p3_notify_codec.h" 解析)
# 2) vins CMakeLists: test_p3_notify 补配对 target_include_directories(... PRIVATE src)(全部既有 test 同款)
# 3) px4ctrl PX4CtrlFSM.h: 删 P3 留在原 public 段前的多余 private:(把 traj_start_trigger_pub/State_t/构造函数埋进 private 的根因)
import sys

# --- 1+2: vins CMakeLists ---
p = "/home/ghj/catkin_ws/src/VINS-Fusion/vins_estimator/CMakeLists.txt"
s = open(p).read()
if "include_directories(src)" in s or "${CERES_INCLUDE_DIRS} src" in s:
    print("vins CMakeLists: src already in include dirs")
else:
    old = """include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
)"""
    new = """include_directories(
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
  src
)"""
    assert s.count(old) == 1, f"main include block match={s.count(old)}"
    s = s.replace(old, new)
    print("vins CMakeLists: main include group +src ok")

old2 = "  catkin_add_gtest(test_p3_notify test/test_p3_notify.cpp)\n"
if "target_include_directories(test_p3_notify PRIVATE src)" in s:
    print("vins CMakeLists: test_p3_notify tid already present")
else:
    assert s.count(old2) == 1, f"gtest line match={s.count(old2)}"
    s = s.replace(old2, old2 + "  target_include_directories(test_p3_notify PRIVATE src)\n")
    print("vins CMakeLists: test_p3_notify +target_include_directories ok")
open(p, "w").write(s)

# --- 3: px4ctrl header ---
p2 = "/home/ghj/catkin_ws/src/px4ctrl/src/PX4CtrlFSM.h"
s2 = open(p2).read()
old3 = "public:\n\tvoid p3NotifyFeed(const std_msgs::UInt32::ConstPtr &msg);\nprivate:\n\tint ha_stage = 0;"
new3 = "\tint ha_stage = 0;\npublic:\n\tvoid p3NotifyFeed(const std_msgs::UInt32::ConstPtr &msg);"
if old3 in s2:
    s2 = s2.replace(old3, new3)
    open(p2, "w").write(s2)
    print("PX4CtrlFSM.h: stray private: removed (ha_stage stays in new public section, original public members restored)")
elif new3 in s2:
    print("PX4CtrlFSM.h: already fixed")
else:
    print("PX4CtrlFSM.h: PATTERN NOT FOUND — manual review needed")
    sys.exit(1)
print("ALL FIXES APPLIED")
