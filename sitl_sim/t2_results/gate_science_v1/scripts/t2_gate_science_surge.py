#!/usr/bin/env python3
# T2 v10.1 单元2a — surge 提取器 v2 (预注册口径)
# 复现 [T2GATECFG] cost 门的真实视角: 滑动 W=20 帧中值作基线, 当前值/基线 = surge 比
# 输出 x5_surge.tsv: 每轮 surge streak(多 R 扫描)/触发时刻/jump onset/前兆时序
# 预注册判据(先于结论):
#   - jump_onset = 首个 |dP|>1.0m 的 10Hz 样本时刻 (VINS odom 帧跳, >10 m/s 等效)
#   - surge@R 触发 = 连续 >=N 帧 cost[i] > R*med(cost[i-W..i-1]); N 扫 {3,5,8}
#   - 前兆成立 = surge 触发时刻 t_s < jump_onset t_j 且 t_j - t_s >= 3s
#   - Bas 同款 (R_b 扫 {2,3,5})
import os, re, glob, csv
import numpy as np
HOME = os.path.expanduser("~")
OUTD = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"

re_slv = re.compile(r"\[T2slv\] t=([\d.]+) phase=\d+ init_cost=([\d.eE+-]+)")
re_diag = re.compile(r"\[T2diag\] t=([\d.]+) P=\[([^\]]*)\].*\|Bas\|=([\d.eE+-]+)")

def sliding_streaks(v, W=20):
    """返回 ratio[i] = v[i]/med(v[max(0,i-W):i]) (i>=W 才有效) 及 per-i 超限可组合数组"""
    n = len(v)
    ratio = np.full(n, np.nan)
    for i in range(W, n):
        m = np.median(v[i - W:i])
        if m > 0:
            ratio[i] = v[i] / m
    return ratio

def max_streak(ratio, R, N):
    """最大连续超限长度; 达到 N 的首个起点."""
    best, best_t, cur, cur_t0 = 0, float("nan"), 0, None
    for i, r in enumerate(ratio):
        if r == r and r > R:
            if cur == 0: cur_t0 = i
            cur += 1
            if cur > best:
                best, best_t = cur, cur_t0
        else:
            cur = 0
    return best

def first_streak_start(t, ratio, R, N):
    cur = 0
    for i, r in enumerate(ratio):
        if r == r and r > R:
            cur += 1
            if cur >= N:
                return float(t[i - N + 1])
        else:
            cur = 0
    return float("nan")

rows = []
for R_dir in sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*")):
    name = os.path.basename(R_dir)[len("run_"):]
    slv, dgm = [], []
    try:
        with open(os.path.join(R_dir, "simvins.log"), errors="replace") as f:
            for line in f:
                if "[T2slv]" in line:
                    m = re_slv.search(line)
                    if m: slv.append((float(m.group(1)), float(m.group(2))))
                elif "[T2diag]" in line:
                    m = re_diag.search(line)
                    if m:
                        p = [float(x) for x in m.group(2).split()]
                        dgm.append((float(m.group(1)), np.linalg.norm(p), float(m.group(3))))
    except FileNotFoundError:
        continue
    if len(slv) < 40 or len(dgm) < 40:
        rows.append(dict(round=name, note="short")); continue
    t_c = np.array([x[0] for x in slv]); v_c = np.array([x[1] for x in slv])
    t_d = np.array([x[0] for x in dgm]); v_p = np.array([x[1] for x in dgm]); v_b = np.array([x[2] for x in dgm])
    # jump onset (10Hz 相邻差)
    dp = np.abs(np.diff(v_p))
    jidx = np.where(dp > 1.0)[0]
    t_jump = float(t_d[jidx[0]]) if len(jidx) else float("nan")
    n_jump = int((dp > 1.0).sum())
    # cost surge (仅 init 后 phase>=1: 用 t>=t_c[0])
    mfly = t_c >= t_c[0]
    ratio_c = sliding_streaks(v_c[mfly])
    t_cf = t_c[mfly]
    # Bas surge
    ratio_b = sliding_streaks(v_b)
    row = dict(round=name, n_jump=n_jump,
               t_jump="%.1f" % t_jump if t_jump == t_jump else "NA")
    for R in (3.0, 5.0, 10.0):
        ms = max_streak(ratio_c, R, 1)
        fs = first_streak_start(t_cf, ratio_c, R, 5)
        row["c_s%d_max" % R] = int(ms)
        row["c_s%d_t5" % R] = ("%.1f" % fs) if fs == fs else "NA"
    for R in (2.0, 3.0, 5.0):
        ms = max_streak(ratio_b, R, 1)
        fs = first_streak_start(t_d, ratio_b, R, 5)
        row["b_s%d_max" % R] = int(ms)
        row["b_s%d_t5" % R] = ("%.1f" % fs) if fs == fs else "NA"
    rows.append(row)

keys = list(rows[0].keys())
with open(OUTD + "/x5_surge.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, delimiter="\t"); w.writeheader()
    for r in rows: w.writerow(r)
print("surge rows:", len(rows))
