#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
t2_domain_quantiles.py -- T2 unit-1a domain-stratified quantile sampler (v1.0)

Taskbook: 2026-10-07_T2_vins_quality_v10.4.md unit 1a.
Cross-domain healthy-run sampling: >=5 plain + >=5 obstacles healthy runs,
frame-level distributions of THREE keys (stereo_r / corners / depth_r),
per-domain pooled quantile bands p5/p25/p50/p75/p95 + per-run medians
(cross-run dispersion coverage -- 3 runs insufficient per taskbook).

Domain source field: world value is read from each run directory -- either
(a) a `world` file inside the run dir, or (b) `*_world` token in the dir
name, or (c) an explicit JSON mapping supplied with --world-map. The data
source actually used is recorded verbatim in the output (unit-0b provenance
note). Provenance ambiguity -> run skipped with ERROR line, never guessed.

Input metric files (auto-discovered per run dir, first match wins):
  - CSV with header containing fuzzy-matched key columns
  - JSONL with numeric leaves (frame metrics)
Fuzzy key match:
  stereo_r : column contains 'stereo' or 'pair_rate'
  corners  : column contains 'corner' or 'supply' or 'gft'
  depth_r  : column contains 'depth_r' or 'depth_ratio' (NOT bare 'depth'
             -- that would match raw depth values)

Usage:
  python3 t2_domain_quantiles.py --runs RUNS.txt --out out.json
  python3 t2_domain_quantiles.py --runs-dir ~/sitl_sim/runs/2026... \
         --world-map worlds.json --out out.json

Output JSON:
  { runs: {run: {world, src, n_frames, key_medians}},
    domains: { plain: {stereo_r: {p5..p95, n}, ...}, obstacles: {...} },
    meta: {...} }
