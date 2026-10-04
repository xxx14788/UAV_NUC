#!/usr/bin/env python3
# e5b_extract.py — E-5b observation arm: ev activation-window segmentation
# from ulog (design: e5b_ev_hpos_observation_design.md; faces P1-P3 prereg).
# Usage: e5b_extract.py ULG [ULG...] -> jsonl rows to stdout
import json
import math
import os
import sys

from pyulog import ULog


def segs(ts, vals, active):
    """contiguous active windows [(t0,t1,n)] from timestamped nonzero flags"""
    out = []
    cur = None
    for t, v in zip(ts, vals):
        a = active(v)
        if a and cur is None:
            cur = [t, t, 1]
        elif a:
            cur[1] = t
            cur[2] += 1
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def fmt_secs(t, t0):
    return round((t - t0) / 1e6, 3) if t0 is not None else None


def process(path):
    u = ULog(path, None)
    t0 = None
    row = {"ulg": path, "basename": os.path.basename(path)}
    ip = u.initial_parameters
    row["params"] = {k: ip.get(k) for k in ("EKF2_EV_CTRL", "EKF2_GPS_CTRL")}
    inv = [d for d in u.data_list if d.name == "estimator_innovations"]
    var = [d for d in u.data_list if d.name == "estimator_innovation_variances"]
    if inv:
        di = inv[0].data
        ts = [float(x) for x in di.get("timestamp", [])]
        if ts:
            t0 = ts[0]
            row["t_end_s"] = fmt_secs(ts[-1], t0)
        row["channels"] = {}
        for ch in ("ev_hpos[0]", "ev_vpos", "ev_hvel[0]", "ev_yaw"):
            if ch not in di:
                continue
            # array channel pairs merge: use max-abs across axis pair
            base = ch[:-3] if ch.endswith("[0]") else ch
            keys = [base + "[0]", base + "[1]"] if ch.endswith("[0]") else [ch]
            keys = [k for k in keys if k in di]
            tsn = [float(x) for x in di.get("timestamp", [])]
            iv = [max(abs(float(di[k][i])) for k in keys) for i in range(len(tsn))]
            windows = segs(tsn, iv, lambda v: v != 0.0)
            n_active = sum(1 for x in iv if x != 0.0)
            # merge windows separated by <0.5s (sampling dropout, not extinction)
            merged = []
            for w in windows:
                if merged and w[0] - merged[-1][1] < 0.5:
                    merged[-1] = (merged[-1][0], w[1], merged[-1][2] + w[2])
                else:
                    merged.append(list(w))
                    merged[-1] = tuple(merged[-1])
            row["channels"][ch] = {
                "n": len(iv), "n_active": n_active,
                "coverage_active": round(n_active / len(iv), 4) if iv else None,
                "windows": [[fmt_secs(w[0], t0), fmt_secs(w[1], t0), w[2]] for w in merged],
                "n_windows": len(merged),
                "extinction_ends_s": [fmt_secs(w[1], t0) for w in merged],
            }
    vo = [d for d in u.data_list if d.name == "vehicle_visual_odometry"]
    if vo:
        d = vo[0].data
        row["vo_input"] = {"n": len(d.get("timestamp", []))}
        if "position_variance" in d:
            pv = [float(x) for x in d["position_variance"]]
            row["vo_input"]["pv_nonzero_frac"] = round(
                sum(1 for x in pv if x != 0.0) / len(pv), 4) if pv else None
    # H-3 (2026-10-04): cs_ev_* true source = estimator_aid_src_ev_*.fused
    # (innovations has NO ev_yaw key — only hpos/hvel/vpos/vvel; historical
    # "cs_ev_yaw" claims must come from aid_src fused fractions)
    aid = {}
    for d in u.data_list:
        if d.name.startswith("estimator_aid_src") and "fused" in d.data:
            f = d.data["fused"]
            fn = int(sum(1 for x in f if x))
            aid[d.name.replace("estimator_aid_src_", "")] = {
                "fused_n": fn, "n": len(f),
                "fused_frac": round(fn / len(f), 4) if len(f) else None}
    if aid:
        row["aid_src"] = aid
    return row


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            print(json.dumps(process(p), ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"ulg": p, "error": str(e)[:120]}))
