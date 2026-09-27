#!/usr/bin/env python3
"""SITL 飞行 bag 数值分析（A6）。

用法: python3 analyze_flight.py <bag文件> [--goal x y z]
输出: 终端指标表 + docs/analysis/<bag名>.png

指标（对应任务书 A6）:
  1. 到位误差与收敛时间（goal 位置 vs 实际轨迹收敛点）
  2. 轨迹-障碍最小距离时序（障碍表内置 = sitl_world_obstacles.world, odom 系）
  3. /position_cmd 与实际运动的跟踪误差与延迟
  4. 速度是否超限（对 max_vel 阈值）

依赖: ROS Noetic python3 环境（rospy/rosbag/msg）+ matplotlib(Agg)
"""
import sys
import math
import os

import rosbag
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nav_msgs.msg import Odometry

# sitl_world_obstacles.world 的障碍表（odom 系，与 world 文件注释一致）
# 格式: name -> (cx, cy, z_base, sx, sy, sz)；z_base=0（全部落地）
OBSTACLES = {
    "box_A": (3.5, -1.5, 0.0, 1.0, 1.0, 1.8),
    "box_B": (5.0, -2.5, 0.0, 1.5, 1.0, 1.2),
    "box_C": (4.5, -3.5, 0.0, 1.0, 1.0, 2.2),
}
# sitl_world_obstacles_v2（T3-W3）：v1 全保留 + box_D/E 狭缝（坐标见 world 头注释）
OBSTACLES_V2 = {
    "box_A": (3.5, -1.5, 0.0, 1.0, 1.0, 1.8),
    "box_B": (5.0, -2.5, 0.0, 1.5, 1.0, 1.2),
    "box_C": (4.5, -3.5, 0.0, 1.0, 1.0, 2.2),
    "box_D": (6.4, -2.0, 0.0, 1.0, 1.0, 2.8),
    "box_E": (6.4, 0.5, 0.0, 1.0, 1.0, 2.8),
}
INFLATION = 0.299   # grid_map obstacles_inflation（advanced_param_sitl.xml）
SAFETY_MARGIN = 0.05
MAX_VEL = 0.5       # run_planner_sitl.launch max_vel


