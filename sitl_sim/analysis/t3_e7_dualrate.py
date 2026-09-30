#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E7 同袋双频对照件(v7.4 等待池⑤;C07-H12/红线 6 口径;脚本就绪待回放窗口)

目的:125/223Hz 双频栈并存的门限移植性判定——
  r/vel 分布漂移<20%  → r 类判据跨频可移植(odom 门限阈值通用);
  acc 统计量漂移     → 产出重标系数表(差分 acc 类判据 125→223 须按系数搬)。

三阶段:
  prepare: 223Hz 源袋 → 125Hz 降采样袋(IMU 话题按 1/125s 网格最近邻抽取,其余话题全拷;
           manifest 记录前后帧数/实测频率)。同袋=除 IMU 网格外逐位一致(单变量纪律)。
  run(编排见 t3_e7_dualrate.sh): t3_replay.sh 串行跑两遍(私有 master 11313;单机一路红线,
           起跑前 pgrep 全场+STATUS 预告——窗口=T2 U2 队列间隙或 STATUS 协调小窗)。
  judge: 两遍回放输出对照——
           r 分布  = odom/imu_propagate 流运动学残差(C07-03 D3 梯形恒等式,同 t3_r_scan
                     口径;r 为距离量纲,odom 帧率~10Hz 与 IMU 频率无关,双频直接可比)
           vel 分布= |V| p50/p95/p999
           acc 统计= IMU 差分统计(‖Δacc‖/Δt 分布 p50/p95)→ 重标系数=stat125/stat223
  selftest: 合成序列验证抽取网格/r 公式/漂移计算三件(不依赖 rosbag)。

用法:
  t3_e7_dualrate.py prepare <bag223> [--imu-topic /mavros/imu/data_raw] [--hz 125] [--out x.bag]
  t3_e7_dualrate.py judge <replay223_dir> <replay125_dir> [--csv out.csv]
  t3_e7_dualrate.py accstats <bag> [--imu-topic ...]     # 单袋 acc 差分统计(重标系数原料)
  t3_e7_dualrate.py --selftest
