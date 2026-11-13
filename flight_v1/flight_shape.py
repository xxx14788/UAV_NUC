#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-13 圆形/八字脚本飞行（不用 RViz 选点）。

链路（与 RViz 点选完全同一条，安全门都保留）：
    本脚本 --PoseStamped(frame=world)--> /move_base_simple/goal
    -> flight_mission.py 校验（RC / FSM / 3.5 m / 时戳）并转发
    -> /flight_v1/goal_gate -> EGO FSM

导引：纯追踪（pure pursuit）
- 目标点始终在路径前方 lookahead 处；
- 目标沿弧长按 speed 前进，但被 s_proj + lookahead 钳住（飞机跟不上时目标等待，不会跑飞）；
- 目标移动 >= min_step 才发（约 2-3 Hz），避免高频 REPLAN；
- 到点不逐点停：换点由 mission 的 REPLACE 路径处理（重置到位计时/导航预算）。

安全：
- 区域盒检查（所有目标在 area×area 内，留 margin）；
- 里程计新鲜度、解锁状态、高度偏差；
- mission ACK 看门狗（拒收/无 ACK 即停）；
- 跟踪失败（lag 持续 > 2*lookahead）即停；
- Ctrl-C 后不再发点：飞机会到最后一个目标后悬停，mission 5 s 到位 + 20 s 倒计时自动降落。

用法（NUC）：
    python3 flight_shape.py --shape circle --radius 1.0 --speed 0.35 --laps 1
    python3 flight_shape.py --shape eight  --amp-x 1.0 --amp-y 0.7 --speed 0.35 --laps 1
    python3 flight_shape.py --shape circle --dry-run          # 只算不飞
