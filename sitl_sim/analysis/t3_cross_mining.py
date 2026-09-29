#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Y1.4 跨袋模式挖掘聚合器:从 t3_library_forensics_db.json 再生全部统计表

产出(到 stdout,md 片段;t3_cross_campaign_mining.md 引用其输出组装):
  T1 形态×场景×配置代交叉表(计数+典型例)
  T2 t* 分布直方图 + 距最近运动瞬态对齐统计
  T3 Bas/Bgs 峰值分布(按形态分层)
  T4 触发事件对齐谱(t* 最近事件分布)
  T5 翻案候选清单(RESULT vs DB 新判分歧行)
每表带样本量脚注;所有行引用 = DB json 索引(0-based 行号)。
"""
import json
import os
import re
import statistics
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRIPT_DIR, "t3_library_forensics_db.json")


def main():
    rows = json.load(open(DB, encoding="utf-8"))
    for i, r in enumerate(rows):
        r["_i"] = i
    out = []

    def sec(t):
        out.append("\n## " + t)

    # ---- T1 形态×场景×配置代 ----
    sec("T1 形态×场景×配置代交叉表(行=DB 行号;仅含有袋发散/健康判实行)")
    from collections import Counter, defaultdict
    mat = defaultdict(list)
    for r in rows:
        if r.get("DB判决") in ("无袋", "SCAN-ERROR"):
            continue
        morph = (r.get("形态") or "?").split("(")[0]
        key = (morph, r.get("场景", "?"), (r.get("配置代") or "?")[:18])
        mat[key].append(r)
    out.append("| 形态 | 场景 | 配置代 | n | 典型例(行/轮/t*) |")
    out.append("|---|---|---|---|---|")
    for key in sorted(mat, key=lambda k: -len(mat[k])):
        rs = mat[key]
        ex = rs[0]
        out.append(f"| {key[0]} | {key[1]} | {key[2]} | {len(rs)} "
                   f"| 行{ex['_i']} {ex['轮名']} t*={ex.get('t*_s')} |")

    # ---- T2 t* 分布 + 运动瞬态对齐 ----
    sec("T2 t* 分布与距最近运动瞬态对齐(smoke_run 域;有 t* 行)")
    ts = []
    for r in rows:
        if r.get("类别") == "smoke_run" and r.get("t*_s") is not None:
            ts.append(r)
    out.append(f"样本 n={len(ts)}(smoke_run 有 t*)")
    buckets = Counter()
    for r in ts:
        t = r["t*_s"]
        b = ("<5" if t < 5 else "5-15" if t < 15 else "15-30" if t < 30
             else "30-45" if t < 45 else "45-70" if t < 70 else "≥70")
        buckets[b] += 1
    out.append("| t* 桶 | <5 | 5-15 | 15-30 | 30-45 | 45-70 | ≥70 |")
    out.append("|---|---|---|---|---|---|---|")
    out.append("| n | " + " | ".join(str(buckets.get(k, 0))
               for k in ("<5", "5-15", "15-30", "30-45", "45-70", "≥70")) + " |")
    out.append("\n距最近运动瞬态(t*−事件;事件=takeoff/poscmd_first/goal×n):")
    out.append("| 轮 | t* | 最近事件 | Δ(s) | 行 |")
    out.append("|---|---|---|---|---|")
    near_stat = []
    for r in ts:
        ev = str(r.get("最近事件") or "")
        m = re.search(r"(\S+)@(-?[\d.]+)s \(Δ=(-?[\d.]+)s\)", ev)
        if m:
            near_stat.append((m.group(1), float(m.group(3))))
            out.append(f"| {r['轮名']} | {r['t*_s']} | {m.group(1)} | {m.group(3)} | {r['_i']} |")
    cnt = Counter(k for k, _ in near_stat)
    out.append(f"\n事件类型计数: {dict(cnt)};"
               f"Δ 中位={statistics.median([abs(d) for _, d in near_stat]):.1f}s"
               f"(n={len(near_stat)})")

    # ---- T3 Bas/Bgs 峰值分布(按形态分层) ----
    sec("T3 Bas/Bgs 峰值分布(有 T2diag 行,按 DB 形态分层)")
    out.append("| 形态 | n有Bas | Bas峰中位 | Bas峰max | Bas>1.0 行 | Bgs峰中位 | 行例 |")
    out.append("|---|---|---|---|---|---|---|")
    bym = defaultdict(list)
    for r in rows:
        if r.get("Bas峰") is not None and r.get("DB判决") not in ("无袋",):
            bym[(r.get("形态") or "?").split("(")[0]].append(r)
    for k in sorted(bym, key=lambda x: -len(bym[x])):
        rs = bym[k]
        bas = sorted(x["Bas峰"] for x in rs)
        bgs = sorted(x["Bgs峰"] for x in rs if x.get("Bgs峰") is not None)
        out.append(f"| {k} | {len(rs)} | {bas[len(bas)//2]:.3f} | {bas[-1]:.3f} | "
                   f"{sum(1 for b in bas if b > 1.0)} | "
                   f"{bgs[len(bgs)//2]:.4f} | 行{rs[0]['_i']} {rs[0]['轮名']} |")

    # ---- T4 触发事件对齐谱 ----
    sec("T4 触发事件对齐谱(t* 轮的最近事件类型×Δ 签名,smoke+replay 域)")
    ev_all = Counter()
    for r in rows:
        if r.get("t*_s") is not None:
            ev = str(r.get("最近事件") or "无事件数据")
            m = re.search(r"(\S+)@", ev)
            ev_all[m.group(1) if m else ev[:12]] += 1
    out.append("| 最近事件类型 | n |")
    out.append("|---|---|")
    for k, v in ev_all.most_common():
        out.append(f"| {k} | {v} |")

    # ---- T5 翻案候选(RESULT vs DB 新判分歧) ----
    sec("T5 翻案候选清单(RESULT.txt 旧判 vs DB 新判分歧;自动比对)")
    out.append("| 轮 | RESULT(旧) | DB 新判 | 分歧点 | 行 |")
    out.append("|---|---|---|---|---|")
    for r in rows:
        m = re.search(r"\|RESULT=(\S+)", r.get("DB判决") or "")
        if not m:
            continue
        old = m.group(1)
        new = (r.get("DB判决") or "").split("|")[0]
        div = new.startswith("FAIL") or new.startswith("判废")
        if (old == "PASS" and div) or (old == "ENV-FAIL" and div):
            out.append(f"| {r['轮名']} | {old} | {new} | 旧过新败/旧ENV新毒 | {r['_i']} |")

    print("\n".join(out))


if __name__ == "__main__":
    main()
