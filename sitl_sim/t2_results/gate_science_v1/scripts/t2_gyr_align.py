#!/usr/bin/env python3
# T2 v10.1 单元3d — gyr_peak 提取器口径对齐 (预注册)
# 口径A (T1/passmap): 全袋 IMU 角速度模长峰值
# 口径B (T2 窗口化): [t_goal0, t_arrive] VINS 窗 → ROS epoch 窗 (锚=simvins.log 首个 ROS 戳 ↔ VINS t=0)
# 输出: 每轮 full_peak / win_peak / 比 + 与 passmap gyr_peak 的秩相关(跨口径可比性)
import os, re, glob, csv, json
import numpy as np
HOME = os.path.expanduser("~")
G = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
pm = {}
with open(HOME + "/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap.csv") as f:
    for row in csv.DictReader(f): pm[row["run_dir"]] = row

import rosbag
met = {r["round"]: r for r in csv.DictReader(open(G + "/x5_metrics.tsv"), delimiter="\t")}
rows = []
for name, m in sorted(met.items()):
    p = pm.get("run_" + name)
    if not p or not p.get("gyr_peak"): continue
    R = HOME + "/sitl_sim/vins_smoke_runs/run_" + name
    bag = os.path.join(R, "flight.bag")
    if not os.path.exists(bag): continue
    # 锚: simvins 首个 ROS 戳
    s0 = None
    with open(os.path.join(R, "simvins.log"), errors="replace") as f:
        for line in f:
            mm = re.search(r"\[(17\d{8}\.\d+)\]", line)
            if mm: s0 = float(mm.group(1)); break
    def pf(x):
        try: return float(x)
        except: return None
    tg, ta = pf(m.get("t_goal0")), pf(m.get("t_arrive"))
    if s0 is None or tg is None: 
        rows.append(dict(round=name, gyr_passmap=p["gyr_peak"], full_peak="NA", win_peak="NA", ratio="NA")); continue
    w0, w1 = tg, ta  # bag 时间戳=相对域(0 起), 与 VINS t 同域, 无需 epoch 锚
    full = win = 0.0
    try:
        with rosbag.Bag(bag, "r") as b:
            for _, msg, t in b.read_messages(topics=["/mavros/imu/data_raw"]):
                av = msg.angular_velocity
                n = (av.x**2 + av.y**2 + av.z**2) ** 0.5
                ts = t.to_sec()
                if n > full: full = n
                if ts >= w0 and (w1 is None or ts <= w1) and n > win: win = n
    except Exception as e:
        rows.append(dict(round=name, gyr_passmap=p["gyr_peak"], full_peak="ERR", win_peak="ERR", ratio="ERR")); continue
    rows.append(dict(round=name, gyr_passmap=p["gyr_peak"], full_peak=round(full, 3),
                     win_peak=round(win, 3), ratio=round(win / full, 3) if full > 0 else "NA"))
with open(G + "/x5_gyr_align.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["round", "gyr_passmap", "full_peak", "win_peak", "ratio"], delimiter="\t")
    w.writeheader()
    for r in rows: w.writerow(r)
ok = [r for r in rows if isinstance(r.get("full_peak"), float) and isinstance(r.get("win_peak"), float)]
if len(ok) >= 5:
    a = [float(r["gyr_passmap"]) for r in ok]; b1 = [r["full_peak"] for r in ok]; b2 = [r["win_peak"] for r in ok]
    def rank(x):
        idx = sorted(range(len(x)), key=lambda i: x[i]); rk = [0]*len(x)
        for i, j in enumerate(idx): rk[j] = i
        return rk
    def spear(x, y):
        rx, ry = rank(x), rank(y)
        return float(np.corrcoef(rx, ry)[0, 1])
    print(f"n={len(ok)} (跳过 ERR/NA {len(rows)-len(ok)})")
    print(f"spearman(passmap_gyr, full_peak) = {spear(a, b1):.3f}")
    print(f"spearman(passmap_gyr, win_peak)  = {spear(a, b2):.3f}")
    print(f"win/full ratio: med={np.median([r['ratio'] for r in ok if isinstance(r.get('ratio'), float)]):.3f}")
    print("\n样本(前 12):")
    for r in ok[:12]:
        print(f"  {r['round']:22s} passmap={r['gyr_passmap']:>6} full={r['full_peak']:>7} win={r['win_peak']:>7} ratio={r['ratio']}")
else:
    print("有效样本不足:", len(ok), rows[:5])
