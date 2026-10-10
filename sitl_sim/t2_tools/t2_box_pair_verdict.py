#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2_box_pair_verdict.py -- ②a box 臂批配对判读汇总（三层判读预设版）
Usage: t2_box_pair_verdict.py <box_pairs.csv>
判据（设计件 §3 冻结，零变动）: 绿率提升≥15pp ∧ 方向一致(单绿对)≥6/8 → 有效
层① box 生效=A 臂 indom_pct>95%（绿率未变也证明机制工作）
层② transit 慢淋=A 臂 dbadt < B 臂 dbadt（逐格）+ jump A<B
层③ 失败预分类=box 无效型(banner=0 或 A≈B 逐位同)/box 过紧型(A 绿率反降≥15pp+
      tic0_drift 劣化)/机理负型(层①生效但判据负)
"""
import sys, csv
from collections import defaultdict

rows = list(csv.DictReader(open(sys.argv[1])))
# env-retry rule: r2 row (written after its r1 in batch order) replaces r1
latest = {}
for r in rows:
    latest[(r["cell"], r["arm"])] = r
pairs = defaultdict(dict)
for (c, a), r in latest.items():
    pairs[c][a] = r

def green(r): return r and r["verdict"] == "PASS"
def f(x):
    try: return float(x)
    except: return None

print("cell | A:vd/jmp/arr/indom/dbadt | B:vd/jmp/arr/indom/dbadt | 绿(A,B) jmpA<B dbadtA<B banner")
n = len(pairs); a_green = b_green = 0; direction = 0; jbetter = 0; jd_both = 0
db_better = 0; db_both = 0; indom_ok = 0; a_count = 0; banner_bad = []
for c in sorted(pairs):
    A, B = pairs[c].get("A"), pairs[c].get("B")
    if not A or not B:
        print("%-5s | INCOMPLETE PAIR (A=%s B=%s)" % (c, bool(A), bool(B)))
        continue
    ga, gb = green(A), green(B)
    a_green += ga; b_green += gb
    if ga != gb: direction += 1
    ja, jb = f(A["jump"]), f(B["jump"])
    if ja is not None and jb is not None:
        jd_both += 1
        if ja < jb: jbetter += 1
    da, db_ = f(A["dbadt"]), f(B["dbadt"])
    if da is not None and db_ is not None:
        db_both += 1
        if da < db_: db_better += 1
    ia = f(A["indom_pct"])
    if ia is not None:
        a_count += 1
        if ia > 95.0: indom_ok += 1
    if A.get("box_banner") == "0": banner_bad.append(c)
    print("%-5s | %s/%s/%s/%.1f/%s | %s/%s/%s/%.1f/%s | (%d,%d) %s %s %s" %
          (c, A["verdict"], A["jump"], A["arrive"], (f(A["indom_pct"]) or -1), A["dbadt"][:6],
           B["verdict"], B["jump"], B["arrive"], (f(B["indom_pct"]) or -1), B["dbadt"][:6],
           ga, gb,
           "yes" if (ja is not None and jb is not None and ja < jb) else "NA",
           "yes" if (da is not None and db_ is not None and da < db_) else "NA",
           A.get("box_banner")))

if n == 0:
    print("NO PAIRS"); sys.exit(1)
rate_a = 100.0 * a_green / n; rate_b = 100.0 * b_green / n
diff = rate_a - rate_b
print("\n== pairs=%d  A(box)绿率=%.1f%%  B(base)绿率=%.1f%%  差=%+.1fpp" % (n, rate_a, rate_b, diff))
print("== 方向一致(单绿)对=%d/%d ; jump A<B=%d/%d(有数值对) ; transit dbadt A<B=%d/%d" %
      (direction, n, jbetter, jd_both, db_better, db_both))
ok = (diff >= 15.0) and (direction >= 6)
print("== 冻结判据(≥15pp ∧ 方向一致≥6/8): %s" %
      ("EFFECTIVE(约束②a=绿率修复主件成立)" if ok else "NOT-EFFECTIVE(如实登记)"))
print("\n== 层① box 生效直接证据: A 臂 indom>95%% = %d/%d 有 diag 的 A 轮" % (indom_ok, a_count))
print("== 层③ 预分类线索: box_banner=0 的 A 轮=%s ; A 绿率反降=%s" %
      (banner_bad if banner_bad else "无", "是(过紧型嫌疑)" if diff <= -15.0 else "否"))
