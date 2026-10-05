#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_j0d_specimen_table.py — j0_decomp 标本汇总表生成器(P17;只读,可再生)。

素材源两类:
  1) <run>/j0_decomp.json(独立模式产出)
  2) <run>/wa_gate_online.json 的 xline.j0_decomp 块(在线判读自动携带)
输出 CSV+MD 两件;按 j0_total 升序。判定语义见 t3_wa_gate.py j0_decomp_layer 头注
(jump=VINS 单帧跳变贡献/transit=平滑漂移分量;dominant=jump/transit/mixed/negligible)。
"""
import json, os, sys, glob, csv

ROOTS = [os.path.expanduser("~/sitl_sim/vins_smoke_runs"),
         os.path.expanduser("~/sitl_sim/t3_results/x11_dryrun_v11"),
         os.path.expanduser("~/sitl_sim/t3_results/j0d_t4w1")]

def collect():
    rows = []
    for root in ROOTS:
        for d in sorted(glob.glob(os.path.join(root, "*"))):
            if not os.path.isdir(d):
                continue
            jd, src = None, None
            p1 = os.path.join(d, "j0_decomp.json")
            p2 = os.path.join(d, "wa_gate_online.json")
            if os.path.exists(p1):
                jd, src = json.load(open(p1)), "standalone"
                if isinstance(jd, dict) and "j0_decomp" in jd:  # 独立模式包装结构解包
                    jd = jd["j0_decomp"]
            elif os.path.exists(p2):
                try:
                    jd = json.load(open(p2)).get("xline", {}).get("j0_decomp")
                    src = "online-embedded"
                except Exception:
                    jd = None
            if not jd:
                continue
            rows.append({
                "dir": os.path.basename(d), "source": src,
                "available": jd.get("available"),
                "j0_total_m": jd.get("j0_total_m"),
                "jump_m": jd.get("jump_m"), "transit_m": jd.get("transit_m"),
                "jump_frac": jd.get("jump_frac"), "dominant": jd.get("dominant"),
                "n_jump_frames": jd.get("n_jump_frames"),
                "max_frame_de_m": jd.get("max_frame_de_m"),
                "residual_m": jd.get("residual_m"), "n_prop": jd.get("n_prop"),
            })
    return rows

def main():
    out_base = sys.argv[1] if len(sys.argv) > 1 else "/tmp/t3_j0d_specimen_table_v1"
    rows = [r for r in collect() if r["available"]]
    rows.sort(key=lambda r: (r["j0_total_m"] is None, r["j0_total_m"] or 0))
    keys = list(rows[0].keys()) if rows else []
    with open(out_base + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    with open(out_base + ".md", "w") as f:
        f.write("# j0_decomp 标本汇总表 v1(P17;再生=%s)\n\n" %
                os.path.basename(__file__))
        f.write("| 轮 | 源 | j0_total | jump | transit | jump% | 主导 | njf | max_de | res | n_prop |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
                r["dir"], r["source"], r["j0_total_m"], r["jump_m"], r["transit_m"],
                ("%.1f%%" % (100 * r["jump_frac"])) if r.get("jump_frac") is not None else "-",
                r["dominant"], r["n_jump_frames"], r["max_frame_de_m"],
                r["residual_m"], r["n_prop"]))
    print("rows=%d -> %s.{csv,md}" % (len(rows), out_base))

if __name__ == "__main__":
    main()
