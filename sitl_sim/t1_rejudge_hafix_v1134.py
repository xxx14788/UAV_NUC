#!/usr/bin/env python3
# T1 v11.34 单元0-① — 2d HAFIX 批统一重判（批 summary HAFIX 列禁引用=grep 错文件 bug 修正版）
# 正源判读面: 每轮 ev 目录 px4ctrl.log 的 [HAFIX] 行 + RESULT.txt 的 LANDING/auto_disarm 行
# gatehit.json 在 drill D1 轮全部不存在（harness 产物面如实注记, landed 改由 RESULT.txt LANDING 收）
# 预注册判据(批脚本文末原文): 每轮 HAFIX_lines>=1 ∧ landed=1; 场景 PASS=5/5; 3d PASS=4 场景全 PASS
import re, os, sys, csv, glob

OUT_V1128 = os.path.expanduser("~/sitl_sim/t1_evidence/v11_28_2026-10-07/unit3_3d_hafix_multirun")
OUT_V1134 = os.path.expanduser("~/sitl_sim/t1_evidence/v11_34_2026-10-09")
SCENES = ["S1_hover_1m", "S2_hover_3m", "S3_transit", "S4_land_1m"]
ROUNDS = [1, 2, 3, 4, 5]

rows = []
for scn in SCENES:
    for r in ROUNDS:
        blog = os.path.join(OUT_V1128, f"{scn}_r{r}.log")
        row = {"scene": scn, "round": r, "batch_log": blog}
        if not os.path.isfile(blog):
            row.update(ev="MISSING_BATCH_LOG", hafix_lines=-1, watch=0, autoland=0, killdisarm=0,
                       cleared=0, landed="NA", auto_disarm="NA", result_class="NA", z_end="NA",
                       arrive="NA", verdict="INVALID")
            rows.append(row); continue
        txt = open(blog, errors="replace").read()
        m = re.search(r"ev=(\S+run_DRILLD1_\S+)", txt)
        ev = m.group(1) if m else "NO_EV_IN_LOG"
        row["ev"] = ev
        pxlog = os.path.join(ev, "px4ctrl.log")
        if os.path.isfile(pxlog):
            hl = open(pxlog, errors="replace").read()
            hafix_lines = hl.count("[HAFIX]")
            row.update(hafix_lines=hafix_lines,
                       watch=hl.count("watch start"),
                       autoland=hl.count("-> AUTO_LAND"),
                       killdisarm=hl.count("KILL + disarm fallback"),
                       cleared=hl.count("] cleared ("))
        else:
            row.update(hafix_lines=-1, watch=0, autoland=0, killdisarm=0, cleared=0)
        rtxt_path = os.path.join(ev, "RESULT.txt")
        landed, ad, rcls, zend, arrv = "NA", "NA", "NA", "NA", "NA"
        if os.path.isfile(rtxt_path):
            rt = open(rtxt_path, errors="replace").read()
            m = re.search(r"LANDING: z_end=([0-9.]+) m \(<0\.15\)->(\d)", rt)
            if m: zend, landed = m.group(1), m.group(2)
            m = re.search(r"auto_disarm->(\d)", rt)
            if m: ad = m.group(1)
            m = re.search(r"TRICHOTOMY: class=(\S+)", rt)
            if m: rcls = m.group(1)
            m = re.search(r"ARRIVE_WATCH1: (\S+)", rt)
            if m: arrv = m.group(1)
        elif os.path.isdir(ev):
            landed, ad, rcls = "NO_RESULT_TXT", "NO_RESULT_TXT", "NO_RESULT_TXT"
        row.update(landed=landed, auto_disarm=ad, result_class=rcls, z_end=zend, arrive=arrv)
        # 预注册判据: HAFIX_lines>=1 ∧ landed=1
        try:
            ok = (row["hafix_lines"] >= 1) and (str(row["landed"]) == "1")
            row["verdict"] = "PASS" if ok else "FAIL"
        except Exception:
            row["verdict"] = "INVALID"
        rows.append(row)

os.makedirs(OUT_V1134, exist_ok=True)
csv_path = os.path.join(OUT_V1134, "hafix_rejudge_v1134.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# 终判汇总
print("=== 2d HAFIX 批统一重判 (v11.34, 正源=ev/px4ctrl.log+RESULT.txt; 批 summary HAFIX 列禁引用) ===")
print(f"{'scene':<13} r  hafix watch land kill clr lnd disarm z_end  arrive            verdict")
scene_pass = {}
for row in rows:
    print(f"{row['scene']:<13} {row['round']}  {row['hafix_lines']:>5} {row['watch']:>5} {row['autoland']:>4} {row['killdisarm']:>4} {row['cleared']:>3} {str(row['landed']):>3} {str(row['auto_disarm']):>7} {str(row['z_end']):>6} {str(row['arrive']):<17} {row['verdict']}")
for scn in SCENES:
    n_pass = sum(1 for r in rows if r["scene"] == scn and r["verdict"] == "PASS")
    scene_pass[scn] = n_pass
    print(f"[SCENE] {scn}: {n_pass}/5 -> {'PASS' if n_pass == 5 else 'FAIL'}")
all_pass = all(v == 5 for v in scene_pass.values())
print(f"[3d FINAL] {'PASS' if all_pass else 'FAIL'} (4 场景全 5/5)")
gatehit_missing = all(not os.path.isfile(os.path.join(r['ev'], 'gatehit.json')) for r in rows if r['ev'].startswith('/'))
print(f"[NOTE] gatehit.json drill-D1 轮不存在={gatehit_missing} (landed 由 RESULT.txt LANDING 行收, auto_disarm 由 RESULT.txt 收)")
print(f"[CSV] {csv_path}")
