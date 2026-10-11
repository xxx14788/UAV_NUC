#!/usr/bin/env python3
# t1_mtrace_liveagg2.py — v2: bt3 不在 .text 区间时用 bt4(PLT/tail-call 帧修复)
import sys, subprocess
from collections import defaultdict
inst, maps = sys.argv[1], sys.argv[2]
TEXT_LO, TEXT_HI = 0x378b0, 0x378b0 + 0xe5c4f
regions = []
for line in open(maps):
    parts = line.split()
    if "-" not in parts[0] or len(parts) < 6: continue
    lo, hi = [int(x, 16) for x in parts[0].split("-")]
    regions.append((lo, hi, parts[-1]))
def locate(a):
    for lo, hi, path in regions:
        if lo <= a < hi: return path, a - lo
    return None, None
live = {}
for line in open(inst + "/mtrace.log"):
    p = line.split()
    if p[0] == "A":
        live[int(p[2], 16)] = (int(p[1]), [int(x, 16) for x in p[3:8]])
    elif p[0] == "F":
        live.pop(int(p[1], 16), None)
agg = defaultdict(lambda: [0, 0])
for ptr, (sz, bts) in live.items():
    bt3 = bts[2] if len(bts) > 2 else 0
    bt4 = bts[3] if len(bts) > 3 else 0
    path3, off3 = locate(bt3)
    key = bt3
    if path3 and "libvins_lib" in path3 and not (TEXT_LO <= off3 < TEXT_HI):
        key = bt4 if bt4 else bt3
    a = agg[key]; a[0] += sz; a[1] += 1
def sym(path, off):
    try:
        r = subprocess.run(["addr2line", "-e", path, "-f", "-C", hex(off)], capture_output=True, text=True, timeout=10)
        L = r.stdout.strip().split("\n")
        return f"{L[0]} @ {L[1] if len(L)>1 else '?'}"
    except Exception: return "?"
total = sum(v[0] for v in agg.values())
print(f"live total {total/1048576:.1f}MB entries {len(agg)}")
for key, (b, n) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:14]:
    path, off = locate(key)
    s = f"{path.split('/')[-1]}+{hex(off)} {sym(path,off)}" if path else f"unmapped {hex(key)}"
    print(f"{b/1048576:8.2f}MB n={n:5d} avg={b/max(n,1)/1024:7.1f}KB {s}")
