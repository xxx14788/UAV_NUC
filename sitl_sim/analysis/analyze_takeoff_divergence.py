#!/usr/bin/env python3
"""T3-W1 起飞发散离线复盘 v2：P1 假设裁决 + P2/P3 分解（数值）。

用法: python3 analyze_takeoff_divergence.py <bag> [<bag>...] [--png-dir DIR]

v2 要点（v1 教训，2026-09-27）：
  - 本批 bag 的 /move_base_simple/goal header 时戳恒为 0 —— goal 事件改按
    到达序号锚定（goal.odom_idx），时间轴用 odom 时戳 + 跳变修复
    （|dt|>3s 截为 0.037s）重建单调伪时间；
  - 失败两轮的实飞结构为「同 bag 双腿」：腿A 原点->goal 成功，落地后
    机体被搬回障碍区侧，腿B 返程发散——按 goal 去重后逐腿分析；
  - 新增机制签名（W1 深挖结论）：
      flip   : /mavros/setpoint_raw/attitude 姿态指令 |pitch|>150deg
               （px4ctrl controller.cpp 姿态合成在大偏航误差下穿倒扣）
      osc    : 姿态指令 pitch 的 std 在腿内 >5deg（发散性振荡）
      yawchg : 腿起始时 cmd.yaw - odom yaw 的初始差（成功腿<=75deg，
               失败腿 114/185deg —— 触发条件）

每腿输出：hover 状态/yawchg/签名/出图判定/odom-truth 偏差/P2(指令vs实际
速度)/P3(路径比、停顿、收敛)/H1 几何复核（前 15 条 cmd 到膨胀面最小距离，
裁决"初始控制点入惩罚圈"假设）。
依赖: ROS Noetic python3（rosbag）+ matplotlib(Agg)。
障碍表与 analyze_flight.py 一致（sitl_world_obstacles.world, odom 系）。
"""
import sys
import math
import os
import statistics

import rosbag
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OBSTACLES = {
    "box_A": (3.5, -1.5, 0.0, 1.0, 1.0, 1.8),
    "box_B": (5.0, -2.5, 0.0, 1.5, 1.0, 1.2),
    "box_C": (4.5, -3.5, 0.0, 1.0, 1.0, 2.2),
}
INFLATION = 0.299
DIST0 = 0.5
MAX_VEL = 0.5
CMD_LIMIT = 0.55     # limit_vel*limit_ratio
ACT_ALARM = 0.7      # P2 验收线 1.4x
MAP_BOUND = 15.0
ODOM_HZ = 27.0       # 实测 ~27Hz，跳变修复的默认周期
FLIP_DEG = 150.0     # |sp_pitch| 超过此值 = 倒扣指令
OSC_STD = 5.0        # 腿内 sp_pitch std 超过此值 = 发散振荡
DUPE_ODOM = 300      # 同目标 goal 到达间隔 < 此 odom 条数 = 重复发送


