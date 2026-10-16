#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c3a_layer_stats.py — 甲合流册 §四 终版判读：单层语料五层分层统计（13m v7.3 扩展层在役; v9 primary 层预留）
输出: <evd>/LAYER_STATS.md + <evd>/layer_rounds.csv
层定义（红线⑮ 三层禁跨层并表, 本工具单层出数）:
  13m 层 = run_C3F73E1-13 + run_C3F73NE1-12（真 v7.3, world-load verified 383a301a; final_v73_jia 语料）
  v9  层 = run_C3L9*/C3F9*（试录/终版, 机器恢复后跑; --layer v9）
归族（红线⑦ 承 c6_stratified_stats 语义）: 随机族=NEVER-FLEW/起飞彩票(RESULT 域); 跳变族=j0d maxde>0.5
S 形门: 13m 层=冻结四门(infl<0.2∧ratio≥1.25∧maxlat≥0.8∧ndetour≥3); v9 层=推导五门(gate_v9_sform_all)
Wilson 95% 双侧。到位 miss=RESULT "leg1 到位(真值) min=X"。慢漂观察面=RESULT 漂移率(v1.5h 豁免 0.03 非门)。
配对带=cling_pairing_bybox 同语义（bag 真值贴窗 1.2m × simvins [T2IQG-METRIC] stereo_r 分箱）。"""
import sys, os, json, glob, math, re, bisect, statistics

CAMP = os.path.expanduser("~/sitl_sim/c3_corridor_20261013")
RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OX, OY = 1.01, 0.98

BOXES_V73 = {"cB1": (4.44, 0.94, "tag"), "cB2": (9.52, 0.12, "ctrl-Wood"), "cB3": (11.92, 1.50, "tag"),
             "cN1": (2.41, 3.25, "tag"), "cN2": (5.03, 4.16, "ctrl-Bricks"), "cN3": (5.95, 6.78, "tag")}
BOXES_V9 = {"cL1": (2.4384, 2.6629, "tag"), "cL2": (4.4607, 4.1761, "tag")}
LAYERS = {
    "13m": dict(patterns=["run_C3F73E*", "run_C3F73NE*"], evd="final_v73_jia", boxes=BOXES_V73,
                sgate=lambda g: (g["gate_min_inflated_lt_0.2"] and g["gate_ratio_ge_1.25"] and
                                 g["gate_maxlat_ge_0.8"] and g["gate_ndetour_ge_3"]),
                world_actual="v7.3 383a301a（world-load verified 25/25）"),
    "v9": dict(patterns=["run_C3F9*", "run_C3L9*"], evd=["final_v9"], boxes=BOXES_V9,
               sgate=lambda g: bool(g.get("gate_v9_sform_all")),
               world_actual="v9 5f3d48eb"),
    "v70": dict(patterns=["run_C3V7E*", "run_C3V7NE*", "run_C3VFE*", "run_C3VFNE*"],
                evd=["trial_v7", "final_v73"], boxes=BOXES_V73,
                sgate=lambda g: (g["gate_min_inflated_lt_0.2"] and g["gate_ratio_ge_1.25"] and
                                 g["gate_maxlat_ge_0.8"] and g["gate_ndetour_ge_3"]),
                world_actual="v7.0 159272bd（C66 勘误实态: C-5/C-6 两批 25 轮实载 v7.0 非 v7.3; tag=箱中心交叉纹理平面形态）"),
}

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def pct(v):
    return "%.1f%%" % (100 * v)

def main(layer):
    cfg = LAYERS[layer]
    evds = [os.path.join(CAMP, e) for e in cfg["evd"]]
    dirs = []
    for pat in cfg["patterns"]:
        dirs += sorted(glob.glob(os.path.join(RUNS, pat)))
    rows = []
    for d in dirs:
        tag = os.path.basename(d)[4:]
        base = os.path.basename(d)
        res_t = open(os.path.join(d, "RESULT.txt"), errors="ignore").read() if os.path.isfile(os.path.join(d, "RESULT.txt")) else ""
        rp = "RESULT=PASS" in res_t
        lottery = ("NEVER-FLEW" in res_t) or ("起飞彩票" in res_t)
        miss = None
        m = re.search(r"leg1 到位\(真值\) min=([0-9.]+)", res_t)
        if m: miss = float(m.group(1))
        drift = None
        m = re.search(r"漂移率 ([0-9.]+) m/s", res_t)
        if m: drift = float(m.group(1))
        jump = False
        jd = os.path.join(d, "j0_decomp.json")
        if os.path.isfile(jd):
            try:
                jump = (json.load(open(jd))["j0_decomp"].get("max_frame_de_m") or 0) > 0.5
            except Exception: pass
        g = None
        for evd in evds:
            gf = os.path.join(evd, "geom_%s.json" % base)
            if os.path.isfile(gf): g = json.load(open(gf)); break
        sgate = cfg["sgate"](g) if g else False
        th = None
        for evd in evds:
            tf = os.path.join(evd, "thrust_%s.json" % base)
            if os.path.isfile(tf): th = json.load(open(tf)); break
        to_clean = None
        if th:
            to_clean = (th.get("thrust_max_win", 9) <= 0.82 and th.get("z_peak_ext", 9) <= 1.5
                        and (th.get("thrust_n_ge_0p82", 9) or 0) == 0)
        corners, pair_by_box = [], {}
        logf = os.path.join(d, "simvins.log")
        bagf = os.path.join(d, "flight.bag")
        if os.path.isfile(logf) and os.path.isfile(bagf):
            try:
                import rosbag
                ts = []
                with rosbag.Bag(bagf, "r") as b:
                    for topic, msg, t in b.read_messages():
                        if topic == "/gazebo/model_states":
                            try: i = msg.name.index("iris_stereo_vins")
                            except ValueError: continue
                            p = msg.pose[i].position
                            ts.append((t.to_sec() - b.get_start_time(), p.x - OX, p.y - OY))
                ts.sort()
                log = open(logf, encoding="utf-8", errors="ignore").read()
                met = [(float(m.group(1)), int(m.group(2)), float(m.group(4))) for m in re.finditer(
                    r"\[T2IQG-METRIC\] t=([0-9.]+) corners=(\d+) depth_r=([0-9.]+) stereo_r=([0-9.]+)", log)]
                tkeys = [fr[0] for fr in ts]
                for t, nc, sr in met:
                    corners.append(nc)
                    i = min(bisect.bisect_left(tkeys, t), len(ts) - 1)
                    x, y = ts[i][1], ts[i][2]
                    for bn, (bx, by, kind) in cfg["boxes"].items():
                        if ((x - bx) ** 2 + (y - by) ** 2) ** 0.5 - 0.5 < 1.2:
                            pair_by_box.setdefault(bn, []).append(sr)
            except Exception as e:
                pass
        tag_sr = [v for bn, arr in pair_by_box.items() if cfg["boxes"][bn][2] == "tag" for v in arr]
        ctrl_sr = [v for bn, arr in pair_by_box.items() if cfg["boxes"][bn][2] != "tag" for v in arr]
        rows.append(dict(tag=tag, rp=rp, lot=lottery, jump=jump, sgate=sgate, miss=miss, drift=drift,
                         to_clean=to_clean, th=th, g=g, corners=sorted(corners),
                         tag_p50=statistics.median(tag_sr) if tag_sr else None,
                         ctrl_p50=statistics.median(ctrl_sr) if ctrl_sr else None,
                         n_cling=len(tag_sr) + len(ctrl_sr)))
    N = len(rows)
    lot_rows = [r for r in rows if r["lot"]]
    cond = [r for r in rows if not r["lot"]]
    jump_rows = [r for r in rows if r["jump"]]
    s_rows = [r for r in rows if r["sgate"]]
    s_cond = [r for r in cond if r["sgate"]]
    misses = [r["miss"] for r in rows if r["miss"] is not None]
    misses_s = sorted(misses)
    to_rows = [r for r in rows if r["to_clean"] is not None]
    to_clean_n = sum(1 for r in to_rows if r["to_clean"])
    out = []
    A = out.append
    A("# %s 层终版判读（甲合流册 §四; world=%s; N=%d）" % (layer, cfg["world_actual"], N))
    A("")
    A("> 生成: c3a_layer_stats.py --layer %s（%s）；语料=%s；三层禁跨层并表（红线⑮）。" %
      (layer, "2026-10-16", "+".join(evds)))
    A("")
    A("## 1. 五层分层统计（S 形门=%s）" %
      ("v9 推导五门(见 v9_design_prereg §4)" if layer == "v9"
       else "冻结四门 infl<0.2∧ratio≥1.25∧maxlat≥0.8∧ndetour≥3（13m/v7.0 层同款）"))
    A("")
    A("| 层 | 定义 | k/N | 成功率 | Wilson 95% |")
    A("|---|---|---|---|---|")
    for nm, k, n in (("L1 无条件", len(s_rows), N),
                     ("L2 条件(剔随机族)", len(s_cond), len(cond)),
                     ("L3 随机族占比", len(lot_rows), N),
                     ("L4 跳变族占比", len(jump_rows), N),
                     ("L5 S 形通过", len(s_rows), N)):
        lo, hi = wilson(k, n)
        A("| %s | — | %d/%d | %s | %s–%s |" % (nm, k, n, pct(k / n if n else 0), pct(lo), pct(hi)))
    A("")
    A("L2 明细（剔随机族后逐轮）: " + ", ".join("%s%s" % (r["tag"], "(S)" if r["sgate"] else "") for r in cond))
    A("")
    A("## 2. 到位 miss 距离分布（判=RESULT 到位门 0.75m; 0 通过=全在门上时本表=结论必引）")
    A("")
    if misses_s:
        A("- N=%d；min=%.2f p25=%.2f **中位=%.2f** p75=%.2f p90=%.2f max=%.2f（m）" %
          (len(misses_s), misses_s[0], misses_s[len(misses_s)//4], statistics.median(misses_s),
           misses_s[3*len(misses_s)//4], misses_s[int(0.9*(len(misses_s)-1))], misses_s[-1]))
        fam = {"随机族": [r["miss"] for r in lot_rows if r["miss"] is not None],
               "跳变族": [r["miss"] for r in jump_rows if not r["lot"] and r["miss"] is not None],
               "S形轮": [r["miss"] for r in s_rows if r["miss"] is not None],
               "其余(干净未过S)": [r["miss"] for r in rows if not r["lot"] and not r["jump"] and not r["sgate"] and r["miss"] is not None]}
        for k, v in fam.items():
            if v:
                vs = sorted(v)
                A("- %s: n=%d 中位=%.2f min=%.2f max=%.2f" % (k, len(vs), statistics.median(vs), vs[0], vs[-1]))
    n_arr = sum(1 for r in rows if r["rp"])
    lo, hi = wilson(n_arr, N)
    A("- 到位判(0.75m) PASS: %d/%d = %s [%.1f%%–%.1f%%]" % (n_arr, N, pct(n_arr / N), 100 * lo, 100 * hi))
    A("")
    A("## 3. 起飞面全量 thrust（H4 修复后栈; 判=max_win≤0.82∧z_peak≤1.5∧零 0.82+ 饱和）")
    A("")
    A("- 干净起飞: %d/%d（eject/NF 注记: %s）" %
      (to_clean_n, len(to_rows), ", ".join(r["tag"] for r in to_rows if r["th"] and r["th"].get("eject_flag"))))
    if to_rows:
        A("- th@8s 带: %s" % ", ".join("%.2f" % r["th"]["thrust_at_8s"] for r in to_rows if r["th"]))
        zpk = sorted(r["th"]["z_peak_ext"] for r in to_rows if r["th"])
        A("- z_peak 带: %.2f–%.2f m（判≤1.5）" % (zpk[0], zpk[-1]) if zpk else "-")
    A("")
    A("## 4. 逐轮供给/配对带（T2IQG 观察面; 贴窗 1.2m 分箱 stereo_r）")
    A("")
    A("| 轮 | corners p50 | 贴窗帧数 | tag 箱 p50 | 对照箱 p50 |")
    A("|---|---|---|---|---|")
    for r in rows:
        A("| %s | %s | %d | %s | %s |" %
          (r["tag"], "%.0f" % statistics.median(r["corners"]) if r["corners"] else "-",
           r["n_cling"], "%.2f" % r["tag_p50"] if r["tag_p50"] is not None else "-",
           "%.2f" % r["ctrl_p50"] if r["ctrl_p50"] is not None else "-"))
    tag_p50s = [r["tag_p50"] for r in rows if r["tag_p50"] is not None]
    ctrl_p50s = [r["ctrl_p50"] for r in rows if r["ctrl_p50"] is not None]
    if tag_p50s:
        A("")
        A("- tag 箱贴窗 p50 带: %.2f–%.2f（n=%d 轮有贴窗帧）；对照箱 p50 带: %s" %
          (min(tag_p50s), max(tag_p50s), len(tag_p50s),
           ("%.2f–%.2f" % (min(ctrl_p50s), max(ctrl_p50s))) if ctrl_p50s else "无对照贴窗帧"))
    A("")
    A("## 5. 慢漂观察面（非门; v1.5h 豁免 0.03 m/s=1.8 m/min）")
    A("")
    dr = sorted(r["drift"] for r in rows if r["drift"] is not None)
    if dr:
        A("- 漂移率带: %.4f–%.4f m/s（中位 %.4f）= %.2f–%.2f m/min; 豁免带(≤0.03)内轮数 %d/%d" %
          (dr[0], dr[-1], statistics.median(dr), 60 * dr[0], 60 * dr[-1],
           sum(1 for v in dr if v <= 0.03), len(dr)))
    A("")
    A("## 6. 归族总表")
    A("")
    A("| 轮 | RESULT | 随机族 | 跳变族 | S形 | 到位miss | 慢漂 m/s | 起飞干净 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in rows:
        A("| %s | %s | %s | %s | %s | %s | %s | %s |" %
          (r["tag"], "PASS" if r["rp"] else "FAIL", "√" if r["lot"] else "-", "√" if r["jump"] else "-",
           "√" if r["sgate"] else "-", "%.2f" % r["miss"] if r["miss"] is not None else "-",
           "%.4f" % r["drift"] if r["drift"] is not None else "-",
           ("√" if r["to_clean"] else "×") if r["to_clean"] is not None else "-"))
    md = "\n".join(out) + "\n"
    outdir = evds[0] if layer == "13m" else os.path.join(CAMP, "layer_%s" % layer)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "LAYER_STATS.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(outdir, "layer_rounds.csv"), "w", encoding="utf-8") as f:
        f.write("tag,result,lottery,jump,sform,miss_m,drift_ms,takeoff_clean,corners_p50,tag_p50,ctrl_p50\n")
        for r in rows:
            f.write("%s,%s,%d,%d,%d,%s,%s,%s,%s,%s,%s\n" %
                    (r["tag"], 1 if r["rp"] else 0, 1 if r["lot"] else 0, 1 if r["jump"] else 0,
                     1 if r["sgate"] else 0, r["miss"] if r["miss"] is not None else "",
                     r["drift"] if r["drift"] is not None else "",
                     ("1" if r["to_clean"] else "0") if r["to_clean"] is not None else "",
                     "%.0f" % statistics.median(r["corners"]) if r["corners"] else "",
                     "%.3f" % r["tag_p50"] if r["tag_p50"] is not None else "",
                     "%.3f" % r["ctrl_p50"] if r["ctrl_p50"] is not None else ""))
    print(md)

if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--layer") + 1] if "--layer" in sys.argv else "13m")
