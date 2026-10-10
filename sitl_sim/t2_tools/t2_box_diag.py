#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2_box_diag.py -- ②a box 臂批三层判读数据面（层①②：域内占比+transit 慢淋）
prereg: box_arm_batch_prereg_v1010.md §3（批前冻结）
数据源: run 目录 simvins.log 的 [T2diag] t=.. P=.. V=.. |Bas|=.. Bas=[..] Bgs=[..] tic0=[..] 行
输出(单行 CSV): indom_pct,transit_t0,transit_t1,dbadt_mean,max_bas,tic0_drift,n_frames
  indom_pct   = 全帧 |Bas| 各分量<=0.5 且 |Bgs| 各分量<=0.05 的时间占比（层①，>95%=box 生效）
  transit     = 首帧 |V|>0.3 起 至 |V| 回降<0.2 止（设计件 ②b 窗定义复用为度量窗）
  dbadt_mean  = transit 窗内 |d(Ba)/dt| 均值（L1 分量和/时间，层② 慢淋疗效）
  max_bas     = 全帧 |Bas| 峰值（域界贴合度）
  tic0_drift  = tic0 末值-首值 范数（层③ 外参劣化征兆面）
Usage: t2_box_diag.py <run_dir_or_simvins_log>
"""
import sys, re, os, math

BA_HALF, BG_HALF = 0.5, 0.05

def parse(path):
    if os.path.isdir(path):
        path = os.path.join(path, "simvins.log")
    pts = []
    pat = re.compile(
        r"\[T2diag\] t=([0-9.]+) P=\[([-\.eE+0-9 ]+?)\] V=\[([-\.eE+0-9 ]+?)\] "
        r"\|Bas\|=[0-9.]+ \|Bgs\|=[0-9.]+ Bas=\[([-\.eE+0-9 ]+?)\] Bgs=\[([-\.eE+0-9 ]+?)\] "
        r"tic0=\[([-\.eE+0-9 ]+?)\]")
    with open(path, errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if m:
                t = float(m.group(1))
                v = [float(x) for x in m.group(3).split()]
                ba = [float(x) for x in m.group(4).split()]
                bg = [float(x) for x in m.group(5).split()]
                tic0 = [float(x) for x in m.group(6).split()]
                if len(ba) == 3 and len(bg) == 3 and len(v) == 3:
                    pts.append((t, v, ba, bg, tic0))
    return pts

def main():
    pts = parse(sys.argv[1])
    if len(pts) < 8:
        print("INSUFFICIENT,NA,NA,NA,NA,NA,0")
        return
    # 层①: 全帧域内占比（逐帧二值，时间近似等间隔=帧占比）
    indom = sum(1 for (_, _, ba, bg, _) in pts
                if all(abs(x) <= BA_HALF for x in ba) and all(abs(x) <= BG_HALF for x in bg))
    indom_pct = 100.0 * indom / len(pts)
    max_bas = max(math.sqrt(sum(x * x for x in ba)) for (_, _, ba, _, _) in pts)
    # transit 窗: 首帧 |V|>0.3 起，至其后首帧 |V|<0.2 止
    t0 = t1 = None
    armed = False
    for (t, v, _, _, _) in pts:
        vn = math.sqrt(sum(x * x for x in v))
        if not armed:
            if vn > 0.3:
                armed = True; t0 = t
        else:
            if vn < 0.2:
                t1 = t; break
    if t1 is None and armed:
        t1 = pts[-1][0]
    if not armed:
        print("NO-TRANSIT,%.3f,NA,NA,%.4f,%.4f,%d" % (indom_pct, max_bas, 0.0, len(pts)))
        return
    seg = [(t, ba, bg) for (t, v, ba, bg, _) in pts if t0 <= t <= t1]
    # 层②: transit |d(Ba)/dt| 均值（L1 分量和 / dt）
    rs = []
    for (ta, baa, bga), (tb, bab, bgb) in zip(seg, seg[1:]):
        dt = tb - ta
        if dt <= 0: continue
        d = sum(abs(y - x) for x, y in zip(baa, bab))
        rs.append(d / dt)
    dbadt = sum(rs) / len(rs) if rs else float("nan")
    tic0_first, tic0_last = pts[0][4], pts[-1][4]
    drift = math.sqrt(sum((y - x) ** 2 for x, y in zip(tic0_first, tic0_last)))
    print("%.3f,%.2f,%.2f,%.4f,%.4f,%.4f,%d" %
          (indom_pct, t0 - pts[0][0], t1 - pts[0][0], dbadt, max_bas, drift, len(pts)))

if __name__ == "__main__":
    main()