def dist_point_box(p, box):
    cx, cy, z0, sx, sy, sz = box
    dx = max(abs(p[0] - cx) - sx / 2.0, 0.0)
    dy = max(abs(p[1] - cy) - sy / 2.0, 0.0)
    dz = max(max(z0 - p[2], p[2] - (z0 + sz)), 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def yaw_q(x, y, z, w):
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def roll_pitch_q(x, y, z, w):
    roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    pitch = math.degrees(math.atan2(2 * (w * y - z * x), 1 - 2 * (y * y + z * z)))
    return roll, pitch


def angdiff_deg(a, b):
    return (a - b + 540.0) % 360.0 - 180.0


def load_bag(bag_path):
    """到达序读取；goal 记录到达时 odom 序号；sp 记录姿态指令 roll/pitch/thr。"""
    odom, cmd, sp, goals = [], [], [], []
    with rosbag.Bag(bag_path) as bag:
        for topic, msg, _st in bag.read_messages():
            if topic == "/mavros/local_position/odom":
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                odom.append({"t": msg.header.stamp.to_sec(),
                             "p": [p.x, p.y, p.z],
                             "yaw": math.degrees(yaw_q(q.x, q.y, q.z, q.w))})
            elif topic == "/position_cmd":
                cmd.append({"t": msg.header.stamp.to_sec(),
                            "p": [msg.position.x, msg.position.y, msg.position.z],
                            "v": [msg.velocity.x, msg.velocity.y, msg.velocity.z],
                            "yaw": math.degrees(msg.yaw),
                            "oi": len(odom)})
            elif topic == "/mavros/setpoint_raw/attitude":
                r, p = roll_pitch_q(msg.orientation.x, msg.orientation.y,
                                    msg.orientation.z, msg.orientation.w)
                sp.append({"t": msg.header.stamp.to_sec(), "r": r, "p": p,
                           "thr": msg.thrust, "oi": len(odom)})
            elif topic == "/move_base_simple/goal":
                p = msg.pose.position
                goals.append({"oi": len(odom), "g": [p.x, p.y,
                                                    p.z if p.z > 0.1 else 1.0]})
    # 伪时间：跳变修复为 1/ODOM_HZ
    fixes = 0
    for i in range(1, len(odom)):
        dt = odom[i]["t"] - odom[i - 1]["t"]
        if dt < -0.5 or dt > 3.0:
            odom[i]["t"] = odom[i - 1]["t"] + 1.0 / ODOM_HZ
            fixes += 1
    return odom, cmd, sp, goals, fixes


def dedupe_goals(goals, odom):
    """同目标且到达间隔小于 DUPE_ODOM 条 odom 的 goal 合并。"""
    out = []
    for g in goals:
        if out and (math.dist(g["g"], out[-1]["g"]) < 0.5
                    and g["oi"] - out[-1]["oi"] < DUPE_ODOM):
            continue
        out.append(g)
    return out


def at_odom(arr, oi, key_oi="oi"):
    """arr 中到达序号 <= oi 的最后一条。"""
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if arr[mid][key_oi] <= oi:
            lo = mid
        else:
            hi = mid - 1
    return arr[lo] if arr and arr[lo][key_oi] <= oi else None


def analyze_leg(bag_name, li, goal, odom, cmd, sp):
    oi0 = goal["oi"]
    t0 = odom[min(oi0, len(odom) - 1)]["t"]
    leg_len = min(1200, len(odom) - oi0)  # 腿窗口：goal 后最多 1200 条 odom(~45s)
    od_w = odom[oi0:oi0 + leg_len]
    cmd_w = [c for c in cmd if oi0 <= c["oi"] < oi0 + leg_len]
    sp_w = [s for s in sp if oi0 <= s["oi"] < oi0 + leg_len]
    if len(od_w) < 50:
        return {"skip": "odom<50"}
    r = {"bag": bag_name, "leg": li, "goal": [round(x, 2) for x in goal["g"]],
         "takeoff": [round(x, 2) for x in od_w[0]["p"]],
         "hover_yaw": round(od_w[0]["yaw"], 1)}

    # 触发条件：初始 yaw 目标差
    if cmd_w:
        c0 = at_odom(cmd_w, oi0 + 30)
        if c0:
            r["yawchg"] = round(abs(angdiff_deg(c0["yaw"], r["hover_yaw"])), 1)
    # cmd.yaw 相对 hover 的最大瞬时差（扫描幅度）
    if cmd_w:
        mx = max(abs(angdiff_deg(c["yaw"], r["hover_yaw"])) for c in cmd_w[:400])
        r["yaw_slew_max"] = round(mx, 1)

    # 签名：flip / osc
    if sp_w:
        pitches = [s["p"] for s in sp_w]
        r["sp_pitch_min"] = round(min(pitches), 1)
        r["sp_pitch_max"] = round(max(pitches), 1)
        r["sp_pitch_std"] = round(statistics.pstdev(pitches), 2)
        r["flip"] = any(abs(p) > FLIP_DEG for p in pitches)
        r["osc"] = r["sp_pitch_std"] > OSC_STD
        kills = [s for s in sp_w if s["thr"] < 0.01]
        r["killed"] = bool(kills and sp_w[-1]["thr"] < 0.01)

    # 出图 & 终点
    out = next((m for m in od_w if abs(m["p"][0]) > MAP_BOUND
                or abs(m["p"][1]) > MAP_BOUND), None)
    r["exit_map"] = None if out is None else {
        "t_rel": round(out["t"] - t0, 1), "p": [round(x, 1) for x in out["p"]]}
    r["final"] = [round(x, 1) for x in od_w[-1]["p"]]
    d_end = math.dist(od_w[-1]["p"], goal["g"])
    r["final_err"] = round(d_end, 2)

    # H1 复核：前 15 条移动 cmd 到膨胀面最小距离
    movers = [c for c in cmd_w[:40]
              if math.dist(c["p"], od_w[0]["p"]) > 0.1][:15]
    if movers:
        dmin = min(dist_point_box(c["p"], b) - INFLATION
                   for c in movers for b in OBSTACLES.values())
        r["d_cmd15_min_infl"] = round(dmin, 3)
        r["penalty_pts"] = sum(
            1 for c in movers
            if min(dist_point_box(c["p"], b) - INFLATION
                   for b in OBSTACLES.values()) < DIST0)

    # P2：指令 vs 实际（odom 差分）
    act = []
    for i in range(1, len(od_w)):
        dt = od_w[i]["t"] - od_w[i - 1]["t"]
        if 0.01 < dt < 0.5:
            v = [(a - b) / dt for a, b in zip(od_w[i]["p"], od_w[i - 1]["p"])]
            act.append(math.hypot(*v[:2]))
    cmdv = [math.hypot(c["v"][0], c["v"][1]) for c in cmd_w]
    if cmdv and act:
        r["p2"] = {"cmd_max": round(max(cmdv), 2),
                   "cmd_over": round(sum(1 for x in cmdv if x > CMD_LIMIT) / len(cmdv), 4),
                   "act_max": round(max(act), 2),
                   "act_over": round(sum(1 for x in act if x > ACT_ALARM) / len(act), 4)}

    # P3：路径比/停顿/收敛
    fly = [m for m in od_w if m["p"][2] > 0.3]
    if len(fly) > 30:
        path = sum(math.dist(fly[i]["p"], fly[i - 1]["p"])
                   for i in range(1, len(fly)))
        straight = math.dist(fly[0]["p"], goal["g"])
        conv = None
        for i, m in enumerate(fly):
            if math.dist(m["p"], goal["g"]) < 0.2 and fly[-1]["t"] - m["t"] > 3:
                conv = round(m["t"] - t0, 1)
                break
        # 停顿占比：1s 窗位移 <0.1m 且在飞行高度
        stall = tot = 0
        for i in range(len(fly)):
            j = i
            while j + 1 < len(fly) and fly[j + 1]["t"] - fly[i]["t"] < 1.0:
                j += 1
            if fly[j]["t"] - fly[i]["t"] > 0.5:
                tot += 1
                if math.dist(fly[j]["p"], fly[i]["p"]) < 0.1:
                    stall += 1
        r["p3"] = {"path": round(path, 1), "straight": round(straight, 1),
                   "ratio": round(path / straight, 2) if straight > 0.5 else None,
                   "conv_s": conv,
                   "stall_frac": round(stall / tot, 3) if tot else None}
    return r


def print_leg(r):
    if "skip" in r:
        print(f"[{r['bag']} L{r['leg']}] SKIP {r['skip']}")
        return
    keys = ["goal", "takeoff", "hover_yaw", "yawchg", "yaw_slew_max",
            "sp_pitch_min", "sp_pitch_max", "sp_pitch_std", "flip", "osc",
            "killed", "exit_map", "final", "final_err",
            "d_cmd15_min_infl", "penalty_pts"]
    body = " ".join(f"{k}={r[k]}" for k in keys if k in r)
    print(f"[{r['bag']} L{r['leg']}] {body}")
    if "p2" in r:
        print(f"    P2 {r['p2']}")
    if "p3" in r:
        print(f"    P3 {r['p3']}")


def plot_leg(r, png, odom, cmd, sp, oi0, leg_len):
    """单腿四联图：XY 轨迹 / 姿态指令 pitch / cmd_yaw 相对差 / 速度。"""
    t0 = odom[min(oi0, len(odom) - 1)]["t"]
    od = odom[oi0:oi0 + leg_len]
    cw = [c for c in cmd if oi0 <= c["oi"] < oi0 + leg_len]
    sw = [s for s in sp if oi0 <= s["oi"] < oi0 + leg_len]
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    a = ax[0][0]
    a.plot([m["p"][0] for m in od], [m["p"][1] for m in od], "b-", lw=1, label="odom")
    if cw:
        a.plot([c["p"][0] for c in cw], [c["p"][1] for c in cw], "g.", ms=1,
               alpha=0.4, label="cmd")
    for name, (cx, cy, z0, sx, sy, sz) in OBSTACLES.items():
        a.add_patch(plt.Rectangle((cx - sx / 2, cy - sy / 2), sx, sy,
                                  fc="orange", alpha=0.6))
    a.plot(*r["goal"][:2], "r*", ms=14, label="goal")
    a.plot(*r["takeoff"][:2], "ks", ms=7, label="takeoff")
    a.set_aspect("equal")
    a.set_title(f"{r['bag']} L{r['leg']} XY (odom frame)")
    a.legend(fontsize=7)
    a = ax[0][1]
    if sw:
        a.plot([s["t"] - t0 for s in sw], [s["p"] for s in sw], "r-", lw=0.7)
        a.axhline(FLIP_DEG, color="k", ls=":", lw=0.7)
        a.axhline(-FLIP_DEG, color="k", ls=":", lw=0.7)
    a.set_title("sp_pitch (flip lines +/-150deg)")
    a = ax[1][0]
    if cw:
        a.plot([c["t"] - t0 for c in cw],
               [angdiff_deg(c["yaw"], r["hover_yaw"]) for c in cw], "g-", lw=0.7)
    a.axhline(0, color="k", lw=0.5)
    a.set_title("cmd_yaw - hover_yaw (deg)")
    a = ax[1][1]
    if cw:
        a.plot([c["t"] - t0 for c in cw],
               [math.hypot(c["v"][0], c["v"][1]) for c in cw], "g-", lw=0.7,
               label="|cmd v|")
    for i in range(1, len(od)):
        od[i]["sp"] = math.hypot(od[i]["p"][0] - od[i - 1]["p"][0],
                                 od[i]["p"][1] - od[i - 1]["p"][1]) / max(
            od[i]["t"] - od[i - 1]["t"], 1e-3) if od[i]["t"] > od[i - 1]["t"] else 0
    a.plot([m["t"] - t0 for m in od[1:]], [m["sp"] for m in od[1:]], "b-", lw=0.5,
           alpha=0.7, label="|odom diff v|")
    a.axhline(CMD_LIMIT, color="orange", ls="--", lw=0.8)
    a.axhline(ACT_ALARM, color="r", ls=":", lw=0.8)
    a.set_title("P2 speed")
    a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(png, dpi=100)
    plt.close(fig)


def main():
    args = sys.argv[1:]
    png_dir = "/tmp/t3w1"
    if "--png-dir" in args:
        i = args.index("--png-dir")
        png_dir = args[i + 1]
        args = args[:i] + args[i + 2:]
    os.makedirs(png_dir, exist_ok=True)
    for bag_path in args:
        name = os.path.splitext(os.path.basename(bag_path))[0].replace(
            "flight_2026-09-26_", "")
        odom, cmd, sp, goals, fixes = load_bag(bag_path)
        goals = dedupe_goals(goals, odom)
        print(f"\n### {name}: odom={len(odom)} cmd={len(cmd)} timefixes={fixes}"
              f" legs={len(goals)}")
        for li, g in enumerate(goals):
            r = analyze_leg(name, li, g, odom, cmd, sp)
            print_leg(r)
            if "skip" not in r:
                png = os.path.join(png_dir, f"t3w1_{name}_L{li}.png")
                try:
                    plot_leg(r, png, odom, cmd, sp, g["oi"],
                             min(1200, len(odom) - g["oi"]))
                    print(f"    png -> {png}")
                except Exception as exc:
                    print(f"    png FAILED: {exc}")


if __name__ == "__main__":
    main()
