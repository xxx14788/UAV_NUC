#!/bin/bash
# 盯盘 v3（F-5, 2026-10-22 判读v5）——在 v1（VINS Bas/cost 尾读）之上增实时显示：
#   ①指令/实际倾角（deg）②odom staleness（ms）③门拒收计数 ④REINIT_RESET/重初始化事件
# 用法：bash ~/realflight_monitor_v3.sh   （Ctrl+C 退）
set +u; source /opt/ros/noetic/setup.bash; source ~/catkin_ws/devel/setup.bash 2>/dev/null; set -u
echo "=== 盯盘 v3（倾角/staleness/门拒收/重初始化）==="
python3 <<'PYEOF'
import math, time, threading
import rospy
from quadrotor_msgs.msg import Px4ctrlDebug
from rosgraph_msgs.msg import Log
from sensor_msgs.msg import Imu
st = {"tilt_d": None, "stale": None, "rej": 0, "ev": [], "tilt_a": None}
lock = threading.Lock()
def tilt_of(x, y, z, w):
    return math.degrees(math.acos(max(-1.0, min(1.0, 1.0 - 2.0*(x*x + y*y)))))
def cb(m):
    with lock:
        st["tilt_d"] = tilt_of(m.des_q_x, m.des_q_y, m.des_q_z, m.des_q_w)
        st["stale"] = m.odom_staleness_ms
def cblog(m):
    s = m.msg or ""
    with lock:
        if "REJECTED" in s: st["rej"] += 1
        for k in ("[REINIT_RESET]", "failure detection", "big IMU", "relocked", "HAFIX"):
            if k in s:
                st["ev"].append("%.1f %s" % (rospy.get_time() % 1000, s[:70])); st["ev"] = st["ev"][-3:]
def cbimu(m):
    q = m.orientation
    with lock: st["tilt_a"] = tilt_of(q.x, q.y, q.z, q.w)
rospy.init_node("monitor_v3", anonymous=True, disable_signals=True)
rospy.Subscriber("/debugPx4ctrl", Px4ctrlDebug, cb, queue_size=5)
rospy.Subscriber("/rosout", Log, cblog, queue_size=50)
rospy.Subscriber("/mavros/imu/data", Imu, cbimu, queue_size=5)
t0 = time.monotonic()
while not rospy.is_shutdown():
    with lock:
        print("\r t=%4.0fs 指令倾角=%5.1f° 实际=%5.1f° | stale=%6.0fms | 门拒收=%d | %s   " %
              (time.monotonic()-t0, st["tilt_d"] or -1, st["tilt_a"] or -1, st["stale"] or -1,
               st["rej"], " || ".join(st["ev"][-1:]) or "—"), end="", flush=True)
    time.sleep(0.5)
PYEOF
