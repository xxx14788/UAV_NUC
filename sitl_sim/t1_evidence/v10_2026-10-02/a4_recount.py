#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A.4 caliber reconciliation recount (T1 v10.4 unit 1, C-11).

Same-stream/same-threshold/same-window recount of jump counts across two
generations (U3' stack 285278cc vs U3pp stack lib 5dde4d7e+vins_node 86c5c6a3).
Streams: /vins_estimator/imu_propagate AND /vins_estimator/odometry (dual column).
Threshold: consecutive |dP| > 0.5 m (T2 delivery caliber).
Also records: stream gaps > 2 s (reboot/silence faces), jump clustering, dP>0.02
sub-threshold cluster count (T1 probe-caliber reference from v10.1 typology).

Usage: python3 a4_recount.py <out_json> <bag1> [bag2 ...]
"""
import json
import math
import sys

import rosbag

TH = 0.5      # T2 delivery caliber
TH_SMALL = 0.02  # T1 v10.1 probe-caliber reference

def stream_stats(msgs):
    """msgs: list of (t_bag, t_hdr, x, y, z, vx, vy, vz)."""
    n = len(msgs)
    out = {
        "n": n,
        "t_bag0": msgs[0][0] if n else None,
        "t_bag1": msgs[-1][0] if n else None,
        "t_hdr0": msgs[1][0] if False else (msgs[0][1] if n else None),
        "t_hdr1": msgs[-1][1] if n else None,
    }
    jumps = []
    small = 0
    maxdP = 0.0
    vmax = 0.0
    for i in range(1, n):
        dx = msgs[i][2] - msgs[i - 1][2]
        dy = msgs[i][3] - msgs[i - 1][3]
        dz = msgs[i][4] - msgs[i - 1][4]
        dP = math.sqrt(dx * dx + dy * dy + dz * dz)
        dt = msgs[i][1] - msgs[i - 1][1]
        if dP > maxdP:
            maxdP = dP
        if dP > TH:
            jumps.append({
                "i": i, "t": round(msgs[i][1], 3), "dt": round(dt, 3),
                "dP": round(dP, 4),
                "P": [round(msgs[i][2], 3), round(msgs[i][3], 3), round(msgs[i][4], 3)],
                "prev_P": [round(msgs[i-1][2], 3), round(msgs[i-1][3], 3), round(msgs[i-1][4], 3)],
            })
        elif dP > TH_SMALL:
            small += 1
    for m in msgs:
        v = math.sqrt(m[5] ** 2 + m[6] ** 2 + m[7] ** 2)
        if v > vmax:
            vmax = v
    # gaps > 2s on header stamps (reboot / silence faces)
    gaps = []
    for i in range(1, n):
        dt = msgs[i][1] - msgs[i - 1][1]
        if dt > 2.0:
            gaps.append({"i": i, "t_before": round(msgs[i-1][1], 3),
                         "t_after": round(msgs[i][1], 3), "gap_s": round(dt, 3)})
    # clustering: split jump list into clusters separated by > 5 s
    clusters = []
    if jumps:
        cur = [jumps[0]]
        for j in jumps[1:]:
            if j["t"] - cur[-1]["t"] > 5.0:
                clusters.append(cur)
                cur = [j]
            else:
                cur.append(j)
        clusters.append(cur)
    out.update({
        "jumps_gt_0p5": len(jumps),
        "small_0p02_0p5": small,
        "maxdP": round(maxdP, 4),
        "vmax": round(vmax, 4),
        "gaps_gt_2s": gaps[:40],
        "n_gaps": len(gaps),
        "n_clusters": len(clusters),
        "cluster_spans": [
            {"t0": round(c[0]["t"], 3), "t1": round(c[-1]["t"], 3),
             "n": len(c), "maxdP": max(x["dP"] for x in c)}
            for c in clusters
        ][:60],
        "jump_events": jumps if len(jumps) <= 1300 else jumps[:40] + [{"TRUNC": True}] + jumps[-20:],
    })
    return out


def process_bag(path):
    res = {"bag": path.split("/")[-1]}
    for topic, key in [("/vins_estimator/imu_propagate", "imu_prop"),
                       ("/vins_estimator/odometry", "odom")]:
        msgs = []
        try:
            with rosbag.Bag(path, "r") as bag:
                for _, m, _t in bag.read_messages(topics=[topic]):
                    p = m.pose.pose.position
                    v = m.twist.twist.linear
                    msgs.append((_t.to_sec(), m.header.stamp.to_sec(),
                                 p.x, p.y, p.z, v.x, v.y, v.z))
        except Exception as e:  # noqa: BLE001
            res[key] = {"error": str(e)[:200]}
            continue
        res[key] = stream_stats(msgs) if msgs else {"n": 0}
    return res


def main():
    out_path, bags = sys.argv[1], sys.argv[2:]
    results = []
    for b in bags:
        print(f"processing {b}", flush=True)
        results.append(process_bag(b))
        with open(out_path, "w") as f:
            json.dump(results, f, indent=1)
    print(f"done -> {out_path}")


if __name__ == "__main__":
    main()
