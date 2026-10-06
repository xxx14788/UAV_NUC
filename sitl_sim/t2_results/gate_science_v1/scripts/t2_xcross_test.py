#!/usr/bin/env python3
# T2 v10.1 2b 补充 — 视差交叉面 ([T2xcross] rel) 判别力快测
import os, re, glob, csv
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f): pm[row["run_dir"]] = row
re_x = re.compile(r"\[T2xcross\] t=([\d.]+) id=\d+ est=([\d.eE+-]+) svd=([\d.eE+-]+) rel=([\d.eE+-]+) track=(\d+)")
re_d = re.compile(r"\[T2depth\] t=([\d.]+) id=\d+ src=(\S+).*depth=([\d.eE+-]+)")
rows = []
for R_dir in sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*")):
    name = os.path.basename(R_dir)[len("run_"):]
    p = pm.get("run_" + name)
    if not p: continue
    rels_t, rels_g, negd = [], [], []
    try:
        with open(os.path.join(R_dir, "simvins.log"), errors="replace") as f:
            for line in f:
                if "[T2xcross]" in line:
                    m = re_x.search(line)
                    if m:
                        t, rel = float(m.group(1)), float(m.group(4))
                        if rel == rel and 0 <= rel <= 10:
                            (rels_g if t <= 26 else rels_t).append(rel)
                elif "[T2depth]" in line:
                    m = re_d.search(line)
                    if m:
                        d = float(m.group(3))
                        negd.append(1 if d <= 0 else 0)
    except FileNotFoundError:
        continue
    j = float(p["jump_prepost"]) if p["jump_prepost"] not in ("", "-1") else np.nan
    grp = "GREEN" if p["result"] == "PASS" else ("JUMP" if (j == j and j >= 5) else "OFAIL")
    rows.append(dict(round=name, world=p["world"], grp=grp,
                     x_gnd_p50=np.median(rels_g) if rels_g else np.nan,
                     x_gnd_p90=np.percentile(rels_g, 90) if rels_g else np.nan,
                     x_gnd_max=np.max(rels_g) if rels_g else np.nan,
                     x_fly_p50=np.median(rels_t) if rels_t else np.nan,
                     x_fly_p90=np.percentile(rels_t, 90) if rels_t else np.nan,
                     negd_frac=np.mean(negd) if negd else np.nan))
with open(G + "/x5_xcross.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t"); w.writeheader()
    for r in rows: w.writerow(r)
def auc(pos, neg):
    pos = [x for x in pos if x == x]; neg = [x for x in neg if x == x]
    if not pos or not neg: return float("nan")
    w_ = sum((1 if a > b else 0.5 if a == b else 0) for a in pos for b in neg)
    return w_ / (len(pos) * len(neg))
print("=== 视差交叉面: 起飞前(gnd<=t26)/飞行中(fly) rel 分布 与 判别力 ===")
for m, lbl in (("x_gnd_p50","gnd_p50"),("x_gnd_p90","gnd_p90"),("x_gnd_max","gnd_max"),("x_fly_p90","fly_p90"),("negd_frac","negd_frac")):
    for world in ("obstacles","plain"):
        g=[r[m] for r in rows if r["world"]==world and r["grp"]=="GREEN"]
        jj=[r[m] for r in rows if r["world"]==world and r["grp"]=="JUMP"]
        o=[r[m] for r in rows if r["world"]==world and r["grp"]=="OFAIL"]
        if not g or not jj: continue
        print(f"{world:9s} {lbl:9s} G_med={np.median(g):8.4f} J_med={np.median(jj):8.4f} O_med={np.median(o) if o else float('nan'):8.4f} AUC(J/G)={auc(jj,g):5.2f} AUC(J/O)={auc(jj,o) if o else float('nan'):5.2f}")
