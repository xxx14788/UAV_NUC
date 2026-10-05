#!/usr/bin/env python3
"""全库 j0/forensics 联合抽取 (喂单元4/5/6). 3090+NUC 双机."""
import json, os, sys, glob

BASES = {
    "3090": "/home/ghj/sitl_sim/vins_smoke_runs",
    "NUC": "/home/uav/sitl_sim/vins_smoke_runs",
}
if len(sys.argv) > 1:
    BASES = {"3090": BASES["3090"]}  # single-machine mode

out = open(sys.argv[-1] if len(sys.argv) > 1 else "/tmp/corpus_j0.tsv", "w")
out.write("machine\tround\tj0_total\tjump_m\ttransit_m\tjump_frac\tdominant\tt_end"
          "\tacc_peak\tgyr_peak\ttruth_z_max\tprop_bbox\todom_bbox\tdrift_fin"
          "\tlost_fail\tnan_cnt\treboot_cnt\tinit_n\tscene_hint\n")

for mach, base in BASES.items():
    for rd in sorted(glob.glob(base + "/run_*")):
        name = os.path.basename(rd)
        j0 = {}
        try:
            with open(rd + "/j0_decomp.json") as f:
                d = json.load(f)
            j0 = d.get("j0_decomp", d)
        except Exception:
            pass
        fo = {}
        try:
            with open(rd + "/forensics_v2.json") as f:
                fo = json.load(f)
        except Exception:
            pass
        im = fo.get("imu", {}) or {}
        term = fo.get("终态", {}) or fo.get("\u7ec8\u6001", {}) or {}
        # slv nan / reboot counts from log (cheap greps)
        nan_c = rb_c = init_n = 0
        logf = rd + "/simvins.log"
        if os.path.exists(logf):
            try:
                with open(logf, errors="replace") as f:
                    txt = f.read()
                nan_c = txt.count("T2slv") and sum(
                    1 for ln in txt.splitlines()
                    if ln.startswith("[T2slv") and "-nan" in ln)
                rb_c = txt.count("cost gate: streak")
                init_n = txt.count("Initialization finish")
            except Exception:
                pass
        res = ""
        try:
            with open(rd + "/RESULT.txt", errors="replace") as f:
                res = f.read(400)
        except Exception:
            pass
        tf = sum(1 for kw in ("never-flew",) if kw in res)
        scene = "gnd" if "gnd" in name.lower() else (
            "hov" if "hov" in name.lower() else "")
        out.write("\t".join(str(x) for x in [
            mach, name,
            j0.get("j0_total_m", ""), j0.get("jump_m", ""),
            j0.get("transit_m", ""), j0.get("jump_frac", ""),
            j0.get("dominant", ""), j0.get("t_end", ""),
            im.get("acc_peak", ""), im.get("gyr_peak", ""),
            term.get("truth_z_max", ""), term.get("prop_bbox_diag_m", ""),
            term.get("odom_bbox_diag_m", ""),
            term.get("final_drift_prop_truth_m", ""),
            tf, nan_c, rb_c, init_n, scene]) + "\n")
out.close()
print("done ->", out.name)
