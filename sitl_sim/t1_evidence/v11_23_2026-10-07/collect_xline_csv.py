#!/usr/bin/env python3
"""X7 figs CSV 收集器(T1 v11.23):13 轮取 wa_gate_online.json 正源(原始飞行时判读产物,
判读器 md5 bee17577 零触碰——重判路径在 10-07 窗三轮 vins.log 尾行截断浮点上崩,不修工具红线)
+3 轮(E8O/1e×2) RESULT.txt 面行(列注记=vins 内部列空,provenance 如实)。"""
import csv, json, os
R = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OUT = os.path.expanduser("~/sitl_sim/t3_results/xline_wa_gate_20261007.csv")
order = ["X1final_040931","X2g1_041203","X2g3_042025","X2g4_030233","X3l2a_031040",
         "X3l2b_032653","X3l2b_043724","X4_E12O_031818","X4_NE8O_032059","X4_NE12O_032330",
         "X4_S12P_032611","X4_E8O_033233","X4_S8O_033810","X4_N8P_034553",
         "X4_1e_E8P_035301","X4_1e_HVNET1_040009"]
MANUAL = {
 "X4_E8O_033233":    ["PASS","1/1/1/1","0.081",1,0,"","","",1,"","","","","","","","","",""],
 "X4_1e_E8P_035301":["FAIL","0/1/1/1","3.122","","","","","",1,"","","","","","","","","",""],
 "X4_1e_HVNET1_040009":["FAIL","0/1/1/1","4.119","","","","","",1,"","","","","","","","","",""],
}
cols = ["dir","verdict","four","j0_jump","fj_raw","fj_smj","j0_rev","env_sig","t1d1",
        "vins_pass","reboot_n","gaps","coverage","bas_peak","bgs_peak","track_med",
        "spike_rate","ate_rmse","morph","t_star"]
rows = []
for name in order:
    p = os.path.join(R, "run_"+name, "wa_gate_online.json")
    if os.path.exists(p):
        r = json.load(open(p))
        x, v = r.get("xline", {}), r.get("vins", {})
        rows.append([name, r.get("verdict"),
            "/".join(str(f) for f in x.get("four") or []),
            x.get("j0_jump_m"), x.get("fj_raw"), x.get("fj_smj"),
            x.get("j0_rev_pass"), x.get("env_sig"),
            int(bool(x.get("t1d1_domain"))), v.get("pass_vins"),
            v.get("reboot_n"), v.get("odom_gaps_gt"), v.get("coverage"),
            v.get("bas", {}).get("peak"), v.get("bas", {}).get("bgs_peak"),
            v.get("bas", {}).get("track_med"), v.get("spikes", {}).get("spike_rate"),
            v.get("ate", {}).get("ate_rmse_m"),
            r.get("forensics", {}).get("morph"), r.get("forensics", {}).get("t_star")])
    else:
        rows.append([name] + MANUAL[name])
        print("[collect] %s = RESULT 面行(vins 内部列空,provenance 注记)" % name)
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols); w.writerows(rows)
print("wrote %d rows -> %s" % (len(rows), OUT))
