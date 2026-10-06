#!/usr/bin/env python3
# t1_x5_curve.py — 剂量-稳定性曲线(任务书 v11.17 §4.1;H1-H3 判读)
import csv, os, collections
IN = os.path.expanduser("~/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_curve.md")
rows = list(csv.DictReader(open(IN)))
# 每格取最新一次(mtime 序=run_dir 时间戳后缀)
best = {}
for r in rows:
    if float(r["arrive_truth"] or -1) < 0 and r["result"] not in ("PASS","FAIL"): continue
    k = r["tag"]
    if k not in best or r["run_dir"] > best[k]["run_dir"]: best[k] = r
cells = [r for r in best.values() if r["variant"] in ("", "R2")]
l2 = [r for r in best.values() if r["variant"] == "L2"]
green = lambda r: r["result"] == "PASS"
print("cells=%d (l2=%d) greens=%d" % (len(cells), len(l2), sum(map(green, cells))))
lines = ["# X5 剂量-稳定性曲线（4.1；源=x5_passmap.csv 每格最新轮）", ""]
# 按 方向×距离×world 主表
lines.append("| 格 | world | gyr_peak | acc_peak | 结果 | 到位 | jump |")
lines.append("|---|---|---|---|---|---|---|")
for r in sorted(cells, key=lambda x: (x["direction"], float(x["distance_m"]), x["world"])):
    lines.append("| %s%s | %s | %s | %s | %s | %s | %s |" % (r["direction"], r["distance_m"], r["world"][:4],
        r["gyr_peak"], r["acc_peak"], r["result"], r["arrive_truth"], r["jump_prepost"]))
# gyr_peak 分带(剂量带)
def band(v):
    v = float(v)
    return "L(<0.3)" if v < 0.3 else ("M(0.3-0.6)" if v < 0.6 else "H(>=0.6)")
lines.append("")
lines.append("## 剂量带汇总（H1:绿率对 gyr_peak 带相关 vs 距离档）")
lines.append("| 带 | n | 绿数 | 绿率 | jump 中位 | 到位中位(绿轮) |")
lines.append("|---|---|---|---|---|---|")
for b in ("L(<0.3)", "M(0.3-0.6)", "H(>=0.6)"):
    g = [r for r in cells if band(r["gyr_peak"]) == b]
    if not g: lines.append("| %s | 0 | - | - | - | - |" % b); continue
    gr = [r for r in g if green(r)]
    js = sorted(float(r["jump_prepost"]) for r in g if float(r["jump_prepost"]) >= 0)
    ar = sorted(float(r["arrive_truth"]) for r in gr)
    lines.append("| %s | %d | %d | %.0f%% | %s | %s |" % (b, len(g), len(gr), 100.0*len(gr)/len(g),
        "%.2f" % js[len(js)//2] if js else "-", "%.2f" % ar[len(ar)//2] if ar else "-"))
# 距离档对照
lines.append("")
lines.append("| 距离档 | n | 绿数 | 绿率 |")
lines.append("|---|---|---|---|")
for d in ("5","8","12"):
    g = [r for r in cells if r["distance_m"] == d]
    lines.append("| %sm | %d | %d | %.0f%% |" % (d, len(g), sum(map(green,g)), 100.0*sum(map(green,g))/max(1,len(g))))
# 稳定带判定(任务书: 连续 ≥3 格全绿 或 全绿率 ≥80% 剂量区间; 负结果如实)
lines.append("")
stab = []
for b in ("L(<0.3)", "M(0.3-0.6)", "H(>=0.6)"):
    g = [r for r in cells if band(r["gyr_peak"]) == b]
    if g and sum(map(green, g)) / len(g) >= 0.8: stab.append(b)
# 连续 3 格绿(按 gyr 升序排格序列)
seq = sorted(cells, key=lambda r: float(r["gyr_peak"]))
run_ = 0; consec = False
for r in seq:
    run_ = run_ + 1 if green(r) else 0
    if run_ >= 3: consec = True; break
lines.append("## 中间稳定带判定（判据=连续≥3 格全绿 ∨ 某剂量带绿率≥80%）")
lines.append("- 全绿率>=80%% 带: %s" % (stab if stab else "**无**"))
lines.append("- 连续>=3 格全绿序列: %s" % ("**存在**" if consec else "**无**"))
lines.append("- 总绿率: %d/%d = %.0f%%" % (sum(map(green,cells)), len(cells), 100.0*sum(map(green,cells))/max(1,len(cells))))
lines.append("- 跳变前兆签名适用性:见 jump_dissect_v1/dissect_report_v1 D3/D4 门逐轮标注(下表)")
for r in sorted(cells, key=lambda x: -float(x["jump_prepost"] or 0))[:5]:
    lines.append("  - %s jump=%s gyr=%s" % (r["tag"], r["jump_prepost"], r["gyr_peak"]))
open(OUT, "w").write("\n".join(lines) + "\n")
print("CURVE -> %s" % OUT)
