#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_warmup_greenrate_table.py — 1c 预热对照批 T3 统计面（格级前后绿率对比表）v1.0
T3 v10.9 单元2 判读支持件;判据正源=INPUTFACE/1b_bias_route/1b_bias_three_prereg_v1.md §2.3（冻结逐字）:
  判定: 预热臂绿率提升 ≥15pp 且配对方向一致 ≥6/8 → 有效; 否则如实登记。
  副=bias 收敛曲线(预热段末 |d(Ba)/dt| 末2s 均值 < 初2s 均值的 20% 判"已收敛"——收敛指标定义冻结)。
口径声明: 绿=RESULT PASS(判读链 t1_warmup_pair_verdict.py 同源); A=预热臂 B=无预热对照臂。
输入=warmup_pairs.csv(T1 判读产物; 复验批同 schema 直接换 --pairs);
bias 收敛列=subprocess 复用 t1_warmup_bias_convergence.py(冻结口径单一源, 禁本文件重写公式)。
输出=repo 正源 t3_results/warmup_greenrate_<label>_<date>.{csv,md}(v10.9 单元1 目录收敛约定)。
"""
import argparse, csv, os, subprocess, sys, datetime
from collections import defaultdict

GEN_VERSION = "t3_warmup_greenrate_table_v1.0 (T3 v10.9 单元2; OUT=repo 正源)"
CONV_TOOL = os.path.expanduser("~/sitl_sim/t2_tools/t1_warmup_bias_convergence.py")

def green(r):
    return r is not None and r.get("verdict") == "PASS"

def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def bias_conv(run_root, tag):
    """复用冻结口径收敛器; run 目录=glob(run_<tag>_*) 容纳无时间戳 tag; 返回 flag 文本。"""
    import glob as _g
    if not (os.path.isfile(CONV_TOOL) and tag):
        return "NA"
    cands = _g.glob(os.path.join(run_root, "run_" + tag)) + \
            _g.glob(os.path.join(run_root, "run_" + tag + "_*"))
    if not cands:
        return "NO-RUNDIR"
    try:
        p = subprocess.run([sys.executable, CONV_TOOL, sorted(cands)[-1]],
                           capture_output=True, text=True, timeout=120)
        out = (p.stdout or "").strip().splitlines()
        flag = "NA"
        for ln in out:
            if "CONVERGED" in ln.upper():
                flag = "CONVERGED" if "NOT" not in ln.upper() else "NOT-CONVERGED"
        return flag
    except Exception:
        return "ERR"

def main():
    ap = argparse.ArgumentParser(description="预热对照批格级绿率统计面; " + GEN_VERSION)
    ap.add_argument("--pairs", default=os.path.expanduser(
        "~/sitl_sim/t1_evidence/v11_31_2026-10-08/unit1_greenrate/warmup_pairs.csv"))
    ap.add_argument("--runs-root", default=os.path.expanduser("~/sitl_sim/vins_smoke_runs"))
    ap.add_argument("--label", default="batch1_v1131")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/catkin_ws/sitl_sim/t3_results"))
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--no-bias", action="store_true", help="跳过 bias 收敛复算(纯表模式)")
    ap.add_argument("--version", action="version", version=GEN_VERSION)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.pairs, encoding="utf-8-sig")))
    pairs = defaultdict(dict)
    for r in rows:
        pairs[r["cell"]][r["arm"]] = r
    cells = sorted(pairs)

    csv_rows, md = [], []
    n_pairs = a_green = b_green = a_fav = diverged = 0
    jbetter = jworse = 0
    for c in cells:
        A, B = pairs[c].get("A"), pairs[c].get("B")
        if not A or not B:
            csv_rows.append(dict(cell=c, note="INCOMPLETE-PAIR(A=%s B=%s)" % (bool(A), bool(B))))
            continue
        n_pairs += 1
        ga, gb = green(A), green(B)
        a_green += ga; b_green += gb
        if ga and not gb:
            a_fav += 1
        if ga != gb:
            diverged += 1
        ja, jb = fnum(A.get("jump")), fnum(B.get("jump"))
        if ja is not None and jb is not None:
            if ja < jb: jbetter += 1
            elif ja > jb: jworse += 1
        # bias 收敛(A 臂=预热段有效面; B 臂对照)
        ba = "SKIP" if a.no_bias else bias_conv(a.runs_root, A.get("tag", ""))
        bb = "SKIP" if a.no_bias else bias_conv(a.runs_root, B.get("tag", ""))
        csv_rows.append(dict(
            cell=c, A_tag=A.get("tag"), A_verdict=A.get("verdict"), A_green=int(ga),
            A_jump=A.get("jump"), A_arrive=A.get("arrive"), A_warmup_goals=A.get("warmup_goals"),
            A_bias_conv=ba,
            B_tag=B.get("tag"), B_verdict=B.get("verdict"), B_green=int(gb),
            B_jump=B.get("jump"), B_arrive=B.get("arrive"),
            pair_dir="A优" if (ga and not gb) else ("B优" if (gb and not ga) else "同"),
        ))

    rate_a = 100.0 * a_green / n_pairs if n_pairs else 0.0
    rate_b = 100.0 * b_green / n_pairs if n_pairs else 0.0
    pp = rate_a - rate_b
    need_pp, need_dir = 15.0, (6, 8)
    eff_pp = pp >= need_pp
    eff_dir = a_fav >= need_dir[0] and n_pairs >= need_dir[1]
    verdict = "EFFECTIVE(进 M 阈值细化)" if (eff_pp and eff_dir) else \
              ("NOT-EFFECTIVE(如实登记)" if n_pairs >= need_dir[1] else "样本不足(如实登记)")
    # 新病面预案面: 预热自伤登记(A 绿<B 绿 且 jump A 劣化)
    selfharm = (pp <= -15.0)

    out_base = os.path.join(a.out_dir, "warmup_greenrate_%s_%s" % (a.label, a.date))
    fn = ["cell", "A_tag", "A_verdict", "A_green", "A_jump", "A_arrive",
          "A_warmup_goals", "A_bias_conv", "B_tag", "B_verdict", "B_green",
          "B_jump", "B_arrive", "pair_dir"]
    with open(out_base + ".csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=fn, extrasaction="ignore")
        w.writeheader(); w.writerows(csv_rows)

    md.append("# 1c 预热对照批·格级前后绿率对比表（T3 统计面 %s）" % a.label)
    md.append("")
    md.append("> 生成器 %s | 输入=%s | 生成 %s" % (
        GEN_VERSION, a.pairs, datetime.datetime.now().strftime("%F %T")))
    md.append("> 判据正源=1b_bias_three_prereg_v1.md §2.3 冻结逐字: **预热臂绿率提升 ≥15pp 且配对方向一致 ≥6/8 → 有效**; "
              "副=bias 收敛(末2s |d(Ba)/dt| 均值 < 初2s 均值 20% 判已收敛, 口径冻结, 收敛器=t1_warmup_bias_convergence.py 复用)。")
    md.append("> 口径: 绿=RESULT PASS; A=预热臂, B=无预热对照。")
    md.append("")
    md.append("| cell | A(verdict/jump/arrive/bias收敛) | B(verdict/jump/arrive) | 对方向 |")
    md.append("|---|---|---|---|")
    for r in csv_rows:
        if "note" in r:
            md.append("| %s | %s | | |" % (r["cell"], r["note"])); continue
        md.append("| %s | %s %s j=%s arr=%s bc=%s | %s %s j=%s arr=%s | %s |" % (
            r["cell"], r["A_verdict"], "绿" if r["A_green"] == "1" else "",
            r["A_jump"], r["A_arrive"], r["A_bias_conv"],
            r["B_verdict"], "绿" if r["B_green"] == "1" else "",
            r["B_jump"], r["B_arrive"], r["pair_dir"]))
    md.append("")
    md.append("## 判据应用（冻结口径逐字套用）")
    md.append("")
    md.append("- A(预热)绿率 **%d/%d=%.1f%%** vs B(无预热) **%d/%d=%.1f%%** → 提升 **%+.1fpp**（判据 ≥+15pp: **%s**）"
              % (a_green, n_pairs, rate_a, b_green, n_pairs, rate_b, pp, "满足" if eff_pp else "不满足"))
    md.append("- 配对方向（A 优向）**%d/%d**（判据 ≥6/8: **%s**; 方向分化对合计 %d, 其中 B 单绿 %d）"
              % (a_fav, n_pairs, "满足" if eff_dir else "不满足", diverged, b_green if a_green == 0 else diverged - a_fav))
    md.append("- 副指标 jump: A<B %d 对 / A>B %d 对（登记不判 PASS/FAIL）" % (jbetter, jworse))
    md.append("- **判决: %s**" % verdict)
    if selfharm:
        md.append("- 新病面预案触发登记: **预热自伤面**（%+.1fpp ≤ −15pp; 预注册 §2.3 分型登记条款兑现）" % pp)
    open(out_base + ".md", "w", encoding="utf-8").write("\n".join(md) + "\n")

    print("\n".join(md[-8:]))
    print("-> %s.{csv,md}" % out_base)

if __name__ == "__main__":
    main()
