#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t1_warmup_pair_verdict.py -- 1c 预热对照批配对判读汇总
Usage: t1_warmup_pair_verdict.py <warmup_pairs.csv>
Output: 格级配对表(绿率/jump/到位)+冻结判据套用(≥15pp 且方向一致≥6/8→有效)
绿=RESULT PASS;j0 副指标=jump 列;到位=arrive 列(<0.5 到位)。
"""
import sys, csv
from collections import defaultdict

rows = list(csv.DictReader(open(sys.argv[1])))
pairs = defaultdict(dict)
for r in rows:
    pairs[r["cell"]][r["arm"]] = r

def green(r): return r and r["verdict"] == "PASS"
def f(x):
    try: return float(x)
    except: return None

print("cell | A:verdict/jump/arrive | B:verdict/jump/arrive | 绿对(A,B) | jump A<B?")
n = len(pairs); a_green = b_green = 0; direction = 0; jbetter = 0
for c in sorted(pairs):
    A, B = pairs[c].get("A"), pairs[c].get("B")
    if not A or not B:
        print("%-5s | INCOMPLETE PAIR (A=%s B=%s)" % (c, bool(A), bool(B)))
        continue
    ga, gb = green(A), green(B)
    a_green += ga; b_green += gb
    if ga != gb: direction += 1
    ja, jb = f(A["jump"]), f(B["jump"])
    jb_better = (ja is not None and jb is not None and ja < jb)
    if jb_better: jbetter += 1
    print("%-5s | %s/%s/%s | %s/%s/%s | (%d,%d) | %s" %
          (c, A["verdict"], A["jump"], A["arrive"], B["verdict"], B["jump"], B["arrive"],
           ga, gb, "yes" if jb_better else ("no" if (ja is not None and jb is not None) else "NA")))

rate_a = 100.0 * a_green / n; rate_b = 100.0 * b_green / n
print("\n== pairs=%d  A(预热)绿率=%.1f%%  B(无预热)绿率=%.1f%%  差=%+.1fpp" % (n, rate_a, rate_b, rate_a - rate_b))
print("== 方向一致(单绿)对=%d/%d ; jump A<B=%d/%d(有数值对)" % (direction, n, jbetter, n))
ok = (rate_a - rate_b >= 15.0) and (direction >= 6)
print("== 冻结判据(≥15pp ∧ 方向一致≥6/8): %s" % ("EFFECTIVE(有效)" if ok else "NOT-EFFECTIVE(如实登记:预热无效=激励不足或 bias-lock 非主导佐证材料)"))
