#!/usr/bin/env python3
# T1 v11.40 单元2 — HAFIX 终验批六环判读链（B-7 参数化版）
# 六环+判据沿 v1139 逐字（零漂移）: ①watch 触发 ②AUTO_LAND ③KILL 发出(ACCEPTED/FAIL+result)
#   ④armed True→False ⑤真值 z 落地 ⑥disarm 后置 landed 门; 预注册=每轮 HAFIX_lines>=1 ∧ landed=1
# v11.40 参数化（上周期 B-7 槽位表头失真修复）:
#   - 场景×轮数从 OUT 内实际 *_r<N>.log 推导（废除硬编码 SCENES×ROUNDS）
#   - 场景 PASS=该场景实际轮数全在 {PASS,SILENT-OK} ∧ ≥1 机制轮（PASS）
#   - 批 PASS=全部场景 PASS（废除 len==20 硬编码）
# v11.40 S4 边界解读预注册（任务书单元 2 原文）:
#   - S4 轮 hafix_lines=0 ∧ landed=1（注入时已落地）= 正确静默 → SILENT-OK，禁误判 FAIL
#     （修复前复验批 S4 r1/r3 形态）
# 用法: t1_rejudge_hafix_v1140.py <OUT_dir>
import re, os, csv, sys, glob

OUT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1
                         else "~/sitl_sim/t1_evidence/v11_40_2026-10-10/hafix_finalverify")

scene_rounds = {}
for p in glob.glob(os.path.join(OUT, "*_r*.log")):
    m = re.match(r"(.+)_r(\d+)\.log$", os.path.basename(p))
    if m:
        scene_rounds.setdefault(m.group(1), set()).add(int(m.group(2)))
SCENES = sorted(scene_rounds)
if not SCENES:
    print("NO BATCH LOGS in", OUT); sys.exit(2)

def parse_pxlog(ev):
    """返回 dict: 各环 sim 时刻+文本(缺失=None)"""
    rings = dict(ring1_watch=None, ring2_autoland=None, ring3_kill=None,
                 ring3_kill_result=None, ring6_disarm=None, cleared=0,
                 hafix_lines=0, p3_reboot_evt=0)
    px = os.path.join(ev, "px4ctrl.log")
    if not os.path.isfile(px):
        return rings
    pat = re.compile(r"\[(?:ERROR|WARN|INFO)\] \[([0-9.]+), ([0-9.]+)\]: (.*)")
    for line in open(px, errors="replace"):
        m = pat.match(re.sub(r"\x1b\[[0-9;]*m", "", line).strip())
        if not m:
            continue
        wall, sim, txt = m.group(1), float(m.group(2)), m.group(3)
        if "[HAFIX]" not in txt:
            if "reboot_notify" in txt:
                rings["p3_reboot_evt"] += 1
            continue
        rings["hafix_lines"] += 1
        if "watch start" in txt:
            rings["ring1_watch"] = sim
        elif "-> AUTO_LAND" in txt:
            rings["ring2_autoland"] = sim
        elif "KILL cmd400" in txt and "ACCEPTED" in txt:
            rings["ring3_kill"] = sim
        elif "KILL FAIL" in txt:
            rings["ring3_kill"] = rings["ring3_kill"] or sim
            mm = re.search(r"result=(\d+)", txt)
            rings["ring3_kill_result"] = mm.group(1) if mm else "?"
        elif "landed gate open -> disarm OK" in txt:
            rings["ring6_disarm"] = sim
        elif "] cleared (" in txt:
            rings["cleared"] += 1
    return rings

def parse_bag(ev):
    """flight.bag: armed True→False 时刻(环4)+真值 z 落地(环5)"""
    out = dict(ring4_armed_drop=None, ring5_zmin=None, ring5_ztail=None, bag_ok=False)
    bagp = os.path.join(ev, "flight.bag")
    if not os.path.isfile(bagp):
        return out
    import rosbag
    try:
        bag = rosbag.Bag(bagp)
    except Exception as e:
        out["ring4_armed_drop"] = f"BAG-OPEN-FAIL"
        return out
    armed, zs = [], []
    iris_idx = None
    for topic, msg, t in bag.read_messages(topics=["/gazebo/model_states", "/mavros/state"]):
        if topic == "/mavros/state":
            armed.append((t.to_sec(), msg.armed))
        else:
            if iris_idx is None:
                iris_idx = next((i for i, n in enumerate(msg.name) if "iris" in n), 0)
            zs.append((t.to_sec(), msg.pose[iris_idx].position.z))
    bag.close()
    out["bag_ok"] = True
    armed.sort()
    for i in range(1, len(armed)):
        if armed[i-1][1] and not armed[i][1]:
            out["ring4_armed_drop"] = armed[i][0]
            break
    if zs:
        zs.sort()
        tail = zs[-2000:] if len(zs) >= 2000 else zs
        out["ring5_zmin"] = min(z for _, z in tail)
        out["ring5_ztail"] = zs[-1][1]
    return out

def parse_result(ev):
    out = dict(landed="NA", auto_disarm="NA", z_end="NA", arrive="NA")
    rp = os.path.join(ev, "RESULT.txt")
    if os.path.isfile(rp):
        rt = open(rp, errors="replace").read()
        m = re.search(r"LANDING: z_end=([0-9.]+) m \(<0\.15\)->(\d)", rt)
        if m: out["z_end"], out["landed"] = m.group(1), m.group(2)
        m = re.search(r"auto_disarm->(\d)", rt)
        if m: out["auto_disarm"] = m.group(1)
        m = re.search(r"ARRIVE_WATCH1: (\S+)", rt)
        if m: out["arrive"] = m.group(1)
    return out

