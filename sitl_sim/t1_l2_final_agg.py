#!/usr/bin/env python3
# t1_l2_final_agg.py — L2 探针窗全实例终聚合: 每实例 free 配对→统一库偏移键(修 PLT 帧用 gdb 栈结论)→合并+RSS 斜率
import sys, glob, subprocess, os, re
from collections import defaultdict

W = sys.argv[1]  # probe_window dir
TEXT_LO, TEXT_HI = 0x378b0, 0x378b0 + 0xe5c4f

def load_maps(mapsfile):
    regions = []
    for line in open(mapsfile):
        parts = line.split()
        if "-" not in parts[0] or len(parts) < 6: continue
        lo, hi = [int(x, 16) for x in parts[0].split("-")]
        regions.append((lo, hi, parts[-1]))
    return regions

def locate(regions, a):
    for lo, hi, path in regions:
        if lo <= a < hi: return path, a - lo
    return None, None

def maps_time(f):
    m = re.search(r"maps_(\d{6})\.txt", f)
    return m.group(1) if m else "000000"

# 实例目录起止(HHMMSS from rss.csv first row wall clock)
def inst_window(iev):
    try:
        first = open(iev + "/rss.csv").readlines()[1].split(",")[0]
        m = re.search(r"T(\d\d):(\d\d):(\d\d)", first)
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    except Exception:
        return None

agg_all = defaultdict(lambda: [0, 0])   # (lib, off) → bytes, n
rss_rows = []
inst_stats = []
for iev in sorted(glob.glob(W + "/inst*")):
    ml = iev + "/mtrace.log"
    if not os.path.exists(ml): continue
    # 选实例期内的 maps
    iw = inst_window(iev)
    mfiles = sorted(glob.glob(os.path.dirname(iev) + "/maps_*.txt"), key=maps_time)
    mfile = None
    if iw is not None and mfiles:
        best = None
        for f in mfiles:
            t = maps_time(f)
            ts = int(t[0:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6])
            if ts <= iw + 300: best = f
            else: break
        mfile = best or mfiles[0]
    if not mfile: continue
    regions = load_maps(mfile)
    live = {}
    for line in open(ml):
        p = line.split()
        if p[0] == "A":
            live[int(p[2], 16)] = (int(p[1]), [int(x, 16) for x in p[3:8]])
        elif p[0] == "F":
            live.pop(int(p[1], 16), None)
    for ptr, (sz, bts) in live.items():
        bt3 = bts[2] if len(bts) > 2 else 0
        path3, off3 = locate(regions, bt3)
        key_bt = bt3
        if path3 and "libvins_lib" in path3 and not (TEXT_LO <= off3 < TEXT_HI):
            key_bt = bts[3] if len(bts) > 3 else bt3
        path, off = locate(regions, key_bt)
        if path:
            k = (path.split("/")[-1], off)
            a = agg_all[k]; a[0] += sz; a[1] += 1
    # rss 斜率素材
    rows = [l.split(",") for l in open(iev + "/rss.csv").readlines()[1:] if "," in l]
    pts = [(int(r[2]), int(r[1])) for r in rows if r[1].isdigit()]
    if len(pts) >= 2:
        dur = pts[-1][0] - pts[0][0]
        gain = pts[-1][1] - pts[0][1]
        if dur >= 120:
            rss_rows.append((dur, gain))
            inst_stats.append(f"{os.path.basename(iev)}: dur={dur}s rss_gain={gain}KB rate={gain/dur*3600/1048576:.2f}GB/h")

# RSS 斜率合并
tot_d = sum(r[0] for r in rss_rows); tot_g = sum(r[1] for r in rss_rows)
print("=== per-instance RSS ===")
for s in inst_stats: print(" " + s)
if tot_d > 0:
    print(f"MERGED: {tot_d}s total, {tot_g/1048576:.0f}MB gain → {tot_g/1048576/tot_d*3600:.2f}GB/h")
print()
print("=== merged live allocations by (lib, offset) top 15 ===")
for (lib, off), (b, n) in sorted(agg_all.items(), key=lambda kv: -kv[1][0])[:15]:
    print(f"{b/1048576:8.2f}MB n={n:6d} avg={b/max(n,1)/1024:7.1f}KB {lib}+{hex(off)}")
