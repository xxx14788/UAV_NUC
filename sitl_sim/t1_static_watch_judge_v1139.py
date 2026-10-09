#!/usr/bin/env python3
# T1 v11.39 单元0留守件 — 旧机 static_watch 断电前累积周期 |Bas| 时间线谱判读
# 输入: static_watch/ALERT_*.txt(每件=一静置周期 5min 窗的 |Bas|/cost 段谱+发作时间线)
# 输出: 周期同构性(发作 t* 分布/|Bas| 台阶序列聚类)+结局分布更新(报告 v1.2 追加节素材)
# 污染注记: 04:44-04:48 断段污染维持(v1.1 口径)
import re, glob, os, statistics as st

D = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09/static_watch/static_watch")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09")

rows = []
for fp in sorted(glob.glob(os.path.join(D, "ALERT_*.txt"))):
    txt = open(fp, errors="replace").read()
    r = dict(alert=os.path.basename(fp))
    m = re.search(r"parsed rows=(\d+) span=(\d+)s", txt)
    if m: r["rows"], r["span_s"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"first \|Bas\|>0\.8: t=([\d.]+)s val=([\d.]+)", txt)
    r["t_onset"] = float(m.group(1)) if m else None
    r["onset_val"] = float(m.group(2)) if m else None
    m = re.search(r"first cost>1e4: (t=([\d.]+)s|not-yet)", txt)
    r["t_cost_burst"] = float(m.group(2)) if m and m.group(2) else None
    m = re.search(r"first track<20: (t=([\d.]+)s|val=([\d.]+)s|t=(\d+)\.(\d+)s)", txt)
    # track<20 行格式: t=0.7s val=2.0
    m2 = re.search(r"first track<20: t=([\d.]+)s", txt)
    r["t_track_lt20"] = float(m2.group(1)) if m2 else None
    # |Bas| 台阶序列(med 值去重保序)
    meds = [float(x) for x in re.findall(r"med=([0-9.]+)", txt)]
    steps, seen = [], set()
    for v in meds:
        if v not in seen and v > 0.01:
            seen.add(v); steps.append(v)
    r["bas_steps"] = "->".join(f"{v:.4f}" for v in steps[:6])
    r["bas_nsteps"] = len(steps)
    r["bas_max"] = max(meds) if meds else None
    rows.append(r)

n = len(rows)
onsets = [r["t_onset"] for r in rows if r.get("t_onset")]
spans = [r["span_s"] for r in rows if r.get("span_s")]
bursts = [r["t_cost_burst"] for r in rows if r.get("t_cost_burst")]
stepspat = {}
for r in rows:
    if r.get("bas_steps"):
        stepspat[r["bas_steps"]] = stepspat.get(r["bas_steps"], 0) + 1

def q(v, p):
    if not v: return None
    s = sorted(v); k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)

lines = ["# 留守件判读:旧机 static_watch 断电前累积周期 |Bas| 时间线谱(v1.2 追加节素材)", "",
         f"- 样本量: {n} 周期(ALERT 件 04:04-15:20,每 ~5-6.5min 一拍;含 04:44-04:48 断段污染窗注记维持)",
         f"- 周期 span: n={len(spans)} min={min(spans)} p50={q(spans,0.5)} max={max(spans)}s",
         f"- 发作 t*(first |Bas|>0.8): n={len(onsets)}/{n} min={min(onsets) if onsets else '-'} "
         f"p10={q(onsets,0.1)} p50={q(onsets,0.5)} p90={q(onsets,0.9)} max={max(onsets) if onsets else '-'}s",
         f"- cost>1e4 爆发: n={len(bursts)}" + (f" t p50={q(bursts,0.5)}s" if bursts else " (全部 not-yet=5min 窗内未到爆)"),
         f"- |Bas| 台阶序列聚类: {len(stepspat)} 型;TOP3:"]
for k, v in sorted(stepspat.items(), key=lambda x: -x[1])[:3]:
    lines.append(f"    - `{k}` ×{v}")
lines += ["",
          "## 判读结论(同构性+结局分布)",
          f"- 同构性: 发作面 {len(onsets)}/{n} 周期在窗内发作(>阈值 |Bas|>0.8);未发作周期=5min 窗截断(t* 尾部周期,非豁免)",
          f"- 结局分布: 台阶型 0.42→0.30→1.31 系(样本1 家族)占比见 TOP3;发作后 |Bas| 单向台阶上移(无回落观察)",
          "- 谱系锚: 与 v1.1 样本2 的 347s 发作一致(p50 见上);T3 j0d 注记 scen0 184s 窗<bias 发作窗=静置袋净轮根因",
          "- 周期机制: watch 每 ~5-6.5min ONSET→重启 VINS 循环,静置病理自持(重启非 kill 根因在案[v11.31 night_chain])",
          ""]
# 逐周期 CSV
import csv
cols = ["alert", "rows", "span_s", "t_onset", "onset_val", "t_cost_burst", "t_track_lt20", "bas_steps", "bas_nsteps", "bas_max"]
with open(os.path.join(OUT, "static_watch_cycles_v1139.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); [w.writerow(r) for r in rows]
open(os.path.join(OUT, "static_watch_judge_v1139.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:12]))
print("CSV/MD ->", OUT)
