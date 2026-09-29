#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Y3 legs 历史全量重扫(T3 v7.2):新口径重判 + X4 5/5 自动判定

新口径三件(任务书 Y3):震颤感知(3 帧平滑后跳变)+平滑跳变计数+锚差漂移
(腿末 3s 均值 prop-vs-truth 距离);另带双流污染(P0)与真值口径到位。

对象(在盘 legs 袋,历史已清盘轮在 md 以无袋行入账):
  A. vins_smoke_runs 全轮(X 族;旧判=RESULT.txt)
  B. bags/flight_*.bag(09-23/26 早期直录;规划轮,无 VINS 验收旧判→登记型)
  C. bags/t2v3_route_112652.bag(T2 W1.3 route 腿,借读,白名单)

逐腿输出 legs_rescan.csv:袋/腿号/腿窗/到位min(GT)/锚差漂移/smj/污染/新判/旧判/变动原因
X4 判定:x4_judge(--x4 轮目录×5)按 runbook §3 判据表出 5/5 自动判决。

用法:
  t3_legs_rescan.py scan [--only 子串]        # 增量,输出 <script_dir>/t3_legs_rescan.csv
  t3_legs_rescan.py x4judge <run_dir> ×5      # X4 五连飞自动判定(模板验证可用任意轮)
