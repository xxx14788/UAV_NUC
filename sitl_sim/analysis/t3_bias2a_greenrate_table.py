#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_bias2a_greenrate_table.py — ②a box 臂批 T3 统计面（格级 A/B 绿率对比+bias 面三层）v1.0
T3 v11.1 单元 1d；warmup_greenrate_table 复用改造（判读链同源,schema=box_pairs_v1010.csv）。
判据正源（逐字,零变动）=bias_constraint2_design_v1.md §3 + box_arm_batch_prereg_v1010.md §2:
  绿率提升 ≥15pp ∧ 方向一致(单绿对) ≥6/8 → ②a 有效;
  副指标=transit 窗 |d(Ba)/dt| 均值(层②)+域内占比 indom_pct(层①:>95%=box 物理生效);
  层③失败模式预分类:box 无效型(A≈B∨banner=0)/box 过紧型(绿率反降≥15pp)/机理负型(①生效但无改善)。
三方对照=M3 前基线(m3_prebaseline_v1.csv,今晚 B2 转录)+WU2 复验批 B 臂(warmup_pairs_v107.csv)。
输入: --pairs(默认 1b_bias_route/box_pairs_v1010.csv) --label(默认 bias2a)
输出=repo 正源 t3_results/warmup_greenrate_<label>_<date>.{csv,md}。
"""
import argparse, csv, os, datetime
from collections import defaultdict

GEN_VERSION = "t3_bias2a_greenrate_table_v1.1 (T3 v11.1 单元1d; ②a/②b 双 schema 兼容[box_banner/tlock_banner]; OUT=repo 正源)"
PREREG = ("判据正源=bias_constraint2_design_v1.md §3(c16f59c1 冻结)+box_arm_batch_prereg_v1010.md §2"
          "(批前冻结)——绿率 ≥15pp ∧ 方向 ≥6/8;判据零变动")


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_pairs(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def green(r):
    return r is not None and r.get("verdict") == "PASS"


def eff(r):
    return r is not None and r.get("verdict") in ("PASS", "FAIL")


def main():
    ap = argparse.ArgumentParser(description="②a box 臂批统计面; " + GEN_VERSION)
    ap.add_argument("--pairs", default=os.path.expanduser(
        "~/sitl_sim/t2_results/INPUTFACE/1b_bias_route/box_pairs_v1010.csv"))
    ap.add_argument("--label", default="bias2a")
    ap.add_argument("--out-dir", default=os.path.expanduser(
        "~/catkin_ws/sitl_sim/t3_results"))
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    a = ap.parse_args()

    pairs = load_pairs(a.pairs)
    by_cell = defaultdict(dict)
    for r in pairs:
        by_cell[r["cell"]][r["arm"]] = r

    rows, dir_a_better, n_pairs_valid = [], 0, 0
    ga = gb = ea = eb = 0
    for cell in sorted(by_cell):
        A, B = by_cell[cell].get("A"), by_cell[cell].get("B")
        row = dict(cell=cell,
                   A_tag=A["tag"] if A else "", A_v=(A["verdict"] if A else ""),
                   A_jump=A["jump"] if A else "", A_arrive=A["arrive"] if A else "",
                   A_indom=A.get("indom_pct", "") if A else "",
                   A_dbadt=A.get("dbadt", "") if A else "",
                   B_tag=B["tag"] if B else "", B_v=(B["verdict"] if B else ""),
                   B_jump=B["jump"] if B else "", B_arrive=B["arrive"] if B else "",
                   B_indom=B.get("indom_pct", "") if B else "",
                   B_dbadt=B.get("dbadt", "") if B else "")
        if A and B and eff(A) and eff(B):
            n_pairs_valid += 1
            ga += green(A); gb += green(B); ea += 1; eb += 1
            if (green(A) and not green(B)) or (not green(A) and not green(B) and
                    (fnum(A["jump"]) or 0) < (fnum(B["jump"]) or 9e9)):
                dir_a_better += 1
                row["pair_dir"] = "A优"
            elif green(B) and not green(A):
                row["pair_dir"] = "B优"
            else:
                row["pair_dir"] = "同"
        else:
            row["pair_dir"] = "不完整(ENV/缺臂)"
        rows.append(row)

    n = max(1, n_pairs_valid)
    ra = 100.0 * ga / n
    rb = 100.0 * gb / n
    diff = ra - rb
    valid = (diff >= 15.0 and dir_a_better >= 6) if n_pairs_valid else False
    # 层③ 失败模式预分类（判负时）; banner 列 ②a=box_banner / ②b=tlock_banner(v1.1 兼容)
    mode = ""
    if not valid:
        aindom = [fnum(r["A_indom"]) for r in rows if fnum(r.get("A_indom", "")) is not None]
        def _banner(row):
            if row is None: return "1"
            v = row.get("box_banner")
            if v is None or v == "": v = row.get("tlock_banner", "1")
            return v
        banner0 = any(_banner(by_cell[c].get("A")) == "0" for c in by_cell)
        if banner0 or (aindom and max(aindom) < 95.0):
            mode = "box 无效型嫌疑(banner=0 或 indom<95%)→配置链审计"
        elif diff <= -15.0:
            mode = "box 过紧型嫌疑(绿率反降 ≥15pp)→域值审计转 ②b"
        elif aindom and max(aindom) >= 95.0:
            mode = "机理负型嫌疑(层①生效但无改善)→漂移吸收非主因证据"
        else:
            mode = "未定(层① 数据不足)"

    out_csv = os.path.join(a.out_dir, "warmup_greenrate_%s_%s.csv" % (a.label, a.date))
    fieldns = ["cell", "A_tag", "A_v", "A_jump", "A_arrive", "A_indom", "A_dbadt",
               "B_tag", "B_v", "B_jump", "B_arrive", "B_indom", "B_dbadt", "pair_dir"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    out_md = out_csv[:-4] + ".md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# ②a box 臂批 T3 统计面 v1.0（%s）\n\n%s\n\n" % (
            datetime.datetime.now().strftime("%F %T"), PREREG))
        f.write("输入=%s（%d 行 pairs）\n\n" % (a.pairs, len(pairs)))
        f.write("## 判定\n\n- A(box) 绿率 %d/%d=%.1f%% vs B(默认) %d/%d=%.1f%% = **%+.1fpp**；"
                "方向 A 优 %d/%d\n" % (ga, n, ra, gb, n, rb, diff, dir_a_better, n_pairs_valid))
        f.write("- **判据（≥15pp ∧ ≥6/8）→ %s**\n" % ("有效 ✓" if valid else "无效（判负）"))
        if mode:
            f.write("- 层③ 失败模式预分类：%s\n" % mode)
        f.write("\n## 格级表\n\n| 格 | A 判 | A jump | A 到位 | A indom%% | A dbadt | B 判 | B jump | B 到位 | B indom%% | B dbadt | 方向 |\n|---|\n")
        for r in rows:
            f.write("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
                r["cell"], r["A_v"], r["A_jump"], r["A_arrive"], r["A_indom"], r["A_dbadt"],
                r["B_v"], r["B_jump"], r["B_arrive"], r["B_indom"], r["B_dbadt"], r["pair_dir"]))
        f.write("\n表=%s\n" % out_csv)
    print("[OUT] %s / %s" % (out_csv, out_md))
    print("A %.1f%% vs B %.1f%% = %+.1fpp; dir %d/%d -> %s %s" % (
        ra, rb, diff, dir_a_better, n_pairs_valid, "有效" if valid else "判负", mode))


if __name__ == "__main__":
    main()
