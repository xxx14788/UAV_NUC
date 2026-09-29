#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WA1.1 全库深度普查工具:解析插桩 VINS 的 [T2depth] 行,产出每袋深度 dossier
schema(字段字典):
  log 行: [T2depth] t=<stamp> id=<feature_id> src=<stereo|motion2|svd|shift>
          u=<px> v=<px> depth=<m> depth2=<m|-1> track=<len> sf=<start_frame>
          flag=<ok|init_neg|init_low>
  dossier JSON:
    n_events / n_by_src{stereo,motion2,svd,shift} / n_init_replace{init_neg,init_low}
    depth_pct{P01,P05,P25,P50,P75,P95,P99,min,max}   (ok 深度,不含 INIT_DEPTH 替换值)
    near_pct{lt0.3,lt0.5,lt1.0} / far_pct{gt15,gt30}
    histogram[bin_left,bin_right,count]               (对数等宽 24 bins 0.05-120m)
    cross_check{stereo_pairs,relerr_pct{P50,P90,P95,P99},gt20,gt30,gt50(占比)}
    track_len_pct{P50,P90,max}
    per_sec_median_depth[[t_sec,median],...]          (毒窗分析)
    uvpri: 不记录逐点明细(库级体积),明细走 --csv
用法:
  t2_depth_census.py <vins.log 或回放结果目录> [--csv out.csv] [--json out.json]
  t2_depth_census.py --selftest <R_CAN_dir> <CTRL2_dir>   # W-A0 对账协议
