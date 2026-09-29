#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WB1 逐帧诊断 extractor:插桩 vins.log -> T2frame CSV
schema(字段字典;每行=一个求解帧,主键 t):
  t                    帧时戳([T2diag])
  track                滑窗 track 数([T2diag] last_track_num)
  bas_x/y/z,bgs_x/y/z  bias 分量与范数([T2diag])
  tic0_xyz,td          外参/时延([T2diag])
  init_cost,final_cost,iters,slv_ms,term  求解器([T2slv])
  cost_tot/prior/imu/vis,prior_n/imu_n/vis_n  因子分解([T2cost],-1=无trace)
  tri,gate_rej,xrej,init_replace  深度门统计([T2gate],-1=无门)
  depth_p05/p50/p95    本帧行内三角化深度分位([T2depth] 聚合)
  chi2_total,chi2_rej  chi2 门([T2chi2],-1=关)
  wa2_trigger          先验门触发(1)/边缘化跳过标记([T2WA2G] 对齐)
用法: t2_frame_dump.py <vins.log|dir> [--csv out.csv] [--json out.json]
"""
import sys, os, re, csv, json, argparse

RE = {
    "diag": re.compile(r"\[T2diag\] t=([\d.]+) P=\[[^\]]+\] V=\[[^\]]+\] \|Bas\|=([\d.]+) \|Bgs\|=([\d.]+)"),
    "slv": re.compile(r"\[T2slv\] t=([\d.]+) phase=(\d+) init_cost=([\d.eE+-]+) final_cost=([\d.eE+-]+) iters=(\d+) term=(\d+) slv_ms=([\d.]+)"),
    "cost": re.compile(r"\[T2cost\] t=([\d.]+) tot=([\d.eE+-]+) prior=([\d.eE+-]+) imu=([\d.eE+-]+) vis=([\d.eE+-]+) prior_n=(\d+) imu_n=(\d+) vis_n=(\d+)"),
    "gate": re.compile(r"\[T2gate\] t=([\d.]+) tri=(\d+) rej=(\d+) xrej=(\d+) init_replace=(\d+) gate=(\d+)"),
    "chi2": re.compile(r"\[T2chi2\] t=([\d.]+) total=(\d+) rej=(\d+) m=([\d.]+) conf=([\d.]+)"),
    "wa2g": re.compile(r"\[T2WA2G\] t=([\d.]+) TRIG seq=(\d+) cost=([\d.eE+-]+) dbas=([\d.eE+-]+) strategy=(\d+)"),
    "depth": re.compile(r"\[T2depth\] t=([\d.]+) id=\d+ src=(\w+) u=[-\d.]+ v=[-\d.]+ depth=([\d.eE+-]+) depth2=[-\d.]+ track=\d+ sf=\d+ flag=(\w+)"),
    "fail": re.compile(r"\[T2fail\] t=([\d.]+)"),
}

def extract(path):
    frames = {}  # t -> dict
    def F(t):
        t = round(float(t), 4)
        if t not in frames: frames[t] = {"t": t}
        return frames[t]
    depths = {}
    for line in open(path, errors="replace"):
        m = RE["diag"].search(line)
        if m:
            f = F(m.group(1))
            f["bas_norm"] = float(m.group(2)); f["bgs_norm"] = float(m.group(3))
            continue
        m = RE["slv"].search(line)
        if m:
            f = F(m.group(1))
            f["init_cost"] = float(m.group(3)); f["final_cost"] = float(m.group(4))
            f["iters"] = int(m.group(5)); f["term"] = int(m.group(6)); f["slv_ms"] = float(m.group(7))
            continue
        m = RE["cost"].search(line)
        if m:
            f = F(m.group(1))
            f["cost_tot"] = float(m.group(2)); f["cost_prior"] = float(m.group(3))
            f["cost_imu"] = float(m.group(4)); f["cost_vis"] = float(m.group(5))
            f["prior_n"] = int(m.group(6)); f["imu_n"] = int(m.group(7)); f["vis_n"] = int(m.group(8))
            continue
        m = RE["gate"].search(line)
        if m:
            f = F(m.group(1))
            f["tri"] = int(m.group(2)); f["gate_rej"] = int(m.group(3))
            f["xrej"] = int(m.group(4)); f["init_replace"] = int(m.group(5))
            continue
        m = RE["chi2"].search(line)
        if m:
            f = F(m.group(1))
            f["chi2_total"] = int(m.group(2)); f["chi2_rej"] = int(m.group(3))
            continue
        m = RE["wa2g"].search(line)
        if m:
            f = F(m.group(1)); f["wa2_trigger"] = 1
            continue
        m = RE["depth"].search(line)
        if m:
            t = round(float(m.group(1)), 4)
            d = float(m.group(3))
            if m.group(4) == "ok" and d > 0:
                depths.setdefault(t, []).append(d)
            continue
        m = RE["fail"].search(line)
        if m:
            f = F(m.group(1)); f["fail"] = 1
            continue
    rows = []
    for t in sorted(frames):
        f = frames[t]
        ds = sorted(depths.get(t, []))
        if ds:
            f["depth_p05"] = ds[int(0.05 * (len(ds) - 1))]
            f["depth_p50"] = ds[len(ds) // 2]
            f["depth_p95"] = ds[int(0.95 * (len(ds) - 1))]
        rows.append(f)
    return rows

# robust post-extract of offset-sensitive fields (works with/without Bas component columns)
def fix_td_track(path, rows):
    p1 = re.compile(r"\[T2diag\] t=([\d.]+).*td=([\d.]+) track=(\d+)")
    p2 = re.compile(r"\[T2diag\] t=([\d.]+).*?tic0=\[([-\d.]+) ([-\d.]+) ([-\d.]+)\]")
    p3 = re.compile(r"\[T2diag\] t=([\d.]+).*?Bas=\[([-\d.]+) ([-\d.]+) ([-\d.]+)\] Bgs=\[([-\d.]+) ([-\d.]+) ([-\d.]+)\]")
    td_map, tic_map, bas_map = {}, {}, {}
    for line in open(path, errors="replace"):
        t1 = p1.search(line)
        if t1: td_map.setdefault(round(float(t1.group(1)), 4), (float(t1.group(2)), int(t1.group(3))))
        t2 = p2.search(line)
        if t2: tic_map.setdefault(round(float(t2.group(1)), 4), tuple(float(t2.group(i)) for i in (2, 3, 4)))
        t3 = p3.search(line)
        if t3: bas_map.setdefault(round(float(t3.group(1)), 4), tuple(float(t3.group(i)) for i in range(2, 8)))
    for r in rows:
        v = td_map.get(r["t"])
        if v: r["td"] = v[0]; r["track"] = v[1]
        v = tic_map.get(r["t"])
        if v: r["tic0_x"], r["tic0_y"], r["tic0_z"] = v
        v = bas_map.get(r["t"])
        if v: r["bas_x"], r["bas_y"], r["bas_z"], r["bgs_x"], r["bgs_y"], r["bgs_z"] = v

FIELDS = ["t", "track", "bas_norm", "bas_x", "bas_y", "bas_z", "bgs_norm", "bgs_x", "bgs_y", "bgs_z",
          "tic0_x", "tic0_y", "tic0_z", "td", "init_cost", "final_cost", "iters", "slv_ms", "term",
          "cost_tot", "cost_prior", "cost_imu", "cost_vis", "prior_n", "imu_n", "vis_n",
          "tri", "gate_rej", "xrej", "init_replace", "chi2_total", "chi2_rej",
          "depth_p05", "depth_p50", "depth_p95", "wa2_trigger", "fail"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--csv")
    ap.add_argument("--json")
    a = ap.parse_args()
    log = os.path.join(a.target, "vins.log") if os.path.isdir(a.target) else a.target
    rows = extract(log)
    fix_td_track(log, rows)
    out_csv = a.csv or (os.path.join(a.target, "t2frame.csv") if os.path.isdir(a.target) else log + ".t2frame.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow(r)
    if a.json or os.path.isdir(a.target):
        out_json = a.json or os.path.join(a.target, "t2frame.json")
        json.dump(rows, open(out_json, "w"), indent=0)
    print(f"[t2frame] {log}: frames={len(rows)} -> {out_csv}")

if __name__ == "__main__":
    main()
