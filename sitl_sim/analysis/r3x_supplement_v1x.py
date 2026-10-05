#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R3x supplement v1.x — 3090 machine-control rounds' timing faces into the
stable-band test (taskbook v11.4 unit 7 half-item: expansion sampling; the
"clean-side sample" half stays void — 3090 had 0 clean rounds, noted).

Aggregation and scatter keys VERBATIM from r3x_final.py (prereg v1,
descriptive, no gate): per-round aggregates -> cross-round
sc=(max-min)/np.median; MAIN=[imu_p50/p95/p99, age_odometry_p50_ms, rtf1_med];
stable if all MAIN sc<=0.30. (v1.x first cut deviated: rtf absdev + p95 —
discarded, in-ledger; this is the caliber-faithful rerun.)
"""
import glob
import io
import json
import os

import numpy as np

BASE = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_4_2026-10-05")
RUNS = sorted(os.path.basename(r) for r in glob.glob(os.path.join(BASE, "run_T2MACH*")))


def pct(a, q):
    a = sorted(a)
    if not a:
        return None
    return a[min(int(q * len(a)), len(a) - 1)]


def agg(run):
    f = os.path.join(BASE, run, "probe_r3x.jsonl")
    if not os.path.exists(f):
        return {"missing": True}
    faces = {}
    with io.open(f, encoding="utf-8") as fh:
        for ln in fh:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            faces.setdefault(r.get("face"), []).append(r)
    out = {}
    ij = faces.get("imu_jit", [])
    if ij:
        g = lambda k: [x[k] for x in ij if x.get(k) is not None]  # noqa: E731
        out["imu_p50_ms"] = pct(g("p50_ms"), 0.5)
        out["imu_p95_ms"] = pct(g("p95_ms"), 0.5)
        out["imu_p99_ms"] = pct(g("p99_ms"), 0.5)
    for stream in ("odometry", "imu_propagate"):
        st = [x for x in faces.get("stampage", []) if x.get("stream") == stream]
        if st:
            g = lambda k: [x[k] for x in st if x.get(k) is not None]  # noqa: E731
            out["age_%s_p50_ms" % stream] = pct(g("p50_ms"), 0.5)
            out["age_%s_p95_ms" % stream] = pct(g("p95_ms"), 0.5)
    rt = faces.get("rtf", [])
    if rt:
        r1 = [x["rtf_1s"] for x in rt if x.get("rtf_1s") is not None]
        if r1:
            out["rtf1_med"] = pct(r1, 0.5)
    return out


def main():
    res = {"prereg": "r3x supplement v1.x (r3x_final.py caliber verbatim; "
                     "first-cut deviation discarded in-ledger)",
           "rounds": {}}
    for run in RUNS:
        res["rounds"][run] = agg(run)
    keys = ["imu_p50_ms", "imu_p95_ms", "imu_p99_ms",
            "age_odometry_p50_ms", "age_odometry_p95_ms",
            "age_imu_propagate_p50_ms", "rtf1_med"]
    res["scatter"] = {}
    for k in keys:
        vals = [res["rounds"][r].get(k) for r in RUNS
                if res["rounds"][r].get(k) is not None]
        if len(vals) >= 3:
            med = float(np.median(vals))
            sc = (max(vals) - min(vals)) / med if med > 1e-9 else None
            res["scatter"][k] = {"min": round(min(vals), 4), "max": round(max(vals), 4),
                                 "med": round(med, 4),
                                 "sc": round(sc, 3) if sc is not None else None,
                                 "n": len(vals)}
    MAIN = ["imu_p50_ms", "imu_p95_ms", "imu_p99_ms", "age_odometry_p50_ms", "rtf1_med"]
    main_sc = {k: res["scatter"].get(k, {}).get("sc") for k in MAIN}
    res["judgment"] = {"main_features_sc": main_sc,
                       "stable_all_le_0p30": all(v is not None and v <= 0.30
                                                 for v in main_sc.values())}
    fn = os.path.join(OUT, "r3x_supplement_v1x.json")
    with io.open(fn, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("MAIN sc:", main_sc)
    print("stable(<=0.30):", res["judgment"]["stable_all_le_0p30"], "->", fn)


if __name__ == "__main__":
    main()
