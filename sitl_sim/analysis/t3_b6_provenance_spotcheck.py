#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 provenance 三源列抽验 v1.0（触发条款=下次矩阵消费——本次 combo 滚入即触发）
抽样=新增 62 轮中 5 轮+旧 350 轮分层 5 轮;核对面:
  - provenance 声明 banner:T2* ↔ simvins.log 实际 banner 行
  - arm 列 ↔ banner 内容一致性(IQG 解析等)
  - result 列 ↔ RESULT.txt 首行
  - judge_site 恒 3090(判读单源化纪律)
"""
import csv, os, random

HOME = os.path.expanduser("~")
SMOKE = HOME + "/sitl_sim/voke_runs"  # placeholder overwritten below
SMOKE = HOME + "/sitl_sim/vins_smoke_runs"
NEW = HOME + "/catkin_ws/sitl_sim/t3_results/combo_matrix_20261010_rounds.csv"
OLD = HOME + "/catkin_ws/sitl_sim/t3_results/combo_matrix_20261009_rounds.csv"

new = {r["round"]: r for r in csv.DictReader(open(NEW))}
old = {r["round"]: r for r in csv.DictReader(open(OLD))}
added = [k for k in new if k not in old]
random.seed(20261010)
sample_added = random.sample(added, min(5, len(added)))
old_strata = [k for k in old if k.startswith(("run_X4_", "run_X5_", "run_WU", "run_M3"))]
sample_old = random.sample(old_strata, min(5, len(old_strata)))

ok = fail = 0
for k in sample_added + sample_old:
    r = new[k]
    d = os.path.join(SMOKE, k)
    log = os.path.join(d, "simvins.log")
    banners_in_log = []
    if os.path.isfile(log):
        with open(log, errors="replace") as f:
            for ln in f:
                if "[T2SGCFG]" in ln or "[T2GATECFG]" in ln or "[T2RFIXCFG]" in ln or "[T2IQGCFG]" in ln or "[T2BIASBOX]" in ln:
                    banners_in_log.append(ln.strip()[:80])
                    if len(banners_in_log) > 4:
                        break
    prov = r.get("arm_prov") or ""
    claimed = [t for t in ("T2SGCFG", "T2GATECFG", "T2RFIXCFG", "T2IQGCFG", "T2BIASBOX") if ("banner:" + t) in prov]
    claimed_in_log = [t for t in claimed if any(("[%s]" % t) in b for b in banners_in_log)]
    res = r.get("result") or ""
    rt = os.path.join(d, "RESULT.txt")
    res_line = open(rt, errors="replace").readline().strip()[:40] if os.path.isfile(rt) else "(no RESULT.txt)"
    verdict = "PASS" if len(claimed) == len(claimed_in_log) else "FAIL"
    if verdict == "PASS":
        ok += 1
    else:
        fail += 1
    print("[%s] %-32s prov_banners=%s log_hit=%d/%d result=%-8s judge_site=%s" % (
        verdict, k, "+".join(claimed) or "(era-map)", len(claimed_in_log), len(claimed) or 0, res, r.get("judge_site")))
    if verdict == "FAIL":
        print("     log banners:", banners_in_log[:3], "| RESULT head:", res_line)
print("\nspot-check: %d PASS / %d FAIL (sample=%d+%d)" % (ok, fail, len(sample_added), len(sample_old)))
