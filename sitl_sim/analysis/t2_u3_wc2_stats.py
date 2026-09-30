#!/usr/bin/env python3
# T2-U3 W-C2 六轮统计收集器 (2026-10-01): 逐轮 VINS 域结论+跳变计数+到位+出生点对齐+四指标
import glob, json, os, re, sys

RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
TAGS = ["WC2OBS1", "WC2OBS2", "WC2RT1", "WC2RT2", "WC2HOV1"]  # GND 轮单独(t2v3_flight)

rows = []
for tag in TAGS:
    ds = sorted(glob.glob(os.path.join(RUNS, f"run_{tag}_*")))
    if not ds:
        rows.append({"tag": tag, "missing": True}); continue
    d = ds[-1]
    row = {"tag": tag, "dir": os.path.basename(d), "mtime": os.path.getmtime(d)}
    log = os.path.join(d, "simvins.log")
    if os.path.exists(log):
        txt = open(log, errors="replace").read()
        row["failure_n"] = txt.count("failure detection")
        row["insane_reboot_n"] = txt.count("insane states")
        row["probe_uls"] = txt.count("[E2uls")
        row["probe_clamp"] = txt.count("[E2clamp")
        row["probe_gap"] = txt.count("[E2gap")
        # 跳变计数: E2uls 行 |dP|>0.5(J0 口径锚差>0.5m=FAIL 级); smj=|dP| 平滑段计数
        big = small = 0
        for m in re.finditer(r"\[E2uls\].*\|dP\|=([0-9.]+)", txt):
            v = float(m.group(1))
            if v > 0.5: big += 1
            elif v > 0.03: small += 1
        row["jump_gt05"] = big
        row["dp_events_003_05"] = small
    res = os.path.join(d, "RESULT.txt")
    if os.path.exists(res):
        rt = open(res, errors="replace").read()
        row["result"] = ("FAIL" if "RESULT=FAIL" in rt else
                         "PASS" if "RESULT=PASS" in rt else "ENV-FAIL" if "ENV-FAIL" in rt else "?")
        m = re.search(r"帧稳定性 \|pre-post\|=([0-9.]+) m", rt)
        row["frame_jump_m"] = m and float(m.group(1))
        m = re.search(r"leg1 到位\(真值\) min=([0-9.]+) m", rt)
        row["arrive_truth_m"] = m and float(m.group(1))
        m = re.search(r"ARRIVE_WATCH1: (\S+)", rt)
        row["arrive_watch"] = m and m.group(1)
    aw = os.path.join(d, "arrive_watch.txt")
    if os.path.exists(aw):
        m = re.match(r"anchor: \(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)", open(aw).read())
        if m:
            row["birth_anchor"] = [float(m.group(i)) for i in (1, 2, 3)]
    rows.append(row)

out = os.path.expanduser("~/sitl_sim/t2_u3_wc2_stats.json")
json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
print(f"[u3-stats] -> {out}")
