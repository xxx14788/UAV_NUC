#!/usr/bin/env python3
# T1 v11.39 单元2d — 实机域五袋估计质量判读(r2 四袋+scen0 静置;判读面=odom 轨迹)
# 预期行为表(任务书 v11.39 冻结):
#   scen0 静置   : 零位移(<0.05m)+零跳变
#   scen1 微抖   : 零位移(<0.05m)+零跳变 (微动不触发爆=USB 劣化数据污染归因的对照臂)
#   scen2 缓动   : 平滑轨迹+端点漂移量化;慢漂分量分解=实机域 transit/慢淋首观测
#   scen3 走动   : 米级位移+往返漂移量化(去程/回程终点差)
#   scen4 平移   : 往返重复性(多趟终点散布)
# 超出预期表=异常分型登记。输出: est_quality_v1139.csv + est_quality_v1139.md(报告 v2 主体)
import rosbag, csv, os, math, sys

BAGDIR = os.path.expanduser("~/sitl_sim/t4_evidence/realmachine_pre_record/bags")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09")
BAGS = [
    ("scen0_static", "scen0_static_baseline.bag", "static"),
    ("scen1_microshake", "r2_scen1_microshake.bag", "static"),
    ("scen2_slowmove", "r2_scen2_slowmove.bag", "slowmove"),
    ("scen3_walk", "r2_scen3_walk.bag", "walk"),
    ("scen4_slide", "r2_scen4_slide.bag", "slide"),
]

def read_odom(path):
    b = rosbag.Bag(path)
    pts = []
    for topic, msg, t in b.read_messages(topics=["/vins_estimator/odometry"]):
        p = msg.pose.pose.position
        pts.append((t.to_sec(), p.x, p.y, p.z))
    b.close()
    pts.sort()
    return pts

def analyze(name, pts, kind):
    r = dict(scene=name, kind=kind, n=len(pts))
    if len(pts) < 10:
        r["note"] = "TOO_FEW_FRAMES"; return r
    t0, t1 = pts[0][0], pts[-1][0]
    dur = t1 - t0
    r["dur_s"] = round(dur, 1)
    r["rate_hz"] = round(len(pts) / dur, 1)
    # 跳变谱
    jumps = [math.dist(pts[i][1:], pts[i-1][1:]) for i in range(1, len(pts))]
    maxjump = max(jumps)
    r["maxjump_m"] = round(maxjump, 4)
    r["jumps_gt_05cm"] = sum(1 for j in jumps if j > 0.05)
    r["jumps_gt_10cm"] = sum(1 for j in jumps if j > 0.10)
    # 轨迹与包络
    pathlen = sum(jumps)
    r["pathlen_m"] = round(pathlen, 3)
    for ax, k in ((1, "x"), (2, "y"), (3, "z")):
        vs = [p[ax] for p in pts]
        r[f"env_{k}_m"] = round(max(vs) - min(vs), 4)
    p0, pe = pts[0][1:], pts[-1][1:]
    enddrift = math.dist(p0, pe)
    r["end_drift_m"] = round(enddrift, 4)
    r["drift_rate_m_per_min"] = round(enddrift / dur * 60, 4)
    # 慢漂分量分解(scen2 核心): 位置每轴最小二乘线性斜率×dur(去掉运动本身后的一阶趋势)
    # 对静态/缓动场景,斜率×dur≈总线性漂移(慢淋);走动场景此值无意义(标记 NA)
    if kind in ("static", "slowmove"):
        for ax, k in ((1, "x"), (2, "y"), (3, "z")):
            ts = [p[0] - t0 for p in pts]; vs = [p[ax] for p in pts]
            n = len(ts); ms = sum(ts) / n; mv = sum(vs) / n
            den = sum((t - ms) ** 2 for t in ts)
            slope = sum((t - ms) * (v - mv) for t, v in zip(ts, vs)) / den if den else 0
            r[f"lindrift_{k}_m"] = round(slope * dur, 4)
    # 往返结构(走动/平移): 3D 位置对起点的距离曲线,局部极大=各趟终点
    if kind in ("walk", "slide"):
        d = [math.dist(p[1:], p0) for p in pts]
        # 平滑(窗口 2s)后找局部极大(高于 0.2m 阈值,峰间距>10s)
        w = max(1, int(2 * r["rate_hz"]))
        sm = [sum(d[max(0, i - w):i + w]) / len(d[max(0, i - w):i + w]) for i in range(len(d))]
        peaks = []
        for i in range(w, len(sm) - w):
            if sm[i] >= max(sm[i - w:i + w + 1]) and sm[i] > 0.2:
                if not peaks or (pts[i][0] - pts[peaks[-1]][0]) > 10:
                    peaks.append(i)
        r["trips"] = len(peaks)
        if len(peaks) >= 2:
            pv = [math.dist(pts[i][1:], p0) for i in peaks]
            spread = max(pv) - min(pv)
            r["trip_peak_spread_m"] = round(spread, 4)
            # 相邻峰位置差(3D)=去程/回程终点差
            pairwise = [round(math.dist(pts[peaks[i]][1:], pts[peaks[i-1]][1:]), 4)
                        for i in range(1, len(peaks))]
            r["peak_pair_dists"] = "/".join(str(x) for x in pairwise[:6])
    return r

