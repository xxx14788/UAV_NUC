#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外科恢复重放(T3 v11.1 单元1e): combo 20261010 表 run_X4_E12O_031818 j0d 三列。
纪律正源=expansion_20261009.md §2 文档化例外 2(外科恢复×3): 该轮 wa_gate_online.json
被 10-08 02:30 背书重跑器冒烟覆写(bag 已处置→decomp 降级 available=False);
处置=从 20261009 表恢复三字段(旧表值=覆写前正源判读,零重判纪律维持)。
本件=同纪律在 20261010 表的重放;验证=恢复后与 20261009 表逐位一致+其余 411 轮零触碰。
"""
import csv, os

HOME = os.path.expanduser("~")
D = HOME + "/catkin_ws/sitl_sim/t3_results"
OLD = D + "/combo_matrix_20261009_rounds.csv"
NEW = D + "/combo_matrix_20261010_rounds.csv"
TARGET = "run_X4_E12O_031818"
FIELDS = ["j0d_jump", "j0d_transit", "j0d_dom"]

old = {r["round"]: r for r in csv.DictReader(open(OLD))}
with open(NEW, encoding="utf-8-sig") as f:
    rd = csv.DictReader(f)
    hdr, rows = rd.fieldnames, list(rd)
hit = 0
for r in rows:
    if r["round"] == TARGET:
        for k in FIELDS:
            r[k] = old[TARGET][k]
        hit += 1
assert hit == 1, "target row not found"
with open(NEW, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=hdr)
    w.writeheader()
    w.writerows(rows)

# 复验: 全表与 20261009 逐位比对(旧 350 全含)
new = {r["round"]: r for r in csv.DictReader(open(NEW))}
drift = [(k, c) for k, o in old.items() for c in hdr if k in new and (o.get(c) or "") != (new[k].get(c) or "")]
print("surgical recovery applied: %s %s" % (TARGET, {k: new[TARGET][k] for k in FIELDS}))
print("post-check: old 350 vs new drifted_cells=%d (expect 0)" % len(drift))
