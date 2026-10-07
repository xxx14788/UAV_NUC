#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_greenrate_ci.py — 筛选报告绿率差置信区间计算器（T3 v10.6 单元 1；模板 §5 承诺件）.

方法(预注册于此, 报告引用本文件为方法凭据):
  - 单比例: Wilson score 区间
  - 两比例差: Newcombe(1998) hybrid score(MOVER)区间 = 筛选报告主报区间
  - 功效注记(逐字, T1 2a): n=16/机对 20pp 差的功效 ~50%
用法: python3 t3_greenrate_ci.py <绿数A> <nA> <绿数B> <nB> [--alpha 0.05]
"""
import math, sys

def wilson(k, n, z):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def newcombe(k1, n1, k2, n2, z):
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    p1, p2 = k1 / max(n1, 1), k2 / max(n2, 1)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi

def main():
    if len(sys.argv) < 5:
        print("用法: t3_greenrate_ci.py <绿数A> <nA> <绿数B> <nB> [--alpha 0.05]"); return 64
    k1, n1, k2, n2 = (int(x) for x in sys.argv[1:5])
    alpha = 0.05
    if "--alpha" in sys.argv:
        alpha = float(sys.argv[sys.argv.index("--alpha") + 1])
    z = 1.0 - alpha / 2
    from statistics import NormalDist
    zc = NormalDist().inv_cdf(z)
    l1, u1 = wilson(k1, n1, zc)
    l2, u2 = wilson(k2, n2, zc)
    d, lo, hi = newcombe(k1, n1, k2, n2, zc)
    print("A: %d/%d = %.1f%%  Wilson 95%%CI [%.1f%%, %.1f%%]" % (k1, n1, 100 * k1 / max(n1,1), 100 * l1, 100 * u1))
    print("B: %d/%d = %.1f%%  Wilson 95%%CI [%.1f%%, %.1f%%]" % (k2, n2, 100 * k2 / max(n2,1), 100 * l2, 100 * u2))
    print("差(A−B) = %+.1f pp  Newcombe 95%%CI [%+.1f pp, %+.1f pp]" % (100 * d, 100 * lo, 100 * hi))
    # 判据接口(逐字引用, 不放宽): L1 绿率差 ≥15pp=胜者
    if d >= 0.15:
        print("L1 判读: 差 ≥15pp → A 胜(判据层①)")
    elif d <= -0.15:
        print("L1 判读: 差 ≤−15pp → B 胜(判据层①)")
    else:
        inside = (lo <= -0.10 and 0.10 <= hi) or abs(d) < 0.10
        print("L1 判读: 平手带(|差|<15pp) → 进判据层②; 追加批触发面(平手∧|差|<10pp)=%s" % ("是" if inside else "否(点估计差≥10pp)"))
    print("注记: n=16/机对 20pp 差的功效 ~50%(T1 2a 逐字); 跨机结论必须带本 CI 呈报")
    return 0

if __name__ == "__main__":
    sys.exit(main())
