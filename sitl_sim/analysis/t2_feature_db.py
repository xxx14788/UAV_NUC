#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WB2 跨袋特征质量数据库汇编器
输入:WA1C_* census 目录集 + 可选 judge/t2frame -> 每袋一行(镜像 T3-Y1.3 发散库字段以便 join)
字段: bag/scene/sdf_gen/events/init_neg_pct/src_split(stereo|motion2|svd|shift)/
      depth_p05_p50_p95/lt0.5_pct/gt30_pct/xcheck_n/xgt30/xgt50/
      track_p50_p90/n_diag/reboot/bas_max/verdict/notes
输出: CSV+JSON 双落盘(docs/analysis/t2_feature_db.*)
用法: t2_feature_db.py [--out-prefix docs/analysis/t2_feature_db]
"""
import os, re, csv, json, argparse, glob

SCENE = {  # 袋名 -> (场景, SDF 代, 历史判决)
    "RCAN173345_flight": ("obstacles", "noise-v2(σ1.08)", "FAIL(T3移交 canonical 失败)"),
    "X1IMG015950_flight": ("obstacles", "noise-v2", "带图轮(未判)"),
    "X1IMG2_020706_flight": ("obstacles", "noise-v2", "init 崩溃(本轮实测)"),
    "ROUTE112652_t2v3_route_112652": ("无障碍 route", "noise-v2", "PASS(W1.3 轮2)"),
    "HOVER203248_t2v3_hover_203248": ("悬停", "旧 SDF(无噪声)", "参考"),
    "GROUND202520_t2v3_ground_202520": ("地面", "旧 SDF", "参考"),
    "W2B121141_t2v3_w2b_121141": ("w2b 场景", "noise-v2", "FAIL(W2 移交 EKF2)"),
    "ROUTE215016_t2v3_route_215016": ("无障碍 route(长)", "旧 SDF", "旧失败轮"),
}

def collect(root):
    rows = []
    for d in sorted(glob.glob(os.path.join(root, "WA1C_*"))):
        name = os.path.basename(d)[len("WA1C_"):]
        dj = os.path.join(d, "depth_dossier.json")
        if not os.path.exists(dj):
            rows.append({"bag": name, "notes": "no dossier(缺失原因:无 census 产物)"})
            continue
        j = json.load(open(dj))
        r = {"bag": name}
        scene, sdf, verdict = SCENE.get(name, ("?", "?", "?"))
        r.update(scene=scene, sdf_gen=sdf, hist_verdict=verdict)
        r["events"] = j.get("n_events", 0)
        src = j.get("n_by_src", {})
        r["src_stereo"] = src.get("stereo", 0); r["src_motion2"] = src.get("motion2", 0)
        r["src_svd"] = src.get("svd", 0); r["src_shift_slim"] = src.get("shift", 0)
        r["init_neg_n"] = sum(j.get("n_init_replace", {}).values())
        r["init_neg_pct"] = round(100.0 * r["init_neg_n"] / max(r["events"], 1), 1)
        dp = j.get("depth_pct", {})
        r["depth_p05"], r["depth_p50"], r["depth_p95"] = dp.get("P05"), dp.get("P50"), dp.get("P95")
        r["lt0_5_pct"] = round(100 * j.get("near_pct", {}).get("lt0.5", 0), 1)
        r["gt30_pct"] = round(100 * j.get("far_pct", {}).get("gt30", 0), 1)
        xc = j.get("xcheck", {})
        r["xcheck_n"], r["xgt30"] = xc.get("n"), xc.get("gt30")
        r["xgt50"] = xc.get("gt50")
        tl = j.get("track_len_pct", {})
        r["track_p50"], r["track_p90"] = tl.get("P50"), tl.get("P90")
        # judge (if any)
        jp = os.path.join(d, "judge.json")
        if os.path.exists(jp):
            k = json.load(open(jp))
            r["n_diag"], r["reboot"], r["bas_max"] = k.get("n_diag"), k.get("reboot_n"), k.get("bas_max")
            r["ate"], r["verdict"] = k.get("ate"), k.get("verdict")
        rows.append(r)
    return rows

FIELDS = ["bag", "scene", "sdf_gen", "hist_verdict", "events", "init_neg_pct", "src_stereo",
          "src_motion2", "src_svd", "src_shift_slim", "depth_p05", "depth_p50", "depth_p95",
          "lt0_5_pct", "gt30_pct", "xcheck_n", "xgt30", "xgt50", "track_p50", "track_p90",
          "n_diag", "reboot", "bas_max", "ate", "verdict", "notes"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/sitl_sim/t3_results"))
    ap.add_argument("--out-prefix", default=os.path.expanduser("~/catkin_ws/docs/analysis/t2_feature_db"))
    a = ap.parse_args()
    rows = collect(a.root)
    os.makedirs(os.path.dirname(a.out_prefix), exist_ok=True)
    with open(a.out_prefix + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    json.dump(rows, open(a.out_prefix + ".json", "w"), indent=1, ensure_ascii=False)
    print(f"[feature_db] {len(rows)} rows -> {a.out_prefix}.csv/.json")
    for r in rows:
        print("  %-38s ev=%-6d init_neg=%-5s%% p95=%-7s xgt30=%-6s %s" %
              (r.get("bag"), r.get("events", 0), r.get("init_neg_pct", "-"),
               r.get("depth_p95", "-"), r.get("xgt30", "-"), r.get("hist_verdict", "")[:20]))

if __name__ == "__main__":
    main()
