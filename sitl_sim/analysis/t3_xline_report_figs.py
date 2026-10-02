#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3 X7 验收报告图表再生器(等待池②骨架版;X 线轮回填后成稿)

数据源:
  汇总 CSV   = t3_wa_gate.py --online --csv <csv> <run_dir>... 批量产出(列见 CSV_COLS)
  逐轮 JSON  = <run_dir>/wa_gate_online.json(xline/vins/forensics 三层)
fig 清单(X7 §9):
  fig1 逐轮判决面板(CSV 即可) | fig4 帧跳变双口径分布(CSV 即可)
  fig5 特征数分布(需逐轮 JSON) | fig2 ATE 时间线(需 bag,回填期实现)
  fig3 Bas/Bgs 时间线(需 simvins.log,回填期实现) | fig6 X5 通过率地图(X5 后实现)
matplotlib 缺失→降级 ASCII 表(NUC headless 常态;骨架自检用)。
用法:
  t3_xline_report_figs.py --csv x.csv [--runs-glob '~/sitl_sim/vins_smoke_runs/run_X*'] [--out-dir docs/figs]
  t3_xline_report_figs.py --selftest   # 合成 mini CSV 管线自检(无 matplotlib 亦过)
"""
import argparse
import csv
import glob
import json
import os
import sys

CSV_COLS = ["dir", "verdict", "four", "j0_jump", "fj_raw", "fj_smj", "j0_rev",
            "env_sig", "t1d1", "vins_pass", "reboot_n", "gaps", "coverage",
            "bas_peak", "bgs_peak", "spike_rate", "ate_rmse", "morph", "t_star"]

FIG_SPECS = {
    "fig1": "逐轮判决面板(CSV): verdict/four/j0_jump/fj_raw/fj_smj/vins_pass 网格",
    "fig2": "ATE 出生点对齐时间线(逐轮 bag odom-truth 分桶 p50/p95/max;文本版)",
    "fig3": "Bas/Bgs 时间线(逐轮 simvins.log T2diag 分桶;文本版)",
    "fig4": "帧跳变双口径分布(CSV): fj_raw vs fj_smj 散布+j0_jump 参照线",
    "fig5": "特征数 track_med 分布(逐轮 JSON vins.bas.track_med;回填期实现)",
    "fig6": "X5 场景-通过率地图(X5 单元后实现:目标×速度网格通过率)",
}

# T2diag 行(与 t3_wa_gate.py 同款口径;fig3 数据源)
import re as _re
_RE_DIAG = _re.compile(
    r"T2diag.*?\st=(-?[\d.]+).*?\|Bas\|=([\d.eE+-]+).*?\|Bgs\|=([\d.eE+-]+)"
    r".*?tic0=\[([^\]]+)\].*?track=(\d+)")


def load_csv(path):
    rows = []
    with open(path, "r", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("dir"):
                rows.append(r)
    return rows


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def render_fig1_text(rows):
    """fig1 文本版:逐轮判决面板(骨架期主产出;matplotlib 版回填期补)。"""
    lines = ["fig1(文本版) X 线逐轮判决面板",
             "%-28s %-9s %-8s %7s %6s %6s %6s %5s %6s" %
             ("dir", "verdict", "four", "j0jump", "fjraw", "fjsmj", "reboot",
              "t1d1", "ate")]
    for r in rows:
        lines.append("%-28s %-9s %-8s %7s %6s %6s %6s %5s %6s" % (
            r.get("dir"), r.get("verdict"), r.get("four"), r.get("j0_jump"),
            r.get("fj_raw"), r.get("fj_smj"), r.get("reboot_n"),
            r.get("t1d1"), r.get("ate_rmse")))
    n = len(rows)
    npass = sum(1 for r in rows if r.get("verdict") == "PASS")
    nt1d1 = sum(1 for r in rows if str(r.get("t1d1")) == "1")
    nvins = sum(1 for r in rows if str(r.get("vins_pass")) == "True")
    lines.append(f"小计: {n} 轮 / PASS {npass} / T1-D1 域 {nt1d1} / vins 域健康 {nvins}")
    return "\n".join(lines)


def render_fig4_text(rows):
    raws = [fnum(r.get("fj_raw")) for r in rows]
    smjs = [fnum(r.get("fj_smj")) for r in rows]
    js = [fnum(r.get("j0_jump")) for r in rows]
    def stat(v, fmt=".0f"):
        v = [x for x in v if x is not None]
        if not v:
            return "n=0"
        v.sort()
        return (f"n={len(v)} min={min(v):{fmt}} med={v[len(v)//2]:{fmt}} "
                f"max={max(v):{fmt}} ≥1 轮占比={sum(1 for x in v if x >= 1)/len(v):.0%}")
    return ("fig4(文本版) 帧跳变双口径分布\n"
            f"  fj_raw : {stat(raws)}\n  fj_smj : {stat(smjs)}\n"
            f"  j0_jump: {stat(js, '.2f')}  (锚差口径;>0.5=J0 FAIL,与帧间口径双注明=红线)")


def collect_track_med(runs_glob):
    """fig5 数据:逐轮 wa_gate_online.json vins.bas.track_med(有 T2diag 的轮才有)。"""
    out = []
    for d in sorted(glob.glob(os.path.expanduser(runs_glob))):
        p = os.path.join(d, "wa_gate_online.json")
        if not os.path.exists(p):
            continue
        try:
            j = json.load(open(p, "r", errors="replace"))
            b = (j.get("vins") or {}).get("bas") or {}
            if b.get("track_med") is not None:
                out.append((os.path.basename(d), b["track_med"]))
        except Exception:
            continue
    return out


def try_matplotlib(figs_text, out_dir):
    """回填期:matplotlib 渲染;骨架期环境无 matplotlib 则跳过(文本版已产出)。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        return True
    except ImportError:
        print("[figs] matplotlib 不可用——文本版为准(骨架期预期路径)")
        return False


