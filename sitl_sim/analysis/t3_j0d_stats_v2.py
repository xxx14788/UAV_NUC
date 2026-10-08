#!/usr/bin/env python3
"""j0d 三列全系统计 v2.1 扩切口(T3 v10.9 单元1 目录收敛;2026-10-09)
=2026-10-06 版(113 袋轮)扩 X4 批 9 轮 → 122 袋轮(X4 前 9 轮 j0_decomp 可用面)
CAMPAIGN_ARM 映射: X4 前缀 → machine=3090(X4批次) boot=boot-X4-1007 arm=v2+cauchy4(054ddc8d)
t2fail=X4 轮 REINIT/simvins.log 实查=0(4 FAIL 轮同查); four_green=RESULT PASS 映射
provenance: 原 118 表口径=113 available(v9.9 j0d 批) — 本版重扫后 available 数见汇总行
谱系: v1(=t3_j0d_stats.py, OUT 已是 repo, 产 20261006 表)已退役归档 retired_generators/;
     v2(2026-10-07, OUT 硬编码 HOME 侧=双目录病源)→ v2.1 OUT 默认改 repo 正源+版本自描述。
     v2.1 对同输入与 v2 逐字节等价(CSV 行零漂移, 验证件=t3_results/dir_convergence_20261009.md)。
"""
import argparse, csv, glob, json, os, datetime

GEN_VERSION = "t3_j0d_stats_v2.1 (T3 v10.9 单元1; OUT=repo 正源)"

_ap = argparse.ArgumentParser(description="j0d 三列全系统计表生成器; " + GEN_VERSION)
_ap.add_argument("--smoke", default=os.path.expanduser("~/sitl_sim/vins_smoke_runs"))
_ap.add_argument("--combo", default=None,
    help="CAMPAIGN_ARM 联表; 默认=自动取 out-dir 内最新 combo_matrix_*_rounds.csv"
         "(v2.1 起自描述, 谱系=v2 时代靠临时改行换表=双目录病源之一); 显式传路径可钉死")
_ap.add_argument("--l3", default=os.path.expanduser(
    "~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/l3_recompute_v14.csv"))
_ap.add_argument("--out-dir", default=os.path.expanduser(
    "~/catkin_ws/sitl_sim/t3_results"),
    help="默认=repo 正源(v2.1 起收敛; v2 及以前=HOME 侧 ~/sitl_sim/t3_results, 已冻结历史)")
_ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"),
    help="表日期戳; 输出=<out-dir>/j0d_stats_<date>.{csv,txt}; 禁覆写旧日期戳")
_ap.add_argument("--version", action="version", version=GEN_VERSION)
A = _ap.parse_args()
SMOKE, L3 = A.smoke, A.l3
OUT = os.path.join(A.out_dir, "j0d_stats_" + A.date)
if A.combo is None:
    import glob as _glob
    _cands = sorted(_glob.glob(os.path.join(A.out_dir, "combo_matrix_*_rounds.csv")))
    if not _cands:
        raise SystemExit("FAIL: %s 内无 combo_matrix_*_rounds.csv; 显式传 --combo" % A.out_dir)
    COMBO = _cands[-1]
    print("[v2.1] combo 联表自动取最新: %s" % COMBO)
else:
    COMBO = A.combo
X5PM = {}
import csv as _csv
_pm_path = os.path.expanduser("~/sitl_sim/t1_evidence/v11_17_2026-10-06/x5_passmap_live.csv")
if os.path.exists(_pm_path):
    for _r in _csv.DictReader(open(_pm_path, encoding="utf-8-sig")):
        if _r.get("tag"):
            X5PM[_r["tag"]] = _r

# X4 CAMPAIGN_ARM 映射(正源=x4_final_tally.md md5 206506c5 + RESULT.txt 实读)
X4MAP = {
 "run_X4_E12O_031818":  {"fg":"1","arr":"0.278"},
 "run_X4_NE8O_032059":  {"fg":"1","arr":"0.037"},
 "run_X4_NE12O_032330": {"fg":"1","arr":"0.220"},
 "run_X4_S12P_032611":  {"fg":"0","arr":"11.106"},
 "run_X4_E8O_033233":   {"fg":"1","arr":"0.156"},
 "run_X4_S8O_033810":   {"fg":"0","arr":"6.009"},
 "run_X4_N8P_034553":   {"fg":"1","arr":"0.083"},
 "run_X4_1e_E8P_035301":{"fg":"0","arr":"2.291"},
 "run_X4_1e_HVNET1_040009":{"fg":"0","arr":"0.439"},
}

