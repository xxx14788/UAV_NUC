#!/usr/bin/env python3
# T2 v10.1 单元2a/2b — X5 批 cost/|Bas| 全轮提取器 (预注册: 提取口径先于结论)
# 输入 : ~/sitl_sim/vins_smoke_runs/run_X5_*  (59 轮)
# 输出 : gate_science_v1/extract/<round>.csv   每样本行: t,cost,bas,track,vel,phase
#        gate_science_v1/x5_metrics.tsv        轮级汇总(供分析器消费)
# 口径(预注册):
#   - cost = [T2slv] init_cost (每次求解的初始残差, 对病态最敏感; final_cost 对应收敛后)
#   - bas  = [T2diag] |Bas|
#   - 阶段: INIT < first_slv ; GROUND till 起飞(|V|>0.3 连3样本) ; TRANSIT till 到达
#           (goal0 后 |V|<0.15 连2s) ; POST = 其后到轮尾
#   - 基线窗 basewin = [t_first_slv+5, t_first_slv+25] (init 后正常收敛平台)
#   - lift_ratio = 最差 20s 滑窗中位 / 基线中位
#   - lift_onset = 首个 t: cost>=2x基线 且其后 5s 内持续 >=2x基线
import os, re, glob, csv, sys
import numpy as np

HOME = os.path.expanduser("~")
RUNS = sorted(glob.glob(HOME + "/sitl_sim/vins_smoke_runs/run_X5_*"))
OUTD = HOME + "/catkin_ws/sitl_sim/t2_results/gate_science_v1"
EXTD = OUTD + "/extract"
os.makedirs(EXTD, exist_ok=True)

re_slv = re.compile(r"\[T2slv\] t=([\d.]+) phase=(\d+) init_cost=([\d.eE+-]+) final_cost=([\d.eE+-]+) iters=(\d+) term=(\d+) slv_ms=([\d.]+)")
re_diag = re.compile(r"\[T2diag\] t=([\d.]+) P=\[([^\]]*)\] V=\[([^\]]*)\] \|Bas\|=([\d.eE+-]+).*track=(\d+)")
re_goal = re.compile(r"^GOAL\s+([\d.]+)\s+seq=(\d+)")

def med(a):
    a = np.asarray(a, dtype=float)
    return float(np.median(a)) if len(a) else float("nan")

def worst_window_ratio(t, v, t0, t1, base, win=20.0):
    """最差滑窗(窗内中位/基线)比值, 窗口在 [t0,t1] 内滑动; 若区间<win 用整段."""
    m = (t >= t0) & (t <= t1)
    if m.sum() < 3 or not base or base <= 0:
        return float("nan"), float("nan")
    tt, vv = t[m], v[m]
    span = tt[-1] - tt[0]
    if span <= win:
        r = med(vv) / base
        return r, float(tt[0])
    worst_r, worst_t = 0.0, float("nan")
    j = 0
    for i in range(len(tt)):
        while tt[i] - tt[j] > win:
            j += 1
        if tt[i] - tt[j] >= win * 0.5:  # 半窗起算
            r = med(vv[j:i + 1]) / base
            if r > worst_r:
                worst_r, worst_t = r, float(tt[j])
    return worst_r, worst_t

def lift_onset(t, v, base, k=2.0, hold=5.0):
    """首个进入 >=k*base 且持续 hold 秒的起点."""
    if not base or base <= 0:
        return float("nan")
    thr = k * base
    n = len(t)
    for i in range(n):
        if v[i] >= thr:
            m = (t >= t[i]) & (t <= t[i] + hold)
            seg = v[m.to.make_array() if hasattr(m, 'to') else m] if False else v[(t >= t[i]) & (t <= t[i] + hold)]
            if len(seg) and np.min(seg) >= thr:
                return float(t[i])
    return float("nan")

