#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_vrfy2_regress.py — VRFY2 类历史判读回归抽查 runner（T3 v10.6 单元 0/保底①就绪件）.

纪律来源: T3 v10.6 单元 0 "round_result 换代后零重判纪律确认"; v10.3 先例=VRFY2 回归零重判.

两段式:
  [阶段1 默认] CSV↔判读产物 一致性回归: 从最新 combo_matrix_*_rounds.csv 分层抽样
      (净轮/风暴/中漂移 各 --k 层, 固定种子预注册抽样), 逐轮以独立镜像解析器
      (parse_result/parse_wa_json 正则口径镜像自 t3_combo_matrix v9.9-20261006 系)
      从 run 目录判读产物(RESULT.txt/wa_gate_online.json/simvins.log)重提字段,
      与 CSV 行逐字段 diff —— 捕获统计层漂移(零重判=零字段漂移).
  [阶段2 --live] 判读器重跑回归: 需在 JUDGE_CMDS 填入 3090 现行判读器调用式
      (输出重定向到侧文件, 判读落盘独立纪律); 未配置=拒跑(禁猜 CLI).

用法:
  python3 t3_vrfy2_regress.py [--csv <path>] [--k 2] [--seed 20261008] [--live]
退出码: 0=零重判 PASS; 1=存在漂移(呈报表已打); 2=环境缺件; 64=用法.
"""
import argparse, csv, datetime, glob, json, os, random, re, subprocess, sys

T3_RESULTS = os.path.expanduser("~/catkin_ws/sitl_sim/t3_results")
SMOKE = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OUTSIDE_WORK = os.path.expanduser("~/sitl_sim/t3_evidence/vrfy2_regress")

# 阶段2 判读器调用式(3090 现行链; 部署时确认后填充——禁脚本内猜):
#   每项: (说明, 命令模板, {占位符: run_dir 绝对路径})
JUDGE_CMDS = [
    # ("round_result 7e907b7d 系", ["python3", "<path>/round_result.py", "{RUN}"], None),
    # ("wa_gate --j0-decomp",       ["python3", "<path>/t3_wa_gate.py", "--j0-decomp", "{RUN}"], None),
]

# ---- 镜像解析器(口径=t3_combo_matrix 20261006 系; 阶段1 独立重提) ----
def parse_result(path):
    r = dict(arrive=None, arrive_pass=None, avoid_pass=None, poscmd_pass=None,
             disarm=None, j0=None, result=None)
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return r
    m = re.search(r"leg1 到位\(真值\) min=([\d.-]+) m \(<[\d.]+.*?\)->([01])", txt)
    if m:
        r["arrive"], r["arrive_pass"] = float(m.group(1)), int(m.group(2))
    m = re.search(r"避障 min_dist=[\d.-]+ m \(>[\d.]+\)->([01])", txt)
    if m:
        r["avoid_pass"] = int(m.group(1))
    m = re.search(r"poscmd ([\d.]+) Hz \(>=\d+\)->([01])", txt)
    if m:
        r["poscmd_pass"] = int(m.group(2))
    m = re.search(r"auto_disarm->([01?])", txt)
    if m:
        r["disarm"] = m.group(1)
    m = re.search(r"帧稳定性 \|pre-post\|=([\d.]+) m", txt)
    if m:
        r["j0"] = float(m.group(1))
    m = re.search(r"RESULT=(PASS|FAIL|ENV-FAIL)", txt)
    if m:
        r["result"] = m.group(1)
    return r

def parse_wa_json(path):
    r = dict(j0d_jump=None, j0d_transit=None, j0d_dom=None, njf=None, wa_verdict=None)
    try:
        d = json.load(open(path))
    except Exception:
        return r
    dec = d.get("xline", {}).get("j0_decomp", {})
    if dec.get("available"):
        r["j0d_jump"], r["j0d_transit"] = dec.get("jump_m"), dec.get("transit_m")
        r["j0d_dom"] = dec.get("dominant")
    c = d.get("controlled", {})
    if "jumps_in" in c:
        r["njf"] = c.get("jumps_in", 0) + c.get("jumps_out", 0)
    r["wa_verdict"] = d.get("verdict")
    return r

def reextract(run_dir):
    """从判读产物独立重提 CSV 对照字段(不依赖原脚本)."""
    res = parse_result(os.path.join(run_dir, "RESULT.txt"))
    wa = parse_wa_json(os.path.join(run_dir, "wa_gate_online.json"))
    sim_missing = not os.path.exists(os.path.join(run_dir, "simvins.log"))
    if sim_missing:
        t2fail = None  # 源缺失: 原工具语义=空串计数得 0(伪值)——单独归类, 不算真漂移
    else:
        sim = open(os.path.join(run_dir, "simvins.log"), encoding="utf-8", errors="replace").read()
        t2fail = sim.count("failure detection")
    four = None
    if all(res.get(k) is not None for k in ("arrive_pass", "avoid_pass", "poscmd_pass")) and res.get("disarm") in "01":
        four = int(res["arrive_pass"] == 1 and res["avoid_pass"] == 1
                   and res["poscmd_pass"] == 1 and res["disarm"] == "1")
    return dict(result=res["result"], arrive=res["arrive"], j0=res["j0"],
                j0d_jump=wa["j0d_jump"], j0d_transit=wa["j0d_transit"],
                j0d_dom=wa["j0d_dom"], njf=wa["njf"], wa_verdict=wa["wa_verdict"],
                t2fail=t2fail, four_green=four, sim_missing=sim_missing)

def eq(a, b):
    if a is None and (b is None or b == ""):
        return True
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-9
    return str(a) == str(b)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="默认=自动取 t3_results 最新 combo_matrix_*_rounds.csv")
    ap.add_argument("--root", default=SMOKE, help="run_* 轮目录根(默认 %s)" % SMOKE)
    ap.add_argument("--k", type=int, default=2, help="每分层抽样轮数")
    ap.add_argument("--seed", type=int, default=20261008)
    ap.add_argument("--live", action="store_true", help="阶段2 判读器重跑(JUDGE_CMDS 已配置时)")
    a = ap.parse_args()

    csv_path = a.csv
    if not csv_path:
        cands = sorted(glob.glob(os.path.join(T3_RESULTS, "combo_matrix_*_rounds.csv")),
                       key=os.path.getmtime)
        if not cands:
            print("FAIL: 未发现 combo_matrix_*_rounds.csv 于", T3_RESULTS); return 2
        csv_path = cands[-1]
    rows = list(csv.DictReader(open(csv_path)))
    print("VRFY2 回归抽查  csv=%s  n=%d  k=%d/层 seed=%d  ts=%s" % (
        os.path.basename(csv_path), len(rows), a.k, a.seed,
        datetime.datetime.now().strftime("%F %T")))

    # 分层: 沿 j0d 三列口径(风暴=T2fail>0; 净轮=T2fail=0∧j0_total<0.5; 中漂移=其余)
    def cat_of(r):
        try:
            t2f = int(r.get("t2fail") or 0)
        except ValueError:
            t2f = 0
        j0t = None
        for k in ("j0d_jump", "j0"):
            v = r.get(k)
            if v not in (None, ""):
                try:
                    j0t = float(v); break
                except ValueError:
                    pass
        if t2f > 0:
            return "风暴"
        return "净轮" if (j0t is not None and j0t < 0.5) else "中漂移"

    strata = {}
    for r in rows:
        strata.setdefault(cat_of(r), []).append(r["round"])
    rng = random.Random(a.seed)
    sample = []
    for cat in ("净轮", "风暴", "中漂移"):
        pool = sorted(strata.get(cat, []))
        take = pool if len(pool) <= a.k else rng.sample(pool, a.k)
        sample += [(cat, rn) for rn in take]
    # 预注册纪律: 抽样先落盘再看结果
    os.makedirs(OUTSIDE_WORK, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sample_file = os.path.join(OUTSIDE_WORK, "sample_%s.txt" % stamp)
    open(sample_file, "w").write("\n".join("%s\t%s" % kv for kv in sample) + "\n")
    print("抽样(先落盘后判读): %s" % sample_file)
    for cat, rn in sample:
        print("  [%s] %s" % (cat, rn))

    # 阶段1: 产物↔CSV 字段回归
    FIELD_MAP = [("result", "result"), ("arrive", "arrive"), ("j0", "j0"),
                 ("j0d_jump", "j0d_jump"), ("j0d_transit", "j0d_transit"),
                 ("j0d_dom", "j0d_dom"), ("njf", "njf"), ("wa_verdict", "wa_verdict"),
                 ("t2fail", "t2fail"), ("four_green", "four_green")]
    drift = []
    src_missing = []
    missing = []
    for cat, rn in sample:
        rd = os.path.join(a.root, rn)
        if not os.path.isdir(rd):
            missing.append(rn); continue
        fresh = reextract(rd)
        crow = next(r for r in rows if r["round"] == rn)
        if fresh.pop("sim_missing", False):
            # 源缺失归类: CSV 值若为 0=原工具空串计数伪值(一致), 非 0=不可能值=真漂移
            csv_t2f = (crow.get("t2fail") or "").strip()
            if csv_t2f not in ("", "0"):
                drift.append((rn, "t2fail", "simvins.log缺失但CSV="+csv_t2f, "不可能值"))
            else:
                src_missing.append(rn)
                continue
        for fk, ck in FIELD_MAP:
            if not eq(fresh.get(fk), crow.get(ck)):
                drift.append((rn, fk, fresh.get(fk), crow.get(ck)))
    print("-- 阶段1 CSV↔产物一致性: 抽 %d 轮, 缺目录 %d, 字段漂移 %d 处, 源缺失(溯源弱注记) %d 轮" % (
        len(sample), len(missing), len(drift), len(src_missing)))
    for rn in missing:
        print("   MISSING-DIR %s" % rn)
    for rn in src_missing:
        print("   SOURCE-MISSING %s (simvins.log 缺失; CSV t2fail=0 为原工具空串计数伪值, 非判读漂移——该轮溯源弱[NUC 同步部分轮])" % rn)
    for rn, fk, fv, cv in drift:
        print("   DRIFT %s.%s 产物=%r CSV=%r" % (rn, fk, fv, cv))

    # 阶段2: 判读器重跑(可选; JUDGE_CMDS 未配置=拒跑)
    if a.live:
        active = [c for c in JUDGE_CMDS if not any("<path>" in tok for tok in c[1])]
        if not active:
            print("-- 阶段2 跳过: JUDGE_CMDS 未配置(部署时确认 3090 现行判读器调用式后填入; 禁猜)")
        else:
            for cat, rn in sample:
                rd = os.path.join(SMOKE, rn)
                side = os.path.join(OUTSIDE_WORK, "live_%s_%s" % (stamp, rn))
                os.makedirs(side, exist_ok=True)
                for desc, tmpl, _ in active:
                    cmd = [tok.replace("{RUN}", rd).replace("{OUT}", side) for tok in tmpl]
                    print("   LIVE %s: %s" % (rn, " ".join(cmd)))
                    rc = subprocess.call(cmd, stdout=open(os.path.join(side, "stdout.txt"), "w"),
                                         stderr=subprocess.STDOUT)
                    if rc != 0:
                        drift.append((rn, "live_rc:" + desc, rc, 0))
    if not drift and not missing:
        verdict = "PASS-零重判" if not src_missing else "PASS-零重判(带 %d 轮源缺失溯源弱注记)" % len(src_missing)
    else:
        verdict = "FAIL-存在漂移/缺件(呈报)"
    print("RESULT: %s" % verdict)
    return 0 if (not drift and not missing) else 1

if __name__ == "__main__":
    sys.exit(main())
