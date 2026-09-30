#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA3.1 线性域定量:全库实测 ΔBa/ΔBgs 分布 + IMU 一阶修正项数值量级表
数据源:WA1C_*/vins.log 的 [T2diag](全库 8 袋,范数)+ WA1V_RCAN_TRACE t2frame.csv(分量)
一阶修正项(VINS-Fusion IntegrationBase):
  dp_dba = -0.5*dt^2*I (dp_dbg 含旋转耦合,以 dt^2 量级计)
  dv_dba = -dt*I
判据:线性化有效半径~阈值 0.10(ba)/0.01(bg)(上游 #if 0 内的值)
用法: wa3_linearity.py  -> 打印逐袋表 + 存 JSON
"""
import re, os, json, glob

def parse_diag(path):
    rows = []
    for line in open(path, errors="replace"):
        m = re.search(r"\[T2diag\] t=([\d.]+).*\|Bas\|=([\d.]+) \|Bgs\|=([\d.]+)", line)
        if m:
            rows.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    return rows

def stats(rows):
    dba, dbg = [], []
    for i in range(1, len(rows)):
        dba.append(abs(rows[i][1] - rows[i - 1][1]))
        dbg.append(abs(rows[i][2] - rows[i - 1][2]))
    s = sorted(dba); g = sorted(dbg)
    q = lambda v, f: v[min(len(v) - 1, int(f * (len(v) - 1)))] if v else None
    return dict(n=len(dba), dba_p50=q(s, .5), dba_p95=q(s, .95), dba_max=s[-1] if s else None,
                dbg_p50=q(g, .5), dbg_p95=q(g, .95), dbg_max=g[-1] if g else None,
                dba_over010=sum(1 for x in s if x > 0.10),
                dbg_over001=sum(1 for x in g if x > 0.01))

def correction_terms(dba, dt=1.0/223.0):
    # 一阶修正项量级(单帧区间 dt=4.48ms):dv 修正=dba*dt, dp 修正=0.5*dba*dt^2
    # 全窗(N=10 帧间 9 个区间)累计以 dt_win=9*dt 计
    dt_win = 9 * dt
    return dict(dv_1frame=dba * dt, dp_1frame=0.5 * dba * dt * dt,
                dv_win=dba * dt_win, dp_win=0.5 * dba * dt_win * dt_win)

out = {}
print("%-40s %6s | %8s %8s %8s | %8s %8s %8s | over_thr" %
      ("bag", "n", "dBA_p50", "dBA_p95", "dBA_max", "dBg_p50", "dBg_p95", "dBg_max"))
for d in sorted(glob.glob(os.path.expanduser("~/sitl_sim/t3_results/WA1C_*"))):
    log = os.path.join(d, "vins.log")
    if not os.path.exists(log): continue
    st = stats(parse_diag(log))
    if not st["n"]: continue
    name = os.path.basename(d)[len("WA1C_"):]
    out[name] = st
    print("%-40s %6d | %8.4f %8.4f %8.4f | %8.5f %8.5f %8.5f | dBA>0.10: %d  dBg>0.01: %d" %
          (name, st["n"], st["dba_p50"], st["dba_p95"], st["dba_max"],
           st["dbg_p50"], st["dbg_p95"], st["dbg_max"], st["dba_over010"], st["dbg_over001"]))

print("\n=== 一阶修正项量级(dba 阈值 0.10 上下) ===")
for ba in (0.05, 0.10, 0.50, 1.00, 2.53):
    c = correction_terms(ba)
    print("dBA=%4.2f: 单帧 dv 修正=%.5f m/s dp 修正=%.7f m | 全窗 dv=%.4f dp=%.6f" %
          (ba, c["dv_1frame"], c["dp_1frame"], c["dv_win"], c["dp_win"]))
print("\n判读:窗口内 bias 漂移 dBA 超过 repropagate 线性域(0.10)的帧占比=上表 over_thr/n;")
print("实测 RCAN(FAIL) vs ROUTE(PASS) 的 dBA 分布对比见上表——repropagate 需要性裁决输入")
json.dump(out, open(os.path.expanduser("~/sitl_sim/t2_results/wa3_linearity_db.json"), "w"), indent=1)
print("saved -> wa3_linearity_db.json")