"""
import argparse
import bisect
import math
import sys

# ------------------------------------------------------------------ 纯几何

def build_path(shape, radius=1.0, amp_x=1.0, amp_y=0.7, n=2400):
    """返回 (pts, cum, total)。pts 为闭合折线（不重复首点），cum 长度 n+1。"""
    if n < 32:
        raise ValueError("n 太小")
    pts = []
    if shape == "circle":
        for i in range(n):
            t = 2.0 * math.pi * i / n
            pts.append((radius * math.cos(t), radius * math.sin(t)))
    elif shape == "eight":
        # Gerono 双纽线：x=a sin t, y=b sin 2t；t=0/π 过中心，左右各一瓣
        for i in range(n):
            t = 2.0 * math.pi * i / n
            pts.append((amp_x * math.sin(t), amp_y * math.sin(2.0 * t)))
    else:
        raise ValueError("shape 只能是 circle/eight")
    cum = [0.0]
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    return pts, cum, cum[-1]


def point_at(pts, cum, s):
    """按弧长取点（s 自动按整圈取模）。"""
    total = cum[-1]
    if total <= 0:
        return pts[0]
    s = s % total
    i = bisect.bisect_right(cum, s) - 1
    i = min(max(i, 0), len(pts) - 1)
    s0, s1 = cum[i], cum[i + 1]
    f = 0.0 if s1 <= s0 else (s - s0) / (s1 - s0)
    p0, p1 = pts[i], pts[(i + 1) % len(pts)]
    return (p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1]))


def project(pts, cum, p, s_hint, window, step=0.02):
    """在 [s_hint-window, s_hint+window] 内找最近点的弧长（局部搜索，八字交叉不跳瓣）。"""
    lo = s_hint - window
    hi = s_hint + window
    best_d, best_s = float("inf"), s_hint
    s = lo
    while s <= hi + 1e-9:
        q = point_at(pts, cum, s)
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d < best_d:
            best_d, best_s = d, s
        s += step
    return best_s


def next_carrot(s_cursor, s_proj, dt, speed, lookahead, s_end):
    """目标沿弧长前进：≤speed*dt，≤s_proj+lookahead，≤终点；绝不后退。"""
    tgt = min(s_cursor + speed * dt, s_proj + lookahead, s_end)
    return max(s_cursor, tgt)


def path_metrics(pts, cum, speed):
    total = cum[-1]
    # 最大曲率（三点外接圆）
    kmax = 0.0
    n = len(pts)
    for i in range(0, n, max(1, n // 600)):
        a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        ab = math.hypot(b[0] - a[0], b[1] - a[1])
        bc = math.hypot(c[0] - b[0], c[1] - b[1])
        ca = math.hypot(a[0] - c[0], a[1] - c[1])
        area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if ab * bc * ca > 1e-12:
            kmax = max(kmax, 2.0 * area2 / (ab * bc * ca))
    return {"length": total, "kmax": kmax, "acc_centripetal": speed * speed * kmax}


def bounds_margin(pts, area, margin):
    """返回 [area/2-margin] - max(|x|,|y|)，<0 表示越界。"""
    half = area / 2.0 - margin
    m = max(max(abs(x), abs(y)) for x, y in pts)
    return half - m


# ------------------------------------------------------------------ ROS 飞行

def _read_z():
    import rospy
    z = rospy.get_param("/drone_0_ego_planner_node/fsm/manual_goal_z", 0.70)
    return float(z)


def run(args):
    import csv
    import os
    import time

    import rospy
    from geometry_msgs.msg import PoseStamped
    from mavros_msgs.msg import State
    from nav_msgs.msg import Odometry
    from std_msgs.msg import String

    rospy.init_node("flight_shape", anonymous=False)
    z_goal = args.z if args.z > 0 else _read_z()

    # 1) 等 odom 新鲜 + 已解锁 + px4ctrl 在 AUTO_HOVER/CMD_CTRL
    odom = {"t": 0.0, "p": None}
    ack = {"t": 0.0, "txt": "", "n": 0}

    def odom_cb(msg):
        odom["t"] = time.monotonic()
        p = msg.pose.pose.position
        odom["p"] = (p.x, p.y, p.z)

    def ack_cb(msg):
        ack["t"] = time.monotonic()
        ack["txt"] = (msg.data or "").strip()
        ack["n"] += 1

    rospy.Subscriber("/vins_estimator/imu_propagate", Odometry, odom_cb, queue_size=10)
    rospy.Subscriber("/flight_v1/goal_ack", String, ack_cb, queue_size=20)
    pub = rospy.Publisher("/move_base_simple/goal", PoseStamped, queue_size=5)

    print("等待 odom（/vins_estimator/imu_propagate）...", flush=True)
    t0 = time.monotonic()
    while not rospy.is_shutdown() and (odom["p"] is None or time.monotonic() - odom["t"] > 0.5):
        if time.monotonic() - t0 > 10:
            raise RuntimeError("10 s 内没有新鲜 odom —— 栈没起或 VINS 没输出")
        rospy.sleep(0.1)

    print("等待解锁 + px4ctrl AUTO_HOVER/CMD_CTRL ...", flush=True)
    t0 = time.monotonic()
    while not rospy.is_shutdown():
        try:
            st = rospy.wait_for_message("/mavros/state", State, timeout=3)
        except Exception:
            st = None
        fsm = ""
        try:
            raw = rospy.wait_for_message("/debugPx4ctrl/fsm_state", String, timeout=0.5).data or ""
            fsm = raw.split()[0] if raw.split() else ""
        except Exception:
            pass
        if st is not None and st.armed and fsm in ("AUTO_HOVER", "CMD_CTRL"):
            break
        if time.monotonic() - t0 > 60:
            raise RuntimeError("60 s 内未进入已解锁 AUTO_HOVER/CMD_CTRL（先起飞到悬停）")
        rospy.sleep(0.2)

    # 形状中心：默认取当前悬停点；给了 --center-file 则复用（圆->八字连续飞不跑偏）
    cpath = os.path.expanduser(args.center_file) if args.center_file else ""
    if cpath and os.path.exists(cpath):
        with open(cpath) as f:
            cx, cy = [float(x) for x in f.read().split()[:2]]
        center = (cx, cy)
        print("复用形状中心 (%.2f, %.2f)：%s" % (cx, cy, cpath), flush=True)
    else:
        center = (odom["p"][0], odom["p"][1])
        if cpath:
            os.makedirs(os.path.dirname(cpath), exist_ok=True)
            with open(cpath, "w") as f:
                f.write("%.3f %.3f\n" % center)
            print("记录形状中心 (%.2f, %.2f)：%s" % (center[0], center[1], cpath), flush=True)
    z_start = odom["p"][2]
    pts, cum, total = build_path(args.shape, args.radius, args.amp_x, args.amp_y)
    pts = [(center[0] + x, center[1] + y) for x, y in pts]
    s_end = total * args.laps
    print("形状=%s 周长=%.2f m 圈数=%d 目标高度=%.2f 起点=(%.2f,%.2f) 中心=(%.2f,%.2f)"
          % (args.shape, total, args.laps, z_goal, z_start, 0.0, center[0], center[1]), flush=True)

    csv_path = args.csv or os.path.expanduser(
        "~/flight_data/shape_%s_%s.csv" % (args.shape, time.strftime("%Y%m%d_%H%M%S")))
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fcsv = open(csv_path, "w", newline="")
    wr = csv.writer(fcsv)
    wr.writerow(["t", "s_cursor", "s_proj", "tx", "ty", "ox", "oy", "oz", "dist", "ack"])

    s_cursor = 0.0
    s_proj = 0.0
    last_pub = None
    last_pub_t = 0.0
    pub_n = 0
    aborted = None
    t_begin = time.monotonic()
    lag_since = None
    t_end = None

    def publish_target(tx, ty):
        nonlocal last_pub, last_pub_t, pub_n
        m = PoseStamped()
        m.header.stamp = rospy.Time.now()
        m.header.frame_id = "world"
        m.pose.position.x = tx
        m.pose.position.y = ty
        m.pose.position.z = z_goal
        m.pose.orientation.w = 1.0
        pub.publish(m)
        last_pub = (tx, ty)
        last_pub_t = time.monotonic()
        pub_n += 1

    try:
        rate = rospy.Rate(args.rate)
        while not rospy.is_shutdown():
            now = time.monotonic()
            if now - t_begin > args.max_time:
                aborted = "超过 max-time %.0f s" % args.max_time
                break
            if odom["p"] is None or now - odom["t"] > 1.0:
                aborted = "odom 失鲜 > 1 s"
                break
            ox, oy, oz = odom["p"]
            if abs(oz - z_start) > 0.20:
                aborted = "高度偏差 %.2f m（起点 %.2f / 当前 %.2f）" % (oz - z_start, z_start, oz)
                break
            if pub_n > 0 and ack["n"] == 0 and now - last_pub_t > 1.5:
                aborted = "mission 无 ACK（可能被拒：RC/FSM/半径/时戳）"
                break
            if ack["txt"].startswith("REJECTED") and now - ack["t"] < 1.0:
                aborted = "mission 拒收：%s" % ack["txt"]
                break

            s_proj = project(pts, cum, (ox, oy), s_cursor, 2.0 * args.lookahead)
            s_cursor = next_carrot(s_cursor, s_proj, 1.0 / args.rate, args.speed,
                                   args.lookahead, s_end)
            lag = s_cursor - s_proj
            if lag > 2.0 * args.lookahead:
                lag_since = lag_since or now
                if now - lag_since > 2.0:
                    aborted = "跟踪失败：lag %.2f m 持续 > 2 s" % lag
                    break
            else:
                lag_since = None

            tx, ty = point_at(pts, cum, min(s_cursor, s_end))
            if math.hypot(ox - tx, oy - ty) > 3.0:
                aborted = "目标距当前 %.2f m > 3.0（mission 限 3.5）" % math.hypot(ox - tx, oy - ty)
                break
            moved = 1e9 if last_pub is None else math.hypot(tx - last_pub[0], ty - last_pub[1])
            if moved >= args.min_step or (s_cursor >= s_end and last_pub != (tx, ty)):
                publish_target(tx, ty)

            d = math.hypot(ox - tx, oy - ty)
            wr.writerow(["%.3f" % (now - t_begin), "%.3f" % s_cursor, "%.3f" % s_proj,
                         "%.3f" % tx, "%.3f" % ty, "%.3f" % ox, "%.3f" % oy, "%.3f" % oz,
                         "%.3f" % d, ack["txt"]])
            if pub_n % 10 == 0:
                fcsv.flush()

            if s_cursor >= s_end - 1e-6 and math.hypot(ox - tx, oy - ty) < 0.25:
                print("已到路径终点（发点 %d 次），停止发点。等 mission 到位 5 s + 20 s 倒计时自动降落。"
                      % pub_n, flush=True)
                break
            if s_cursor >= s_end - 1e-6:
                t_end = t_end or now
                if now - t_end > 12.0:
                    aborted = "终点 12 s 内未收敛到 0.25 m（末段跟踪超差）"
                    break
            rate.sleep()
    except KeyboardInterrupt:
        aborted = "用户 Ctrl-C"
    finally:
        fcsv.close()
        if aborted:
            print("已停止发点：%s" % aborted, flush=True)
            print("飞机将飞完最后目标（≤%.1f m）后悬停；mission 5 s 到位、20 s 无新点自动降落。"
                  % args.lookahead, flush=True)
        print("CSV: %s（发点 %d 次，ACK %d 次）" % (csv_path, pub_n, ack["n"]), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="圆形/八字脚本飞行（经 mission 转发，不用 RViz）")
    ap.add_argument("--shape", choices=["circle", "eight"], default="circle")
    ap.add_argument("--radius", type=float, default=1.0, help="圆半径 m（≤ area/2-margin）")
    ap.add_argument("--amp-x", type=float, default=1.0, help="八字 x 半幅 m")
    ap.add_argument("--amp-y", type=float, default=0.7, help="八字 y 半幅 m")
    ap.add_argument("--laps", type=int, default=1)
    ap.add_argument("--speed", type=float, default=0.35, help="目标沿弧长速度 m/s（≤0.5）")
    ap.add_argument("--lookahead", type=float, default=0.60, help="前视距离 m")
    ap.add_argument("--min-step", type=float, default=0.05, help="目标移动多少才发点 m")
    ap.add_argument("--rate", type=float, default=10.0, help="控制循环 Hz")
    ap.add_argument("--area", type=float, default=3.5, help="允许区域边长 m")
    ap.add_argument("--margin", type=float, default=0.25, help="区域边界余量 m")
    ap.add_argument("--z", type=float, default=0.0, help="目标高度；0=读规划器 manual_goal_z")
    ap.add_argument("--max-time", type=float, default=180.0)
    ap.add_argument("--csv", default="")
    ap.add_argument("--center-file", default="", help="形状中心文件（存在则复用，否则记录当前悬停点）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if not (0.05 <= a.speed <= 0.50):
        ap.error("speed 必须在 0.05..0.50（规划器 max_vel=0.5）")
    if a.lookahead < 0.3:
        ap.error("lookahead 太小（<0.3 m），圆会抖")

    pts, cum, total = build_path(a.shape, a.radius, a.amp_x, a.amp_y)
    m = path_metrics(pts, cum, a.speed)
    margin = bounds_margin(pts, a.area, a.margin)
    sag = 0.0
    if a.shape == "circle" and a.radius > 0:
        sag = a.radius - math.sqrt(max(0.0, a.radius ** 2 - (a.lookahead / 2) ** 2))
    print("shape=%s 周长=%.2f m  laps=%d  预计 %.1f s"
          % (a.shape, total, a.laps, total * a.laps / a.speed))
    print("最大曲率=%.3f 1/m  向心加速度@%.2f m/s=%.2f m/s²（规划器 max_acc=4.0）"
          % (m["kmax"], a.speed, m["acc_centripetal"]))
    print("区域检查：area=%.1f margin=%.1f -> 余量 %.2f m %s"
          % (a.area, a.margin, margin, "OK" if margin >= 0 else "越界!"))
    print("前视 %.2f m 对应弦高 %.3f m（越小越贴形状）" % (a.lookahead, sag))
    print("发点：目标每前进 ≥%.2f m 发一次；ACK 看门狗 1.5 s" % a.min_step)

    if margin < 0:
        print("拒绝：形状超出允许区域。减小 radius/amp 或加大 area。", file=sys.stderr)
        return 2
    if m["acc_centripetal"] > 4.0:
        print("拒绝：向心加速度超规划器 max_acc。降 speed 或加大曲率半径。", file=sys.stderr)
        return 2
    if a.dry_run:
        for s in (0.0, total / 8, total / 4, total / 2, 3 * total / 4, total):
            x, y = point_at(pts, cum, s)
            print("  s=%5.2f -> (%6.3f, %6.3f)" % (s, x, y))
        print("dry-run OK（未连接 ROS、未发点）")
        return 0

    try:
        run(a)
    except Exception as exc:
        print("失败：%r" % (exc,), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
