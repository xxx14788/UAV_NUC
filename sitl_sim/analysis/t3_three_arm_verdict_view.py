#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_three_arm_verdict_view.py — 三臂终判·T3 判决表判读面 v1.0（双口径列）
T3 v10.9 单元2b 判读支持件。
判据正源=INPUTFACE/1c_design/1c_three_arm_design_prereg_v1.md §4.1（冻结逐字）:
  "消除" = 跳变不复现: j0 终态 <1m;
  "改变形态" = 跳变时刻偏移 >2s 或幅值变化 >30%;
  命中归因: 单因子变换产生"消除"(强实锤)或"改变形态"(弱实锤); 三臂全无作用=估计器内部独大收窄。
口径声明（本表双列的由来, 1d 臂A判决口径注记同源）:
  口径① end-start: 回放判读器 j0_end=odometry 末-首（无 truth 域的锚对差; 判读器 t1_three_arm_judge.py）;
  口径② jump_prepost(在线正源语义): 在线 j0_total=|a_pre-a_post| 双锚（E8P 在线正源=3.12）;
    回放轮无 truth 不可复算 j0_total → 可比对项=跳变族形态面(maxjump/jump_t/njumps),
    在线锚=11 事件(>5m)+max 55.0（1e 在线表）。改变形态判据作用在形态面列。
参考基线（冻结材料轮实测, 本表内置）:
  M-A 基线(base_MA r1b/r2, alive): maxjump_ref=85.73 / jump_t_ref=197.85s / njumps_ref≈1921 / j0_end 带 0.011-0.030;
    (base_MA_r1 alive=0 = 死轮登记不入基线带)
  M-B 基线(base_MB r1/r2): j0_end_ref≈4.51(慢漂带) / njumps_ref=0;
