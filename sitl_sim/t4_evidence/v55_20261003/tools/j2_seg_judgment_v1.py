#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# j2_seg_judgment_v1.py — 依 docs/t4_j2_seg_judgment_prereg_v1.md 协议机械出 seg 级判定表（36 位）
# 输入: sitl_sim/t4_evidence/v55_20261003/derived/pool_m1m2_byseg.csv (49d2ac3 正源)
# 输出: 同目录 j2_seg_judgment_v1.csv + j2_seg_judgment_v1.md（含门值表）
# 计算口径（prereg §2a）：一切门值与比较用十进制定点（Decimal，csv 字符串直读）；
# CI 跨门=严格不等式（CI_lo < 门 < CI_hi），门恰等于边界=不跨不降级。
# 纯文件 IO；零重放零提帧；判定比较全精度，显示 4 位舍入。
import csv, io
from decimal import Decimal as D

BASE = "/home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived"
CSV_IN = BASE + "/pool_m1m2_byseg.csv"
OUT_CSV = BASE + "/j2_seg_judgment_v1.csv"
OUT_MD = BASE + "/j2_seg_judgment_v1.md"
BAGS = ["U3PG_210307", "U3PH_210708", "U3PO_211438", "U3PR1_212450", "U3PR2_213717", "X1final_173345"]
METRICS = ["M1_supply_frac", "M2_grid4x4_occupancy_frac"]
SEGS = ["0", "1", "2"]


def quantile_linear(vals, p):
    # vals: Decimal 列表; p: Decimal（prereg §2a 十进制定点）
    v = sorted(vals)
    h = D(len(v) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(v) - 1)
    frac = h - D(lo)
    return v[lo] * (D(1) - frac) + v[hi] * frac


def f4(x):
    return "%.4f" % float(x)


rows = list(csv.DictReader(open(CSV_IN, encoding="utf-8")))
data = {(r["bag"], r["seg"], r["metric"]): r for r in rows}

judgments = []  # (bag, seg, metric, cell, ci_lo, ci_hi, gate_p10, gate_p50, state, downgraded)
for metric in METRICS:
    for seg in SEGS:
        cells = {b: D(data[(b, seg, metric)]["p50"]) for b in BAGS}
        vals = [cells[b] for b in BAGS]
        p10 = quantile_linear(vals, D("0.10"))
        p50 = quantile_linear(vals, D("0.50"))
        for b in BAGS:
            r = data[(b, seg, metric)]
            c = D(r["p50"])
            lo = D(r["p50_ci95_lo"])
            hi = D(r["p50_ci95_hi"])
            if c >= p50:
                state = "前位"
            elif c >= p10:
                state = "中位带"
            else:
                state = "低位旗"
            downgraded = "否"
            if state != "中位带":
                gate = p50 if state == "前位" else p10
                if lo < gate < hi:
                    state = "中位带"
                    downgraded = "是"
            judgments.append((b, seg, metric, c, lo, hi, p10, p50, state, downgraded))

with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["bag", "seg", "metric", "cell_p50", "ci95_lo", "ci95_hi",
                "gate_p10", "gate_p50", "state", "ci_downgraded"])
    for j in judgments:
        w.writerow([j[0], j[1], j[2]] + [str(x) for x in j[3:8]] + [j[8], j[9]])

from collections import Counter
cnt = Counter(j[8] for j in judgments)
dg = [(j[0], j[1], j[2]) for j in judgments if j[9] == "是"]
low = [(j[0], j[1], j[2], j[3]) for j in judgments if j[8] == "低位旗"]

md = io.StringIO()
md.write("# J2 seg 级判定表 v1（依 docs/t4_j2_seg_judgment_prereg_v1.md 协议机械生成）\n\n")
md.write("> 判据先行链：prereg commit 先于本产物；数据正源=pool_m1m2_byseg.csv（49d2ac3）。\n")
md.write("> 计算口径=十进制定点（prereg §2a）；位次三态（前位/中位带/低位旗）语义隔离于袋级三态；\n")
md.write("> 低位旗=@T2 优先序注记素材，非判决。\n\n")
md.write("## 门值表（跨袋 n=6 cell-P50 产额分位，线性插值，4 位舍入显示）\n\n")
md.write("| seg | 指标 | P10 门 | P50 门 |\n|---|---|---|---|\n")
for metric in METRICS:
    for seg in SEGS:
        js = [j for j in judgments if j[2] == metric and j[1] == seg]
        md.write("| %s | %s | %s | %s |\n" % (seg, metric, f4(js[0][6]), f4(js[0][7])))
md.write("\n## 判定表（18 cell × 2 指标 = 36 位）\n\n")
md.write("| bag | seg | M1 cell P50 (CI95) | M1 判定 | M2 cell P50 (CI95) | M2 判定 |\n")
md.write("|---|---|---|---|---|---|\n")
for b in BAGS:
    for seg in SEGS:
        m1 = next(j for j in judgments if j[0] == b and j[1] == seg and j[2] == "M1_supply_frac")
        m2 = next(j for j in judgments if j[0] == b and j[1] == seg and j[2] == "M2_grid4x4_occupancy_frac")
        md.write("| %s | %s | %s [%s,%s] | %s%s | %s [%s,%s] | %s%s |\n" % (
            b, seg, f4(m1[3]), f4(m1[4]), f4(m1[5]), m1[8], "（CI跨门降级）" if m1[9] == "是" else "",
            f4(m2[3]), f4(m2[4]), f4(m2[5]), m2[8], "（CI跨门降级）" if m2[9] == "是" else ""))
md.write("\n## 汇总\n\n")
md.write("- 三态计数：前位 %d / 中位带 %d / 低位旗 %d（合计 %d）。\n" % (cnt["前位"], cnt["中位带"], cnt["低位旗"], len(judgments)))
md.write("- CI 跨门降级 %d 格：%s。\n" % (len(dg), "、".join("%s seg%s %s" % (d[0], d[1], d[2].split("_")[0]) for d in dg)))
md.write("- 低位旗 %d 格：%s。\n" % (len(low), "、".join("%s seg%s %s(%s)" % (l[0], l[1], l[2].split("_")[0], f4(l[3])) for l in low)))
md.write("\n## 复现\n\n- 重跑命令：`python3 %s/j2_seg_judgment_v1.py`（纯文件 IO，nice -n 10 可选）。\n" % BASE)
md.write("- 判定比较全精度（Decimal），显示 4 位舍入；任何人重跑应逐位复现。\n")
open(OUT_MD, "w", encoding="utf-8").write(md.getvalue())
print("STATS 前位=%d 中位带=%d 低位旗=%d 降级=%d" % (cnt["前位"], cnt["中位带"], cnt["低位旗"], len(dg)))
print("LOW " + " | ".join("%s seg%s %s %s" % (l[0], l[1], l[2].split("_")[0], f4(l[3])) for l in low))
print("DG " + " | ".join("%s seg%s %s" % (d[0], d[1], d[2].split("_")[0]) for d in dg))
