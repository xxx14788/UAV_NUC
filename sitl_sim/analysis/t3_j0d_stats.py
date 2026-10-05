#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3 v9.9 单元 2: j0d 三列全系统计表(净轮/风暴/中漂移; anchor v1.4 新口径).

数据源:
  - vins_smoke_runs/run_*/j0_decomp.json  (bee17577 判读器 --j0-decomp 产物, 2026-10-06 全库批跑)
  - t3_results/combo_matrix_20261006_rounds.csv (四绿/T2fail/machine/boot/arm/j0)
  - L3 重算表 (arr_new 到位 v1.4 新口径)
分类(预注册口径延伸, 表头声明):
  风暴   = T2fail(failure detection)>0
  净轮   = T2fail=0 ∧ j0_total<0.5 (prereg V2 主判字面)
  中漂移 = T2fail=0 ∧ j0_total≥0.5 (无失败但位置质量中带; j0d 组成列区分 jump/transit 主导)
X2g3 重判绿佐证行 = L3 arr_new 破 0.75 门 ∧ 判读面逐位在册(§2.8a 算术勘误效应), 单独旗标列。
"""
import csv, glob, json, os, sys

SMOKE = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
COMBO = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results/combo_matrix_20261006_rounds.csv")
L3 = os.path.expanduser("~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/l3_recompute_v14.csv")
OUT = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results/j0d_stats_20261006")

combo = {r["round"]: r for r in csv.DictReader(open(COMBO))}
l3 = {r["round"]: r for r in csv.DictReader(open(L3))}

rows = []
for p in sorted(glob.glob(os.path.join(SMOKE, "run_*", "j0_decomp.json"))):
    name = os.path.basename(os.path.dirname(p))
    try:
        d = json.load(open(p)).get("j0_decomp", {})
    except Exception:
        continue
    if not d.get("available"):
        continue
    c = combo.get(name, {})
    t2f = int(c.get("t2fail") or 0)
    j0t = d.get("j0_total_m")
    cat = "风暴" if t2f > 0 else ("净轮" if (j0t is not None and j0t < 0.5) else "中漂移")
    l3r = l3.get(name, {})
    arr_new = l3r.get("arr_new", "")
    arr_old = c.get("arrive", "")
    # 重判绿佐证行条件: 旧口径到位≥0.75(未破门) ∧ L3 新口径<0.75(破门)
    corrobor = ""
    try:
        if arr_old != "" and arr_new != "" and float(arr_old) >= 0.75 and float(arr_new) < 0.75:
            corrobor = "重判绿佐证(L3)"
    except ValueError:
        pass
    rows.append(dict(
        round=name, machine=c.get("machine", "?"), boot=c.get("boot", ""),
        arm=c.get("arm", "")[:46], cat=cat,
        j0_result_txt=c.get("j0", ""), j0_total=j0t,
        jump_m=d.get("jump_m"), transit_m=d.get("transit_m"),
        jump_frac=d.get("jump_frac"), n_jump=d.get("n_jump_frames"),
        dominant=d.get("dominant"), n_prop=d.get("n_prop"),
        t2fail=t2f, four_green=c.get("four_green", ""),
        arrive_old=c.get("arrive", ""), arrive_new=arr_new,
        l3_flag=l3r.get("flag", ""), corrobor=corrobor,
    ))

rows.sort(key=lambda r: (r["cat"], r["machine"], r["round"]))
with open(OUT + ".csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# 汇总
from collections import Counter, defaultdict
cnt = Counter(r["cat"] for r in rows)
by_machine = defaultdict(Counter)
for r in rows:
    by_machine[r["machine"].split("(")[0]][r["cat"]] += 1
lines = []
lines.append("=" * 96)
lines.append("j0d 三列全系统计表(净轮/风暴/中漂移; anchor v1.4 新口径)  生成 2026-10-06")
lines.append("判读器=t3_wa_gate bee17577 --j0-decomp 全库批跑(113 袋轮) | join=combo_matrix+L3 | 分类: 风暴=T2fail>0; 净轮=T2fail=0∧j0_total<0.5; 中漂移=T2fail=0∧j0_total≥0.5")
lines.append("=" * 96)
lines.append("总数 %d: %s" % (len(rows), ", ".join("%s=%d" % kv for kv in cnt.most_common())))
for mk in ("3090", "NUC", "?"):
    if mk in by_machine:
        c = by_machine[mk]
        lines.append("  %-4s %2d 轮: 净轮=%d 中漂移=%d 风暴=%d" % (mk, sum(c.values()), c["净轮"], c["中漂移"], c["风暴"]))
# 净轮名册
lines.append("")
lines.append("-- 净轮名册 (T2fail=0 ∧ j0_total<0.5):")
for r in rows:
    if r["cat"] == "净轮":
        lines.append("  %-28s %-9s %-6s j0=%.3f jump=%.3f transit=%.3f dom=%s 四绿=%s %s" % (
            r["round"], r["machine"][:9], r["boot"], r["j0_total"],
            r["jump_m"] if r["jump_m"] is not None else -1,
            r["transit_m"] if r["transit_m"] is not None else -1,
            r["dominant"], r["four_green"], r["corrobor"]))
# X2g3 佐证行
lines.append("")
lines.append("-- X2g3 重判绿佐证行(L3 新口径到位破 0.75 门; §2.8a 算术勘误效应逐位):")
for r in rows:
    if r["corrobor"]:
        lines.append("  %-28s 到位 old=%s → new=%s (<0.75 翻绿) | j0d: j0_total=%s jump=%s transit=%s dom=%s | 四绿=%s(disarm 面维持原判, 佐证限到位锚口径)" % (
            r["round"], r["arrive_old"], r["arrive_new"], r["j0_total"], r["jump_m"], r["transit_m"], r["dominant"], r["four_green"]))
# 中漂移主导组成
dom_md = Counter(r["dominant"] for r in rows if r["cat"] == "中漂移")
lines.append("")
lines.append("-- 中漂移主导组成: %s" % ", ".join("%s=%d" % kv for kv in dom_md.most_common()))
dom_net = Counter(r["dominant"] for r in rows if r["cat"] == "净轮")
lines.append("-- 净轮主导组成:   %s" % ", ".join("%s=%d" % kv for kv in dom_net.most_common()))
txt = "\n".join(lines)
open(OUT + ".txt", "w").write(txt)
print(txt)
