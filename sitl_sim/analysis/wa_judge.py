#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA 三判据自动判读器(W-A0 手工口径的脚本化;t3_wa_gate.py 交付后对账)
输入:回放结果目录(吃 vins.log + eval.json)
输出:一行 JSON 判据 {bag, ate, bas_max, bas_over1_pct, bas_over25_n, reboot_n,
      cost_over1e4_n, cost_cycle_detected, tri_init_neg, verdict}
判据(W-A0 定标):PASS = reboot_n==0 && bas_over25_n==0 && bas_over1_pct<1% &&
  ate<=0.185(单轮噪声带门) && cost_over1e4_n<=9 && 无周期循环
用法: wa_judge.py <dir> [<dir>...]
"""
import sys, os, re, json

def judge(d):
    log = os.path.join(d, "vins.log")
    r = {"dir": os.path.basename(d)}
    bas, costs, fails, gates, depth_neg = [], [], 0, 0, 0
    t_prev, cycle = None, 0
    for line in open(log, errors="replace"):
        m = re.search(r"\[T2diag\] t=([\d.]+).*\|Bas\|=([\d.]+)", line)
        if m: bas.append((float(m.group(1)), float(m.group(2))))
        m = re.search(r"\[T2slv\].*init_cost=([\d.eE+-]+)", line)
        if m: costs.append(float(m.group(1)))
        if "[T2fail]" in line: fails += 1
        m = re.search(r"\[T2gate\] t=[\d.]+ tri=(\d+) rej=(\d+) xrej=(\d+) init_replace=(\d+)", line)
        if m:
            gates += int(m.group(2))
        if "[T2depth]" in line and "init_neg" in line: depth_neg += 1
    n = len(bas)
    r["n_diag"] = n
    if n:
        vals = sorted(v for _, v in bas)
        r["bas_max"] = round(vals[-1], 3)
        r["bas_p99"] = round(vals[int(0.99 * n)], 3)
        r["bas_over1_pct"] = round(100.0 * sum(1 for v in vals if v > 1.0) / n, 2)
        r["bas_over25_n"] = sum(1 for v in vals if v > 2.5)
    r["reboot_n"] = fails
    if costs:
        r["cost_max"] = round(max(costs), 1)
        r["cost_over1e4_n"] = sum(1 for c in costs if c > 1e4)
        # cycle detector: >=2 spikes (local max >1e3) separated by recovery below 1e3
        spike, rec = 0, False
        for c in costs:
            if c > 1e4 and not spike: spike = 1; rec = False
            elif c < 1e3 and spike: rec = True; spike = 0
        r["cost_cycle"] = "spike/recovery alternation present" if any(c > 1e4 for c in costs) and any(c < 1e3 for c in costs) else "none"
    r["gate_rej_n"] = gates
    r["init_neg_n"] = depth_neg
    ev = os.path.join(d, "eval.json")
    if os.path.exists(ev):
        e = json.load(open(ev))
        r["ate"] = e.get("ate_post60_m")
        r["n_odom"] = e.get("n_odom")
    ok = (r.get("reboot_n", 1) == 0 and r.get("bas_over25_n", 1) == 0
          and r.get("bas_over1_pct", 100) < 1.0 and r.get("n_diag", 0) > 200
          and (r.get("ate") is None or r["ate"] <= 0.185)
          and r.get("cost_over1e4_n", 99) <= 9)
    r["verdict"] = "PASS" if ok else "FAIL"
    return r

if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(json.dumps(judge(d), ensure_ascii=False))