"""
import sys, os, re, json, math, argparse
from collections import defaultdict

LINE = re.compile(
    r"\[T2depth\] t=([\d.eE+-]+) id=(\d+) src=(\w+) u=([-\d.]+) v=([-\d.]+) "
    r"depth=([\d.eE+-]+) depth2=([\d.eE+-]+) track=(\d+) sf=(\d+) flag=(\w+)")

XLINE = re.compile(
    r"\[T2xcross\] t=([\d.eE+-]+) id=(\d+) est=([\d.eE+-]+) svd=([\d.eE+-]+) "
    r"rel=([\d.eE+-]+) track=(\d+) sf=(\d+)")

def parse_log(path):
    ev = []
    with open(path, errors="replace") as f:
        for line in f:
            m = LINE.search(line)
            if m:
                ev.append(dict(t=float(m.group(1)), id=int(m.group(2)), src=m.group(3),
                               u=float(m.group(4)), v=float(m.group(5)),
                               depth=float(m.group(6)), depth2=float(m.group(7)),
                               track=int(m.group(8)), sf=int(m.group(9)), flag=m.group(10)))
    return ev

def parse_xcross(path):
    xc = []
    with open(path, errors="replace") as f:
        for line in f:
            m = XLINE.search(line)
            if m:
                xc.append(dict(t=float(m.group(1)), id=int(m.group(2)),
                               est=float(m.group(3)), svd=float(m.group(4)),
                               rel=float(m.group(5)), track=int(m.group(6))))
    return xc

def pct(sorted_vals, q):
    if not sorted_vals:
        return None
    i = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[i]

def dossier(ev, log_path, xc=None):
    d = {"log": log_path, "n_events": len(ev)}
    if not ev:
        return d
    by_src = defaultdict(int); by_flag = defaultdict(int)
    ok_depths = []; cross_rel = []; tracks = []
    per_sec = defaultdict(list)
    for e in ev:
        by_src[e["src"]] += 1; by_flag[e["flag"]] += 1
        tracks.append(e["track"])
        if e["flag"] == "ok" and e["depth"] > 0:
            ok_depths.append(e["depth"])
            per_sec[int(e["t"])].append(e["depth"])
            if e["src"] == "stereo" and e["depth2"] > 0:
                denom = max(e["depth"], e["depth2"])
                cross_rel.append(abs(e["depth"] - e["depth2"]) / denom if denom > 1e-9 else 0.0)
    d["n_by_src"] = dict(by_src); d["n_init_replace"] = {
        k: v for k, v in by_flag.items() if k != "ok"}
    s = sorted(ok_depths)
    d["n_ok_depth"] = len(s)
    if s:
        qs = {}
        for q in (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99):
            qs[f"P{int(q*100):02d}"] = round(pct(s, q), 4)
        qs["min"], qs["max"] = round(s[0], 4), round(s[-1], 4)
        d["depth_pct"] = qs
        n = len(s)
        d["near_pct"] = {"lt0.3": round(sum(1 for x in s if x < 0.3) / n, 4),
                         "lt0.5": round(sum(1 for x in s if x < 0.5) / n, 4),
                         "lt1.0": round(sum(1 for x in s if x < 1.0) / n, 4)}
        d["far_pct"] = {"gt15": round(sum(1 for x in s if x > 15) / n, 4),
                        "gt30": round(sum(1 for x in s if x > 30) / n, 4)}
        lo, hi, nb = math.log(0.05), math.log(120.0), 24
        bins = [0] * nb
        for x in s:
            k = int((math.log(max(x, 0.05)) - lo) / (hi - lo) * nb)
            bins[min(k, nb - 1)] += 1
        edges = [round(math.exp(lo + (hi - lo) * i / nb), 4) for i in range(nb + 1)]
        d["histogram"] = [[edges[i], edges[i + 1], bins[i]] for i in range(nb)]
    c = sorted(cross_rel)
    if c:
        d["cross_check"] = {"stereo_pairs": len(c),
            "relerr_pct": {q: round(pct(c, f), 4) for q, f in (("P50", .5), ("P90", .9), ("P95", .95), ("P99", .99))},
            "gt20": round(sum(1 for x in c if x > 0.20) / len(c), 4),
            "gt30": round(sum(1 for x in c if x > 0.30) / len(c), 4),
            "gt50": round(sum(1 for x in c if x > 0.50) / len(c), 4)}
    t = sorted(tracks)
    d["track_len_pct"] = {"P50": pct(t, .5), "P90": pct(t, .9), "max": t[-1]}
    d["per_sec_median_depth"] = [[k, round(pct(sorted(v), .5), 4)] for k, v in sorted(per_sec.items())]
    # [T2xcross]-based cross-check stats (authoritative source: periodic stereo-vs-SVD dumps)
    if xc:
        rels = sorted(x["rel"] for x in xc)
        n = len(rels)
        d["xcheck"] = {"n": n,
            "rel_pct": {q: round(pct(rels, f), 4) for q, f in (("P50", .5), ("P90", .9), ("P95", .95), ("P99", .99))},
            "gt20": round(sum(1 for x in rels if x > 0.20) / n, 4),
            "gt30": round(sum(1 for x in rels if x > 0.30) / n, 4),
            "gt50": round(sum(1 for x in rels if x > 0.50) / n, 4),
            "gt866": round(sum(1 for x in rels if x > 0.866) / n, 4)}
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="vins.log or replay result dir")
    ap.add_argument("--csv")
    ap.add_argument("--json")
    a = ap.parse_args()
    log = os.path.join(a.target, "vins.log") if os.path.isdir(a.target) else a.target
    ev = parse_log(log)
    xc = parse_xcross(log)
    d = dossier(ev, log, xc)
    out_json = a.json or (os.path.join(a.target, "depth_dossier.json")
                          if os.path.isdir(a.target) else log + ".dossier.json")
    with open(out_json, "w") as f:
        json.dump(d, f, indent=1)
    print(f"[census] {log}: events={d['n_events']} by_src={d.get('n_by_src')} "
          f"init_replace={d.get('n_init_replace')} ok={d.get('n_ok_depth')} "
          f"P05={d.get('depth_pct',{}).get('P05')} P50={d.get('depth_pct',{}).get('P50')} "
          f"P95={d.get('depth_pct',{}).get('P95')} xcheck_n={d.get('xcheck',{}).get('n')} "
          f"xgt30={d.get('xcheck',{}).get('gt30')}")
    if a.csv:
        with open(a.csv, "w") as f:
            f.write("t,id,src,u,v,depth,depth2,track,sf,flag\n")
            for e in ev:
                f.write(f"{e['t']},{e['id']},{e['src']},{e['u']},{e['v']},"
                        f"{e['depth']},{e['depth2']},{e['track']},{e['sf']},{e['flag']}\n")
        print(f"[census] csv -> {a.csv}")

if __name__ == "__main__":
    main()
