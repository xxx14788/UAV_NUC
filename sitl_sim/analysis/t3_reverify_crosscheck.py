#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1 HAFIX 复验批影子重判×T1 终判逐位对照（T3 v11.1 单元 1c 收尾件）
正源: T1=reverify_verdict_v1139.csv(20 轮终判)+ev_index.txt(场景映射)
      T3=t3_2d_hafix_rejudge_20261010.csv(影子重判,全量 1[6-9]* 含增量批)
对照面: 逐轮 (hafix_lines, landed, prereg 判定[HAFIX>=1∧landed=1]) 三元组
+场景汇总(映射取 T1 ev_index=T1 侧正源,我侧 summary.txt 缺=如实)
"""
import csv, os, re

HOME = os.path.expanduser("~")
T1CSV = HOME + "/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_reverify/reverify_verdict_v1139.csv"
EVIDX = HOME + "/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_reverify/ev_index.txt"
T3CSV = HOME + "/catkin_ws/sitl_sim/t3_results/t2d_hafix_rejudge_20261010.csv"

# T1 ev_index: "S1_hover_1m r1 final ... ev=/path/run_XXX"
ev_scene = {}
for ln in open(EVIDX, errors="replace"):
    m = re.match(r"(\S+)\s+r(\d+)\s+final\s+drill_rc=(\d+)\s+ev=\S*/(run_\S+)", ln.strip())
    if m:
        ev_scene[m.group(4)] = m.group(1)

t1 = list(csv.DictReader(open(T1CSV, encoding="utf-8-sig")))
t3 = {os.path.basename(r["round"]): r for r in csv.DictReader(open(T3CSV, encoding="utf-8-sig"))}

match3 = mismatch = 0
rows = []
for r in t1:
    rd = os.path.basename(r["ev"])
    scene = ev_scene.get(rd, "?")
    mine = t3.get(rd)
    if not mine:
        rows.append((scene, rd, "NO-ROW", "", "", ""))
        continue
    t1_hafix = int(r["hafix_lines"] or 0)
    t1_landed = int(r["landed"] or 0)
    t1_pass = (t1_hafix >= 1 and t1_landed == 1)
    t3_hafix = int(mine.get("hafix_n") or 0)
    t3_landed_val = (mine.get("landed") or "").strip()
    t3_landed = 1 if t3_landed_val.startswith("1") else 0
    t3_pass = (t3_hafix >= 1 and t3_landed == 1)
    agree = (t1_pass == t3_pass) and (t1_hafix >= 1) == (t3_hafix >= 1) and t1_landed == t3_landed
    if agree:
        match3 += 1
    else:
        mismatch += 1
    rows.append((scene, rd.split("_")[-1], "hafix %d/%d" % (t1_hafix, t3_hafix),
                 "landed %d/%d" % (t1_landed, t3_landed),
                 "PASS" if t1_pass else "FAIL", "PASS" if t3_pass else "FAIL"))

from collections import defaultdict
sc = defaultdict(lambda: [0, 0])
for scene, _, _, _, p1, p3 in rows:
    if p1 == "PASS":
        sc[scene][0] += 1
    sc[scene][1] += 1
print("per-round agreement: %d/%d (mismatch=%d)" % (match3, len(t1), mismatch))
print("\nscene summary (T1 verdict basis):")
for k in sorted(sc):
    print("  %-14s %d/%d PASS" % (k, sc[k][0], sc[k][1]))
total_pass = sum(v[0] for v in sc.values())
print("\nbatch: %d/%d PASS -> %s (T1 final verdict: 3/20 NOT-PASS)" % (
    total_pass, len(t1), "PASS" if total_pass == len(t1) else "NOT-PASS"))
for m in [r for r in rows if True]:
    pass
# 明细落盘
out = HOME + "/catkin_ws/sitl_sim/t3_results/t2d_hafix_reverify_crosscheck_20261010.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["scene", "round", "hafix_t1/t3", "landed_t1/t3", "t1_verdict", "t3_shadow_verdict"])
    w.writerows(rows)
print("[OUT]", out)
