#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A.4 third recount — machine-control (3090 MACH1-12) dual-stream jump census.

Prereg: t1_evidence/v11_4_2026-10-05/a4_recount3_prereg.md (frozen first).
Method verbatim from a4_recount.py (v10.4) + armed-window segmentation
(second-recount §4 discipline: flight window vs shutdown tail vs birth)
+ 5 m big-jump line + mechanical three-branch verdict.

Usage: python3 a4_recount3.py <out_json> <bag1> [bag2 ...]
"""
import json
import math
import sys

import rosbag

TH = 0.5        # main line (T2 delivery caliber, verbatim)
TH_BIG = 5.0    # big-jump line (prereg v3; F3B15 29.07m / BL-family divider)
TH_SMALL = 0.02  # sub-threshold reference (v10.1 probe caliber)


def load_streams(path):
    """One bag pass: imu_prop + odom + state(armed spans)."""
    streams = {"imu_prop": [], "odom": []}
    armed_edges = []
    armed_prev = False
    with rosbag.Bag(path, "r") as bag:
        for topic, m, t in bag.read_messages(topics=[
                "/vins_estimator/imu_propagate", "/vins_estimator/odometry",
                "/mavros/state"]):
            ts = t.to_sec()
            if topic == "/mavros/state":
                a = bool(m.armed)
                if a and not armed_prev:
                    armed_edges.append(("arm", ts))
                elif not a and armed_prev:
                    armed_edges.append(("disarm", ts))
                armed_prev = a
                continue
            p = m.pose.pose.position
            v = m.twist.twist.linear
            key = "imu_prop" if topic.endswith("imu_propagate") else "odom"
            streams[key].append((ts, m.header.stamp.to_sec(),
                                 p.x, p.y, p.z, v.x, v.y, v.z))
    return streams, armed_edges


def flight_span(armed_edges, t0_default, t1_default):
    if not armed_edges:
        return t0_default, t1_default, "no-armed-full-span"
    arm_t = armed_edges[0][1]
    dis_t = armed_edges[-1][1]
    return arm_t, dis_t, "armed-span"


def seg_of(t, arm_t, dis_t, t_end):
    """coarse segment label on header stamps (armed edges are bag-time;
    MACH bags record both domains close — label by proximity, heuristic)."""
    if t <= arm_t - 1.0:
        return "birth"
    if t <= dis_t + 1.0:
        return "flight"
    return "tail"


def stream_stats(msgs, arm_t, dis_t):
    n = len(msgs)
    out = {"n": n}
    if n < 2:
        return out
    jumps, big_flight = [], []
    small = 0
    maxdP = 0.0
    for i in range(1, n):
        dx = msgs[i][2] - msgs[i - 1][2]
        dy = msgs[i][3] - msgs[i - 1][3]
        dz = msgs[i][4] - msgs[i - 1][4]
        dP = math.sqrt(dx * dx + dy * dy + dz * dz)
        th = msgs[i][1]
        if dP > maxdP:
            maxdP = dP
        if dP > TH:
            seg = seg_of(th, arm_t, dis_t, msgs[-1][1])
            jumps.append({"t": round(th, 3), "dP": round(dP, 4), "seg": seg})
            if dP > TH_BIG and seg == "flight":
                big_flight.append(round(dP, 4))
        elif dP > TH_SMALL:
            small += 1
    gaps = []
    for i in range(1, n):
        dt = msgs[i][1] - msgs[i - 1][1]
        if dt > 2.0:
            gaps.append({"t": round(msgs[i - 1][1], 3), "gap_s": round(dt, 3)})
    segs = {}
    for j in jumps:
        segs.setdefault(j["seg"], []).append(j["dP"])
    out.update({
        "jumps_gt_0p5_total": len(jumps),
        "jumps_by_seg": {k: len(v) for k, v in segs.items()},
        "jump_max_by_seg": {k: round(max(v), 3) for k, v in segs.items()},
        "big_gt_5m_in_flight": len(big_flight),
        "big_vals": big_flight[:20],
        "small_0p02_0p5": small,
        "maxdP": round(maxdP, 4),
        "n_gaps_gt2s": len(gaps),
        "gaps": gaps[:20],
        "jump_events": jumps if len(jumps) <= 200 else jumps[:60] + [{"TRUNC": True}] + jumps[-20:],
    })
    return out


def main():
    out_path, bags = sys.argv[1], sys.argv[2:]
    results = []
    for b in bags:
        run = b.rstrip("/").split("/")[-2] if "/" in b else b
        print("processing", run, flush=True)
        try:
            streams, edges = load_streams(b)
            arm_t, dis_t, mode = flight_span(edges, 0, 1e18, )
            rec = {"run": run, "armed_mode": mode,
                   "armed_edges": [(k, round(v, 3)) for k, v in edges[:12]]}
            for key in ("odom", "imu_prop"):
                rec[key] = stream_stats(streams[key], arm_t, dis_t)
            results.append(rec)
        except Exception as e:  # noqa: BLE001
            results.append({"run": run, "error": str(e)[:200]})
        with open(out_path, "w") as f:
            json.dump(results, f, indent=1)

    # mechanical three-branch verdict (prereg v3 §1)
    ok = [r for r in results if "error" not in r]
    n = len(ok)
    rounds_big = [r for r in ok if r["odom"]["big_gt_5m_in_flight"] > 0 or
                  r["imu_prop"]["big_gt_5m_in_flight"] > 0]
    med_odom_flight = sorted(r["odom"]["jumps_by_seg"].get("flight", 0) for r in ok)
    med = med_odom_flight[n // 2] if n else 0
    verdict = {
        "n_rounds": n,
        "rounds_with_big_flight_jump": len(rounds_big),
        "median_odom_flight_jumps_0p5": med,
        "branch": None,
    }
    if len(rounds_big) == 0 and med <= 2:
        verdict["branch"] = 1  # jump face migrated with the machine
    elif len(rounds_big) >= (n + 1) // 2:
        verdict["branch"] = 2  # big jumps persist cross-machine
    elif len(rounds_big) == 0:
        verdict["branch"] = 3  # no big jumps; small/tail persists
    else:
        verdict["branch"] = "mixed"
    with open(out_path.replace(".json", "_verdict.json"), "w") as f:
        json.dump(verdict, f, indent=1)
    print("[verdict]", json.dumps(verdict))


if __name__ == "__main__":
    main()
