#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_2d_hafix_rejudge.py — T1 night_chain 2d(HAFIX 多场景批)统一重判读器 v1.0
T3 v10.9 单元2d; 销 T1 C-9（t1_batch_3d.sh 判读行 grep 错文件=批 stdout 永远 0 的假象）。
正源判读面（T1 v11.32 B-0 原文口径）: 每轮 [HAFIX] 行=各轮 px4ctrl.log（非 drill stdout）;
  landed/auto_disarm=RESULT.txt（LANDING z_end<0.15 → landed; auto_disarm->N; GATEHIT-STAT chain 同步收）。
预注册判据（t1_batch_3d.sh 文末, 冻结）: 每轮 HAFIX_lines≥1 ∧ landed=1;
  场景 PASS=5/5 轮 PASS; 3d PASS=4 场景全 PASS。
场景映射: goal.txt(0.50 0.50 1.0=S1/S4; 0.50 0.50 3.0=S2; 1.01 8.98 1.0=S3)
  + S1/S4 消歧=轮时长(窗 W25/W75; bag 时长>60s 倾向 S4 land 窗)——映射表随输出落盘可审计。
输入: --runs-root(默认 vins_smoke_runs) --pattern(默认 DRILLD1_N8P_2*) --since/--until 时间过滤(HHMM)。
输出=repo 正源 t3_results/t2d_hafix_rejudge_<date>.{csv,md}。
"""
import argparse, csv, glob, os, re, datetime, subprocess

GEN_VERSION = "t3_2d_hafix_rejudge_v1.0 (T3 v10.9 单元2d; C-9 销号件; OUT=repo 正源)"


def load_summary(path):
    """解析 summary.txt '--- SCN round R HH:MM:SS ---' 行 + 批毕时刻 → [(scn, rep, dt)]; done_dt。"""
    evs, done = [], None
    if not path or not os.path.isfile(path):
        return evs, done
    for ln in open(path, errors="replace"):
        m = re.match(r"--- (\S+) round (\d+) (\d{2}:\d{2}:\d{2}) ---", ln.strip())
        if m:
            try:
                dt = datetime.datetime.strptime("20261008_" + m.group(3), "%Y%m%d_%H:%M:%S")
                evs.append((m.group(1), m.group(2), dt))
            except ValueError:
                print("[warn] summary 行时间解析失败: %r" % ln.strip()[:60])
        m2 = re.search(r"batch done (\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", ln)
        if m2:
            done = datetime.datetime.strptime(m2.group(1) + "_" + m2.group(2), "%Y-%m-%d_%H:%M:%S")
    return evs, done


def match_scenario(r, evs, done):
    """轮目录时刻 → 最近的(且在其后≤300s)场景启动事件; 批毕后落轮=非本批(D5_L2 等)。"""
    if not evs or not r["ts_dt"]:
        return scenario_of(r, r["bag_s"]), "", "goal推断"
    t = r["ts_dt"]
    if done and t > done:
        return "非本批(批毕后)", "", "batch_done=%s" % done.strftime("%H:%M:%S")
    cands = [(scn, rep) for scn, rep, dt in evs if dt <= t and (t - dt).total_seconds() <= 300]
    if not cands:
        return "?", "", "无300s内启动事件"
    scn, rep = cands[-1]
    return scn, rep, "summary映射"


def f_t(hhmmss):
    try:
        return datetime.datetime.strptime("20261008_" + hhmmss, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def parse_round(d):
    n = os.path.basename(d)
    m = re.search(r"_(\d{6})$", n)
    r = dict(round=n, ts=m.group(1) if m else "", ts_dt=f_t(m.group(1)) if m else None,
             scenario="?", rep="", hafix_n=0, hafix_maxstage=0, hafix_last="", landed="NA",
             z_end="", disarm="", gatehit_chain="", result="", goal="", bag_s="", note="")
    g = os.path.join(d, "goal.txt")
    if os.path.isfile(g):
        r["goal"] = open(g, errors="replace").read().splitlines()[0][:40] if open(g, errors="replace").read() else ""
    p = os.path.join(d, "px4ctrl.log")
    if os.path.isfile(p):
        try:
            for ln in open(p, errors="replace"):
                if "[HAFIX]" not in ln:
                    continue
                r["hafix_n"] += 1
                r["hafix_last"] = re.sub(r"\x1b\[[0-9;]*m", "", ln).strip()[-90:]
                ms = re.search(r"stage (\d+)", ln)
                if ms:
                    r["hafix_maxstage"] = max(r["hafix_maxstage"], int(ms.group(1)))
        except OSError:
            pass
    else:
        r["note"] = "no-px4ctrl.log"
    res = os.path.join(d, "RESULT.txt")
    if os.path.isfile(res):
        txt = open(res, errors="replace").read()
        mz = re.search(r"LANDING: z_end=([0-9.]+) m \(<0.15\)->([01])", txt)
        if mz:
            r["z_end"], r["landed"] = mz.group(1), mz.group(2)
        md = re.search(r"auto_disarm->([01])", txt)
        if md:
            r["disarm"] = md.group(1)
        mg = re.search(r"GATEHIT-STAT: n=(\d+).*?chain=([^\n]*)", txt)
        if mg:
            r["gatehit_chain"] = ("n=%s " % mg.group(1)) + mg.group(2).strip()
        mr = re.search(r"RESULT=(\w+)", txt)
        if mr:
            r["result"] = mr.group(1)
    else:
        r["note"] = (r["note"] + ";" if r["note"] else "") + "no-RESULT"
    # bag 时长(场景消歧用)
    try:
        out = subprocess.run(["python3", "-c",
                              "import rosbag,sys;b=rosbag.Bag(sys.argv[1]);print('%.0f'%b._get_start_time() and '%.0f'%(b._get_end_time()-b._get_start_time()));b.close()",
                              os.path.join(d, "flight.bag")], capture_output=True, text=True, timeout=60)
        r["bag_s"] = (out.stdout or "").strip()
    except Exception:
        pass
    return r


def scenario_of(r, dur):
    g = r["goal"]
    if "0.50 0.50 3.0" in g:
        return "S2_hover_3m"
    if "1.01 8.98" in g:
        return "S3_transit"
    if "0.50 0.50 1.0" in g:
        if dur and float(dur) > 90:
            return "S4_land_1m(W75)"
        return "S1_hover_1m"
    return "?"


def main():
    ap = argparse.ArgumentParser(description="2d HAFIX 批统一重判读; " + GEN_VERSION)
    ap.add_argument("--runs-root", default=os.path.expanduser("~/sitl_sim/vins_smoke_runs"))
    ap.add_argument("--pattern", default="run_DRILLD1_N8P_2*")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/catkin_ws/sitl_sim/t3_results"))
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--skip-bagdur", action="store_true", help="跳过 bag 时长探测(场景消歧退化为 goal-only)")
    ap.add_argument("--summary", default=os.path.expanduser(
        "~/sitl_sim/t1_evidence/v11_28_2026-10-07/unit3_3d_hafix_multirun/summary.txt"),
        help="批 summary.txt(场景→时刻映射正源); 缺失时退化为 goal 推断")
    ap.add_argument("--version", action="version", version=GEN_VERSION)
    a = ap.parse_args()

    rounds = []
    evs, done = load_summary(a.summary)
    for d in sorted(glob.glob(os.path.join(a.runs_root, a.pattern))):
        r = parse_round(d)
        if a.skip_bagdur:
            r["bag_s"] = ""
        r["scenario"], rep, r["map_src"] = match_scenario(r, evs, done)
        if rep:
            r["rep"] = rep
        rounds.append(r)

    # 无 summary 映射时: 场景×rep 编号(时间序内同场景第 k 次=rep k)
    if not evs:
        seen = {}
        for r in rounds:
            s = r["scenario"]
            seen[s] = seen.get(s, 0) + 1
            r["rep"] = str(seen[s])

    # 预注册判据
    for r in rounds:
        ok = (r["hafix_n"] >= 1) and (r["landed"] == "1")
        r["round_pass"] = "PASS" if ok else ("NO-JUDGE" if r["landed"] == "NA" and r["hafix_n"] == 0 and r["note"] else "FAIL")

    scen_stat = {}
    for r in rounds:
        if r["scenario"].startswith("非本批") or r["scenario"] == "?":
            continue
        scen_stat.setdefault(r["scenario"], []).append(r["round_pass"] == "PASS")
    md = []
    md.append("# 2d(HAFIX 多场景批) 统一重判读（T3 判读面）")
    md.append("")
    md.append("> 生成器 %s | 生成 %s | 输入=%s/%s" % (
        GEN_VERSION, datetime.datetime.now().strftime("%F %T"), a.runs_root, a.pattern))
    md.append("> 正源面: [HAFIX]=px4ctrl.log 实读（批脚本 stdout grep 假象勘误=T1 C-9）; landed=RESULT.txt LANDING z_end<0.15。")
    md.append("> 预注册判据（t1_batch_3d.sh 冻结）: 每轮 HAFIX≥1 ∧ landed=1; 场景 PASS=5/5; 3d PASS=4 场景全 PASS。")
    md.append("")
    md.append("| round | ts | 场景(映射源) | rep | HAFIX行数/maxstage | landed(z_end) | disarm | GATEHIT | RESULT | 轮判 |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rounds:
        md.append("| %s | %s | %s [%s] | %s | %d/stage%d | %s(%s) | %s | %s | %s | **%s** |" % (
            r["round"], r["ts"], r["scenario"], r.get("map_src", ""), r["rep"], r["hafix_n"],
            r["hafix_maxstage"], r["landed"], r["z_end"] or "—", r["disarm"] or "—",
            r["gatehit_chain"] or "—", r["result"] or "—", r["round_pass"]))
    md.append("")
    md.append("## 场景汇总（预注册口径）")
    md.append("")
    all_pass = True
    for s in sorted(scen_stat):
        v = scen_stat[s]
        p = "PASS" if all(v) and len(v) >= 5 else ("PASS(非5轮面: n=%d)" % len(v) if all(v) else "FAIL")
        if not all(v):
            all_pass = False
        md.append("- %s: %d/%d 轮 PASS → %s" % (s, sum(v), len(v), p))
    md.append("")
    md.append("**3d 批总判: %s**（4 场景全 5/5 才 PASS; 轮数≠5 的场景面如实注记）" % (
        "PASS" if all_pass and all(len(v) >= 5 for v in scen_stat.values()) else "NOT-PASS(如实)"))
    md.append("")
    md.append("> 场景映射审计注: S1/S4 同 goal 靠窗长消歧(bag 时长; --skip-bagdur 时退化为时长缺省=S1 偏置,"
              "映射表全部列在上表可复核; 若 D5_L2 带监控 drill 轮混入 pattern, 其 note/RESULT 面会示异)。")

    out_base = os.path.join(a.out_dir, "t2d_hafix_rejudge_%s" % a.date)
    fn = ["round", "ts", "scenario", "rep", "map_src", "hafix_n", "hafix_maxstage", "hafix_last",
          "landed", "z_end", "disarm", "gatehit_chain", "result", "round_pass", "goal", "bag_s", "note"]
    with open(out_base + ".csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=fn, extrasaction="ignore")
        w.writeheader(); w.writerows(rounds)
    open(out_base + ".md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[-10:]))
    print("-> %s.{csv,md}" % out_base)

if __name__ == "__main__":
    main()