输出: judge → stdout 判决行 + e7_dualrate.json(两 dir 各一份)
"""
import argparse
import json
import math
import os
import statistics
import sys

PORTABILITY_MAX_DRIFT = 0.20   # r/vel 可移植判据:分位漂移<20%(任务书 E7)
QUANTILES = (0.50, 0.95, 0.999)


# ---------------- 通用统计 ----------------

def quant(vals, q):
    if not vals:
        return None
    vals = sorted(vals)
    i = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return vals[i]


def dist_stats(pairs):
    """pairs=[(t,x,y,z,vx,vy,vz)] → (r 序列, |v| 序列)。r=梯形积分恒等式残差(C07-03 D3)。"""
    rs, vs = [], []
    for i in range(1, len(pairs)):
        t0, x0, y0, z0, vx0, vy0, vz0 = pairs[i - 1]
        t1, x1, y1, z1, vx1, vy1, vz1 = pairs[i]
        dt = t1 - t0
        if dt <= 0 or dt > 1.0:
            continue
        ex = x1 - x0 - 0.5 * (vx0 + vx1) * dt
        ey = y1 - y0 - 0.5 * (vy0 + vy1) * dt
        ez = z1 - z0 - 0.5 * (vz0 + vz1) * dt
        rs.append(math.sqrt(ex * ex + ey * ey + ez * ez))
        vs.append(math.sqrt(vx1 * vx1 + vy1 * vy1 + vz1 * vz1))
    return rs, vs


def stream_from_bag(bag_path, topic):
    """过滤读单一流 → [(t,x,y,z,vx,vy,vz)](bag 帧时戳;红线 4 过滤读)。"""
    try:
        import rosbag
    except ImportError:
        sys.exit("[e7] 需要 ROS 环境: source /opt/ros/noetic/setup.bash")
    out = []
    with rosbag.Bag(bag_path, "r") as b:
        for tp, msg, ts in b.read_messages(topics=[topic]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            p, v = msg.pose.pose.position, msg.twist.twist.linear
            out.append((t, p.x, p.y, p.z, v.x, v.y, v.z))
    return out


# ---------------- prepare:223→125 降采样 ----------------

def downsample_grid(stamps, hz):
    """1/hz 网格最近邻抽取(不重复取帧);返回选中索引列表。"""
    if not stamps:
        return []
    t0, t1 = stamps[0], stamps[-1]
    step = 1.0 / hz
    sel, j = [], 0
    g = t0
    while g <= t1 + 1e-9 and j < len(stamps):
        while j + 1 < len(stamps) and abs(stamps[j + 1] - g) <= abs(stamps[j] - g):
            j += 1
        sel.append(j)
        nxt = j + 1
        if nxt >= len(stamps):
            break
        g = max(g + step, stamps[nxt])
        j = nxt
    return sel


def cmd_prepare(args):
    try:
        import rosbag
    except ImportError:
        sys.exit("[e7] 需要 ROS 环境: source /opt/ros/noetic/setup.bash")
    src = os.path.abspath(args.bag)
    out = args.out or src.replace(".bag", "_%dhz.bag" % int(args.hz))
    imu_n0 = imu_n1 = other_n = 0
    with rosbag.Bag(src, "r") as b, rosbag.Bag(out, "w") as w:
        stamps = {}
        for tp, msg, ts in b.read_messages(topics=[args.imu_topic]):
            stamps.setdefault(tp, []).append(ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9)
        sel = {tp: set(downsample_grid(v, args.hz)) for tp, v in stamps.items()}
        idx = {tp: -1 for tp in stamps}
        with rosbag.Bag(src, "r") as b2:  # 二遍:写(一遍读索引+一遍写,避免内存双袋)
            for tp, msg, ts in b2.read_messages():
                if tp in sel:
                    idx[tp] += 1
                    if idx[tp] in sel[tp]:
                        w.write(tp, msg, ts)
                        imu_n1 += 1
                    else:
                        imu_n0 += 1
                else:
                    w.write(tp, msg, ts)
                    other_n += 1
    manifest = {"src": src, "out": out, "imu_topic": args.imu_topic,
                "target_hz": args.hz, "imu_kept": imu_n1, "imu_dropped": imu_n0,
                "other_msgs": other_n}
    with open(out + ".e7manifest.json", "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("[e7-prepare] %s → %s (IMU kept %d / dropped %d, other %d)" %
          (src, out, imu_n1, imu_n0, other_n))
    return out


# ---------------- accstats / judge ----------------

def acc_diff_stats(bag_path, imu_topic):
    """IMU 差分统计:‖Δacc‖/Δt 序列(p50/p95)——重标系数原料(差分 acc 类门限跨频须重标)。"""
    try:
        import rosbag
    except ImportError:
        sys.exit("[e7] 需要 ROS 环境")
    prev = None
    d = []
    with rosbag.Bag(bag_path, "r") as b:
        for tp, msg, ts in b.read_messages(topics=[imu_topic]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            a = msg.linear_acceleration
            cur = (t, a.x, a.y, a.z)
            if prev is not None:
                dt = cur[0] - prev[0]
                if 0 < dt < 1.0:
                    dv = math.sqrt(sum((cur[i] - prev[i]) ** 2 for i in (1, 2, 3)))
                    d.append(dv / dt)
            prev = cur
    return {"n": len(d), "p50": quant(d, 0.50), "p95": quant(d, 0.95),
            "max": max(d) if d else None}


def collect(replay_dir):
    """回放输出目录 → r/vel 双流分布(vins_out.bag: odom + imu_propagate)。"""
    bag = os.path.join(replay_dir, "vins_out.bag")
    res = {}
    for name, topic in (("odom", "/vins_estimator/odometry"),
                        ("prop", "/vins_estimator/imu_propagate")):
        try:
            rs, vs = dist_stats(stream_from_bag(bag, topic))
        except Exception as e:
            res[name] = {"error": repr(e)}
            continue
        res[name] = {"n": len(rs),
                     "r_p50": quant(rs, 0.50), "r_p95": quant(rs, 0.95),
                     "r_p999": quant(rs, 0.999),
                     "v_p50": quant(vs, 0.50), "v_p95": quant(vs, 0.95),
                     "v_p999": quant(vs, 0.999)}
    return res


def drift(a, b):
    if a is None or b is None or a == 0:
        return None
    return abs(b - a) / abs(a)


def cmd_judge(args):
    s223, s125 = collect(args.dir223), collect(args.dir125)
    verdicts = {}
    for stream in ("odom", "prop"):
        a, b = s223.get(stream, {}), s125.get(stream, {})
        row = {}
        for k in ("r_p50", "r_p95", "r_p999", "v_p50", "v_p95", "v_p999"):
            row[k] = {"223": a.get(k), "125": b.get(k),
                      "drift": drift(a.get(k), b.get(k))}
        worst = max((v["drift"] for v in row.values() if v["drift"] is not None),
                    default=None)
        row["worst_drift"] = worst
        row["portable"] = bool(worst is not None and worst < PORTABILITY_MAX_DRIFT)
        verdicts[stream] = row
    out = {"dir223": os.path.basename(args.dir223.rstrip("/")),
           "dir125": os.path.basename(args.dir125.rstrip("/")),
           "portability_max_drift": PORTABILITY_MAX_DRIFT,
           "streams": verdicts,
           "note": "r/vel 漂移<20%→r 类判据跨频可移植;acc 差分类另见重标系数"
                   "(accstats 于两源袋各跑一次,stat125/stat223 即系数;C07-H12/红线 6)"}
    for d in (args.dir223, args.dir125):
        with open(os.path.join(d, "e7_dualrate.json"), "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    for stream, row in verdicts.items():
        print("[e7-judge] %s: %s worst_drift=%s" %
              (stream, "PORTABLE" if row["portable"] else "NOT-PORTABLE",
               round(row["worst_drift"], 3) if row["worst_drift"] is not None else None))
        for k, v in row.items():
            if isinstance(v, dict):
                print("    %-6s 223=%-12s 125=%-12s drift=%s" %
                      (k, v["223"], v["125"],
                       round(v["drift"], 3) if v["drift"] is not None else None))
    if args.csv:
        import csv
        newf = not os.path.exists(args.csv)
        with open(args.csv, "a", newline="") as f:
            w = csv.writer(f)
            if newf:
                w.writerow(["stream", "r_p50_223", "r_p50_125", "r_p50_drift",
                            "r_p95_223", "r_p95_125", "r_p95_drift",
                            "v_p95_223", "v_p95_125", "v_p95_drift", "portable"])
            for stream, row in verdicts.items():
                w.writerow([stream] + sum(
                    ([row[k]["223"], row[k]["125"],
                      round(row[k]["drift"], 4) if row[k]["drift"] is not None else None]
                     for k in ("r_p50", "r_p95", "v_p95")), []) + [row["portable"]])


# ---------------- selftest(合成序列;不依赖 rosbag) ----------------

def run_selftest():
    ok = True
    # 1) 抽取网格:223Hz 合成 1000 帧 → 125Hz 网格,实测频率≈125±2%
    stamps = [i * 1.0 / 223.0 for i in range(1000)]
    sel = downsample_grid(stamps, 125.0)
    hz = (len(sel) - 1) / (stamps[sel[-1]] - stamps[sel[0]])
    c1 = abs(hz - 125.0) < 2.5 and len(sel) == len(set(sel))
    ok &= c1
    print("[e7-selftest] grid: kept=%d hz=%.1f -> %s" % (len(sel), hz, "PASS" if c1 else "FAIL"))
    # 2) r 公式:恒定速度直线运动 r≡0;单帧速度错误 r=|dv|*dt/2
    perfect = [(i * 0.1, i * 0.1, 0, 0, 1.0, 0, 0) for i in range(50)]
    rs, _ = dist_stats(perfect)
    c2a = max(rs, default=1) < 1e-9
    bad = list(perfect)
    t, x, y, z, *_ = bad[25]
    bad[25] = (t, x, y, z, 1.5, 0, 0)   # 该帧速度虚高 0.5
    rs2, _ = dist_stats(bad)
    c2b = abs(max(rs2) - 0.5 * 0.1 * 0.5) < 1e-9
    ok &= (c2a and c2b)
    print("[e7-selftest] r-formula: perfect=%s single-fault=%s -> %s" %
          (c2a, c2b, "PASS" if (c2a and c2b) else "FAIL"))
    # 3) 漂移:同分布→~0;×1.3→0.3(>20% 不可移植)
    d0 = drift(100.0, 103.0)
    d1 = drift(100.0, 130.0)
    c3 = abs(d0 - 0.03) < 1e-9 and abs(d1 - 0.30) < 1e-9
    ok &= c3
    print("[e7-selftest] drift: 3%%->%.2f 30%%->%.2f -> %s" % (d0, d1, "PASS" if c3 else "FAIL"))
    print("[e7-selftest] 总判决: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p1 = sub.add_parser("prepare")
    p1.add_argument("bag")
    p1.add_argument("--imu-topic", default="/mavros/imu/data_raw")
    p1.add_argument("--hz", type=float, default=125.0)
    p1.add_argument("--out", default=None)
    p2 = sub.add_parser("judge")
    p2.add_argument("dir223")
    p2.add_argument("dir125")
    p2.add_argument("--csv", default=None)
    p3 = sub.add_parser("accstats")
    p3.add_argument("bag")
    p3.add_argument("--imu-topic", default="/mavros/imu/data_raw")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(run_selftest())
    if args.cmd == "prepare":
        cmd_prepare(args)
    elif args.cmd == "judge":
        cmd_judge(args)
    elif args.cmd == "accstats":
        print(json.dumps(acc_diff_stats(args.bag, args.imu_topic), indent=1))
    else:
        ap.error("需要子命令 prepare/judge/accstats 或 --selftest")


if __name__ == "__main__":
    main()
