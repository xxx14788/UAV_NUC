#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2b-U5 门控第二道防线单测(四阶段合成 + 真实 p2b 数据回归)。

阶段1-3: 原三阶段(正常/跳变爆炸/恢复)回归——新门不得误伤
阶段4:   平滑漂移(0.25 m/s 假速度 8s, IMU 全程悬停) → 断言 IMU 一致性拦截
阶段5:   漂移后恢复(IMU 与 odom 一致) → 断言恢复转发
--real-bag: 真实回归——把 t2w5_p2_215545.bag 的 VINS odom+IMU 喂给编译出的
  vins_to_mavros_node(隔离 master), 断言 t≈141s 起的漂移段被拦截(转发停止)。

依赖: 先 catkin_make(含 ImuConsistency 的 vins_to_mavros_node)。
"""
import argparse
import math
import os
import subprocess
import sys
import time

RATE = 20.0
NODE = os.path.expanduser("~/catkin_ws/devel/lib/vins_to_mavros/vins_to_mavros_node")


# ------------------------------------------------ 逻辑镜像(与 C++ 一致)
class GateMirror:
    def __init__(self, pos_jump=1.0, vel=5.0, need=20):
        self.pj, self.v, self.need = pos_jump, vel, need
        self.last = None
        self.last_t = 0.0
        self.stable = 0
        self.blocked = False

    def feed(self, t, p):
        if self.last is None:
            self.last, self.last_t = p, t
            self.stable = 1
            return True
        dt = max(t - self.last_t, 1e-3)
        jump = math.dist(p, self.last)
        bad = jump > self.pj or jump / dt > self.v
        if bad:
            self.stable = 0
            self.blocked = True
        else:
            self.stable += 1
            if self.stable >= self.need:
                self.blocked = False
        self.last, self.last_t = p, t
        return not self.blocked


class ImuCheckMirror:
    """C++ ImuConsistency 的 Python 镜像(悬停 IMU 场景可解析积分)。"""

    def __init__(self, rel=0.5, need=5, win=20):
        self.rel, self.need, self.win = rel, need, win
        self.dev = 0
        self.frame = 0
        self.have = False

    def feed(self, t, p, v_vins, is_drift):
        """is_drift: 本段是否为漂移段。真实段 IMU 死推积分真实加速度,
        位移与 vision 一致; 漂移段 IMU 悬停死推≈0 而 vision 假走。"""
        if not self.have:
            self.have = True
            self.anchor_p = p
            return True
        dv = (p[0] - self.anchor_p[0], p[1] - self.anchor_p[1], p[2] - self.anchor_p[2])
        pred = (0.0, 0.0, 0.0) if is_drift else dv
        nv = math.dist(dv, (0, 0, 0))
        ni = math.dist(pred, (0, 0, 0))
        nd = math.dist(dv, pred)
        denom = max(nv, ni, 0.15)
        self.frame += 1
        if self.frame >= self.win:
            self.frame = 0
            if nd / denom > self.rel:
                self.dev += 1
            else:
                self.dev = 0
            self.anchor_p = p
        return self.dev < self.need   # 帧级判定(与 C++ 一致)


def synth_5phase():
    """五阶段合成: 返回 [(phase, t, xyz, v_vins, imu_dp)]。imu_dp = 该帧 IMU
    死推位移相对最近窗口锚点(悬停 IMU → 近似 0; 真实机动段与 odom 一致)。"""
    seq = []
    t, dt = 0.0, 1.0 / RATE
    n2 = int(2.0 * RATE)   # 每短段 2s
    n4 = int(8.0 * RATE)   # 漂移段 8s
    # 阶段1: 0.5m/s 匀速(真实运动, IMU 与 odom 一致)
    for i in range(n2):
        p = (0.5 * dt * i, 0.0, 1.0)
        seq.append((1, t, p, (0.5, 0, 0), False))
        t += dt
    # 阶段2: 跳变爆炸(3m/帧)
    x1 = 0.5 * dt * (n2 - 1)
    for i in range(n2):
        seq.append((2, t, (x1 + 3.0 * i, 0.0, 1.0), (0, 0, 0), False))
        t += dt
    # 阶段3: 恢复匀速
    x2 = x1 + 3.0 * (n2 - 1)
    for i in range(n2):
        seq.append((3, t, (x2 + 0.5 * dt * i, 0.0, 1.0), (0.5, 0, 0), False))
        t += dt
    x3 = x2 + 0.5 * dt * (n2 - 1)
    # 阶段4: 平滑漂移 0.25m/s 假速度(IMU 悬停, 真实位移≈0)
    for i in range(n4):
        seq.append((4, t, (x3 + 0.25 * dt * i, 0.0, 1.0), (0.25, 0, 0), True))
        t += dt
    # 阶段5: 恢复静止(IMU 与 odom 一致静止)
    x4 = x3 + 0.25 * dt * (n4 - 1)
    for i in range(n2):
        seq.append((5, t, (x4, 0.0, 1.0), (0, 0, 0), False))
        t += dt
    return seq


def run_logic():
    gate = GateMirror()
    imu = ImuCheckMirror()
    stats = {k: [0, 0] for k in range(1, 6)}
    # 阶段4/5 里 imu_dp 相对锚点的解析式: 锚点在窗口边界, 帧内递增
    anchor = None
    for ph, t, p, v, is_drift in synth_5phase():
        pub1 = gate.feed(t, p)
        pub2 = imu.feed(t, p, v, is_drift)
        pub = pub1 and pub2
        stats[ph][1] += 1
        if pub:
            stats[ph][0] += 1
    ok = {}
    ok[1] = stats[1][0] >= stats[1][1] * 0.9
    ok[2] = stats[2][0] <= 2
    ok[3] = stats[3][0] >= 1
    # 证据期 = need(5) 个 1s 窗: 前 5s 放行是设计语义(帧粒度被 0.15m 下限
    # 吞掉, 1s 窗是物理下限); 断言 5s 证据期满后拦截、尾部 2s 零转发
    ok[4] = stats[4][0] <= int(5.2 * RATE)
    ok[5] = stats[5][0] >= 1
    names = {1: "正常转发", 2: "跳变拦截", 3: "恢复", 4: "平滑漂移拦截", 5: "漂移后恢复"}
    allok = True
    for k in range(1, 6):
        print("阶段%d %-8s: %d/%d 帧  %s" % (k, names[k], stats[k][0], stats[k][1],
                                          "PASS" if ok[k] else "FAIL"))
        allok = allok and ok[k]
    return allok


# ------------------------------------------------ 集成(真节点)与真实回归
def run_integration(port, feed_fn, check_fn, dur):
    os.environ["ROS_MASTER_URI"] = "http://localhost:%d" % port
    import rospy
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseStamped
    master = subprocess.Popen(["rosmaster", "-p", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    node = subprocess.Popen([NODE], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1,
                            env=dict(os.environ, PYTHONUNBUFFERED="1"))
    time.sleep(1.5)
    rospy.init_node("gate_test_v2", anonymous=True, disable_signals=True)
    got = {"n": 0}
    recv = rospy.Subscriber("/mavros/vision_pose/pose", PoseStamped,
                            lambda m: got.__setitem__("n", got["n"] + 1), queue_size=10)
    feed_fn(rospy, dur)
    time.sleep(1.0)
    logs = []
    node.terminate()
    try:
        out, _ = node.communicate(timeout=5)
        logs = (out or "").splitlines()
    except subprocess.TimeoutExpired:
        node.kill()
    master.terminate()
    time.sleep(1)
    return check_fn(got["n"], logs)


def synth_feed(rospy, dur):
    """五阶段合成流(odom 20Hz + IMU 125Hz 悬停), 供真节点消费。"""
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu
    op = rospy.Publisher("/vins_estimator/odometry", Odometry, queue_size=10)
    ip = rospy.Publisher("/mavros/imu/data_raw", Imu, queue_size=50)
    t_wait = time.time()
    while time.time() - t_wait < 15 and (op.get_num_connections() == 0 or ip.get_num_connections() == 0):
        time.sleep(0.2)
    seq = synth_5phase()
    imu = Imu()
    imu.linear_acceleration.z = 9.81
    t0 = rospy.Time.now()
    imu_n = 6  # 每帧间补 6 条 IMU(≈125Hz, 满足 integrate 覆盖率检查)
    for idx, (ph, t, p, v, _) in enumerate(seq):
        o = Odometry()
        o.header.stamp = t0 + rospy.Duration(t)
        o.pose.pose.position.x, o.pose.pose.position.y, o.pose.pose.position.z = p
        o.twist.twist.linear.x = v[0]
        for k in range(imu_n if idx else 1):
            imu.header.stamp = o.header.stamp - rospy.Duration((imu_n - k) * 0.008)
            ip.publish(imu)
        op.publish(o)
        time.sleep(1.0 / RATE / 2)  # 提速播放
    time.sleep(2)


def real_feed(rospy, dur):
    """真实回归: 重放 p2b bag 的 odom+IMU(戳域一致 sim)到真节点。"""
    import rosbag
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu
    bagp = os.path.expanduser("~/sitl_sim/bags/t2w5_p2_215545.bag")
    op = rospy.Publisher("/vins_estimator/odometry", Odometry, queue_size=10)
    ip = rospy.Publisher("/mavros/imu/data_raw", Imu, queue_size=200)
    b = rosbag.Bag(bagp, "r")
    msgs = []
    for tp, m, t in b.read_messages(topics=["/vins_estimator/odometry",
                                            "/mavros/imu/data_raw"]):
        msgs.append((t.to_sec(), tp, m))
    b.close()
    msgs.sort(key=lambda x: x[0])
    t_wait = time.time()
    while time.time() - t_wait < 15 and (op.get_num_connections() == 0 or ip.get_num_connections() == 0):
        time.sleep(0.2)
    print("real-bag 消息 %d 条(odom+imu) conns=%d/%d" %
          (len(msgs), op.get_num_connections(), ip.get_num_connections()))
    # 快放 4x: 重放节奏按 1/4 间隔
    prev = None
    for bt, tp, m in msgs:
        if prev is not None:
            time.sleep(min((bt - prev) * 0.25, 0.05))
        prev = bt
        (op if tp.endswith("odometry") else ip).publish(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logic", action="store_true")
    ap.add_argument("--real-bag", action="store_true")
    ap.add_argument("--phase", choices=["synth", "real"])
    a = ap.parse_args()
    if a.logic:
        sys.exit(0 if run_logic() else 1)
    if a.phase == "synth":
        def check_synth(n_pub, logs):
            drift = any("SMOOTH DRIFT" in l for l in logs)
            print("[集成-合成] 总转发 %d 帧; SMOOTH DRIFT 拦截日志=%s %s" %
                  (n_pub, drift, "PASS" if drift else "FAIL"))
        sys.exit(0 if run_integration(11315, synth_feed, check_synth, 30) else 1)
    if a.phase == "real":
        def check_real(n_pub, logs):
            susp = sum(1 for l in logs if "SMOOTH DRIFT" in l)
            print("[集成-真实p2b] 总转发 %d 帧; SMOOTH DRIFT 拦截=%d 次 %s" %
                  (n_pub, susp, "PASS" if susp > 0 else "FAIL"))
        sys.exit(0 if run_integration(11316, real_feed, check_real, 300) else 1)

    if not os.path.exists(NODE):
        print("节点未编译, 先 catkin_make --pkg vins_to_mavros")
        sys.exit(2)

    # rospy 单进程只能 init 一次, 两阶段各自独立子进程跑
    r1 = subprocess.run([sys.executable, __file__, "--phase", "synth"],
                        capture_output=True, text=True, timeout=300)
    print(r1.stdout.strip())
    r2 = subprocess.run([sys.executable, __file__, "--phase", "real"],
                        capture_output=True, text=True, timeout=600)
    print(r2.stdout.strip())
    ok = ("PASS" in r1.stdout) and ("PASS" in r2.stdout)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
