#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_combo_expand_check.py — 组合矩阵/j0d 扩切口加性校验器（T3 v10.6 单元 2 就绪件）.

纪律: 扩切口=旧表每一行在新表逐字段重现(零重判的扩切口形态); 旧行任何字段变动
= HALT 呈报, 禁以新表静默改史. 新行=纯加性, 列清单+分类汇总.

兼容两种表: combo_matrix_*_rounds.csv (键=round) / j0d_stats_*.csv (键=round).
用法: python3 t3_combo_expand_check.py --old <old.csv> --new <new.csv> [--key round]
退出码: 0=加性 PASS; 1=旧行变动(HALT); 2=环境缺件.
"""
import argparse, csv, sys

def load(path, key):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = r.get(key)
            if not k:
                print("FAIL: %s 缺键列 %s" % (path, key)); sys.exit(2)
            rows[k] = r
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--key", default="round")
    a = ap.parse_args()

    old, new = load(a.old, a.key), load(a.new, a.key)
    oldcols = None

    # 1) 旧行逐字段重现校验
    drifted, missing = [], []
    for k, orow in sorted(old.items()):
        if k not in new:
            missing.append(k); continue
        nrow = new[k]
        for col in orow:
            if (orow[col] or "") != (nrow.get(col) or ""):
                drifted.append((k, col, orow[col], nrow.get(col)))

    # 2) 新行清单
    added = sorted(set(new) - set(old))

    print("扩切口加性校验: old=%d new=%d added=%d missing=%d drifted=%d" % (
        len(old), len(new), len(added), len(missing), len(drifted)))
    for k in missing:
        print("  MISSING-ROW %s (旧行在新表消失=违规)" % k)
    for k, col, ov, nv in drifted:
        print("  DRIFT %s.%s 旧=%r 新=%r" % (k, col, ov, nv))
    # 3) 新行分类汇总(j0d 三列口径, 若列在)
    if added:
        have_cat = all(c in new[added[0]] for c in ("t2fail", "j0_total")) or "cat" in new[added[0]]
        cnt = {}
        for k in added:
            r = new[k]
            if "cat" in r:
                c = r["cat"]
            else:
                try:
                    t2f = int(r.get("t2fail") or 0)
                except ValueError:
                    t2f = 0
                j0t = None
                v = r.get("j0_total") or r.get("j0d_jump") or r.get("j0")
                if v not in (None, ""):
                    try:
                        j0t = float(v)
                    except ValueError:
                        pass
                c = "风暴" if t2f > 0 else ("净轮" if (j0t is not None and j0t < 0.5) else "中漂移")
            cnt[c] = cnt.get(c, 0) + 1
        print("新行分类: " + ", ".join("%s=%d" % kv for kv in sorted(cnt.items())))
        for k in added[:50]:
            print("  + %s" % k)

    ok = not drifted and not missing
    print("RESULT: %s" % ("PASS-纯加性" if ok else "HALT-旧行变动/缺失(呈报, 禁覆写旧表)"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