ASCII-only logs.
"""

import argparse
import csv
import glob
import json
import os
import sys

KEY_SPECS = {
    "stereo_r": ("stereo", "pair_rate"),
    "corners": ("corner", "supply", "gft"),
    "depth_r": ("depth_r", "depth_ratio"),
}
QUANTILES = (5, 25, 50, 75, 95)


def find_world(run_dir, world_map, run_name):
    """Return (world, source_description) or (None, reason)."""
    if world_map and run_name in world_map:
        return world_map[run_name], "world_map"
    wf = os.path.join(run_dir, "world")
    if os.path.isfile(wf):
        with open(wf) as f:
            val = f.read().strip().splitlines()[0].strip() if f else ""
        if val:
            return val, "run_dir/world file"
    for cand in glob.glob(os.path.join(run_dir, "*world*")):
        base = os.path.basename(cand)
        if base.endswith(".world") or base == "world":
            return os.path.splitext(base)[0], "run_dir file name"
    # token in dir name: ..._plain_... / ..._obstacles_...
    low = run_name.lower()
    for dom in ("plain", "obstacles"):
        if dom in low.split("_") or ("_" + dom) in low or (dom + "_") in low:
            return dom, "run name token"
    return None, "no world source"


def metric_files(run_dir):
    """Candidate metric files inside a run dir (ordered by preference)."""
    pats = ["*frame*metric*", "*metrics*", "*probe*", "*.csv", "*.jsonl"]
    seen = []
    for p in pats:
        for f in sorted(glob.glob(os.path.join(run_dir, p))):
            if os.path.isfile(f) and f not in seen:
                seen.append(f)
    return seen


def load_series(path):
    """Return {key: [floats]} using fuzzy column match. {} if no keys found."""
    if path.endswith(".jsonl") or path.endswith(".ndjson"):
        series = {k: [] for k in KEY_SPECS}
        got_any = False
        with open(path, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                flat = _flatten(rec)
                for key, hints in KEY_SPECS.items():
                    for fld, v in flat.items():
                        low = fld.lower()
                        if any(h in low for h in hints) and isinstance(v, (int, float)):
                            series[key].append(float(v))
                            got_any = True
                            break
        return series if got_any else {}
    # CSV
    with open(path, errors="replace", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return {}
        col_idx = {}
        for key, hints in KEY_SPECS.items():
            for i, h in enumerate(header):
                low = h.strip().lower()
                if any(hint in low for hint in hints):
                    col_idx[key] = i
                    break
        if not col_idx:
            return {}
        series = {k: [] for k in col_idx}
        for row in reader:
            if not row:
                continue
            for key, i in col_idx.items():
                if i < len(row):
                    try:
                        series[key].append(float(row[i]))
                    except ValueError:
                        pass
        return series


def _flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, prefix + str(k) + "."))
    elif isinstance(obj, (int, float)):
        out[prefix[:-1]] = obj
    return out


def quantile(sorted_vals, p):
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    idx = int(round((p / 100.0) * (n - 1)))
    return sorted_vals[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", help="file with one run dir per line")
    ap.add_argument("--runs-dir", help="directory whose children are run dirs")
    ap.add_argument("--world-map", help="JSON {run_name: world}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-runs-per-domain", type=int, default=5)
    args = ap.parse_args()

    run_dirs = []
    if args.runs:
        with open(args.runs) as f:
            run_dirs = [ln.strip() for ln in f if ln.strip()]
    elif args.runs_dir:
        run_dirs = sorted(
            [os.path.join(args.runs_dir, d)
             for d in os.listdir(args.runs_dir)
             if os.path.isdir(os.path.join(args.runs_dir, d))])
    else:
        print("[hard] need --runs or --runs-dir")
        return 3

    world_map = None
    if args.world_map:
        with open(args.world_map) as f:
            world_map = json.load(f)

    report = {"runs": {}, "domains": {}, "meta": {}}
    pool = {}  # domain -> key -> [vals]
    for rd in run_dirs:
        name = os.path.basename(rd.rstrip("/"))
        world, src = find_world(rd, world_map, name)
        if world is None:
            print("[ERROR] %s: %s -- SKIPPED (no domain guess allowed)" % (name, src))
            report["runs"][name] = {"world": None, "src": src, "error": src}
            continue
        world = world.lower()
        series = {}
        used_file = None
        for mf in metric_files(rd):
            s = load_series(mf)
            if s:
                series = s
                used_file = os.path.basename(mf)
                break
        if not series:
            print("[ERROR] %s: no metric file with known keys -- SKIPPED" % name)
            report["runs"][name] = {"world": world, "src": src,
                                    "error": "no metric file"}
            continue
        med = {}
        for k, vals in series.items():
            if not vals:
                continue
            sv = sorted(vals)
            med[k] = {
                "n": len(vals),
                "p50": quantile(sv, 50),
            }
            pool.setdefault(world, {}).setdefault(k, []).extend(vals)
        report["runs"][name] = {
            "world": world,
            "src": src,
            "metric_file": used_file,
            "n_frames": max((len(v) for v in series.values()), default=0),
            "key_medians": med,
        }
        print("[ok] %-28s world=%-10s file=%s keys=%s"
              % (name, world, used_file, sorted(series.keys())))

    # pooled per-domain quantile bands
    for world, keys in pool.items():
        report["domains"][world] = {}
        for k, vals in keys.items():
            sv = sorted(vals)
            band = {"n": len(sv)}
            band.update({("p%d" % p): quantile(sv, p) for p in QUANTILES})
            report["domains"][world][k] = band

    # sufficiency check (taskbook: >=5 per domain)
    suff = {}
    for world in ("plain", "obstacles"):
        n = len([r for r in report["runs"].values()
                 if r.get("world") == world])
        suff[world] = {"runs": n,
                       "sufficient": n >= args.min_runs_per_domain}
    report["meta"] = {
        "tool": "t2_domain_quantiles.py",
        "version": "1.0",
        "min_runs_per_domain": args.min_runs_per_domain,
        "sufficiency": suff,
        "domain_field_provenance": "unit-0b note: world read from run dirs "
                                   "(per-run 'src' field records exact source)",
    }

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)
    ok = all(v["sufficient"] for v in suff.values())
    print("[done] %s sufficiency=%s" % (args.out,
          "PASS" if ok else "INSUFFICIENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
