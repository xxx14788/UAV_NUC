#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t1_roc_v1.py — T1 v11.20 单元2 离线 ROC 验证(门引擎同核重放;构造性保证=在线/离线同代码)
问题(任务书预注册): 绿格11 零误拦 ∧ 巨跳6 全触发 — 是否存在工作点?
网格: adapt (cost_ratio,bas_ratio) ∈ {1.5,2,3,5,8,15,30,50}²(OR 组合)+单指标;sustain=5s 固定
      abs 门: T2 健康带的上界代理(其面已被 T2 §1.1 否定,此处登记面)
判据: 工作点存在 ⇔ greens_false=0 ∧ jumps_caught=6/6;否则门不可靠(预注册分支)
      提前量分布=trip_t vs t_jump(round_index.json 在册)——前兆预警窗真实存在的验证
输出: roc_v1/{sensitivity.tsv, pregate_roc.tsv, roc_verdict.md}
"""
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(os.path.join(HERE, "t1_gate_watch.py").replace(os.sep, "_"), os.path.join(HERE, "t1_gate_watch.py"))
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)

RUNS = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_20_2026-10-07/roc_v1")
os.makedirs(OUT, exist_ok=True)

JUMP6 = ["X5_N8O_194814", "X5_SE8O_195656", "X5_E5O_202513", "X5_E8P_224044", "X5_E5P_203112", "X5_E12P_204010"]
GREEN11 = ["X5_E12O_203723", "X5_E12O_R2_225937", "X5_NE8O_201655", "X5_NE12O_223045", "X5_S12P_205411",
           "X5_E8O_192244", "X5_S8O_192525", "X5_N8P_195421", "X5_N12O_212904", "X5_S5O_204600", "X5_W5P_210249"]
HELDOUT = ["X5_E8P_220756", "X5_E8P_L2_225245"]
GRID = [1.5, 2, 3, 5, 8, 15, 30, 50]

def replay_once(run, cost_ratio, bas_ratio):
    P = json.loads(json.dumps(gw.DEF_PARAMS))
    P["frozen"] = True
    P["inflight"]["adapt"]["cost_ratio"] = cost_ratio
    P["inflight"]["adapt"]["bas_ratio"] = bas_ratio
    rd = os.path.join(RUNS, run if run.startswith("run_") else "run_" + run)
    G = gw.run_eval(os.path.join(rd, "simvins.log"), P, "replay", tick_out=None)
    trip = G.tripped
    return {"tripped": bool(trip), "metric": trip[0] if trip else None,
            "trip_t": round(trip[2], 1) if trip else None,
            "t_to": G.t_to, "base_cost": G.base_cost, "base_bas": G.base_bas}

def main():
    ridx = json.load(open(os.path.expanduser(
        "~/sitl_sim/t1_evidence/v11_20_2026-10-07/causation/round_index.json")))
    tj = {r["tag"]: r.get("t_jump_t2slv") for r in ridx["rounds"]}
    rows = []
    print("[roc] replay 网格: %d 组合 × %d 轮" % (len(GRID) ** 2, len(JUMP6) + len(GREEN11) + len(HELDOUT)))
    for cr in GRID:
        for br in GRID:
            res = {}
            for run in JUMP6 + GREEN11 + HELDOUT:
                res[run] = replay_once(run, cr, br)
            gf = sum(1 for t in GREEN11 if res[t]["tripped"])
            jc = sum(1 for t in JUMP6 if res[t]["tripped"])
            hc = sum(1 for t in HELDOUT if res[t]["tripped"])
            rows.append({"cost_ratio": cr, "bas_ratio": br, "greens_false": gf,
                         "jumps_caught": jc, "heldout_caught": hc,
                         "op": (gf == 0 and jc == 6),
                         "detail_jumps": {t: res[t]["tripped"] for t in JUMP6}})
            print("  cr=%-5s br=%-5s greens_false=%d/11 jumps=%d/6 heldout=%d/2%s" %
                  (cr, br, gf, jc, hc, "  <== 工作点!" if (gf == 0 and jc == 6) else ""))
    with open(OUT + "/sensitivity.tsv", "w") as f:
        f.write("cost_ratio\tbas_ratio\tgreens_false\tjumps_caught\theldout_caught\toperating_point\n")
        for r in rows:
            f.write("%s\t%s\t%d\t%d\t%d\t%d\n" % (r["cost_ratio"], r["bas_ratio"],
                    r["greens_false"], r["jumps_caught"], r["heldout_caught"], 1 if r["op"] else 0))
    # 最接近工作点的角落注记
    zf = [r for r in rows if r["greens_false"] == 0]
    best_catch = max((r["jumps_caught"] for r in zf), default=None)
    min_false_at_catch6 = min((r["greens_false"] for r in rows if r["jumps_caught"] == 6), default=None)
    # pregate 面(T2 §2 反例复核:E8P_224044)
    pg = {}
    for run in JUMP6 + GREEN11:
        try:
            rd = os.path.join(RUNS, run if run.startswith("run_") else "run_" + run)
            gw.do_pregate(rd, json.loads(json.dumps(gw.DEF_PARAMS)))
            j = json.load(open(os.path.join(rd, "pregate_%s.json" % run.rsplit("_", 1)[0])))
            pg[run] = j["metrics"]
        except Exception as e:
            pg[run] = {"error": str(e)}
    with open(OUT + "/pregate_roc.tsv", "w") as f:
        f.write("tag\tgroup\tinit_final_cost\tbas_med_post_init\ttrack_med\n")
        for tag, m in sorted(pg.items()):
            grp = "jump6" if tag in JUMP6 else "green11"
            f.write("%s\t%s\t%s\t%s\t%s\n" % (tag, grp, m.get("init_final_cost"),
                    m.get("bas_med_post_init"), m.get("track_med")))
    ops = [r for r in rows if r["op"]]
    verd = {
        "question": "绿格11零误拦 ∧ 巨跳6全触发 — 工作点存在?",
        "operating_points": len(ops),
        "max_jumps_at_zero_false": best_catch["jumps_caught"] if best_catch else None,
        "min_greens_false_at_6catch": min_false_at_catch6,
        "verdict": "门可靠(存在工作点)" if ops else
                   "门不可靠(零工作点;预注册分支:禁上真轮作绿率提升器→无门基线支)",
        "engine": "t1_gate_watch.run_eval 同核(replay 模式)",
        "grid": "adapt cost_ratio×bas_ratio %s, sustain=5s" % GRID,
    }
    json.dump(verd, open(OUT + "/roc_verdict.json", "w"), ensure_ascii=False, indent=1)
    with open(OUT + "/roc_verdict.md", "w") as f:
        f.write("# ROC v1 判决(T1 v11.20 单元2;引擎同核重放)\n\n```\n%s\n```\n\n" % json.dumps(verd, ensure_ascii=False, indent=1))
        f.write("灵敏度全表=sensitivity.tsv;pregate 面=pregate_roc.tsv(E8P_224044 反例=init 健康带内钉死,\n与 T2 gate_science_report §2 一致:起飞前门不成立)。\n")
    print(json.dumps(verd, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
