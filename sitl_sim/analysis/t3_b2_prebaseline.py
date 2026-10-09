#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_b2_prebaseline.py — M3′ 前基线转录 v1.0（T3 v10.7 B2 遗留件；v11.1 单元 5 消费）
契约原文（plans_T3_v10.7.md 尾件表 B2）：M3 v1.1 十八轮格级数字→grid,round,j0,four_green,t2fail
转录+md5 记档；源=t3_results/m3_batch_report.csv（在盘）。
映射：grid=cell, round=round, j0=jump(jump_prepost 口径), four_green=verdict(PASS→1/FAIL→0),
t2fail=源无此列→空(如实,不编造;附 iqg_rejects 原列供参考)。脏行"0"(源解析残留)剔除如实注记。
"""
import csv, hashlib, os

SRC = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results/m3_batch_report.csv")
OUT = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results/m3_prebaseline_v1.csv")

rows, dropped = [], 0
VALID_GRIDS = {"E8P", "S12P", "S8O", "E12O", "NE8O", "N8P"}
for r in csv.DictReader(open(SRC)):
    if (r.get("cell") or "").strip() not in VALID_GRIDS or not (r.get("round") or "").strip():
        dropped += 1
        continue
    rows.append(dict(
        grid=r["cell"].strip(), round=r["round"].strip(), tag=r["tag"].strip(),
        j0=r["jump"].strip(), four_green=("1" if r["verdict"].strip() == "PASS" else "0"),
        t2fail="",  # 源无此列——如实留空
        verdict=r["verdict"].strip(), arrive=r["arrive"].strip(),
        disarm=r["disarm"].strip(), iqg_rejects=r["iqg_rejects"].strip(),
    ))
rows.sort(key=lambda x: (["E8P", "S12P", "S8O", "E12O", "NE8O", "N8P"].index(x["grid"]), int(x["round"])))
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
md5_src = hashlib.md5(open(SRC, "rb").read()).hexdigest()
md5_out = hashlib.md5(open(OUT, "rb").read()).hexdigest()
green = sum(1 for r in rows if r["four_green"] == "1")
print("source md5=%s -> transcript md5=%s" % (md5_src, md5_out))
print("rows=%d (dropped dirty=%d) four_green=1: %d/%d" % (len(rows), dropped, green, len(rows)))
print("[OUT]", OUT)