def dist_point_box(p, box):
    """点到轴对齐箱表面的最短距离（在箱外为正；内部为负）。"""
    cx, cy, z0, sx, sy, sz = box
    dx = max(abs(p[0] - cx) - sx / 2.0, 0.0)
    dy = max(abs(p[1] - cy) - sy / 2.0, 0.0)
    dz = max(max(z0 - p[2], p[2] - (z0 + sz)) , 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def main():
    bag_path = sys.argv[1]
    goal_cli = None
    global OBSTACLES
    if "--world" in sys.argv and sys.argv[sys.argv.index("--world") + 1] == "v2":
        OBSTACLES = OBSTACLES_V2
    if "--goal" in sys.argv:
        i = sys.argv.index("--goal")
        goal_cli = [float(sys.argv[i + 1]), float(sys.argv[i + 2]), float(sys.argv[i + 3])]

    t, pos = [], []          # odom 轨迹
    tc, cmd_p = [], []       # position_cmd 参考
    goal = goal_cli

    with rosbag.Bag(bag_path) as bag:
        for topic, msg, st in bag.read_messages():
            if topic == "/mavros/local_position/odom":
                t.append(msg.header.stamp.to_sec())
                pos.append([msg.pose.pose.position.x, msg.pose.pose.position.y,
                            msg.pose.pose.position.z])
            elif topic == "/position_cmd":
                tc.append(msg.header.stamp.to_sec())
                cmd_p.append([msg.position.x, msg.position.y, msg.position.z])
            elif topic == "/move_base_simple/goal" and goal is None:
                goal = [msg.pose.position.x, msg.pose.position.y, 1.0]

    if not pos:
        print("ERROR: no /mavros/local_position/odom in bag")
        return 1
    if goal is None:
        print("WARN: no goal found; arrival metrics skipped")
    n = len(pos)
    print(f"bag={os.path.basename(bag_path)} odom_samples={n} cmd_samples={len(cmd_p)}")

    # ---- 1. 到位误差与收敛时间（仅飞行段：z>0.3，排除地面滑行/降落） ----
    # 到位误差取"首次收敛(<0.2m)后 10s 稳定段"的均值——飞行末点会混入降落下降段
    fly = [i for i in range(n) if pos[i][2] > 0.3]
    if goal is not None and fly:
        t0 = t[fly[0]]
        conv_t = None
        stable = None
        for i in fly:
            if math.dist(pos[i], goal) < 0.2:
                tail = [j for j in fly if j >= i][:60]
                if all(math.dist(pos[j], goal) < 0.3 for j in tail):
                    conv_t = t[i] - t0
                    stable = [j for j in fly if t[j] - t[i] <= 10.0 and t[j] >= t[i]]
                    break
        if stable:
            errs = [math.dist(pos[j], goal) for j in stable]
            err_final = sum(errs) / len(errs)
        else:
            err_final = math.dist(pos[fly[-1]], goal)
        print(f"[1] goal=({goal[0]:.2f},{goal[1]:.2f},{goal[2]:.2f}) "
              f"arrival_err(stable 10s mean)={err_final:.3f}m "
              f"conv_time={conv_t if conv_t else 'n/a'}s stable_n={len(stable) if stable else 0}")

    # ---- 2. 轨迹-障碍最小距离 ----
    dmin_all = {k: math.inf for k in OBSTACLES}
    min_series = []
    for i, p in enumerate(pos):
        if p[2] < 0.15:   # 地面滑行段不计（起飞前/降落后）
            continue
        dmins = {k: dist_point_box(p, b) for k, b in OBSTACLES.items()}
        for k, d in dmins.items():
            dmin_all[k] = min(dmin_all[k], d)
        min_series.append((t[i] - t[0], min(dmins.values())))
    overall = min(dmin_all.values())
    thresh = INFLATION + SAFETY_MARGIN
    verdict = "PASS" if overall > thresh else "FAIL"
    print(f"[2] min_dist_to_obstacles: " +
          ", ".join(f"{k}={v:.3f}m" for k, v in dmin_all.items()))
    print(f"    overall={overall:.3f}m threshold(inflation+margin)={thresh:.3f}m -> {verdict}")

    # ---- 3. 跟踪误差与延迟（odom 30Hz vs cmd 100Hz，时间戳配对；仅飞行段） ----
    track_err, latency = [], []
    import bisect
    flyset = set(fly) if fly else set(range(n))
    for i in range(len(tc)):
        j = bisect.bisect_left(t, tc[i])
        if j >= n or j not in flyset:
            continue
        dt = t[j] - tc[i]
        if abs(dt) > 0.05:
            continue
        e = math.dist(cmd_p[i], pos[j])
        track_err.append(e)
        latency.append(dt)
    if track_err:
        track_err.sort()
        p50 = track_err[len(track_err) // 2]
        p95 = track_err[int(len(track_err) * 0.95)]
        mean_lat = sum(latency) / len(latency)
        print(f"[3] tracking: mean-ish(p50)={p50:.3f}m p95={p95:.3f}m "
              f"max={track_err[-1]:.3f}m latency(mean)={mean_lat*1000:.0f}ms "
              f"(n={len(track_err)})")

    # ---- 4. 速度超限 ----
    vmax = 0.0
    over = 0
    for i in range(1, n):
        dt = t[i] - t[i - 1]
        if dt <= 0:
            continue
        v = math.dist(pos[i], pos[i - 1]) / dt
        vmax = max(vmax, v)
        if v > MAX_VEL * 1.1:
            over += 1
    print(f"[4] vel: max={vmax:.2f}m/s limit={MAX_VEL}m/s over_samples={over}/{n}")

    # ---- 图 ----
    out_dir = os.path.expanduser("~/catkin_ws/docs/analysis")
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, os.path.basename(bag_path).replace(".bag", ".png"))
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
    # 左: XY 轨迹 + 障碍 + goal
    for k, (cx, cy, z0, sx, sy, sz) in OBSTACLES.items():
        ax[0].add_patch(plt.Rectangle((cx - sx / 2 - INFLATION, cy - sy / 2 - INFLATION),
                                      sx + 2 * INFLATION, sy + 2 * INFLATION,
                                      fill=False, ls="--", ec="gray"))
        ax[0].add_patch(plt.Rectangle((cx - sx / 2, cy - sy / 2), sx, sy, fc="salmon", alpha=0.6))
        ax[0].text(cx, cy, k, ha="center", va="center", fontsize=8)
    ax[0].plot([p[0] for p in pos], [p[1] for p in pos], "b-", lw=1, label="odom")
    if cmd_p:
        ax[0].plot([p[0] for p in cmd_p], [p[1] for p in cmd_p], "g.", ms=1, alpha=0.3, label="cmd")
    if goal:
        ax[0].plot(goal[0], goal[1], "r^", ms=10, label="goal")
    ax[0].set_xlabel("x [m] (odom)"); ax[0].set_ylabel("y [m]")
    ax[0].set_aspect("equal"); ax[0].legend(fontsize=8); ax[0].set_title("XY trajectory vs obstacles")
    # 右: 最小距离时序
    if min_series:
        xs = [s[0] for s in min_series]; ys = [s[1] for s in min_series]
        ax[1].plot(xs, ys, "b-", lw=1)
        ax[1].axhline(thresh, color="r", ls="--", label=f"threshold {thresh:.2f}m")
        ax[1].set_xlabel("t [s]"); ax[1].set_ylabel("min dist to boxes [m]")
        ax[1].legend(); ax[1].set_title("Clearance over time")
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    print(f"plot saved: {out_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
