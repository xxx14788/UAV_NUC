#!/usr/bin/env python3
# T2 v10.1 单元2b — 起飞前门材料: init 段健康度指标判别力 (预注册)
# 问题: 病轮 init 段是否已可分? (三层防线第一道可行性检验)
# 指标(预注册, 全部取自 init 完成 t0 后的地面静止窗):
#   M1 init_final_cost = 首个 NON_LINEAR 求解的 final_cost (init 时刻收敛残差)
#   M2 gnd_bas         = [t0, t0+15] |Bas| 中位
#   M3 gnd_track       = [t0, t0+15] track 中位
#   M4 gnd_cost        = [t0, t0+15] cost 中位 (t15 证据的直接检验)
#   M5 init_dur        = VINS 启动到首个 NON_LINEAR 求解的时长
# 判别对象: GREEN vs JUMP(>=5) vs OTHERFAIL, 按世界分层
import os, re, glob, csv
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"

pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f):
        pm[row["run_dir"]] = row

re_line0 = re.compile(r"VINS init 完成 \(\+(\d+)s\)")
rows = []
for R_dir in sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*")):
    name = os.path.basename(R_dir)[len("run_"):]
    p = pm.get("run_" + name)
    if not p: continue
    # 从 extract csv 读
    fcsv = G + "/extract/%s.csv" % name
    if not os.path.exists(fcsv): continue
    t, cost, bas, trk, vel, ph = [], [], [], [], [], []
    with open(fcsv) as f:
        for row in csv.DictReader(f):
            t.append(float(row["t"])); trk.append(float(row["track"])); vel.append(float(row["vel"])); ph.append(row["phase"])
            cost.append(float(row["cost"]) if row["cost"] else np.nan)
            bas.append(float(row["bas"]) if row["bas"] else np.nan)
    t = np.array(t); cost = np.array(cost); bas = np.array(bas); trk = np.array(trk); vel = np.array(vel)
    # init done = 首个有 cost 的样本
    ok = ~np.isnan(cost)
    if not ok.any(): continue
    t0 = t[ok][0]
    m_gnd = (t >= t0) & (t <= t0 + 15)
    init_dur = t0  # 近似: VINS log t=0 起
    first_final = np.nan
    # init 终值 final_cost: 用首个求解 final_cost, 从原始 log 取
    with open(os.path.join(R_dir, "simvins.log"), errors="replace") as f:
        for line in f:
            if "[T2slv]" in line and "phase=1" in line:
                mm = re.search(r"final_cost=([\d.eE+-]+)", line)
                if mm: first_final = float(mm.group(1))
                break
    j = float(p.get("jump_prepost")) if p.get("jump_prepost") not in ("", "-1", None) else np.nan
    grp = "GREEN" if p["result"] == "PASS" else ("JUMP" if (j == j and j >= 5) else "OFAIL")
    rows.append(dict(round=name, world=p["world"], grp=grp, jump=j,
                     M1_init_final=first_final,
                     M2_gnd_bas=float(np.median(bas[m_gnd])) if m_gnd.sum() > 5 else np.nan,
                     M3_gnd_track=float(np.median(trk[m_gnd])) if m_gnd.sum() > 5 else np.nan,
                     M4_gnd_cost=float(np.nanmedian(cost[m_gnd])) if m_gnd.sum() > 5 else np.nan,
                     M5_init_dur=float(init_dur),
                     arrive=float(p.get("arrive_truth")) if p.get("arrive_truth") not in ("", "-1", None) else np.nan))

with open(G + "/x5_init_metrics.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t"); w.writeheader()
    for r in rows: w.writerow(r)
print("rows:", len(rows))

def auc(pos, neg):
    pos = [x for x in pos if x == x]; neg = [x for x in neg if x == x]
    if not pos or not neg: return float("nan")
    # Mann-Whitney AUC: P(pos > neg)
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b: wins += 1
            elif a == b: ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))

print("\n=== 起飞前指标判别力 (JUMP 为病, GREEN 为健; AUC>0.5=JUMP 值偏大) ===")
print(f"{'world':9s} {'metric':14s} {'GREEN med':>10} {'JUMP med':>10} {'OFAIL med':>10} {'AUC(J/G)':>8} {'AUC(J/O)':>8}")
for world in ("obstacles", "plain"):
    for m, lbl in (("M1_init_final", "init_final"), ("M2_gnd_bas", "gnd_bas"), ("M3_gnd_track", "gnd_track"),
                   ("M4_gnd_cost", "gnd_cost"), ("M5_init_dur", "init_dur_s")):
        g = [r[m] for r in rows if r["world"] == world and r["grp"] == "GREEN"]
        j = [r[m] for r in rows if r["world"] == world and r["grp"] == "JUMP"]
        o = [r[m] for r in rows if r["world"] == world and r["grp"] == "OFAIL"]
        if not j or not g:
            print(f"{world:9s} {lbl:14s} n_g={len(g)} n_j={len(j)} n_o={len(o)}  (样本不足)")
            continue
        print(f"{world:9s} {lbl:14s} {np.median(g):10.4g} {np.median(j):10.4g} {np.median(o) if o else float('nan'):10.4g} {auc(j,g):8.2f} {auc(j,o) if o else float('nan'):8.2f}")

print("\n=== 全轮明细 (按世界/组) ===")
for r in sorted(rows, key=lambda x: (x["world"], x["grp"], x["round"])):
    print(f"{r['world']:9s} {r['grp']:5s} {r['round']:22s} jump={r['jump'] if r['jump']==r['jump'] else -1:6.2f} init_fin={r['M1_init_final']:10.4g} gnd_bas={r['M2_gnd_bas']:8.4g} gnd_trk={r['M3_gnd_track']:6.0f} gnd_cost={r['M4_gnd_cost']:9.4g} init_t={r['M5_init_dur']:6.1f} arr={r['arrive'] if r['arrive']==r['arrive'] else -1:6.2f}")
