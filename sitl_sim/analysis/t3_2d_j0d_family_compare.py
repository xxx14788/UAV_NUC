#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_2d_j0d_family_compare.py — 2d(HAFIX 多场景批)轮 j0d 分型×sim 悬停自跳同族性判读面 v1.0
T3 v10.9 单元2c; 任务书措辞: "与 sim 悬停自跳同族性判读的判读面"。
谱系参照正源=t3_results/hover_lineage_verdict_v1.md（T1 v11.23 定案, 冻结口径）:
  悬停自跳族签名=transit 慢淋主导(HVNET1 复刻 j0_total 4.119=transit 3.719[90.3%]+jump 0.409, njf=4);
  导航 B 型跳(S12P)=transit 主导同微观形态; E8P 巨跳格=mixed(脉冲+慢淋复合, njf=409);
  两支族=transit 慢淋主导族 + 脉冲复合族; 净轮(j0_total<0.5)=无跳变病理。
输入: --rejudge(t2d_hafix_rejudge_<date>.csv 场景映射) --j0d(j0d_stats 最新 csv)。
输出=repo 正源 t3_results/t2d_j0d_family_<date>.{csv,md}。
"""
import argparse, csv, glob, os, datetime

GEN_VERSION = "t3_2d_j0d_family_compare_v1.0 (T3 v10.9 单元2c; 谱系参照 hover_lineage_verdict_v1 冻结)"


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def family_of(row):
    """族判定: dominant+j0_total → 同族面（谱系口径: transit 主导族/脉冲复合族/净轮）。"""
    dom = (row.get("dominant") or "").strip()
    j0 = fnum(row.get("j0_total"))
    if j0 is not None and j0 < 0.5:
        return "净轮(无跳变病理)"
    if dom == "transit":
        return "transit 慢淋主导族(与 sim 悬停自跳/导航 B 型同族)"
    if dom == "mixed":
        return "脉冲复合族(与 E8P 巨跳格同族)"
    if dom == "jump":
        return "jump 主导(单帧族——谱系两支外, 如实登记)"
    return "未定(%s)" % (dom or "?")


def main():
    ap = argparse.ArgumentParser(description="2d 轮 j0d 分型×悬停谱系同族性判读面; " + GEN_VERSION)
    ap.add_argument("--rejudge", default=None, help="t2d_hafix_rejudge_<date>.csv(缺省=自动取最新)")
    ap.add_argument("--j0d", default=None, help="j0d_stats_<date>.csv(缺省=自动取最新)")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/catkin_ws/sitl_sim/t3_results"))
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--version", action="version", version=GEN_VERSION)
    a = ap.parse_args()

    def latest(pat):
        c = sorted(glob.glob(os.path.join(a.out_dir, pat)))
        return c[-1] if c else None

    rj_p = a.rejudge or latest("t2d_hafix_rejudge_*.csv")
    j0_p = a.j0d or latest("j0d_stats_*.csv")
    if not rj_p or not j0_p:
        raise SystemExit("FAIL: 缺输入 rejudge=%s j0d=%s" % (rj_p, j0_p))

    rj = {r["round"]: r for r in csv.DictReader(open(rj_p, encoding="utf-8"))}
    j0 = {r["round"]: r for r in csv.DictReader(open(j0_p, encoding="utf-8"))}

    rows, md = [], []
    fam_cnt = {}
    scen_fam = {}
    for rnd, r in sorted(rj.items()):
        if r.get("scenario", "").startswith("非本批"):
            continue
        j = j0.get(rnd)
        if not j:
            rows.append(dict(round=rnd, scenario=r.get("scenario", ""), rep=r.get("rep", ""),
                             hafix_n=r.get("hafix_n", ""), in_j0d="否(无可用 j0_decomp=ENV-FAIL 面)",
                             j0_total="", jump_m="", transit_m="", jump_frac="", dominant="", family="无判读面"))
            fam_cnt["无判读面(ENV-FAIL)"] = fam_cnt.get("无判读面(ENV-FAIL)", 0) + 1
            continue
        fam = family_of(j)
        rows.append(dict(round=rnd, scenario=r.get("scenario", ""), rep=r.get("rep", ""),
                         hafix_n=r.get("hafix_n", ""), in_j0d="是",
                         j0_total=j.get("j0_total", ""), jump_m=j.get("jump_m", ""),
                         transit_m=j.get("transit_m", ""), jump_frac=j.get("jump_frac", ""),
                         dominant=j.get("dominant", ""), family=fam))
        fam_cnt[fam.split("(")[0]] = fam_cnt.get(fam.split("(")[0], 0) + 1
        scen_fam.setdefault(r.get("scenario", "?"), {}).setdefault(fam.split("(")[0], 0)
        scen_fam[r.get("scenario", "?")][fam.split("(")[0]] += 1

    out_base = os.path.join(a.out_dir, "t2d_j0d_family_%s" % a.date)
    fn = list(rows[0].keys()) if rows else ["round"]
    with open(out_base + ".csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=fn); w.writeheader(); w.writerows(rows)

    md.append("# 2d(HAFIX 批)轮 j0d 分型×sim 悬停自跳同族性判读面（T3）")
    md.append("")
    md.append("> 生成器 %s | 生成 %s" % (GEN_VERSION, datetime.datetime.now().strftime("%F %T")))
    md.append("> 输入: rejudge=%s | j0d=%s" % (rj_p, j0_p))
    md.append("> 谱系参照（冻结）: 悬停自跳=transit 慢淋主导族(HVNET1 复刻 90.3% transit); "
              "E8P 巨跳格=mixed 脉冲复合族; 净轮=j0_total<0.5。")
    md.append("")
    md.append("| round | 场景 | rep | HAFIX行 | 入j0d | j0_total | jump | transit | frac | dominant | 族判定 |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % tuple(
            r[k] for k in ("round", "scenario", "rep", "hafix_n", "in_j0d", "j0_total",
                           "jump_m", "transit_m", "jump_frac", "dominant", "family")))
    md.append("")
    md.append("## 分型汇总")
    md.append("")
    for k, v in sorted(fam_cnt.items(), key=lambda kv: -kv[1]):
        md.append("- %s: %d 轮" % (k, v))
    md.append("")
    md.append("## 场景×族交叉")
    md.append("")
    for s in sorted(scen_fam):
        md.append("- %s: %s" % (s, ", ".join("%s=%d" % kv for kv in sorted(scen_fam[s].items()))))
    md.append("")
    md.append("> 同族性读数: 2d 静态病理轮（S1/S2 hover+odom 死亡[HAFIX]轮）的 j0d 微观形态是否落在 "
              "transit 慢淋主导族=与 sim 悬停自跳同族; 脉冲复合族=E8P 巨跳格同族; "
              "净轮=该轮 VINS 未现跳变病理(HAFIX 事件但 j0 面净=odom 死亡≠跳变病理, 如实分栏)。")
    open(out_base + ".md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[-12:]))
    print("-> %s.{csv,md}" % out_base)

if __name__ == "__main__":
    main()
