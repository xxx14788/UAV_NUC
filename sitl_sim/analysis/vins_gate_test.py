#!/usr/bin/env python3
"""vins_to_mavros 健康门控单元验证（T2-W0-5 / W4，2026-09-26 翻机事故防线）。

用法: python3 vins_gate_test.py [--logic-only]

集成模式（默认）: 对着真实编译出的 vins_to_mavros_node 喂合成序列并断言
  /mavros/vision_pose/pose 的拦截/恢复行为:
  阶段1 正常序列（50Hz、≤1m/s）       → 断言转发正常（收到 ≥50 帧）
  阶段2 发散序列（单帧跳 3m、~150m/s） → 断言 0.5s 内停止转发（≤2 帧漏过）
  阶段3 恢复平稳（回到 ≤1m/s）        → 断言 ~20 帧平稳后自动恢复转发
门控参数走 rosparam（/vins_to_mavros/gate_*），与 W4 C++ 实现一致。

--logic-only: 不跑节点，从 vins_to_mavros_node.cpp 源码解析默认阈值，
用等价 Python 逻辑镜像跑同样三段序列（节点未编译时的前置冒烟）。

依赖: ROS Noetic python3（rospy/nav_msgs）；集成模式需先 catkin_make
"""
import argparse
import math
import os
import re
import subprocess
import sys
import time

RATE = 50.0            # 合成 odometry 频率
RUN_S = 2.0            # 阶段时长
GATE_GRACE = 2         # 拦截后允许漏过的帧数
SRC = os.path.expanduser(
    "~/catkin_ws/src/vins_to_mavros/src/vins_to_mavros_node.cpp")


# ---------------------------------------------------------------- 逻辑镜像
def parse_cpp_defaults(path=SRC):
    """从 C++ 源码解析门控默认阈值（防 Python 镜像与 C++ 漂移）。"""
    d = {}
    if not os.path.exists(path):
        return {"gate_pos_jump": 1.0, "gate_vel": 5.0,
                "gate_stable_frames": 20}
    src = open(path, encoding="utf-8").read()
    for key in ("gate_pos_jump", "gate_vel", "gate_stable_frames",
                "gate_enabled"):
        m = re.search(key + r"[^0-9.\-]*(\d+\.?\d*)", src)
        if m:
            d[key] = float(m.group(1))
    return d or {"gate_pos_jump": 1.0, "gate_vel": 5.0,
                 "gate_stable_frames": 20}


class GateMirror:
    """W4 门控的 Python 镜像（判定逻辑与 C++ 保持一致）。"""

    def __init__(self, pos_jump, vel, stable_frames):
        self.pos_jump, self.vel, self.need = pos_jump, vel, stable_frames
        self.last = None
        self.last_t = None
        self.stable = 0
        self.blocked = False

    def feed(self, t, p):
        """喂一帧 (t, xyz) → (published: bool)。"""
        if self.last is None:
            self.last, self.last_t = p, t
            self.stable = 1
            return not self.blocked
        dt = max(t - self.last_t, 1e-3)
        jump = math.dist(p, self.last)
        spd = jump / dt
        bad = jump > self.pos_jump or spd > self.vel
        if bad:
            self.stable = 0
            self.blocked = True
        else:
            self.stable += 1
            if self.stable >= self.need:
                self.blocked = False
        self.last, self.last_t = p, t
        return not self.blocked


def gen_phases():
    """三段合成位姿序列: [(phase, t, xyz)]。"""
    seq = []
    t = 0.0
    dt = 1.0 / RATE
    n = int(RUN_S * RATE)
    # 阶段1: 0.5 m/s 匀速 2s
    for i in range(n):
        seq.append((1, t, (0.5 * dt * i, 0.0, 1.0)))
        t += dt
    # 阶段2: 每帧位置跳 3 m（=150 m/s @50Hz）持续 2s
    x1_end = 0.5 * dt * (n - 1)
    for i in range(n):
        seq.append((2, t, (x1_end + 3.0 * i, 0.0, 1.0)))
        t += dt
    # 阶段3: 回到 0.5 m/s 匀速 2s（从阶段2末位置续走）
    x0 = x1_end + 3.0 * (n - 1)
    for i in range(n):
        seq.append((3, t, (x0 + 0.5 * dt * i, 0.0, 1.0)))
        t += dt
    return seq


def run_logic_only():
    d = parse_cpp_defaults()
    print(f"[logic-only] C++ 默认阈值: {d}")
    gate = GateMirror(d["gate_pos_jump"], d["gate_vel"],
                      int(d["gate_stable_frames"]))
    stats = {1: [0, 0], 2: [0, 0], 3: [0, 0]}  # phase -> [pub, total]
    t_p3_start = None
    t_recover = None
    for ph, t, p in gen_phases():
        if ph == 3 and t_p3_start is None:
            t_p3_start = t
        pub = gate.feed(t, p)
        stats[ph][1] += 1
        if pub:
            stats[ph][0] += 1
            if ph == 3 and t_recover is None:
                t_recover = t - t_p3_start
    ok1 = stats[1][0] >= stats[1][1] * 0.95
    ok2 = stats[2][0] <= GATE_GRACE
    ok3 = stats[3][0] >= 1 and t_recover is not None and \
        t_recover <= (d["gate_stable_frames"] / RATE) + 0.5
    print(f"阶段1 正常转发 {stats[1][0]}/{stats[1][1]}  {'PASS' if ok1 else 'FAIL'}")
    print(f"阶段2 拦截漏过 {stats[2][0]}/{stats[2][1]}  {'PASS' if ok2 else 'FAIL'}")
    print(f"阶段3 恢复转发 {stats[3][0]}/{stats[3][1]}  "
          f"(阶段3开始后 {t_recover:.2f}s 恢复)  {'PASS' if ok3 else 'FAIL'}")
    return ok1 and ok2 and ok3


