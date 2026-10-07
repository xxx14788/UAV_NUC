#!/usr/bin/env python3
"""t1_inject_odom.py — 毒 odom 注入器 v1.0 (T1 v11.25 阶段 4a 演练工具;预注册=drill_prereg_v1)

模式:
  --jump X   单帧 z+X m 跳变注入(毒 odom 跳变案 D2)后交还原发布器(停止竞争)
  --drift V  以 V m/s 沿 x 持续慢漂接管发布(连续错误流案 D5),--dur 秒后停止
原理=竞争发布器:先订阅原流承接最新位姿/-twist;jump=一次性发 X 帧带偏位姿;
drift=接管期间每帧位置按 V*dt 递增(帧率≈原流)。
留痕=inject_<mode>.json(模式/起止/帧数/参数)。"""
import sys, json, argparse, time, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jump", type=float)
    ap.add_argument("--drift", type=float)
    ap.add_argument("--dur", type=float, default=30.0)
    ap.add_argument("--out", default=os.getcwd())
    a = ap.parse_args()
    if not a.jump and not a.drift:
        ap.error("需要 --jump X 或 --drift V")
    import rospy
    from nav_msgs.msg import Odometry
    mode = "jump" if a.jump else "drift"
    rospy.init_node("t1_inject_odom", anonymous=True, disable_signals=True)
    latest = {"msg": None, "t": 0.0}
    sub = rospy.Subscriber("/vins_estimator/odometry", Odometry,
                           lambda m: latest.__setitem__("msg", m), queue_size=1)
    # 等待承接原流一帧
    t0 = time.time()
    while latest["msg"] is None and time.time() - t0 < 10 and not rospy.is_shutdown():
        time.sleep(0.05)
    if latest["msg"] is None:
        print("[inject] 未承接原流(10s 无消息)——VINS 可能未发布", file=sys.stderr)
        return 3
    pub = rospy.Publisher("/vins_estimator/odometry", Odometry, queue_size=2)
    time.sleep(0.5)  # publisher 建连
    n_frames = 0
    t_start = rospy.get_time()
    rec = {"mode": mode, "param": a.jump if a.jump else a.drift,
           "t_start": t_start, "dur": 0.0, "frames": 0}
    if mode == "jump":
        m = latest["msg"]
        m.pose.pose.position.z += a.jump
        # twist 归零防速度尖峰耦合(单帧位姿毒=纯跳变面)
        m.twist.twist.linear.x = m.twist.twist.linear.y = m.twist.twist.linear.z = 0.0
        for _ in range(5):  # 短突发确保消费者吃到
            pub.publish(m)
            rospy.sleep(0.02)
        n_frames = 5
        rec["dur"] = 0.1
    else:
        base = latest["msg"]
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.get_time() - t_start < a.dur:
            m = Odometry()
            m.header.stamp = rospy.Time.now()
            m.header.frame_id = base.header.frame_id
            m.child_frame_id = base.child_frame_id
            dt = rospy.get_time() - t_start
            m.pose = base.pose
            m.pose.pose.position.x = base.pose.pose.position.x + a.drift * dt
            m.twist = base.twist
            m.twist.twist.linear.x = a.drift
            pub.publish(m)
            n_frames += 1
            rate.sleep()
        rec["dur"] = round(rospy.get_time() - t_start, 2)
    rec["frames"] = n_frames
    outp = os.path.join(a.out, "inject_%s.json" % mode)
    json.dump(rec, open(outp, "w"), indent=1)
    print("[inject] %s 完成 frames=%d -> %s" % (mode, n_frames, outp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
