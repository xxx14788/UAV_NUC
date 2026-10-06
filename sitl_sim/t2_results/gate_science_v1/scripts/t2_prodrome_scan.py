#!/usr/bin/env python3
# T2 v10.1 单元3b — 前兆签名逐轮标注表 (t2_prodrome_scan v1, 预注册口径)
# 分类判据(冻结):
#   发作(jump) = diag 10Hz |dP|>1m 存在 或 passmap jump_prepost>=0.5
#   surge 达标 = cost streak>=5 @R5 (复现门语义; R10 列并记)
#   TYPE-A 前兆型  : surge达标 且 (t_surge 早于 t_jump-3s 或 早于轮失败)
#   TYPE-B 迟到/无关: surge达标 但 t_surge 晚于 t_jump (果非因) 或无jump
#   TYPE-C 静默型  : 无 surge 达标(全指标静默)
#   绿轮单列 TYPE-G(生理抬升: 绿轮 surge 达标也属正常)
import os, csv
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f): pm[row["run_dir"]] = row
surge = {r["round"]: r for r in csv.DictReader(open(G + "/x5_surge.tsv"), delimiter="\t")}
met = {r["round"]: r for r in csv.DictReader(open(G + "/x5_metrics.tsv"), delimiter="\t")}
def fl(x):
    try: return float(x)
    except: return float("nan")

out = []
for name, s in surge.items():
    p = pm.get("run_" + name)
    if not p: continue
    m = met.get(name, {})
    jp = fl(p.get("jump_prepost", "nan"))
    tj = fl(s.get("t_jump", "nan"))
    s5 = int(s.get("c_s5_max", 0)); t5_5 = fl(s.get("c_s5_t5", "nan"))
    s10 = int(s.get("c_s10_max", 0)); t5_10 = fl(s.get("c_s10_t5", "nan"))
    b3 = int(s.get("b_s3_max", 0)); bt5 = fl(s.get("b_s3_t5", "nan"))
    jump = (tj == tj) or (jp == jp and jp >= 0.5)
    surge5 = s5 >= 5
    if p["result"] == "PASS":
        typ = "G_green"
    elif surge5 and tj == tj and t5_5 == t5_5 and (tj - t5_5) >= 3.0:
        typ = "A_prodrome"
    elif surge5 and not jump:
        typ = "B_surge_nojump"
    elif surge5:
        typ = "B_late_or_unrelated"
    else:
        typ = "C_silent"
    out.append(dict(round=name, verdict=p["result"], jump_prepost=("%.2f" % jp) if jp == jp else "-1",
                    t_jump_diag=("%.1f" % tj) if tj == tj else "NA",
                    c_surge5max=s5, c_surge5_t=("%.1f" % t5_5) if t5_5 == t5_5 else "NA",
                    c_surge10max=s10,
                    b_surge3max=b3, b_surge3_t=("%.1f" % bt5) if bt5 == bt5 else "NA",
                    bas_onset=m.get("onset_bas", "NA"),
                    cost_lift=m.get("lift_cost", "NA"),
                    type=typ))
with open(G + "/x5_prodrome_scan.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()), delimiter="\t"); w.writeheader()
    for r in out: w.writerow(r)
from collections import Counter
cnt = Counter(r["type"] for r in out)
print("=== t2_prodrome_scan 分类统计 (轮级, passmap 50 评估轮) ===")
for k, v in sorted(cnt.items()):
    print(f"  {k}: {v}")
fail = [r for r in out if r["verdict"] == "FAIL"]
cntf = Counter(r["type"] for r in fail)
print("FAIL 轮分类:", dict(cntf))
print("\n=== A 型(前兆可测)与 C 型(静默)明细 ===")
for r in out:
    if r["type"] in ("A_prodrome", "C_silent") and r["verdict"] == "FAIL":
        print(f"{r['type']:12s} {r['round']:22s} jump={r['jump_prepost']:>6} t_j={r['t_jump_diag']:>6} c5={r['c_surge5max']:>3}@{r['c_surge5_t']:>6} b3={r['b_surge3max']:>3}@{r['b_surge3_t']:>6} bas_onset={r['bas_onset']:>6} lift={r['cost_lift']}")
