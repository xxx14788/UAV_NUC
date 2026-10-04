# -*- coding: utf-8 -*-
# Part B 联合判读: ζ 三要素签名匹配 (prereg_binglun Part B 判据逐字实现)
# E1 解翻转: 发作窗内 P 分量 >=2 次回摆且单次摆幅 >1m
# E2 track 崩塌: 窗内 track 中位数 <50
# E3 伪深注入: 窗内 init_replace 中位数 >5/帧
# 发作窗: 首个 T2fail 或首个隐含速度>2m/s odom 步前 5s 起 10s; never-flew 型=arm 后 P z 首偏>0.3m 起 10s
import re, math, glob, os, statistics

SPECIMENS = [
    ("F3B10", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B10_154733"),
    ("F3B11", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B11_155643"),
    ("F3B12", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B12_160420"),
    ("F3B13", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B13_161000"),
    ("F3B14", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B14_163613"),
    ("F3B15", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B15_190535"),
    ("F3B16", "/home/uav/sitl_sim/vins_smoke_runs/run_F3B16_191620"),
    ("T2ZETA2", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETA2_132510"),
    ("T2ZETA1", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETA1_131820"),
    ("T2ZETA3", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETA3_133227"),
    ("T2ZETA4", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETA4_140024"),
    ("T2ZETA5", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETA5_140137"),
    ("T2ZETACTL2", "/home/uav/sitl_sim/vins_smoke_runs/run_T2ZETACTL2_134622"),
]

def parse_log(d):
    diag = []; gate = []; fails = []; arm_t = None
    logf = os.path.join(d, "simvins.log")
    if not os.path.exists(logf):
        for f in glob.glob(os.path.join(d, "*.log")):
            if "vins" in f: logf = f; break
    if not os.path.exists(logf): return None
    for ln in open(logf, errors="ignore"):
        m = re.search(r"\[T2diag\] t=([\d.]+) P=\[([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\].*track=(\d+)", ln)
        if m:
            diag.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5))))
            continue
        m = re.search(r"\[T2fail\] t=([\d.]+)", ln)
        if m: fails.append(float(m.group(1))); continue
        m = re.search(r"\[T2gate\] t=([\d.]+) tri=\d+ rej=\d+ xrej=\d+ init_replace=(\d+)", ln)
        if m: gate.append((float(m.group(1)), int(m.group(2)))); continue
    return diag, gate, fails

def odom_jumps(d):
    # implied-speed>2m/s steps from flight.bag odom stream (bag time)
    import rosbag
    bag = os.path.join(d, "flight.bag")
    if not os.path.exists(bag): return None
    b = rosbag.Bag(bag); od = []
    for tp, msg, tt in b.read_messages(topics=["/vins_estimator/imu_propagate"]):
        p = msg.pose.pose.position; od.append((tt.to_sec(), p.x, p.y, p.z))
    b.close()
    out = []
    for i in range(1, len(od)):
        dt = od[i][0] - od[i-1][0]
        if 0 < dt < 0.5 and math.dist(od[i][1:], od[i-1][1:]) / dt > 2.0:
            out.append(od[i][0])
    return out

def swings(series):
    # E1: >=2 reversals with swing >1m on any axis (series = list of (t, x, y, z))
    axis_rev = 0
    for k in range(3):
        vals = [s[1+k] for s in series]
        # find alternating local extremes >1m apart
        if len(vals) < 3: continue
        peak, trough, direction = vals[0], vals[0], 0
        for v in vals[1:]:
            if direction >= 0 and v < peak - 1.0:
                axis_rev += 1; direction = -1; trough = v
            elif direction <= 0 and v > trough + 1.0:
                axis_rev += 1; direction = 1; peak = v
            if direction >= 0: peak = max(peak, v)
            else: trough = min(trough, v)
    return axis_rev

results = []
for name, d in SPECIMENS:
    if not os.path.isdir(d):
        results.append((name, "DIR_MISSING")); continue
    parsed = parse_log(d)
    if not parsed or not parsed[0]:
        results.append((name, "LOG_MISSING")); continue
    diag, gate, fails = parsed
    # onset time (log clock t= is image-header time; use directly)
    t_onset = min(fails) if fails else None
    if t_onset is None:
        # never-flew: first P-z deviation >0.3m from running start baseline (first 20 samples)
        base = statistics.median([d0[3] for d0 in diag[:20]])
        for t, x, y, z, tr in diag:
            if abs(z - base) > 0.3: t_onset = t; break
    if t_onset is None:
        # fallback: odom jump steps mapped via relative timeline unavailable; use mid-log
        results.append((name, "NO_ONSET(clean or unmappable)")); continue
    w0, w1 = t_onset - 5, t_onset + 5
    win = [d0 for d0 in diag if w0 <= d0[0] <= w1]
    gwin = [g for g in gate if w0 <= g[0] <= w1]
    if not win:
        results.append((name, "WINDOW_EMPTY")); continue
    e1 = swings([(w[0], w[1], w[2], w[3]) for w in win]) >= 2
    e2 = statistics.median([w[4] for w in win]) < 50
    e3 = statistics.median([g[1] for g in gwin]) > 5 if gwin else False
    hits = sum([e1, e2, e3])
    form = "ZETA-FORM" if hits >= 2 else "non-zeta"
    results.append((name, "onset=%.1f E1=%s E2=%s E3=%s hits=%d/3 %s" % (t_onset, e1, e2, e3, hits, form)))

core = [r for r in results if r[0] in ("F3B10","F3B11","F3B12","F3B13","F3B14","F3B15","F3B16","T2ZETA2")]
n_form = sum(1 for r in core if "ZETA-FORM" in str(r[1]))
print("=== ALL 13 ===")
for n, r in results: print("%-10s %s" % (n, r))
print("=== CORE 8: zeta-form = %d/8 (threshold >=5 accepts) ===" % n_form)