def fig2_run_buckets(run_dir, bucket_s=10.0):
    """fig2 单轮:flight.bag odom+truth 单遍过滤读(红线#4),出生点对齐,分桶误差。
    返回 (name, n_pairs, rmse, t_peak, [(t0,n,p50,p95,max),...]) 或 (name, None...)。"""
    bag = os.path.join(run_dir, "flight.bag")
    if not os.path.exists(bag):
        return (os.path.basename(run_dir), None, None, None, None)
    try:
        import rosbag
        from bisect import bisect_left
        import math as _m
    except ImportError:
        return (os.path.basename(run_dir), None, None, None, None)
    odom, truth = [], []
    try:
        with rosbag.Bag(bag, "r") as b:
            for topic, msg, ts in b.read_messages(
                    topics=["/vins_estimator/odometry", "/gazebo/model_states"]):
                t = ts.to_sec() if hasattr(ts, "to_sec") else ts / 1e9
                if topic == "/vins_estimator/odometry":
                    p = msg.pose.pose.position
                    odom.append((t, p.x, p.y, p.z))
                else:
                    try:
                        i = msg.name.index("iris_stereo_vins")
                    except ValueError:
                        continue
                    p = msg.pose[i].position
                    truth.append((t, p.x, p.y, p.z))
    except Exception as e:
        print(f"[figs] fig2 读袋异常 {bag}: {e!r}", file=sys.stderr)
        return (os.path.basename(run_dir), None, None, None, None)
    if not odom or not truth:
        return (os.path.basename(run_dir), 0, None, None, None)
    ts_t = [r[0] for r in truth]
    g0 = min(truth, key=lambda r: abs(r[0] - odom[0][0]))
    off = (g0[1] - odom[0][1], g0[2] - odom[0][2], g0[3] - odom[0][3])
    t0 = odom[0][0]
    errs = []
    for t, x, y, z in odom:
        j = bisect_left(ts_t, t)
        best = None
        for k in (j - 1, j):
            if 0 <= k < len(truth) and abs(truth[k][0] - t) <= 0.2:
                if best is None or abs(truth[k][0] - t) < abs(truth[best][0] - t):
                    best = k
        if best is None:
            continue
        g = truth[best]
        errs.append((t - t0, _m.dist((x + off[0], y + off[1], z + off[2]),
                                     (g[1], g[2], g[3]))))
    if not errs:
        return (os.path.basename(run_dir), 0, None, None, None)
    import math as _m2
    rmse = _m2.sqrt(sum(e * e for _, e in errs) / len(errs))
    t_peak, e_peak = max(errs, key=lambda r: r[1])
    buckets = {}
    for t, e in errs:
        buckets.setdefault(int(t // bucket_s), []).append(e)
    rows = []
    for bk in sorted(buckets):
        v = sorted(buckets[bk])
        rows.append((bk * bucket_s, len(v), v[len(v) // 2],
                     v[int(0.95 * len(v))], v[-1]))
    return (os.path.basename(run_dir), len(errs), round(rmse, 4),
            (round(t_peak, 1), round(e_peak, 3)), rows)


def render_fig2_text(runs):
    """fig2 文本版:逐轮 ATE 时间线分桶(10s 桶 p50/p95/max;X7 §9 数据面)。"""
    lines = ["fig2(文本版) ATE 出生点对齐时间线(10s 桶;误差 m)"]
    for d in runs:
        name, n, rmse, tp, rows = fig2_run_buckets(d)
        if n is None:
            lines.append(f"  {name}: 跳过(无 flight.bag/不可读)")
            continue
        if n == 0:
            lines.append(f"  {name}: 0 配对帧")
            continue
        lines.append(f"  {name}: n={n} rmse={rmse} t_peak={tp[0]}s e_peak={tp[1]}m")
        if len(rows) <= 14:
            lines.append("    " + " | ".join(
                f"{int(b)}s:n{nb} p50~{p50:.2f} p95~{p95:.2f} max~{mx:.2f}"
                for b, nb, p50, p95, mx in rows))
        else:
            head = " | ".join(f"{int(b)}s:p95~{p95:.2f}" for b, _, _, p95, _ in rows[:8])
            tail = " | ".join(f"{int(b)}s:p95~{p95:.2f}" for b, _, _, p95, _ in rows[-4:])
            lines.append(f"    {head} … {tail}")
    return "\n".join(lines)


def render_fig3_text(runs, bucket_s=30.0):
    """fig3 文本版:逐轮 Bas/Bgs 时间线(simvins.log T2diag 分桶 p50/峰)。"""
    lines = ["fig3(文本版) Bas/Bgs 时间线(30s 桶;旧栈无 T2diag 则记跳过)"]
    for d in runs:
        p = os.path.join(d, "simvins.log")
        name = os.path.basename(d)
        if not os.path.exists(p):
            lines.append(f"  {name}: 跳过(无 simvins.log)")
            continue
        series = []
        try:
            with open(p, "r", errors="replace") as f:
                for ln in f:
                    m = _RE_DIAG.search(ln)
                    if m:
                        series.append((float(m.group(1)), float(m.group(2)),
                                       float(m.group(3)), int(m.group(5))))
        except OSError:
            pass
        if not series:
            lines.append(f"  {name}: 0 T2diag(旧栈)")
            continue
        bas = [b for _, b, _, _ in series]
        bgs = [g for _, _, g, _ in series]
        rb = max(series, key=lambda r: r[1])
        rg = max(series, key=lambda r: r[2])
        tb, vb = rb[0], rb[1]
        tg, vg = rg[0], rg[2]
        tail = sorted(b for t, b, _, _ in series if t >= series[-1][0] - 10.0)
        lines.append(f"  {name}: n={len(series)} Bas_pk={vb:.3f}@{tb:.0f}s "
                     f"Bgs_pk={vg:.4f}@{tg:.0f}s Bas_tail_med="
                     f"{(tail[len(tail)//2] if tail else -1):.3f}")
        buckets = {}
        for t, b, g, _tk in series:
            buckets.setdefault(int(t // bucket_s), []).append((b, g))
        parts = []
        for bk in sorted(buckets):
            v = buckets[bk]
            vb_ = sorted(x for x, _ in v)
            vg_ = sorted(y for _, y in v)
            parts.append(f"{int(bk*bucket_s)}s:Bas~{vb_[len(vb_)//2]:.2f}/Bgs~{vg_[len(vg_)//2]:.3f}")
        if len(parts) <= 12:
            lines.append("    " + " | ".join(parts))
        else:
            lines.append("    " + " | ".join(parts[:8]) + " … " + " | ".join(parts[-3:]))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="t3_wa_gate --online --csv 产出的汇总")
    ap.add_argument("--runs-glob", default=None, help="逐轮目录 glob(fig5)")
    ap.add_argument("--out-dir", default="docs/figs")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        # 管线自检:合成 2 行 CSV→fig1/fig4 文本渲染无异常=过(不依赖 matplotlib)
        synth = "/tmp/t3_figs_selftest.csv"
        with open(synth, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(CSV_COLS)
            w.writerow(["run_SKELETON_A", "FAIL", "0/1/1/1", "2.448", "57", "43",
                        "False", "", "1", "True", "0", "0", "1.0", "0.9808",
                        "0.00132", "0.0046", "1.8859", "数值溢出型", "6.9"])
            w.writerow(["run_SKELETON_B", "PASS", "1/1/1/1", "0.12", "0", "3",
                        "True", "", "0", "True", "0", "0", "0.98", "0.11",
                        "0.002", "0.003", "0.087", "无帧跳变", "None"])
        rows = load_csv(synth)
        ok = len(rows) == 2
        t1 = render_fig1_text(rows)
        t4 = render_fig4_text(rows)
        ok = ok and "PASS 1" in t1 and "T1-D1 域 1" in t1 and "med=43" in t4 and "med=2.45" in t4
        # fig2/fig3 文本版自检:无袋目录跳过路径+T2diag 合成解析路径
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            t2s = render_fig2_text([td])
            ok = ok and "跳过" in t2s
            with open(os.path.join(td, "simvins.log"), "w") as f:
                f.write("[T2diag] t=10.0 P=[0 0 0] V=[0 0 0] |Bas|=0.10 |Bgs|=0.002 "
                        "tic0=[0 0 0] td=0.0 track=80\n"
                        "[T2diag] t=40.0 P=[0 0 0] V=[0 0 0] |Bas|=0.20 |Bgs|=0.004 "
                        "tic0=[0 0 0] td=0.0 track=90\n")
            t3s = render_fig3_text([td])
            ok = ok and "n=2" in t3s and "Bas_pk=0.200@40s" in t3s
            print(t2s + "\n" + t3s)
        print(t1 + "\n" + t4)
        print(f"[figs-selftest] {'PASS' if ok else 'FAIL'}")
        os.remove(synth)
        sys.exit(0 if ok else 1)

    if not args.csv:
        ap.error("需要 --csv 或 --selftest")
    rows = load_csv(args.csv)
    if not rows:
        print("[figs] CSV 无有效行", file=sys.stderr)
        sys.exit(2)
    os.makedirs(args.out_dir, exist_ok=True)
    texts = {"fig1": render_fig1_text(rows), "fig4": render_fig4_text(rows)}
    if args.runs_glob:
        runs = sorted(glob.glob(os.path.expanduser(args.runs_glob)))
        tm = collect_track_med(args.runs_glob)
        if tm:
            body = "\n".join(f"  {d}: {v}" for d, v in tm)
            texts["fig5"] = f"fig5(文本版) 特征数 track_med 分布\n{body}"
        if runs:
            texts["fig2"] = render_fig2_text(runs)
            texts["fig3"] = render_fig3_text(runs)
    have_mpl = try_matplotlib(texts, args.out_dir)
    for name, txt in texts.items():
        print(txt + "\n")
        with open(os.path.join(args.out_dir, name + ".txt"), "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    spec = "\n".join(f"  {k}: {v}" for k, v in FIG_SPECS.items())
    print(f"[figs] 产出 {sorted(texts)} 至 {args.out_dir}"
          f"{' (matplotlib 渲染待回填期)' if not have_mpl else ''}\n图例:\n{spec}")


if __name__ == "__main__":
    main()
