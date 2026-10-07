#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_epsilon_band_audit.py — C.2 截断浮点 epsilon 带审计器（c2_logtail_purify_opinion_v1 §3 结案件）.

口径: 不动判读器/不改 log, 只消费既有 CSV 判读值。每值 epsilon 从其字符串小数位
自适应推导(%.Nf → ±0.5×10^-N), 标旗 |值−门阈| ≤ epsilon 的边界带轮。
门阈面(默认): 到位 0.75 / j0 净轮线 0.5。
用法: python3 t3_epsilon_band_audit.py <combo_or_j0d.csv> [--cols arrive:0.75,j0:0.5]
输出: 边界带轮清单+占比 → 占比可忽略=C.2 记录项关闭; 不可忽略=上呈生产者侧修复。
"""
import argparse, csv, sys

def eps_of(s):
    """字符串小数位 → ±0.5×10^-N; 无小数=0(整值无截断带)."""
    s = (s or "").strip()
    if "." in s:
        return 0.5 * (10 ** -len(s.split(".", 1)[1]))
    return 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvpath")
    ap.add_argument("--cols", default="arrive:0.75,j0_total:0.5,j0d_jump:0.5")
    ap.add_argument("--fallback-cols", default="arrive:0.75,j0:0.5")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csvpath, newline="", encoding="utf-8")))
    if not rows:
        print("FAIL: 空 CSV"); return 2
    have = set(rows[0].keys())
    specs = []
    for part in (a.cols.split(",") + a.fallback_cols.split(",")):
        col, _, thr = part.partition(":")
        if col in have and (col, float(thr)) not in specs:
            specs.append((col, float(thr)))
    if not specs:
        print("FAIL: CSV 无可用判读列(候选=%s)" % ",".join(c for c, _ in specs)); return 2

    total = len(rows)
    flagged = {}
    for r in rows:
        for col, thr in specs:
            v = (r.get(col) or "").strip()
            if not v:
                continue
            try:
                fv = float(v)
            except ValueError:
                continue
            e = eps_of(v)
            if e > 0 and abs(fv - thr) <= e:
                flagged.setdefault(r.get("round", "?"), []).append(
                    "%s=%s (ε=%.4f, 距门 %.4f)" % (col, v, e, abs(fv - thr)))

    print("epsilon 带审计  csv=%s  n=%d  门面=%s" % (a.csvpath, total,
          "; ".join("%s@%.2f" % s for s in specs)))
    if not flagged:
        print("边界带轮: 0/%d (0.0%%) —— 截断未落在任一门阈 ε 带内")
        print("RESULT: C.2 危害面可忽略 → 按意见 §3 记录项关闭")
        return 0
    print("边界带轮: %d/%d (%.1f%%)" % (len(flagged), total, 100.0 * len(flagged) / total))
    for rn, why in sorted(flagged.items()):
        print("  FLAG %s  %s" % (rn, "; ".join(why)))
    print("RESULT: 危害面非零 → 上呈生产者侧修复决策(printf 格式, DECISION_LOG 件)")
    return 1

if __name__ == "__main__":
    sys.exit(main())
