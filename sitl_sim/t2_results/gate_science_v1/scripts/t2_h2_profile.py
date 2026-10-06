#!/usr/bin/env python3
# T2 v10.1 单元3c — H2 温和剖面对照判读 (E/W/N×plain[mild] vs SE/S×obstacles, 带内样本量如实)
import os, csv
from collections import defaultdict
HOME = os.path.expanduser("~")
rows = list(csv.DictReader(open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv")))
# 物理格去重: 剥 _R2/_L2
import re
cells = {}
for r in rows:
    tag = re.sub(r"_(R2|L2)$", "", r["tag"])
    c = cells.setdefault(tag, dict(world=r["world"], dir=r["direction"], dist=r["distance_m"],
                                   profile=r["profile"], green=False, n=0, jmax=-1.0,
                                   arrive=[float(x) for x in [r["arrive_truth"]] if x not in ("", "-1")]))
    c["n"] += 1
    if r["result"] == "PASS": c["green"] = True
    j = float(r["jump_prepost"]) if r["jump_prepost"] not in ("", "-1") else -1
    c["jmax"] = max(c["jmax"], j)
    if r["arrive_truth"] not in ("", "-1"):
        c["arrive"].append(float(r["arrive_truth"]))

def group_stats(sel, label):
    g = [c for c in cells.values() if sel(c)]
    if not g:
        print(f"{label}: n=0 (空带, 如实)")
        return
    gr = sum(1 for c in g if c["green"])
    arr = sorted(min(c["arrive"]) for c in g if c["arrive"])
    print(f"{label}: n={len(g)} 格, 绿 {gr}/{len(g)} = {gr/len(g):.0%}" +
          (f", 到位 best={arr[0]:.2f} med={arr[len(arr)//2]:.2f}" if arr else ""))

print("=== H2 温和剖面对照 (物理格口径 36 格) ===")
print("[臂1] E/W/N × plain (mild 剖面带):")
group_stats(lambda c: c["dir"] in ("E", "W", "N", "NE", "NW") and c["world"] == "plain", "  ENW×plain")
print("[臂2] SE/S × obstacles (对照带):")
group_stats(lambda c: c["dir"] in ("SE", "S", "SW") and c["world"] == "obstacles", "  S系×obstacles")
print("[臂3] 其余(参考):")
group_stats(lambda c: not (c["dir"] in ("E", "W", "N", "NE", "NW") and c["world"] == "plain") and not (c["dir"] in ("SE", "S", "SW") and c["world"] == "obstacles"), "  rest")
print("\n[注] X5 mild 剖面实际分布检查:")
prof = defaultdict(int)
for c in cells.values():
    prof[(c["profile"], c["world"])] += 1
for k, v in sorted(prof.items()):
    print(f"  profile={k[0]:5s} world={k[1]:9s}: {v} 格")
print("\n[每格明细—臂1/臂2]")
for tag, c in sorted(cells.items()):
    in1 = c["dir"] in ("E", "W", "N", "NE", "NW") and c["world"] == "plain"
    in2 = c["dir"] in ("SE", "S", "SW") and c["world"] == "obstacles"
    if in1 or in2:
        arr = min(c["arrive"]) if c["arrive"] else -1
        print(f"{'臂1' if in1 else '臂2'} {tag:12s} {c['dir']:>2s}{c['dist']:>3s} {c['world']:9s} prof={c['profile']:5s} {'GREEN' if c['green'] else 'FAIL'} jmax={c['jmax']:6.2f} arr={arr:6.2f}")
