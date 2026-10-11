#!/usr/bin/env python3
# t1_mtrace_sym_samples.py — 样本帧全符号化
import sys, subprocess
maps = sys.argv[1]
addrs = [int(x, 16) for x in sys.argv[2:]]
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
def sym(path, off):
    try:
        r = subprocess.run(["addr2line", "-e", path, "-f", "-C", hex(off)], capture_output=True, text=True, timeout=10)
        L = r.stdout.strip().split("\n")
        return f"{L[0]} @ {L[1] if len(L)>1 else '?'}"
    except Exception: return "?"
for a in addrs:
    path, off = locate(a)
    if path:
        print(f"{hex(a)} {path.split('/')[-1]}+{hex(off)}  {sym(path, off)}")
    else:
        print(f"{hex(a)} UNMAPPED")
