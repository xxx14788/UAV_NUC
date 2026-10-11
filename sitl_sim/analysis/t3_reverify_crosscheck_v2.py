#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_reverify_crosscheck_v2.py — T1 终判×T3 影子重判逐位对照（v11.40 参数化版）
v1（20261010, T3 v11.1 单元 1c）对照逻辑逐字承袭：逐轮 (hafix_lines, landed,
prereg 判定[HAFIX>=1∧landed=1]) 三元组 + 场景汇总（映射取 T1 ev_index=T1 侧正源）。
v2 变更=三路径+输出路径 CLI 化（废除硬编码 20261010 路径）；对照面仍为预注册三元组
（T1 侧 SILENT-OK 轮的 prereg 三元组按原始形态[hafix=0∧landed=1]参与对照）。
用法: t3_reverify_crosscheck_v2.py <t1_csv> <ev_index> <t3_csv> <out_csv>
"""
import csv, os, re, sys

T1CSV, EVIDX, T3CSV, OUTCSV = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

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
    rd = os.path.basename(r["ev"] or "")
    scene = ev_scene.get(rd, "?")
    mine = t3.get(rd)
    if not mine:
        rows.append((scene, rd, "NO-ROW", "", "", ""))
        continue
    t1_hafix = int(r["hafix_lines"]) if (r["hafix_lines"] or "").isdigit() else 0
    t1_landed = int(r["landed"]) if (r["landed"] or "").isdigit() else 0
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
print("\nscene summary (T1 prereg-triple basis):")
for k in sorted(sc):
    print("  %-14s %d/%d PASS" % (k, sc[k][0], sc[k][1]))
total_pass = sum(v[0] for v in sc.values())
print("\nbatch(prereg-triple): %d/%d PASS -> %s" % (
    total_pass, len(t1), "PASS" if total_pass == len(t1) else "NOT-PASS"))
with open(OUTCSV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["scene", "round", "hafix_t1/t3", "landed_t1/t3", "t1_verdict", "t3_shadow_verdict"])
    w.writerows(rows)
print("[OUT]", OUTCSV)