rows = []
for scn in SCENES:
    for r in sorted(scene_rounds[scn]):
        blog = os.path.join(OUT, f"{scn}_r{r}.log")
        row = dict(scene=scn, round=r)
        if not os.path.isfile(blog):
            row.update(verdict="MISSING_BATCH_LOG")
            rows.append(row); continue
        txt = open(blog, errors="replace").read()
        m = re.search(r"EV=(\S+run_DRILLD1_\S+)", txt)
        ev = m.group(1) if m else ""
        row["ev"] = ev
        if not ev or not os.path.isdir(ev):
            row.update(verdict="EV_NOT_FOUND")
            rows.append(row); continue
        rings = parse_pxlog(ev)
        bag = parse_bag(ev)
        res = parse_result(ev)
        row.update(rings)
        row.update({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in bag.items()})
        row.update(res)
        ring_flags = {
            "r1": rings["ring1_watch"] is not None,
            "r2": rings["ring2_autoland"] is not None,
            "r3": rings["ring3_kill"] is not None,
            "r4": bag["ring4_armed_drop"] not in (None, "BAG-OPEN-FAIL", False),
            "r5": res["landed"] == "1" or (bag["ring5_zmin"] is not None and bag["ring5_zmin"] < 0.15),
            "r6": rings["ring6_disarm"] is not None or res["auto_disarm"] == "1",
        }
        landed_path = ring_flags["r1"] and ring_flags["r2"] and ring_flags["r4"] and ring_flags["r5"]
        kill_path = ring_flags["r3"] and ring_flags["r4"] and ring_flags["r5"]
        prereg = (rings["hafix_lines"] >= 1) and (str(res["landed"]) == "1")
        row["rings"] = "/".join(k for k, v in ring_flags.items() if v) or "NONE"
        row["path"] = "KILL" if kill_path else ("LAND" if landed_path else "-")
        row["prereg_pass"] = "Y" if prereg else "N"
        row["verdict"] = "PASS" if prereg else "FAIL"
        # S4 边界解读预注册(v11.40): 注入时已落地(hafix=0 ∧ landed=1)=正确静默
        if scn.startswith("S4") and rings["hafix_lines"] == 0 and str(res["landed"]) == "1":
            row["verdict"] = "SILENT-OK"
        row["missing_rings"] = ",".join(k for k, v in ring_flags.items() if not v) or "-"
        rows.append(row)

cols = ["scene", "round", "ev", "ring1_watch", "ring2_autoland", "ring3_kill", "ring3_kill_result",
        "ring4_armed_drop", "ring5_zmin", "ring5_ztail", "ring6_disarm", "landed", "auto_disarm",
        "z_end", "hafix_lines", "cleared", "p3_reboot_evt", "rings", "path", "prereg_pass", "verdict", "missing_rings"]
csvp = os.path.join(OUT, "verdict_v1140.csv")
with open(csvp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for row in rows: w.writerow(row)

ok = sum(1 for r in rows if r.get("verdict") == "PASS")
silent = sum(1 for r in rows if r.get("verdict") == "SILENT-OK")
kill_ok = sum(1 for r in rows if r.get("path") == "KILL")
land_ok = sum(1 for r in rows if r.get("path") == "LAND")
killfail = [r for r in rows if r.get("ring3_kill_result") not in (None, "?")]
first_round = next((r for r in rows if r.get("round") == 1), None)
lines = [
    f"# HAFIX 终验批 v11.40 终判表 ({len(rows)} 轮, B-7 参数化: 场景/轮数自日志推导)",
    f"- 预注册判据: 每轮 HAFIX_lines>=1 ∧ landed=1 | S4 边界解读(v11.40 预注册): hafix=0 ∧ landed=1 → SILENT-OK(正确静默)",
    f"- 场景 PASS=实际轮数全 {{PASS,SILENT-OK}} ∧ ≥1 机制轮 | 批 PASS=全部场景 PASS",
    f"- 终判: {ok}/{len(rows)} PASS; SILENT-OK {silent}; KILL 路径 {kill_ok} 轮 / 落地路径 {land_ok} 轮",
    f"- 首轮 cmd400 毒化观察(检查单#2): " + (
        f"S1 r1 ring3={'ACCEPTED' if first_round and first_round.get('ring3_kill') and not first_round.get('ring3_kill_result') else first_round.get('ring3_kill_result') if first_round else 'NA'}"
        if first_round else "NA"),
    f"- FC reboot 副作用(检查单#3): p3_reboot_evt 总计={sum(int(r.get('p3_reboot_evt', 0)) for r in rows)}",
    f"- KILL FAIL 行(若>0=FC 拒绝面,逐轮看 result 码): {len(killfail)} 轮",
    f"- CSV: {csvp}",
]
batch_ok = bool(SCENES)
for scn in SCENES:
    srows = [r for r in rows if r.get("scene") == scn]
    s_ok = sum(1 for r in srows if r.get("verdict") == "PASS")
    s_sil = sum(1 for r in srows if r.get("verdict") == "SILENT-OK")
    s_bad = sum(1 for r in srows if r.get("verdict") not in ("PASS", "SILENT-OK"))
    scn_ok = (s_bad == 0 and s_ok >= 1)
    batch_ok = batch_ok and scn_ok
    lines.append(f"  {scn}: PASS {s_ok} / SILENT-OK {s_sil} / 其他 {s_bad} (共 {len(srows)}) -> {'PASS' if scn_ok else 'NOT-PASS'}")
lines.append(f"- 批终判: {'PASS' if batch_ok else 'NOT-PASS'}")
txt = "\n".join(lines) + "\n"
open(os.path.join(OUT, "final_verdict_v1140.md"), "w").write(txt)
print(txt)
sys.exit(0 if batch_ok else 1)
