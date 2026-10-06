#!/usr/bin/env python3
# T2 v10.1 单元3a — X5 j0d 统计表 (59 轮独立产物消费; @T3 消费口径)
# 分类(承 T3 v9.9 三列, 表头声明): 风暴=T2fail>0 / 净轮=T2fail=0∧j0<0.5 / 中漂移=T2fail=0∧j0>=0.5
# T2fail = simvins.log 内 [T2fail] 行数 (failureDetection 触发)
import os, re, glob, csv, json
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f): pm[row["run_dir"]] = row
rows = []
for p in sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*/j0_decomp.json")):
    rund = os.path.dirname(p)
    name = os.path.basename(rund)[len("run_"):]
    try:
        d = json.load(open(p)).get("j0_decomp", {})
    except Exception:
        continue
    if not d.get("available"): 
        rows.append(dict(round=name, avail=0)); continue
    t2fail = 0
    try:
        with open(os.path.join(rund, "simvins.log"), errors="replace") as f:
            t2fail = sum(1 for line in f if "[T2fail]" in line)
    except FileNotFoundError:
        pass
    j0t = d.get("j0_total_m")
    cat = "风暴" if t2fail > 0 else ("净轮" if (j0t is not None and j0t < 0.5) else "中漂移")
    pr = pm.get("run_" + name, {})
    rows.append(dict(round=name, avail=1, verdict=pr.get("result", "NOTINMAP"),
                     jump_prepost=pr.get("jump_prepost", ""), t2fail=t2fail,
                     j0_total=round(j0t, 4) if j0t is not None else None,
                     jump_m=round(d.get("jump_m", 0), 4), transit_m=round(d.get("transit_m", 0), 4),
                     jump_frac=round(d.get("jump_frac", 0), 4),
                     dominant=d.get("dominant", ""), n_jump_frames=d.get("n_jump_frames", ""),
                     cat=cat))
with open(G + "/x5_j0d_stats.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t"); w.writeheader()
    for r in rows: w.writerow(r)
av = [r for r in rows if r.get("avail")]
from collections import Counter
cnt = Counter(r["cat"] for r in av)
dom = Counter(r["dominant"] for r in av)
print(f"j0d 可用轮: {len(av)}/{len(rows)}")
print("三列分类:", dict(cnt))
print("dominant 分布:", dict(dom))
# H3: transit 主导占比 (在非绿轮中)
fail = [r for r in av if r.get("verdict") == "FAIL"]
domf = Counter(r["dominant"] for r in fail)
print(f"\nH3 transit 主导占比: 全轮 {dom.get('transit',0)}/{len(av)} = {dom.get('transit',0)/len(av):.0%} | 非绿轮 {domf.get('transit',0)}/{len(fail)} = {domf.get('transit',0)/len(fail) if fail else 0:.0%}")
# 与 passmap jump_prepost 的对账 (巨跳轮的 j0d 形态)
print("\n巨跳轮(jump_prepost>=5) j0d 形态:")
for r in av:
    try:
        if r.get("jump_prepost") and float(r["jump_prepost"]) >= 5:
            print(f"  {r['round']:22s} jmax={float(r['jump_prepost']):6.2f} j0d: jump={r['jump_m']:7.3f} transit={r['transit_m']:7.3f} dom={r['dominant']:7s} t2fail={r['t2fail']}")
    except Exception:
        pass