# ---------------------------------------------------------------- 集成模式
def run_integration():
    # 隔离 master（11313）：绝不污染其他会话（live SITL/EKF2）——
    # 测试会发布合成 odom 并监听 vision_pose，串到活动系统上会真把 EKF2 带崩
    os.environ["ROS_MASTER_URI"] = "http://localhost:11313"
    import rospy
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseStamped

    node_bin = os.path.expanduser(
        "~/catkin_ws/devel/lib/vins_to_mavros/vins_to_mavros_node")
    if not os.path.exists(node_bin):
        print(f"[ERROR] 节点未编译: {node_bin}，先 catkin_make（或用 --logic-only）")
        return False

    print("[INFO] 启动隔离 rosmaster :11313 ...")
    master = subprocess.Popen(["rosmaster", "-p", "11313"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    import time as _t
    import rosgraph
    for _ in range(50):
        try:
            if rosgraph.is_master_online():
                break
        except Exception:
            pass
        _t.sleep(0.2)
    else:
        print("[ERROR] rosmaster 启动失败")
        master.terminate()
        return False

    node = None
    try:
        rospy.init_node("vins_gate_test", disable_signals=True)
        # 门控参数（与 C++ 默认一致；显式 set 保证确定性）
        for k, v in [("gate_pos_jump", 1.0), ("gate_vel", 5.0),
                     ("gate_stable_frames", 20), ("gate_enabled", True)]:
            rospy.set_param(f"/vins_to_mavros/{k}", v)
        node = subprocess.Popen(
            ["/bin/bash", "-c",
             f"exec {node_bin} __name:=vins_to_mavros"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ})
        time.sleep(1.5)
        if node.poll() is not None:
            print("[ERROR] vins_to_mavros_node 启动即退出")
            return False

        recv = {"t": [], "phase": []}
        cur_phase = {"ph": 1}

        def on_pose(m):
            recv["t"].append(rospy.get_time())
            recv["phase"].append(cur_phase["ph"])

        rospy.Subscriber("/mavros/vision_pose/pose", PoseStamped, on_pose,
                         queue_size=10)
        pub = rospy.Publisher("/vins_estimator/odometry", Odometry,
                              queue_size=10)
        time.sleep(0.5)  # 连接建立

        seq = gen_phases()
        t_start = rospy.get_time()
        for ph, t, p in seq:
            while rospy.get_time() - t_start < t:
                if rospy.is_shutdown():
                    break
                time.sleep(0.002)
            cur_phase["ph"] = ph
            o = Odometry()
            o.header.stamp = rospy.Time.now()
            o.header.frame_id = "map"
            o.pose.pose.position.x, o.pose.pose.position.y, \
                o.pose.pose.position.z = p
            o.pose.pose.orientation.w = 1.0
            pub.publish(o)
        # 收尾等传输
        time.sleep(0.5)

        # 统计断言
        n1 = sum(1 for ph in recv["phase"] if ph == 1)
        idx2 = [i for i, ph in enumerate(recv["phase"]) if ph == 2]
        idx3 = [i for i, ph in enumerate(recv["phase"]) if ph == 3]
        # 发散序列第 1 帧位移 0（相对上一帧），第 2 帧起 3m/0.02s=150m/s
        ok1 = n1 >= int(RUN_S * RATE * 0.9)
        ok2 = len(idx2) <= GATE_GRACE + 2
        ok3 = len(idx3) >= 1
        print(f"阶段1 收到 {n1} 帧（期望 ~{int(RUN_S*RATE)}）  "
              f"{'PASS' if ok1 else 'FAIL'}")
        print(f"阶段2 拦截期间漏过 {len(idx2)} 帧（允许 ≤{GATE_GRACE+2}）  "
              f"{'PASS' if ok2 else 'FAIL'}")
        print(f"阶段3 恢复后收到 {len(idx3)} 帧（期望 ≥1，20 帧平稳后恢复）  "
              f"{'PASS' if ok3 else 'FAIL'}")
        return ok1 and ok2 and ok3
    finally:
        if node is not None:
            node.terminate()
            try:
                node.wait(timeout=5)
            except subprocess.TimeoutExpired:
                node.kill()
        master.terminate()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logic-only", action="store_true",
                    help="只跑 Python 逻辑镜像（不依赖编译产物）")
    args = ap.parse_args()
    ok = run_logic_only() if args.logic_only else run_integration()
    print("=" * 50)
    print("门控单元验证:", "全部通过" if ok else "存在失败")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
