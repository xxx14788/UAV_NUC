#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_anchor_survey.py — anchor 污染普查器(P18 扩充+裁定后回归基线;只读)。

对每个含 flight.bag 的 run 目录:
  读 /move_base_simple/goal + /vins_estimator/imu_propagate + /gazebo/model_states(name 过滤);
  无 goal 话题 → NO-GOAL 行(不计入污染统计);
  有 goal → 动态窗锚(goal+5s,round_result 口径复刻) vs 静止窗锚(goal-15~-5s)+dz+到位三口径。

用法: t3_anchor_survey.py <run_dir>... [--csv out.csv]
判定基线(裁定案①回归用):|dyn-static|>0.3m 即污染轮;静止锚应≈(1.01,0.98,0.10) 出生偏移带。
"""
import math, os, sys, csv

GOAL_TOL = 0.05

def survey(run_dir):
    import rosbag
    bag = os.path.join(run_dir, "flight.bag")
    if not os.path.exists(bag):
        return {"dir": os.path.basename(run_dir), "state": "NO-BAG"}
    prop, truth, goals = [], [], []
    with rosbag.Bag(bag, "r") as b:
        for topic, msg, ts in b.read_messages(topics=[
                "/vins_estimator/imu_propagate", "/gazebo/model_states",
                "/move_base_simple/goal"]):
            t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
            if topic == "/vins_estimator/imu_propagate":
                p = msg.pose.pose.position
                prop.append((t, p.x, p.y, p.z))
            elif topic == "/gazebo/model_states":
                try:
                    i = msg.name.index("iris_stereo_vins")
                except ValueError:
                    continue
                p = msg.pose[i].position
                truth.append((t, p.x, p.y, p.z))
            else:
                goals.append((t, msg.pose.position.x, msg.pose.position.y, msg.pose.position.z))
    row = {"dir": os.path.basename(run_dir)}
    if not goals:
        row.update({"state": "NO-GOAL", "n_prop": len(prop)})
        return row
    g = goals[0]
    gx, gy, gz = g[1], g[2], g[3]
    g1_ts = g[0]
    if len(prop) < 100 or not truth:
        row.update({"state": "THIN", "n_prop": len(prop)})
        return row
    row["goal"] = "(%.0f,%.0f,%.0f)" % (gx, gy, gz)

    def near(arr, tt):
        return min(arr, key=lambda q: abs(q[0] - tt))

    def anchor(f, to):
        pw = [p for p in prop if f <= p[0] <= to]
        if not pw:
            return None
        tw = [near(truth, p[0]) for p in pw[:50]]
        return tuple(sum(t[k] for t in tw) / len(tw) - sum(p[k] for p in pw[:50]) / len(pw)
                     for k in (1, 2, 3))

    a_dyn = anchor(g1_ts, g1_ts + 5)
    a_st = anchor(g1_ts - 15, g1_ts - 5)
    if not a_dyn or not a_st:
        row.update({"state": "WINDOW-EMPTY", "n_prop": len(prop)})
        return row
    t_end = truth[-1][0]

    def leg_min(ref):
        sel = [p for p in truth if g1_ts <= p[0] <= t_end]
        return min(math.dist((p[1], p[2], p[3]), ref) for p in sel) if sel else -1

    d_st_off = math.dist(a_st, (1.01, 0.98, 0.10))
    d_anchor = math.dist(a_dyn, a_st)
    row.update({
        "state": "OK", "n_prop": len(prop),
        "dyn": "(%.3f,%.3f,%.3f)" % a_dyn, "static": "(%.3f,%.3f,%.3f)" % a_st,
        "dz_dyn_minus_static": round(a_dyn[2] - a_st[2], 3),
        "anchor_gap_m": round(d_anchor, 3),
        "static_vs_birth_off": round(d_st_off, 3),
        "arrive_dyn": round(leg_min(tuple(gx + a_dyn[0], ) if False else (gx + a_dyn[0], gy + a_dyn[1], gz + a_dyn[2])), 3),
        "arrive_static": round(leg_min((gx + a_st[0], gy + a_st[1], gz + a_st[2])), 3),
        "arrive_bare": round(leg_min((gx, gy, gz)), 3),
        "contaminated_gt03": int(d_anchor > 0.3),
    })
    return row

def main():
    argv = sys.argv[1:]
    csv_out = None
    if "--csv" in argv:
        i = argv.index("--csv")
        csv_out = argv[i + 1]
        del argv[i:i + 2]          # --csv 及其值不进目录列表
    args = argv
    rows = [survey(d) for d in args]
    keys = ["dir", "state", "goal", "n_prop", "dyn", "static", "dz_dyn_minus_static",
            "anchor_gap_m", "static_vs_birth_off", "arrive_dyn", "arrive_static",
            "arrive_bare", "contaminated_gt03"]
    for r in rows:
        print("%-28s %-9s dz=%s gap=%s stO=%s arr(d/s/b)=%s/%s/%s%s" % (
            r.get("dir"), r.get("state"), r.get("dz_dyn_minus_static", "-"),
            r.get("anchor_gap_m", "-"), r.get("static_vs_birth_off", "-"),
            r.get("arrive_dyn", "-"), r.get("arrive_static", "-"), r.get("arrive_bare", "-"),
            " *CONTAM" if r.get("contaminated_gt03") else ""))
    ok = [r for r in rows if r.get("state") == "OK"]
    contam = [r for r in ok if r.get("contaminated_gt03")]
    print("--- 汇总: OK=%d NO-GOAL/THIN=%d 污染(>0.3m)=%d/%d ---" % (
        len(ok), len(rows) - len(ok), len(contam), len(ok)))
    if csv_out:
        with open(csv_out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("CSV -> %s" % csv_out)

if __name__ == "__main__":
    main()