"""
import argparse
import csv
import datetime
import math
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
BAGS = os.path.expanduser("~/sitl_sim/bags")
OUT_CSV = os.path.join(SCRIPT_DIR, "t3_legs_rescan.csv")

ARRIVE_M = 0.5       # 到位门(runbook A1/A2 原口径)
JUMP_M = 0.1         # 平滑跳变阈(震颤感知口径)
ANCHOR_M = 0.5       # 锚差漂移门(A2)
TOPICS = ["/move_base_simple/goal", "/gazebo/model_states",
          "/vins_estimator/imu_propagate", "/vins_estimator/odometry",
          "/mavros/imu/data_raw", "/clock", "/position_cmd",
          "/px4ctrl/takeoff_land", "/mavros/state"]


def read_bag(bag):
    import rosbag
    goals, truth, prop, imu_hdr, clock = [], [], [], [], []
    poscmd_n, disarm_seen = 0, False
    with rosbag.Bag(bag, "r") as b:
        for topic, msg, ts in b.read_messages(topics=TOPICS):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            if topic == "/move_base_simple/goal":
                p = msg.pose.position
                goals.append((t, p.x, p.y, p.z))
            elif topic == "/gazebo/model_states":
                for name, pose in zip(msg.name, msg.pose):
                    if "iris" in name:
                        p = pose.position
                        truth.append((t, p.x, p.y, p.z))
                        break
            elif topic == "/vins_estimator/imu_propagate":
                p = msg.pose.pose.position
                prop.append((t, p.x, p.y, p.z))
            elif topic == "/mavros/imu/data_raw":
                hs = getattr(msg.header, "stamp", None)
                if hs is not None:
                    imu_hdr.append(hs.to_sec())
            elif topic == "/clock":
                clock.append(msg.clock.to_sec())
            elif topic == "/position_cmd":
                poscmd_n += 1
            elif topic == "/mavros/state":
                if not msg.armed:
                    disarm_seen = True
    return dict(goals=goals, truth=truth, prop=prop, imu_hdr=imu_hdr,
                clock=clock, poscmd_n=poscmd_n, disarm_seen=disarm_seen)


def regressions(stamps):
    n, worst = 0, 0.0
    for i in range(1, len(stamps)):
        d = stamps[i] - stamps[i - 1]
        if d < -1e-6:
            n += 1
            worst = min(worst, d)
    return n, worst


def smoothed_jumps(seq):
    sm = []
    for i in range(len(seq)):
        lo, hi = max(0, i - 1), min(len(seq), i + 2)
        sm.append(tuple(sum(seq[j][k] for j in range(lo, hi)) / (hi - lo)
                        for k in (1, 2, 3)))
    return sum(1 for i in range(1, len(sm)) if math.dist(sm[i], sm[i - 1]) > JUMP_M)


def tail_anchor(seq, t_end, tail=3.0):
    w = [r for r in seq if r[0] > t_end - tail]
    n = len(w) or 1
    return (sum(r[1] for r in w) / n, sum(r[2] for r in w) / n, sum(r[3] for r in w) / n)


def scan_bag(bag, name, old_verdict):
    S = read_bag(bag)
    rows = []
    if not S["goals"] or not S["truth"]:
        return [{"bag": name, "腿": 0, "旧判": old_verdict, "新判": "无腿(无 goal/无真值)",
                 "缺失原因": "无 goal 流" if not S["goals"] else "无真值流"}]
    hdr_n, hdr_w = regressions(S["imu_hdr"])
    ck_n, ck_w = regressions(S["clock"])
    poison = hdr_n > 1000 or ck_n > 1000
    # 出生点对齐(红线 9):VINS/goal 系与 gazebo truth 系存在 ~1m 级固定平移
    # (t2b-u9 出生点(+1.01,+0.98)假象);以袋首 5s 窗(未起飞)prop−truth 中位为偏移
    from bisect import bisect_left
    off = [0.0, 0.0, 0.0]
    if S["prop"]:
        ts_t = [r[0] for r in S["truth"]]
        t_end5 = S["truth"][0][0] + 5.0
        diffs = [[], [], []]
        for pr in S["prop"]:
            if pr[0] > t_end5:
                break
            i = bisect_left(ts_t, pr[0])
            c = [j for j in (i - 1, i) if 0 <= j < len(ts_t)]
            if not c:
                continue
            j = min(c, key=lambda k: abs(ts_t[k] - pr[0]))
            if abs(ts_t[j] - pr[0]) < 0.05:
                for k in range(3):
                    diffs[k].append(pr[1 + k] - S["truth"][j][1 + k])
        if all(len(d) > 20 for d in diffs):
            off = [sorted(d)[len(d) // 2] for d in diffs]
    gs = sorted(S["goals"])
    # goal 去重:vins_smoke 以 1Hz×8s×2 重发同一 goal(竞态吸收);位置差 >1m 才算新腿
    legs = []
    for g in gs:
        if not legs or math.dist(g[1:4], legs[-1][1:4]) > 1.0:
            legs.append(g)
    for i, g in enumerate(legs):
        t_end = legs[i + 1][0] if i + 1 < len(legs) else (S["truth"][-1][0] if S["truth"] else g[0])
        tw = [r for r in S["truth"] if g[0] <= r[0] <= t_end]
        pw = [r for r in S["prop"] if g[0] <= r[0] <= t_end]
        if not tw:
            rows.append({"bag": name, "腿": i + 1, "旧判": old_verdict,
                         "新判": "无真值段", "缺失原因": "腿窗无 truth 帧"})
            continue
        arrive = min((math.dist((r[1] + off[0], r[2] + off[1], r[3] + off[2]), g[1:4])
                      for r in tw), default=None)
        smj = smoothed_jumps(pw)
        anch = (math.dist(tail_anchor(pw, t_end), tuple(a + o for a, o in
                                                        zip(tail_anchor(tw, t_end), off)))
                if pw else None)
        if poison:
            nv, why = "判废-双流污染", f"hdr回退{hdr_n}/clock回退{ck_n}"
        elif smj > 0:
            nv, why = "FAIL-发散(平滑跳变)", f"smj={smj}"
        elif arrive is not None and arrive < ARRIVE_M and (anch is None or anch < ANCHOR_M):
            nv, why = "PASS", f"到位{arrive:.3f}m"
        elif arrive is not None and arrive < ARRIVE_M:
            nv, why = "FAIL-锚差漂移", f"到位{arrive:.3f} 但锚差{anch:.2f}m"
        else:
            nv, why = "FAIL-未到位", f"min={arrive}"
        rows.append({"bag": name, "腿": i + 1,
                     "腿窗_s": f"{g[0] - S['truth'][0][0]:.0f}-{t_end - S['truth'][0][0]:.0f}",
                     "goal": f"{g[1]:.1f},{g[2]:.1f},{g[3]:.1f}",
                     "出生偏移": f"{off[0]:.2f},{off[1]:.2f},{off[2]:.2f}",
                     "到位min_GT_m": round(arrive, 3) if arrive is not None else None,
                     "锚差漂移_m": round(anch, 3) if anch is not None else None,
                     "smj": smj, "污染": poison,
                     "旧判": old_verdict, "新判": nv, "变动原因": why})
    return rows


def parse_result(run_dir):
    p = os.path.join(run_dir, "RESULT.txt")
    if not os.path.exists(p):
        return "无RESULT(非验收轮)"
    m = re.search(r"RESULT=(\S+)", open(p, errors="replace").read())
    return m.group(1) if m else "?"


def cmd_scan(only):
    targets = []
    for name in sorted(os.listdir(RUNS)):
        if only and only not in name:
            continue
        rd = os.path.join(RUNS, name)
        bag = os.path.join(rd, "flight.bag")
        if os.path.exists(bag):
            targets.append((bag, name, parse_result(rd)))
    for name in sorted(os.listdir(BAGS)):
        if only and only not in name:
            continue
        if name.startswith("flight_") and name.endswith(".bag"):
            targets.append((os.path.join(BAGS, name), name[:-4], "早期直录(无验收判据)"))
    rp = os.path.join(BAGS, "t2v3_route_112652.bag")
    if os.path.exists(rp) and (not only or only in "t2v3_route_112652"):
        targets.append((rp, "t2v3_route_112652", "T2-W1.3轮2(旧判=全过,GT 0.244/0.237)"))
    done = set()
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                done.add(r["bag"] + "#" + r["腿"])
    all_rows = []
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig") as f:
            all_rows = list(csv.DictReader(f))
    for bag, name, old in targets:
        try:
            rows = scan_bag(bag, name, old)
        except Exception as e:
            rows = [{"bag": name, "腿": 0, "旧判": old, "新判": "SCAN-ERROR",
                     "缺失原因": f"读袋异常: {e!r}"}]
        for r in rows:
            k = r["bag"] + "#" + str(r["腿"])
            if k in done:
                continue
            all_rows.append(r)
            print(f"[legs] {k}: 新判={r.get('新判')} 到位={r.get('到位min_GT_m')} "
                  f"锚差={r.get('锚差漂移_m')} smj={r.get('smj')} (旧:{r.get('旧判')})", flush=True)
        # 增量落盘
        cols = ["bag", "腿", "腿窗_s", "goal", "出生偏移", "到位min_GT_m", "锚差漂移_m", "smj",
                "污染", "旧判", "新判", "变动原因", "缺失原因"]
        with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in all_rows:
                w.writerow({c: r.get(c, "") for c in cols})
    print(f"[legs] 汇总 {len(all_rows)} 腿行 → {OUT_CSV}")


def cmd_x4judge(dirs):
    """X4 5/5 自动判定:runbook §3 判据表(A1/A2/B/C/D/J0/P0)。"""
    rounds = []
    for d in dirs:
        name = os.path.basename(d.rstrip("/"))
        res = parse_result(d) if os.path.isdir(d) else "?"
        # J0/P0 由 legs_rescan 行/forensics 提供;此处读 RESULT 四指标+rescan 行
        j0 = p0 = None
        fv = os.path.join(d, "forensics_v2.json")
        if os.path.exists(fv):
            import json
            with open(fv, errors="replace") as f:
                fr = json.load(f)
            j0 = (fr.get("frame_jumps_raw_odom") == 0
                  and fr.get("frame_jumps_smoothed_odom") == 0)
            p0 = not fr.get("verdict", {}).get("poisoning_suspect")
        body = open(os.path.join(d, "RESULT.txt"), errors="replace").read() \
            if os.path.exists(os.path.join(d, "RESULT.txt")) else ""
        a1 = re.search(r"min=([\d.]+) m \(<0.5\)->(\d)", body)
        b_ok = re.search(r"避障 min_dist=([\d.]+) m \(>0.349\)->(\d)", body)
        c_ok = re.search(r"poscmd ([\d.]+) Hz \(>=50\)->(\d)", body)
        d_ok = re.search(r"auto_disarm->(\d)", body)
        crit = {"RESULT": res,
                "A1": (a1.group(2) == "1") if a1 else None,
                "B": (b_ok.group(2) == "1") if b_ok else None,
                "C": (c_ok.group(2) == "1") if c_ok else None,
                "D": (d_ok.group(1) == "1") if d_ok else None,
                "J0": j0, "P0": p0}
        ok = all(v is True for k, v in crit.items() if k != "RESULT")
        env = "ENV-FAIL" in body
        rounds.append({"round": name, "crit": crit, "green": ok and not env,
                       "env": env})
    greens = [r for r in rounds if r["green"]]
    print("| 轮 | A1 | B | C | D | J0 | P0 | ENV | 判 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rounds:
        c = r["crit"]
        print(f"| {r['round']} | {c['A1']} | {c['B']} | {c['C']} | {c['D']} | "
              f"{c['J0']} | {c['P0']} | {r['env']} | "
              f"{'绿' if r['green'] else ('ENV' if r['env'] else 'FAIL')} |")
    n_env = sum(1 for r in rounds if r["env"])
    verdict = f"X4 {'达成:5/5 绿' if len(greens) >= 5 else f'未达:{len(greens)}/5 绿(ENV {n_env} 不计不断)'}"
    print(f"\n[x4judge] {verdict}")
    return 0 if len(greens) >= 5 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "x4judge"])
    ap.add_argument("--only", default=None)
    ap.add_argument("dirs", nargs="*", help="x4judge: 五轮目录")
    args = ap.parse_args()
    if args.cmd == "scan":
        cmd_scan(args.only)
    else:
        sys.exit(cmd_x4judge(args.dirs))


if __name__ == "__main__":
    main()