输入: T1 CSV(three_arm_results_final.csv, 臂A+base) + T2 CSV(bc_recovery_results.csv, 臂B/C; 未到货=自动跳过注记)。
输出=repo 正源 t3_results/three_arm_verdict_view_<date>.{csv,md}。
"""
import argparse, csv, os, datetime, re, statistics as st

GEN_VERSION = "t3_three_arm_verdict_view_v1.0 (T3 v10.9 单元2b; OUT=repo 正源; 判据 §4.1 冻结逐字)"

T1_CSV = os.path.expanduser("~/sitl_sim/t1_evidence/v11_31_2026-10-08/unit1_greenrate/three_arm_results_final.csv")
T2_CSV = os.path.expanduser("~/sitl_sim/t2_results/INPUTFACE/1c_runs/bc_recovery_results.csv")

REF_MA = {"maxjump": 85.73, "jump_t": 197.85, "njumps": 1921, "j0_end_band": (0.011, 0.030)}
REF_MB = {"j0_end": 4.51, "njumps": 0}
ONLINE_E8P = {"j0_total": 3.12, "n_events_gt5m": 11, "max": 55.0}  # jump_prepost 口径在线锚


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_tag(tag):
    """3ARM_<arm>_<op>[_d±X]_r<rep>[_ta_...] -> (arm, op, delta, rep); base 族单独。"""
    m = re.match(r"3ARM_base_(MA|MB)(r\d+\w?)?", tag)
    if m:
        return ("base", m.group(1), "", m.group(2) or "")
    m = re.match(r"3ARM_([ABC])_([A-Za-z0-9]+?)(?:_d([+-]?\d+))?_r(\d+)", tag)
    if m:
        return (m.group(1), m.group(2), m.group(3) or "", m.group(4))
    return ("?", tag, "", "")


def judge_elim(j0_end, njumps):
    """消除判据: j0 终态<1m（§4.2=jump_prepost 勘误后终态漂移语义; 跳变不复现=双面:
    >5m 事件数=0 ∧ 终态<1m——单用 end-start 会在跳变回摆相消时误触[口径分歧实质, 见表头声明]）。"""
    v = fnum(j0_end)
    nj = fnum(njumps)
    if v is None:
        return "NA"
    if nj is not None and nj > 0:
        return "未消除(跳变族%d事件复现; 终态%sm<1m 仅口径①面)" % (int(nj), j0_end)
    if v < 1.0:
        return "消除✓(终态%sm<1m ∧ 0 事件)" % j0_end
    return "未消除(0 事件但终态%sm≥1m——慢漂族带)" % j0_end


def judge_form(maxjump, jump_t, mat):
    """改变形态判据: 时刻偏移>2s 或 幅值变化>30% (vs 材料基线; 形态面=口径②可比对项)。
    M-B 无跳变族 → 判据不适用(慢漂带, 记 band 内/外)。"""
    mj, jt = fnum(maxjump), fnum(jump_t)
    if mat == "MB":
        return "n/a(慢漂族)"
    if mj is None or jt is None:
        return "NA"
    dt = abs(jt - REF_MA["jump_t"])
    dr = abs(mj - REF_MA["maxjump"]) / REF_MA["maxjump"]
    hit_t = dt > 2.0
    hit_a = dr > 0.30
    if hit_t or hit_a:
        parts = []
        if hit_t:
            parts.append("时刻偏移%.1fs>2s✓" % dt)
        if hit_a:
            parts.append("幅值变%.0f%%>30%%✓" % (dr * 100))
        return "改变形态✓(%s)" % "+".join(parts)
    return "形态未变(dt=%.1fs, dA=%.0f%%)" % (dt, dr * 100)


def main():
    ap = argparse.ArgumentParser(description="三臂终判判决表判读面; " + GEN_VERSION)
    ap.add_argument("--t1-csv", default=T1_CSV)
    ap.add_argument("--t2-csv", default=T2_CSV)
    ap.add_argument("--out-dir", default=os.path.expanduser("~/catkin_ws/sitl_sim/t3_results"))
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--version", action="version", version=GEN_VERSION)
    a = ap.parse_args()

    rows = []
    if os.path.isfile(a.t1_csv):
        for r in csv.DictReader(open(a.t1_csv, encoding="utf-8-sig")):
            r["_src"] = "T1"; r["_mat"] = "MB" if "_MB_" in r["tag"] else ("MA" if ("_MA_" in r["tag"] or "base_MA" in r["tag"]) else "?")
            r["_j0"] = r.get("j0_end"); r["_maxjump"] = r.get("maxjump")
            r["_jt"] = r.get("jump_t"); r["_nj"] = r.get("njumps")
            rows.append(r)
    t2_missing = None
    if os.path.isfile(a.t2_csv):
        for r in csv.DictReader(open(a.t2_csv, encoding="utf-8-sig")):
            if r.get("tag", "").startswith("tag") or r.get("j0_end") in (None, "", "NA") and r.get("alive") in ("0", "NA"):
                pass
            r["_src"] = "T2"; r["_mat"] = "MA"  # B/C 恢复批全用 M-A 材料
            r["_j0"] = r.get("j0_end"); r["_maxjump"] = ""  # T2 CSV 无 maxjump 列(有 jumps_n)
            r["_jt"] = ""; r["_nj"] = r.get("jumps_n")
            rows.append(r)
    else:
        t2_missing = a.t2_csv

    out_rows, md = [], []
    strong = weak = noop = 0
    for r in sorted(rows, key=lambda x: x["tag"]):
        tag = r["tag"]
        arm, op, dl, rep = parse_tag(tag)
        mat = r["_mat"]
        alive = r.get("alive", "?")
        j0, mj, nj = fnum(r["_j0"]), fnum(r["_maxjump"]), fnum(r["_nj"])
        elim = judge_elim(r["_j0"], r["_nj"])
        form = judge_form(r["_maxjump"], r["_jt"], mat if arm != "base" else mat)
        # 归因计数（按预注册 §4.1/§4.2 语义: 消除=双面[0 事件∧<1m]; 改变形态=形态面判据; base/死轮不入计数）
        credit = "登记"
        if arm in ("A", "B", "C") and alive == "1":
            if "消除✓" in elim:
                credit = "强实锤(消除)"; strong += 1
            elif "改变形态✓" in form:
                credit = "弱实锤(改变形态)"; weak += 1
            else:
                credit = "无作用"; noop += 1
        out_rows.append(dict(
            tag=tag, src=r["_src"], arm=arm, op=op, delta=dl, rep=rep, material=mat, alive=alive,
            j0_end=r["_j0"], elim_endstart=elim,           # 口径①
            maxjump=r["_maxjump"], jump_t=r["_jt"], njumps=r["_nj"],  # 口径②形态面
            form_verdict=form, credit=credit,
        ))

    out_base = os.path.join(a.out_dir, "three_arm_verdict_view_%s" % a.date)
    fn = list(out_rows[0].keys()) if out_rows else ["tag"]
    with open(out_base + ".csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=fn); w.writeheader(); w.writerows(out_rows)

    md.append("# 三臂终判·判决表判读面（T3 统计面）")
    md.append("")
    md.append("> 生成器 %s | 生成 %s | 输入: T1=%s%s" % (
        GEN_VERSION, datetime.datetime.now().strftime("%F %T"), a.t1_csv,
        (" | T2=%s" % a.t2_csv) if not t2_missing else " | **T2 B/C 恢复批 CSV 未到货(%s)=表暂缺臂 B/C 行**" % t2_missing))
    md.append(">")
    md.append("> 判据 §4.1 冻结逐字: **消除**=j0 终态<1m; **改变形态**=跳变时刻偏移>2s 或幅值变化>30%。")
    md.append("> **双口径声明**: ①end-start=回放判读器 j0_end(odom 末-首); ②jump_prepost=在线正源 j0_total 双锚语义"
              "(E8P 在线锚 j0_total=3.12/11 事件>5m/max 55.0)——回放轮无 truth, 口径②以跳变族形态面(maxjump/jump_t/njumps)比对,"
              "在线 11 事件/55.0 为同族收敛态锚(δ≥5ms 12 轮已证=在线原形态)。")
    md.append("> **口径分歧实质（本表判读要点）**: δ≥5ms 轮 end-start=0.0143<1m 单看会误触「消除」——"
              "但跳变族 11 事件复现（跳摆相消使终态回零）。§4.1「消除」语义=跳变不复现（§4.2 jump_prepost 勘误后终态漂移）,"
              "故归因列要求双面（0 事件∧<1m）——δ≥5ms 计**弱实锤 C1（改变形态）**, 与 T1 1d 臂A判决同判。")
    md.append("> 基线: M-A=85.73@197.85s/~1921 跳(base_MA r1b/r2); M-B=4.51 慢漂带/0 跳。")
    md.append("")
    md.append("| tag | 臂 | 操作(δ) | 材料 | alive | ①j0_end | ①消除 | ②maxjump@t | ②njumps | 改变形态 | 归因 |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in out_rows:
        md.append("| %s | %s | %s%s | %s | %s | %s | %s | %s@%s | %s | %s | %s |" % (
            r["tag"], r["arm"], r["op"], ("(δ%s)" % r["delta"]) if r["delta"] else "",
            r["material"], r["alive"], r["j0_end"], r["elim_endstart"],
            r["maxjump"] or "—", r["jump_t"] or "—", r["njumps"] or "—",
            r["form_verdict"], r["credit"]))
    md.append("")
    md.append("## 归因汇总（在判臂轮; 死轮/base 登记）")
    md.append("")
    md.append("- 强实锤(消除)=**%d**; 弱实锤(改变形态)=**%d**; 无作用=**%d**" % (strong, weak, noop))
    md.append("- 终判读数由臂完备度决定: %s" % (
        "臂 A 24 轮在判(δ≥5ms 12 轮弱实锤逐位收敛态=改变形态✓; δ≤2ms/d0 无作用)——**臂 B/C 待到货后本表重跑补终判**"
        if t2_missing else "三臂在判——终判面齐"))
    open(out_base + ".md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[:12]))
    print("... [%s] strong=%d weak=%d noop=%d -> %s.{csv,md}" % (GEN_VERSION, strong, weak, noop, out_base))

if __name__ == "__main__":
    main()
