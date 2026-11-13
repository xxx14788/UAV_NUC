#!/usr/bin/env python3
"""起飞前姿态一致性闸门（VINS vs PX4）。

原理：静止时 VINS 与 PX4 对同一机体的姿态必须一致（两者用同一个 IMU，
但 VINS 的视觉-惯性初始化会引入每次不同的 roll/pitch 偏差）。实测：
  2026-11-04 22:10  VINS pitch -0.44 / PX4 -0.48  -> 一致，0.1m 级漂移
  2026-11-04 22:30  VINS pitch -0.43 / PX4 -0.36  -> 一致
  2026-11-05 00:38  VINS pitch +2.00 / PX4 -0.20  -> 偏差 2.2deg，1.1m 漂移
偏差 2deg 会产生 9.8*sin(2deg)=0.34 m/s^2 横向加速度，位置环只能压到
0.2m/s 的稳态漂移速度。

用法：rosrun(或直接 python3) 运行 3 秒，看 PASS/FAIL。FAIL 就重启 VINS 重新初始化。
"""
import sys
import numpy as np
import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu

OD = []
PX = []


def cb_od(m):
    q = m.pose.pose.orientation
    OD.append((q.x, q.y, q.z, q.w))


def cb_px(m):
    q = m.orientation
    PX.append((q.x, q.y, q.z, q.w))


def R(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def gb(q):
    return R(q).T @ np.array([0, 0, -1.0])


def main():
    rospy.init_node('att_gate', anonymous=True)
    rospy.Subscriber('/vins_estimator/odometry', Odometry, cb_od, queue_size=5)
    rospy.Subscriber('/mavros/imu/data', Imu, cb_px, queue_size=20)
    t0 = rospy.Time.now()
    while (rospy.Time.now() - t0).to_sec() < 3.0 and not rospy.is_shutdown():
        rospy.sleep(0.05)
    if len(OD) < 10 or len(PX) < 10:
        print('ATT_GATE: NO DATA (vins=%d px4=%d) -> FAIL' % (len(OD), len(PX)))
        return 2
    gv = np.mean([gb(q) for q in OD[-30:]], axis=0)
    gp = np.mean([gb(q) for q in PX[-200:]], axis=0)
    gv /= np.linalg.norm(gv)
    gp /= np.linalg.norm(gp)
    err = np.degrees(np.arccos(np.clip(gv @ gp, -1, 1)))
    acc = 9.81 * np.sin(np.radians(err))
    print('ATT_GATE: VINS g_b=(%+.3f,%+.3f) PX4 g_b=(%+.3f,%+.3f)' % (gv[0], gv[1], gp[0], gp[1]))
    print('ATT_GATE: tilt mismatch = %.2f deg  -> lateral bias %.2f m/s2 (drift %.1f m in 3s)'
          % (err, acc, 0.5 * acc * 9.0))
    # 2026-11-13 收紧（用户令）：PASS<0.3 / WARN 0.3-0.5 / FAIL>=0.5。
    # 0.5deg 对应 0.086 m/s2 侧向偏置（3s 漂 0.39 m），再宽就不能接受。
    if err < 0.3:
        print('ATT_GATE: PASS')
        return 0
    if err < 0.5:
        print('ATT_GATE: WARN  (0.3-0.5deg) — 可以飞，悬停预计有 3-6cm 偏移')
        return 1
    print('ATT_GATE: FAIL  (>=0.5deg) — 请重启 VINS 重新初始化后再飞')
    return 1


if __name__ == '__main__':
    sys.exit(main())