rows = []
for name, fn, kind in BAGS:
    path = os.path.join(BAGDIR, fn)
    if not os.path.isfile(path):
        rows.append(dict(scene=name, kind=kind, note="BAG_MISSING")); continue
    print(f"[read] {fn} ...", flush=True)
    pts = read_odom(path)
    r = analyze(name, pts, kind)
    rows.append(r)
    print(f"  -> n={r.get('n')} maxjump={r.get('maxjump_m')} enddrift={r.get('end_drift_m')}", flush=True)

cols = ["scene", "kind", "n", "dur_s", "rate_hz", "pathlen_m", "maxjump_m", "jumps_gt_05cm",
        "jumps_gt_10cm", "end_drift_m", "drift_rate_m_per_min", "env_x_m", "env_y_m", "env_z_m",
        "lindrift_x_m", "lindrift_y_m", "lindrift_z_m", "trips", "trip_peak_spread_m",
        "peak_pair_dists", "note"]
csvp = os.path.join(OUT, "est_quality_v1139.csv")
with open(csvp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); [w.writerow(r) for r in rows]
print("CSV ->", csvp)

# 预期行为表对照(异常分型)
EXPECT = {
    "scen0_static": ("零位移(<0.05m)+零跳变", lambda r: r.get("end_drift_m", 9) < 0.05 and r.get("jumps_gt_10cm", 9) == 0),
    "scen1_microshake": ("零位移(<0.05m)+零跳变", lambda r: r.get("end_drift_m", 9) < 0.05 and r.get("jumps_gt_10cm", 9) == 0),
    "scen2_slowmove": ("平滑轨迹+端点漂移量化(观测值入表)", lambda r: r.get("maxjump_m", 9) < 0.10),
    "scen3_walk": ("米级位移+往返漂移量化(观测值入表)", lambda r: (r.get("pathlen_m") or 0) > 5),
    "scen4_slide": ("往返重复性(观测值入表)", lambda r: r.get("maxjump_m", 9) < 0.10),
}
lines = ["# 实机域估计质量画像 v1(五袋判读原始面;报告 v2 主体素材)", ""]
for r in rows:
    name = r["scene"]; desc, chk = EXPECT.get(name, ("-", lambda r: True))
    ok = chk(r)
    lines.append(f"## {name} ({r['kind']}) — {'IN-EXPECT' if ok else 'OUT-OF-EXPECT(异常分型登记)'}")
    lines.append(f"- 预期: {desc}")
    for k in cols[2:]:
        if k in r and r[k] is not None:
            lines.append(f"- {k}: {r[k]}")
    lines.append("")
mdp = os.path.join(OUT, "est_quality_v1139.md")
open(mdp, "w").write("\n".join(lines) + "\n")
print("MD ->", mdp)
