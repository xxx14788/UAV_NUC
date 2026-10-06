#!/usr/bin/env python3
# T2 v10.1 单元2a — 29 非绿格病理分型 + 门后条件绿率 (预注册判据冻结)
# 格级口径: tag 为格键; 格级 result=任一轮 PASS; 格级 jump=该格全部轮 jump 最大值(最坏情形)
# 分型判据(冻结):
#   A 巨跳型   jump_max >= 5      — 估计器跳变主导; 本材料证明门不可拦
#   B 中跳型   0.5 <= jump_max < 5
#   C 健康失败 jump_max < 0.5     — VINS 无跳变, 失败=到位/导航 (门拦不住: 无病可拦)
# 门后条件绿率: 上限情形(门拦全部A) = G/(G+C); 实际(门不拦A) = G/(G+A+B+C)
import os, csv
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
rows = list(csv.DictReader(open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv")))
cells = {}
import re as _re
for r in rows:
    tag = _re.sub(r"_(R2|L2)$", "", r["tag"])
    j = float(r["jump_prepost"]) if r["jump_prepost"] not in ("", "-1") else np.nan
    green = (r["result"] == "PASS")
    c = cells.setdefault(tag, dict(world=r["world"], dir=r["direction"], dist=r["distance_m"],
                                   gyr=[float(r["gyr_peak"]) if r["gyr_peak"] else np.nan],
                                   green=False, jmax=-1.0, rounds=[]))
    c["rounds"].append(r["run_dir"].replace("run_", ""))
    if r["gyr_peak"]: c["gyr"].append(float(r["gyr_peak"]))
    if green: c["green"] = True
    if j == j: c["jmax"] = max(c["jmax"], j)

def ctype(c):
    if c["green"]: return "GREEN"
    if c["jmax"] >= 5: return "A_jump_ge5"
    if c["jmax"] >= 0.5: return "B_jump_mid"
    return "C_healthy_fail"

out = []
for tag, c in sorted(cells.items()):
    t = ctype(c)
    arrive = [float(r["arrive_truth"]) for r in rows if r["tag"] == tag and r["arrive_truth"] not in ("", "-1")]
    out.append(dict(tag=tag, type=t, world=c["world"], dir=c["dir"], dist=c["dist"],
                    gyr_med=round(float(np.median(c["gyr"])), 2),
                    jmax=round(c["jmax"], 2),
                    arrive_best=round(min(arrive), 2) if arrive else -1,
                    n_rounds=len(c["rounds"])))
with open(G + "/x5_cell_pathology.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()), delimiter="\t"); w.writeheader()
    for r in out: w.writerow(r)

n = {k: sum(1 for r in out if r["type"] == k) for k in ("GREEN", "A_jump_ge5", "B_jump_mid", "C_healthy_fail")}
print("格级分型:", n, "| total cells:", len(out))
g, a, b, c_ = n["GREEN"], n["A_jump_ge5"], n["B_jump_mid"], n["C_healthy_fail"]
print(f"门后条件绿率: 上限(门拦全部A) = {g}/{g+c_} = {g/(g+c_):.1%} | 实际(门不拦A) = {g}/{len(out)} = {g/len(out):.1%}")
# E×plain 毒格带
ep = [r for r in out if r["dir"] == "E" and r["world"] == "plain"]
print(f"\nE×plain 格带 ({len(ep)} 格):", [(r['tag'], r['type'], r['jmax']) for r in ep])
noep = [r for r in out if not (r["dir"] == "E" and r["world"] == "plain")]
g2 = sum(1 for r in noep if r["type"] == "GREEN")
print(f"剔除 E×plain 后: 绿 {g2}/{len(noep)} = {g2/len(noep):.1%}")
# 剂量面: 绿格 gyr 分布 vs A 型 gyr
gg = sorted(r["gyr_med"] for r in out if r["type"] == "GREEN")
aa = sorted(r["gyr_med"] for r in out if r["type"] == "A_jump_ge5")
print(f"\n绿格 gyr_med 全列: {gg}")
print(f"A型格 gyr_med 全列: {aa}")
print("\n=== 全格分型表 ===")
for r in out:
    print(f"{r['tag']:12s} {r['type']:13s} {r['world']:9s} {r['dir']:>2s}{r['dist']:>3s} gyr={r['gyr_med']:6.2f} jmax={r['jmax']:6.2f} arr_best={r['arrive_best']:6.2f} n={r['n_rounds']}")
