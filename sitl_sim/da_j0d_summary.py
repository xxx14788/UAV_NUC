#!/usr/bin/env python3
# da_j0d_summary.py — δ 批 j0d 汇总(工程 v1.6 单元3 批判读件)
import glob, json, re, sys
rows = []
for d in sorted(glob.glob("/home/ghj/sitl_sim/vins_smoke_runs/run_DAn8p_*")):
    m = re.search(r"run_DAn8p_(\d+)_(\d+)", d)
    r, ts = m.group(1), m.group(2)
    try:
        j = json.load(open(d + "/j0_decomp.json"))["j0_decomp"]
        rows.append((r, ts, j["available"], round(j["j0_total_m"], 3), round(j["jump_m"], 3),
                     round(j["jump_frac"], 2), round(j["transit_m"], 3), j["n_jump_frames"], j["dominant"]))
    except Exception as e:
        rows.append((r, ts, False, "NA", "NA", "NA", "NA", "NA", str(type(e).__name__)))
print("round stamp avail j0_total jump_m jump_frac transit_m njf dominant")
for r in rows:
    print(*r)
