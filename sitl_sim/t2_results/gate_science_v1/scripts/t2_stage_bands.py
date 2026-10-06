#!/usr/bin/env python3
# T2 v10.1 单元2a/2b 收尾 — 健康轮分阶段分位带 + init 段指标阈值混淆矩阵
import os, csv, glob
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f): pm[row["run_dir"]] = row

# --- 1) 健康轮分阶段分位带 (从 extract csv) ---
def stage_bands():
    out = {}
    for world in ("obstacles", "plain"):
        acc = {"INIT": [], "GROUND": [], "TRANSIT": [], "GOAL": [], "POST": []}
        accb = {k: [] for k in acc}
        for name, p in pm.items():
            if p["result"] != "PASS" or p["world"] != world: continue
            f = G + "/extract/%s.csv" % name.replace("run_", "")
            if not os.path.exists(f): continue
            rows = list(csv.DictReader(open(f)))
            ph = np.array([r["phase"] for r in rows])
            cost = np.array([float(r["cost"]) if r["cost"] else np.nan for r in rows])
            bas = np.array([float(r["bas"]) if r["bas"] else np.nan for r in rows])
            for s in acc:
                m = ph == s
                if m.sum() > 10:
                    acc[s].append(np.nanpercentile(cost[m], 50))
                    acc[s].append(np.nanpercentile(cost[m], 90))
                    accb[s].append(np.nanpercentile(bas[m], 50))
                    accb[s].append(np.nanpercentile(bas[m], 90))
        out[world] = (acc, accb)
    return out

print("=== 健康轮(绿)分阶段分位带: cost p50[p50,p90 over rounds] ===")
for world, (acc, accb) in stage_bands().items():
    print(f"--- {world} ---")
    for s in ("INIT", "GROUND", "TRANSIT", "GOAL", "POST"):
        v = acc[s]; b = accb[s]
        if not v: continue
        c_lo, c_hi = np.percentile(v, 10), np.percentile(v, 90)
        b_lo, b_hi = np.percentile(b, 10), np.percentile(b, 90)
        print(f"{s:8s} cost_band=[{c_lo:8.1f},{c_hi:8.1f}] (p50med={np.median(v):8.1f}) | bas_band=[{b_lo:.4f},{b_hi:.4f}] (p50med={np.median(b):.4f})")

# --- 2) init 段指标阈值混淆矩阵 (2b) ---
im = list(csv.DictReader(open(G + "/x5_init_metrics.tsv"), delimiter="\t"))
def fl(x):
    try: return float(x)
    except: return np.nan
print("\n=== 2b init 段阈值候选混淆矩阵 (全库不分世界 / 分世界) ===")
for m, ths in (("M4_gnd_cost", (400, 600, 800)), ("M2_gnd_bas", (0.15, 0.25, 0.4)), ("M1_init_final", (1000, 2000, 5000))):
    print(f"--- {m} ---")
    for th in ths:
        for scope, sel in (("all", lambda r: True),):
            g = [r for r in im if r["grp"] == "GREEN" and sel(r)]
            j = [r for r in im if r["grp"] == "JUMP" and sel(r)]
            gd = sum(1 for r in g if fl(r[m]) > th)
            jd = sum(1 for r in j if fl(r[m]) > th)
            print(f"  th>{th}: GREEN fire {gd}/{len(g)} | JUMP fire {jd}/{len(j)}")

# --- 3) ROC 数据包清单 ---
print("\n=== ROC 数据包文件清单 (喂 T1 单元2 重放) ===")
for f_ in ("x5_metrics.tsv", "x5_surge.tsv", "x5_init_metrics.tsv", "x5_xcross.tsv", "x5_cell_pathology.tsv", "x5_integrity.tsv"):
    p = G + "/" + f_
    print(f"{f_:24s} {os.path.getsize(p) if os.path.exists(p) else 'MISSING'} bytes")
print("extract/: ", len(glob.glob(G + "/extract/*.csv")), "per-round csv")
