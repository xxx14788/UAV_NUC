#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2_window_bias_metric.py — ②b 层①窗内偏差度量工具 v1.0（2026-10-11 收官册单元7末件）

背景: bias 路线四案整体证伪定案(v10.10)后,层①(锁窗内 bias 漂移度量)的剩余价值=
证据面补充(②b 终裁 95ae856f 已定 tlock 未 ENGAGE=批为第二 B 臂;本工具量化该批
轮内 bias 实际漂移,为"锁不锁无差别"终判补数值面)。

口径: 从 simvins.log 解析 [T2diag] 行的 |Bas|/|Bgs|(printf %.6f/%.7f,写侧截断已
按 C.2-W 分支定案=只作带误差量化面);窗=--t0/--t1(默认全窗);逐轮出
start/end/delta/max/mean + 批级 CSV。

用法: python3 t2_window_bias_metric.py <run_dir...> [--t0 S] [--t1 S] [--out CSV]
"""
import argparse
import csv
import glob
import os
import re
import sys

PAT = re.compile(
    r"\[T2diag\] t=([0-9.]+).*?\|Bas\|=([0-9.eE+-]+).*?\|Bgs\|=([0-9.eE+-]+)")


def metric_run(d, t0, t1):
    log = os.path.join(d, "simvins.log")
    if not os.path.isfile(log):
        return None
    bas, bgs = [], []
    try:
        with open(log, errors="replace") as f:
            for ln in f:
                m = PAT.search(ln)
                if not m:
                    continue
                t = float(m.group(1))
                if t0 is not None and t < t0:
                    continue
                if t1 is not None and t > t1:
                    continue
                bas.append(float(m.group(2)))
                bgs.append(float(m.group(3)))
    except OSError:
        return None
    if not bas:
        return None
    return {
        "round": os.path.basename(d.rstrip("/")),
        "n": len(bas),
        "bas_start": bas[0], "bas_end": bas[-1],
        "bas_delta": bas[-1] - bas[0],
        "bas_max": max(bas), "bas_mean": sum(bas) / len(bas),
        "bgs_start": bgs[0], "bgs_end": bgs[-1],
        "bgs_delta": bgs[-1] - bgs[0],
        "bgs_max": max(bgs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="run 目录(支持 glob)")
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    dirs = []
    for r in a.runs:
        dirs.extend(sorted(glob.glob(os.path.expanduser(r))))
    rows, miss = [], []
    for d in dirs:
        m = metric_run(d, a.t0, a.t1)
        if m:
            rows.append(m)
        else:
            miss.append(os.path.basename(d.rstrip("/")))
    hdr = ["round", "n", "bas_start", "bas_end", "bas_delta",
           "bas_max", "bas_mean", "bgs_start", "bgs_end", "bgs_delta", "bgs_max"]
    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
    for r in rows:
        print("%-34s n=%-5d |Bas| %.5f→%.5f Δ%+.5f max %.5f | |Bgs| Δ%+.6f" % (
            r["round"], r["n"], r["bas_start"], r["bas_end"],
            r["bas_delta"], r["bas_max"], r["bgs_delta"]))
    if rows:
        print("批级: |Bas| Δ 范围 [%+.5f, %+.5f] 中位 %+.5f" % (
            min(r["bas_delta"] for r in rows),
            max(r["bas_delta"] for r in rows),
            sorted(r["bas_delta"] for r in rows)[len(rows) // 2]))
    if miss:
        print("无 [T2diag] 面: %s" % ", ".join(miss))
    print("rows=%d miss=%d%s" % (len(rows), len(miss),
          " -> %s" % a.out if a.out else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
