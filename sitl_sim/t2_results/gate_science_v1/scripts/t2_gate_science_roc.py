#!/usr/bin/env python3
# T2 v10.1 单元2a — 门视角 ROC + 病理分型 (预注册判据消费)
# 读 x5_surge.tsv + passmap, 输出:
#   1) (R,N) 网格: 绿轮误拦率 vs 巨跳轮触发率 -> ROC 面
#   2) 29 非绿格病理分型 + 门后条件绿率
#   3) 双指标(cost 主+Bas 副)联合面
import os, csv
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"

pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f):
        pm[row["run_dir"]] = row
surge = list(csv.DictReader(open(G + "/x5_surge.tsv"), delimiter="\t"))
met = {r["round"]: r for r in csv.DictReader(open(G + "/x5_metrics.tsv"), delimiter="\t")}

def fl(x):
    try: return float(x)
    except: return float("nan")

# 轮归类: GREEN=passmap PASS; JUMP=FAIL&jump>=5; OTHERFAIL
greens, jumps, otherf = [], [], []
for r in surge:
    p = pm.get("run_" + r["round"])
    if not p: continue
    if p["result"] == "PASS": greens.append(r)
    else:
        j = fl(p.get("jump_prepost", "nan"))
        if j == j and j >= 5: jumps.append(r)
        else: otherf.append(r)
print(f"greens={len(greens)} jumps={len(jumps)} otherfail={len(otherf)}")

print("\n=== 门视角 ROC: cost surge streak >= N @ ratio R ===")
print("(误拦=绿轮触发率[越低越好] | 拦截=巨跳轮触发率[越高越好])")
print(f"{'R':>5} {'N':>3} | {'green_fire':>10} {'jump_fire':>9} | {'otherf_fire':>11}")
for R in (3.0, 5.0, 10.0):
    for N in (3, 5, 8):
        gf = sum(1 for r in greens if int(r["c_s%d_max" % R]) >= N)
        jf = sum(1 for r in jumps if int(r["c_s%d_max" % R]) >= N)
        of = sum(1 for r in otherf if int(r["c_s%d_max" % R]) >= N)
        print(f"{R:>5} {N:>3} | {gf:>4}/{len(greens):<5} {jf:>3}/{len(jumps):<6} | {of:>4}/{len(otherf)}")

print("\n=== 门视角 ROC: Bas surge streak >= N @ ratio R ===")
for R in (2.0, 3.0, 5.0):
    for N in (3, 5, 8):
        gf = sum(1 for r in greens if int(r["b_s%d_max" % R]) >= N)
        jf = sum(1 for r in jumps if int(r["b_s%d_max" % R]) >= N)
        of = sum(1 for r in otherf if int(r["b_s%d_max" % R]) >= N)
        print(f"{R:>5} {N:>3} | {gf:>4}/{len(greens):<5} {jf:>3}/{len(jumps):<6} | {of:>4}/{len(otherf)}")

print("\n=== 巨跳轮逐轮: surge 触发时刻 vs jump 时刻 (前兆时序) ===")
for r in jumps:
    p = pm["run_" + r["round"]]
    tj = r["t_jump"]
    line = f"{r['round']:22s} jump={fl(p['jump_prepost']):6.2f} t_jump={tj:>6}"
    for R in (5.0, 10.0):
        line += f" | c@{R:g}:max={r['c_s%d_max' % R]:>3} t5={r['c_s%d_t5' % R]:>6}"
    line += f" | b@3:max={r['b_s3_max']:>3} t5={r['b_s3_t5']:>6}"
    print(line)

print("\n=== 绿轮 surge 底噪 (为何误拦/不误拦) ===")
for r in greens:
    line = f"{r['round']:22s} t_jump={r['t_jump']:>6} n_jump={r['n_jump']:>2}"
    for R in (5.0, 10.0):
        line += f" | c@{R:g}:max={r['c_s%d_max' % R]:>3}"
    line += f" | b@3:max={r['b_s3_max']:>3}"
    print(line)