combo = {r["round"]: r for r in csv.DictReader(open(COMBO))}
l3 = {r["round"]: r for r in csv.DictReader(open(L3))}
rows = []
for p in sorted(glob.glob(os.path.join(SMOKE, "run_*", "j0_decomp.json"))):
    name = os.path.basename(os.path.dirname(p))
    try:
        d = json.load(open(p)).get("j0_decomp", {})
    except Exception:
        continue
    if not d.get("available"):
        continue
    if name.startswith("run_X5_"):
        # v1.1(2026-10-07 v11.25 阶段5): X5 联表——四绿/到位=x5_passmap_live 正源;
        # t2fail=simvins.log REINIT/failure detection 实数(C.10 补列)
        x5t = name[7:] if not name.startswith("run_X5_") else name[len("run_X5_"):]
        pm = X5PM.get(x5t) or {}
        gl = os.path.join(SMOKE, name, "simvins.log")
        t2f = 0
        try:
            with open(gl, errors="replace") as f:
                for ln in f:
                    if "failure detection" in ln or "REINIT" in ln:
                        t2f += 1
        except OSError:
            t2f = 0
        res = pm.get("result", "")
        c = {"machine":"3090(X5批次)","boot":"boot-X5-1006/07","arm":"v2+cauchy4(054ddc8d)",
             "t2fail":str(t2f),
             "four_green":("1" if res == "PASS" else ("0" if res else "")),
             "arrive":pm.get("arrive_truth",""), "j0":pm.get("jump_prepost","")}
    elif name.startswith("run_X4_"):
        xm = X4MAP.get(name, {"fg":"","arr":""})
        c = {"machine":"3090(X4批次)","boot":"boot-X4-1007","arm":"v2+cauchy4(054ddc8d)",
             "t2fail":"0","four_green":xm["fg"],"arrive":xm["arr"],"j0":""}
    else:
        c = combo.get(name, {})
    t2f = int(c.get("t2fail") or 0)
    j0t = d.get("j0_total_m")
    cat = "风暴" if t2f > 0 else ("净轮" if (j0t is not None and j0t < 0.5) else "中漂移")
    l3r = l3.get(name, {})
    arr_new = l3r.get("arr_new", "")
    arr_old = c.get("arrive", "")
    corrobor = ""
    try:
        if arr_old != "" and arr_new != "" and float(arr_old) >= 0.75 and float(arr_new) < 0.75:
            corrobor = "重判绿佐证(L3)"
    except ValueError:
        pass
    rows.append(dict(
        round=name, machine=c.get("machine", "?"), boot=c.get("boot", ""),
        arm=c.get("arm", "")[:46], cat=cat,
        j0_result_txt=c.get("j0", ""), j0_total=j0t,
        jump_m=d.get("jump_m"), transit_m=d.get("transit_m"),
        jump_frac=d.get("jump_frac"), n_jump=d.get("n_jump_frames"),
        dominant=d.get("dominant"), n_prop=d.get("n_prop"),
        t2fail=t2f, four_green=c.get("four_green", ""),
        arrive_old=c.get("arrive", ""), arrive_new=arr_new,
        l3_flag=l3r.get("flag", ""), corrobor=corrobor,
    ))
rows.sort(key=lambda r: (r["cat"], r["machine"], r["round"]))
with open(OUT + ".csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
from collections import Counter, defaultdict
cnt = Counter(r["cat"] for r in rows)
by_machine = defaultdict(Counter)
for r in rows:
    by_machine[r["machine"].split("(")[0]][r["cat"]] += 1
L = []
L.append("="*96)
L.append("j0d 三列全系统计表 v2 扩切口(净轮/风暴/中漂移; anchor v1.4 口径)  生成 2026-10-07 (T1 v11.23)")
L.append("扩切口: 2026-10-06 版(113) + X4 批 9(7 批轮+2 1e 标本) + X5 批 59(参数精扫,v11.17 在盘 j0d) + 其他新落 4 = %d 袋轮 available" % len(rows))
L.append("X4 CAMPAIGN_ARM 映射: machine=3090(X4批次)/boot-X4-1007/arm=v2+cauchy4(054ddc8d);t2fail=REINIT 实查 0(4 FAIL 轮同查);four_green=RESULT PASS 映射(正源 x4_final_tally 206506c5);X5 联表(v1.1 v11.25): 四绿/到位/j0=x5_passmap_live 正源;t2fail=simvins.log REINIT/failure detection 实数(C.10 补列销号)")
L.append("分类: 风暴=T2fail>0; 净轮=T2fail=0∧j0_total<0.5; 中漂移=T2fail=0∧j0_total≥0.5 | 判读器 bee17577")
L.append("生成器 %s | OUT=%s | combo join=%s | 生成时刻 %s" % (GEN_VERSION, OUT, COMBO, datetime.datetime.now().strftime("%F %T")))
L.append("="*96)
L.append("总数 %d: %s" % (len(rows), ", ".join("%s=%d" % kv for kv in cnt.most_common())))
for mk in ("3090", "NUC", "?"):
    if mk in by_machine:
        c = by_machine[mk]
        L.append("  %-4s %2d 轮: 净轮=%d 中漂移=%d 风暴=%d" % (mk, sum(c.values()), c["净轮"], c["中漂移"], c["风暴"]))
L.append("")
L.append("-- 净轮名册 (T2fail=0 ∧ j0_total<0.5):")
for r in rows:
    if r["cat"] == "净轮":
        L.append("  %-28s %-9s %-6s j0=%.3f jump=%.3f transit=%.3f dom=%s 四绿=%s %s" % (
            r["round"], r["machine"][:9], r["boot"], r["j0_total"],
            r["jump_m"] if r["jump_m"] is not None else -1,
            r["transit_m"] if r["transit_m"] is not None else -1,
            r["dominant"], r["four_green"], r["corrobor"]))
L.append("")
L.append("-- X2g3 重判绿佐证行(L3 新口径到位破 0.75 门; §2.8a 算术勘误效应逐位):")
for r in rows:
    if r["corrobor"]:
        L.append("  %-28s 旧到位=%s → L3 新=%s flag=%s" % (r["round"], r["arrive_old"], r["arrive_new"], r["l3_flag"]))
with open(OUT + ".txt", "w") as f:
    f.write("\n".join(L) + "\n")
print("\n".join(L[:14]))
print("... [%s] -> %s.{csv,txt}" % (GEN_VERSION, OUT))
