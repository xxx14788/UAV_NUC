#!/usr/bin/env python3
# T2 v10.1 单元1 — T1 定因表复核抽验 (T2 侧独立复算, 非走过场)
# 抽验项:
#   V1 config md5: 59 轮 vins_config.md5 内容值全分布 (对照 T1: 19 轮同 054ddc8d)
#   V2 RTF: 独立复算 2 轮 (bag sim 时长 / 轮 wall 时长, 对照 T1 rtf 值)
#   V3 PX4 结构参数: diff 跳轮 E5O vs 绿格 E8O 的 dump (排除 CAL_/易变前缀)
#   V4 hwmon: 抽 N8O 发作窗 [t_prodrome, t_jump] 的 cpu freq 中位 (对照 T1 json 1768472)
import os, glob, hashlib, json, re, csv
HOME = os.path.expanduser("~")
RUNS = sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*"))
CAU = HOME + "/sitl_sim/t1_evidence/v11_20_2026-10-07/causation"

# V1
md5s = {}
for R in RUNS:
    try:
        with open(os.path.join(R, "vins_config.md5")) as f:
            val = f.read().split()[0]
        md5s.setdefault(val, []).append(os.path.basename(R))
    except Exception:
        pass
print("V1 config md5 独立分布:")
for v, rounds in md5s.items():
    print(f"  {v}: {len(rounds)} 轮")

# V2 RTF 复算 (sitl.log 行首时间戳 or round.log wall 事件; 用 bag_sim_s+轮 wall)
leg4 = json.load(open(CAU + "/leg4_rtf.json"))
print("\nV2 RTF 独立复算:")
for tag in ("X5_E5O", "X5_E12O"):
    rdir = [R for R in RUNS if os.path.basename(R).startswith("run_" + tag + "_")]
    if not rdir: continue
    R = rdir[0]
    # wall: round.log 首末时间戳 [HH:MM:SS]
    ts = re.findall(r"\[(\d\d):(\d\d):(\d\d)\]", open(os.path.join(R, "round.log"), errors="replace").read())
    if len(ts) >= 2:
        wall = (int(ts[-1][0]) * 3600 + int(ts[-1][1]) * 60 + int(ts[-1][2])) - (int(ts[0][0]) * 3600 + int(ts[0][1]) * 60 + int(ts[0][2]))
        sim = leg4["per_round"][tag]["bag_sim_s"]
        print(f"  {tag}: wall={wall}s sim={sim}s my_rtf={sim/wall:.3f} | T1 rtf={leg4['per_round'][tag]['rtf']}")
    else:
        print(f"  {tag}: round.log 时间戳不足, skip")

# V3 PX4 结构 diff
def load_px4(tag):
    rdir = [R for R in RUNS if os.path.basename(R).startswith("run_" + tag + "_")]
    if not rdir: return None
    px = glob.glob(os.path.join(rdir[0], "px4_params_*.txt"))
    if not px: return None
    d = {}
    for line in open(px[0], errors="replace"):
        m = re.match(r"^([A-Za-z0-9_]+)\s+([\d.\-+eE]+)", line)
        if m: d[m.group(1)] = m.group(2)
    return d
j, g = load_px4("X5_E5O"), load_px4("X5_E8O")
VOLATILE = re.compile(r"^(CAL_|COM_FLIGHT|LND_FLIGHT_T_|SYS_|UAVCAN|BAT|SENS|RC_|TC_A|TC_B|LPE|COM_ARM|COM_RC)")
diffs = []
for k in sorted(set(j) & set(g)):
    if j[k] != g[k] and not VOLATILE.match(k):
        diffs.append((k, g[k], j[k]))
print(f"\nV3 PX4 结构参数 diff (E5O 跳 vs E8O 绿, 排除易变前缀后): {len(diffs)} 个")
for k, a, b in diffs[:10]:
    print(f"  {k}: green={a} jump={b}")

# V4 hwmon 抽验
leg3 = json.load(open(CAU + "/leg3_hwmon.json"))
rdir = [R for R in RUNS if os.path.basename(R).startswith("run_X5_N8O_")][0]
rows = list(csv.reader(open(os.path.join(rdir, "hwmon.tsv")), delimiter="\t"))
hdr = rows[0]
print("\nV4 hwmon 列:", hdr[:8])
ti = hdr.index("t") if "t" in hdr else 0
fi = [i for i, h in enumerate(hdr) if "freq" in h.lower()]
fi = fi[0] if fi else None
tp, tj = leg3["per_jump_round"]["X5_N8O"]["t_prodrome"], leg3["per_jump_round"]["X5_N8O"]["t_jump"]
vals = []
for r in rows[1:]:
    try:
        t = float(r[ti])
        if tp <= t <= tj and fi is not None:
            vals.append(float(r[fi]))
    except Exception:
        pass
if vals:
    import numpy as np
    print(f"  N8O 发作窗 [{tp},{tj}] freq 中位(我算)={np.median(vals):.0f} n={len(vals)} | T1 json={leg3['per_jump_round']['X5_N8O']['window']['freq_avg_med']}")
else:
    print("  窗内样本 0 — hwmon t 域可能是 wall 相对域, 与 VINS t 不同轴; 查首行 t:", rows[1][:3] if len(rows) > 1 else "无")
