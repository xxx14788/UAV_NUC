#!/usr/bin/env python3
# t1_nmnear.py — nm 输出中找 <= 目标偏移的最近符号(L2 归属用)
import sys, subprocess
lib, target = sys.argv[1], int(sys.argv[2], 16)
best = None
for nmargs in (["nm", "-C", "--defined-only", lib], ["nm", "-D", "-C", "--defined-only", lib]):
    try:
        r = subprocess.run(nmargs, capture_output=True, text=True, timeout=60)
    except Exception:
        continue
    for line in r.stdout.splitlines():
        p = line.split(" ", 2)
        if len(p) < 3 or not p[0]: continue
        try:
            addr = int(p[0], 16)
        except ValueError:
            continue
        if addr <= target and p[1] in "tTwW":
            if best is None or addr > best[0]:
                best = (addr, p[2])
    if best:
        break
if best:
    print(f"{lib.split('/')[-1]}+{hex(target)} = {best[1]} (+{hex(target-best[0])} into symbol, sym at {hex(best[0])})")
else:
    print("NO-SYMBOL")
