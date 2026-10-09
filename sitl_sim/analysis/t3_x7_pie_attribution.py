#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_x7_pie_attribution.py — SITL 绿率病理归因饼图数据 v1.0（T3 v11.1 单元 2 定量附录①）
combo 350（combo_matrix_20261009_rounds.csv）× j0d 286（j0d_stats_20261009b.csv）联算。
任务书措辞："跳变族/慢淋 transit/其他各占失分 pp——收敛声明的定量支撑"。
三桶互斥分类（优先级）：跳变族(j0d dom=jump/mixed 或 njf>=5) > 慢淋 transit 族(dom=transit)
> 其他(风暴 t2fail>0/到位门 FAIL 无跳/ENV/无 j0d 面等，细分列示)。
失分 pp=桶轮数/350*100（分母=组合矩阵全池）。
"""
import csv, os

HOME = os.path.expanduser("~")
COMBO = HOME + "/catkin_ws/sitl_sim/t3_results/combo_matrix_20261009_rounds.csv"
J0D = HOME + "/catkin_ws/sitl_sim/t3_results/j0d_stats_20261009b.csv"

combo = list(csv.DictReader(open(COMBO)))
j0d = {r["round"]: r for r in csv.DictReader(open(J0D))}

N = len(combo)
buckets = {"jump_clan": [], "transit_clan": [], "other_storm": [], "other_arrive": [], "other_env": [], "other_nodata": [], "other": []}
green = []
for r in combo:
    rd = r["round"]
    if r.get("four_green") == "1":
        green.append(rd)
        continue
    j = j0d.get(rd)
    njf = 0
    dom = ""
    t2f = 0
    if j:
        try: njf = int(j.get("n_jump") or 0)
        except ValueError: njf = 0
        dom = (j.get("dominant") or "").strip()
        try: t2f = int(j.get("t2fail") or 0)
        except ValueError: t2f = 0
    result = (r.get("result") or "").strip()
    if dom in ("jump", "mixed") or njf >= 5:
        buckets["jump_clan"].append(rd)
    elif dom == "transit":
        buckets["transit_clan"].append(rd)
    elif t2f > 0:
        buckets["other_storm"].append(rd)
    elif result.startswith("ENV"):
        buckets["other_env"].append(rd)
    elif j is None:
        buckets["other_nodata"].append(rd)
    elif (r.get("arrive") or "") not in ("",) :
        try:
            if float(r.get("arrive") or 0) >= 0.75:
                buckets["other_arrive"].append(rd)
                continue
            buckets["other"].append(rd)
        except ValueError:
            buckets["other"].append(rd)
    else:
        buckets["other"].append(rd)

fail = N - len(green)
print("池=%d 绿=%d (%.1f%%) 失分=%d (%.1f%%)" % (N, len(green), 100.0*len(green)/N, fail, 100.0*fail/N))
print()
total_other = sum(len(v) for k, v in buckets.items() if k.startswith("other"))
print("失分三桶（互斥；分母=350 全池，pp=轮数/350*100）:")
for k, label in [("jump_clan", "跳变族(dom jump/mixed 或 njf>=5)"), ("transit_clan", "慢淋 transit 族(dom=transit)")]:
    print("  %-38s %3d 轮  %5.1f pp" % (label, len(buckets[k]), 100.0*len(buckets[k])/N))
print("  %-38s %3d 轮  %5.1f pp" % ("其他（细分↓）", total_other, 100.0*total_other/N))
for k, label in [("other_storm", "其他.风暴 t2fail>0"), ("other_arrive", "其他.到位门 FAIL(arrive>=0.75)"),
                 ("other_env", "其他.ENV-FAIL"), ("other_nodata", "其他.无 j0d 面"),
                 ("other", "其他.余量(net/空面)")]:
    if buckets[k]:
        print("    %-36s %3d 轮  %5.1f pp" % (label, len(buckets[k]), 100.0*len(buckets[k])/N))
print()
print("两主族合计=%.1f pp（占失分 %.1f%%）" % (
    100.0*(len(buckets['jump_clan'])+len(buckets['transit_clan']))/N,
    100.0*(len(buckets['jump_clan'])+len(buckets['transit_clan']))/fail if fail else 0))
