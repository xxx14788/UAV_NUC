#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z1.3/C07-E4a bag 验收轨:毒 odom 流回灌 v2 门(设计稿等价实现),门全开。

经真实 ROS 传输回灌(rosbag play --clock + 私有 master + use_sim_time),
harness 订阅 /vins_estimator/imu_propagate(223Hz,px4ctrl SITL 直供流),
逐帧跑 odom_sanity_v2 语义(层序 STAMP-BACK→STAMP-AGE→ACC→JUMP→R→VEL),
统计:拒帧分层计数/毒帧漏入(ACCEPT 且 |v|>5 或 |p|>1e3)/首拒时刻/健康基线零误伤。

用法: t3_gate_sim.py <bag> [port=11315]
输出: stdout 汇总 + /tmp/gate_sim_<bagname>.json
(自跑 rosbag play 与 roscore;结束后清理;单机一路纪律已按 pgrep 前置)
"""
import json
import math
import os
import subprocess
import sys
import time

import rospy
from nav_msgs.msg import Odometry

CFG = dict(max_vel=5.0, max_acc=10.0, max_jump=0.6, reboot_dt=1.0,
           max_r=0.08, stamp_age_max=0.2)


class Gate:
    def __init__(self):
        self.has_ref = False
        self.last_p = None
        self.last_v = None
        self.last_t = 0.0
        self.last_stamp = 0.0
        self.counts = {}
        self.n = 0
        self.first_reject_t = None
        self.leak_v = 0      # ACCEPT 且 |v|>max_vel(毒帧漏入)
        self.leak_far = 0    # ACCEPT 且 |p|>1e3
        self.t0_bag = None
        self.pipe_off = None   # 回放管线延迟(首 50 帧 t_now−stamp 中位;
        #  实机不存在此偏移——回放域绝对戳龄须扣除,否则 AGE 层全是伪影)
        self.age_samples = []

    def feed(self, stamp, t_now, p, v):
        self.n += 1
        if self.t0_bag is None:
            self.t0_bag = stamp
        raw_age = t_now - stamp
        if self.pipe_off is None:
            self.age_samples.append(raw_age)
            if len(self.age_samples) >= 50:
                self.pipe_off = sorted(self.age_samples)[len(self.age_samples) // 2]
            return "WARMUP"
        age = raw_age - self.pipe_off
        def rej(k):
            self.counts[k] = self.counts.get(k, 0) + 1
            if self.first_reject_t is None:
                self.first_reject_t = round(stamp - self.t0_bag, 1)
            return k
        if not all(math.isfinite(x) for x in p + v):
            return rej("NAN")
        if self.has_ref:
            if stamp < self.last_stamp - 1e-9:
                return rej("STAMP_BACK")
            if age > CFG["stamp_age_max"]:
                return rej("STAMP_AGE")
        else:
            self.has_ref = True
            self.last_p, self.last_v = p, v
            self.last_t, self.last_stamp = t_now, stamp
            return "ACCEPT"
        dt = t_now - self.last_t
        reboot_gap = dt >= CFG["reboot_dt"]
        if not reboot_gap:
            dv = math.sqrt(sum((v[k] - self.last_v[k]) ** 2 for k in range(3)))
            if dv / dt > CFG["max_acc"]:
                return rej("ACC")
            dp = math.dist(p, self.last_p)
            if dp > CFG["max_jump"]:
                return rej("JUMP")
            pred = tuple(self.last_p[k] + 0.5 * (self.last_v[k] + v[k]) * dt
                         for k in range(3))
            if math.dist(p, pred) > CFG["max_r"]:
                return rej("R")
        vmag = math.sqrt(sum(x * x for x in v))
        if vmag > CFG["max_vel"]:
            return rej("VEL")
        # ACCEPT:漏入检查
        if vmag > CFG["max_vel"]:
            self.leak_v += 1
        if max(abs(x) for x in p) > 1e3:
            self.leak_far += 1
        self.last_p, self.last_v = p, v
        self.last_t, self.last_stamp = t_now, stamp
        return "ACCEPT"


def main():
    bag = os.path.abspath(sys.argv[1])
    port = sys.argv[2] if len(sys.argv) > 2 else "11315"
    name = os.path.basename(os.path.dirname(bag)) if \
        os.path.basename(bag) == "flight.bag" else os.path.basename(bag)[:-4]
    uri = f"http://localhost:{port}"
    env = dict(os.environ, ROS_MASTER_URI=uri)
    subprocess.Popen(["rosmaster", "-p", port], env=env,
                     stdout=open("/tmp/gate_sim_master.log", "w"), stderr=subprocess.STDOUT,
                     start_new_session=True)
    time.sleep(2)
    play = subprocess.Popen(["rosbag", "play", bag, "--clock"], env=env,
                            stdout=open(f"/tmp/gate_sim_play_{name}.log", "w"),
                            stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(1)
    os.environ["ROS_MASTER_URI"] = uri
    rospy.init_node("t3_gate_sim", anonymous=True)
    rospy.set_param("/use_sim_time", True)
    gate = Gate()
    got = {"n": 0}

    def cb(msg):
        p = msg.pose.pose.position
        v = msg.twist.twist.linear
        stamp = msg.header.stamp.to_sec()
        t_now = rospy.get_rostime().to_sec()
        gate.feed(stamp, t_now, (p.x, p.y, p.z), (v.x, v.y, v.z))
        got["n"] += 1

    rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, cb, queue_size=100)
    t0 = time.time()
    while play.poll() is None and time.time() - t0 < 900:
        time.sleep(2)
    time.sleep(3)
    play.terminate()
    subprocess.run(["pkill", "-f", f"rosmaster -p {port}"], check=False)
    accepted = gate.n - sum(v for k, v in gate.counts.items()) - 50  # 50=warmup 帧
    rep = {"bag": name, "frames": gate.n, "accepted": accepted,
           "rejects_by_layer": gate.counts,
           "pipe_offset_s": round(gate.pipe_off, 4) if gate.pipe_off is not None else None,
           "first_reject_bag_t": gate.first_reject_t,
           "leak_vel": gate.leak_v, "leak_far": gate.leak_far,
           "cfg": CFG}
    with open(f"/tmp/gate_sim_{name}.json", "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