rows_out = []
for R in RUNS:
    name = os.path.basename(R)[len("run_"):]
    slv, dgm = [], []
    try:
        with open(os.path.join(R, "simvins.log"), errors="replace") as f:
            for line in f:
                if "[T2slv]" in line:
                    m = re_slv.search(line)
                    if m:
                        slv.append((float(m.group(1)), float(m.group(3)), float(m.group(4)), int(m.group(5)), int(m.group(6)), float(m.group(7))))
                elif "[T2diag]" in line:
                    m = re_diag.search(line)
                    if m:
                        vv = [float(x) for x in m.group(3).split()]
                        dgm.append((float(m.group(1)), float(m.group(4)), int(m.group(5)), float(np.linalg.norm(vv))))
    except FileNotFoundError:
        continue
    if not slv or not dgm:
        rows_out.append(dict(round=name, note="no_slv_or_diag"))
        continue
    t_s = np.array([x[0] for x in slv]); c_i = np.array([x[1] for x in slv])
    t_d = np.array([x[0] for x in dgm]); bas = np.array([x[1] for x in dgm])
    trk = np.array([x[2] for x in dgm]); vel = np.array([x[3] for x in dgm])
    # 统一采样: 用 T2diag 作主轴(10Hz), cost 就近前向填充
    t_axis = t_d
    cost = c_i[np.searchsorted(t_s, t_axis, side="right") - 1]
    cost = np.where(np.isnan(cost), np.nan, cost)
    # 事件: goal0
    t_goal0 = float("nan")
    try:
        with open(os.path.join(R, "goal_trace.tsv"), errors="replace") as f:
            for line in f:
                m = re_goal.match(line)
                if m:
                    t_goal0 = float(m.group(1)); break
    except FileNotFoundError:
        pass
    # 起飞: |V|>0.3 连3样本(在 goal0 前); 到达: goal0 后 |V|<0.15 连2s
    t_to = float("nan")
    run3 = 0
    for i in range(len(t_axis)):
        if vel[i] > 0.3:
            run3 += 1
            if run3 >= 3:
                t_to = float(t_axis[i - 2]); break
        else:
            run3 = 0
    t_arr = float("nan")
    if not np.isnan(t_goal0):
        run2 = 0
        started = False
        for i in range(len(t_axis)):
            if t_axis[i] <= t_goal0:
                continue
            if vel[i] > 0.5:
                started = True
            if started:
                if vel[i] < 0.15:
                    run2 += 1
                    if run2 >= 2:
                        t_arr = float(t_axis[i - 1]); break
                else:
                    run2 = 0
    # 阶段
    t0s = float(t_s[0])
    phase = np.full(len(t_axis), "GROUND", dtype=object)
    phase[t_axis < t0s] = "INIT"
    if not np.isnan(t_to):
        phase[(t_axis >= t_to)] = "TRANSIT"
    if not np.isnan(t_goal0):
        phase[(t_axis >= t_goal0)] = "GOAL"
    if not np.isnan(t_arr):
        phase[t_axis >= t_arr] = "POST"
    # 基线窗 + lift
    bm = (t_axis >= t0s + 5) & (t_axis <= t0s + 25)
    base_cost = med(cost[bm]) if bm.sum() >= 5 else med(cost[t_axis >= t0s])
    base_bas = med(bas[bm]) if bm.sum() >= 5 else med(bas[t_axis >= t0s])
    fly = t_axis >= (t_to if not np.isnan(t_to) else t0s)
    lc, lct = worst_window_ratio(t_axis, cost, t_axis[fly][0] if fly.any() else t0s, t_axis[-1], base_cost)
    lb, lbt = worst_window_ratio(t_axis, bas, t_axis[fly][0] if fly.any() else t0s, t_axis[-1], base_bas)
    on_c = lift_onset(t_axis, cost, base_cost)
    on_b = lift_onset(t_axis, bas, base_bas)
    # 分阶段分位
    def q(mask, arr, q_):
        return float(np.quantile(arr[mask], q_)) if mask.sum() >= 3 else float("nan")
    seg = {}
    for ph in ("INIT", "GROUND", "TRANSIT", "GOAL", "POST"):
        pm = phase == ph
        seg[ph] = (q(pm, cost, .5), q(pm, cost, .9), q(pm, bas, .5), q(pm, bas, .9), int(pm.sum()))
    # 落盘 per-round csv
    with open(EXTD + "/%s.csv" % name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "cost", "bas", "track", "vel", "phase"])
        for i in range(len(t_axis)):
            w.writerow(["%.3f" % t_axis[i], "%.4g" % cost[i] if not np.isnan(cost[i]) else "", "%.6g" % bas[i], trk[i], "%.3f" % vel[i], phase[i]])
    rows_out.append(dict(
        round=name, n_slv=len(slv), n_diag=len(dgm),
        t_init_done="%.1f" % t0s, t_goal0="%.1f" % t_goal0 if not np.isnan(t_goal0) else "NA",
        t_takeoff="%.1f" % t_to if not np.isnan(t_to) else "NA",
        t_arrive="%.1f" % t_arr if not np.isnan(t_arr) else "NA",
        base_cost="%.4g" % base_cost if base_cost == base_cost else "NA",
        base_bas="%.4g" % base_bas if base_bas == base_bas else "NA",
        lift_cost="%.2f" % lc if lc == lc else "NA", lift_cost_t="%.1f" % lct if lct == lct else "NA",
        lift_bas="%.2f" % lb if lb == lb else "NA", lift_bas_t="%.1f" % lbt if lbt == lbt else "NA",
        onset_cost="%.1f" % on_c if on_c == on_c else "NA",
        onset_bas="%.1f" % on_b if on_b == on_b else "NA",
        c_gnd_p90="%.4g" % seg["GROUND"][1] if seg["GROUND"][1] == seg["GROUND"][1] else "NA",
        c_goal_p50="%.4g" % seg["GOAL"][0] if seg["GOAL"][0] == seg["GOAL"][0] else "NA",
        c_goal_p90="%.4g" % seg["GOAL"][1] if seg["GOAL"][1] == seg["GOAL"][1] else "NA",
        c_post_p90="%.4g" % seg["POST"][1] if seg["POST"][1] == seg["POST"][1] else "NA",
        b_goal_p90="%.6g" % seg["GOAL"][3] if seg["GOAL"][3] == seg["GOAL"][3] else "NA",
        b_post_p90="%.6g" % seg["POST"][3] if seg["POST"][3] == seg["POST"][3] else "NA",
        note=""))

keys = ["round", "n_slv", "n_diag", "t_init_done", "t_goal0", "t_takeoff", "t_arrive",
        "base_cost", "base_bas", "lift_cost", "lift_cost_t", "lift_bas", "lift_bas_t",
        "onset_cost", "onset_bas", "c_gnd_p90", "c_goal_p50", "c_goal_p90", "c_post_p90",
        "b_goal_p90", "b_post_p90", "note"]
with open(OUTD + "/x5_metrics.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, delimiter="\t")
    w.writeheader()
    for r in rows_out:
        w.writerow({k: r.get(k, "") for k in keys})
print("extracted rounds:", len(rows_out), "-> ", OUTD)
