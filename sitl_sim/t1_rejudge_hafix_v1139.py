#!/usr/bin/env python3
# T1 v11.39 单元1 — HAFIX 修复(P-1/P-2)复验批六环判读链
# 六环(任务书 v11.39 预注册): ①watch 触发时刻 ②AUTO_LAND 切换 ③KILL 命令发出(ACCEPTED/FAIL+result 码)
#   ④armed True→False 时刻 ⑤真值 z 落地曲线 ⑥disarm 后置 landed 门时序 —— 逐环取数,缺环=该环 FAIL 定位
# 终判(3d 预注册原文冻结): 每轮 HAFIX_lines≥1 ∧ landed=1 → PASS;场景 PASS=5/5;批 PASS=4 场景全 PASS
# 素材正源: OUT/<scn>_r<i>.log(drill log) / ev= 索引 / EV/px4ctrl.log([ERROR] [wall, sim] 双时戳) / EV/flight.bag
# 新日志锚(v11.39 修复版): KILL cmd400 param1=1.0 ACCEPTED / KILL FAIL success=.. result=.. / landed gate open -> disarm OK
import re, os, csv, sys

OUT = os.path.expanduser("~/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_reverify")
SCENES = ["S1_hover_1m", "S2_hover_3m", "S3_transit", "S4_land_1m"]
ROUNDS = [1, 2, 3, 4, 5]

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
    for r in ROUNDS:
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
        # 六环取数: ③KILL 环=S3/S4 期望必达;①②必达;④armed 降落;⑤z 落地;⑥KILL 路径期望
        ring_flags = {
            "r1": rings["ring1_watch"] is not None,
            "r2": rings["ring2_autoland"] is not None,
            "r3": rings["ring3_kill"] is not None,
            "r4": bag["ring4_armed_drop"] not in (None, "BAG-OPEN-FAIL", False),
            "r5": res["landed"] == "1" or (bag["ring5_zmin"] is not None and bag["ring5_zmin"] < 0.15),
            "r6": rings["ring6_disarm"] is not None or res["auto_disarm"] == "1",
        }
        # 落地先于 kill 窗的轮(盲降成功): 环3 缺=设计正确, 降级为 landed-path 判定
        landed_path = ring_flags["r1"] and ring_flags["r2"] and ring_flags["r4"] and ring_flags["r5"]
        kill_path = ring_flags["r3"] and ring_flags["r4"] and ring_flags["r5"]
        prereg = (rings["hafix_lines"] >= 1) and (str(res["landed"]) == "1")
        row["rings"] = "/".join(k for k, v in ring_flags.items() if v) or "NONE"
        row["path"] = "KILL" if kill_path else ("LAND" if landed_path else "-")
        row["prereg_pass"] = "Y" if prereg else "N"
        # 终判=预注册原文;六环=定位面(缺环列名)
        row["verdict"] = "PASS" if prereg else "FAIL"
        row["missing_rings"] = ",".join(k for k, v in ring_flags.items() if not v) or "-"
        rows.append(row)

cols = ["scene", "round", "ev", "ring1_watch", "ring2_autoland", "ring3_kill", "ring3_kill_result",
        "ring4_armed_drop", "ring5_zmin", "ring5_ztail", "ring6_disarm", "landed", "auto_disarm",
        "z_end", "hafix_lines", "cleared", "p3_reboot_evt", "rings", "path", "prereg_pass", "verdict", "missing_rings"]
csvp = os.path.join(OUT, "reverify_verdict_v1139.csv")
with open(csvp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for row in rows: w.writerow(row)

# 终判表
ok = sum(1 for r in rows if r.get("verdict") == "PASS")
kill_ok = sum(1 for r in rows if r.get("path") == "KILL")
land_ok = sum(1 for r in rows if r.get("path") == "LAND")
killfail = [r for r in rows if r.get("ring3_kill_result") not in (None, "?")]
first_round = next((r for r in rows if r.get("round") == 1), None)
lines = [
    f"# HAFIX 复验批 v11.39 终判表 ({len(rows)} 轮)",
    f"- 预注册判据: 每轮 HAFIX_lines>=1 ∧ landed=1 | 场景 PASS=5/5 | 批 PASS=4 场景全 PASS",
    f"- 终判: {ok}/{len(rows)} PASS;KILL 路径 {kill_ok} 轮 / 落地路径 {land_ok} 轮",
    f"- 首轮 cmd400 毒化观察(检查单#2): " + (
        f"S1 r1 ring3={'ACCEPTED' if first_round and first_round.get('ring3_kill') and not first_round.get('ring3_kill_result') else first_round.get('ring3_kill_result') if first_round else 'NA'}"
        if first_round else "NA"),
    f"- FC reboot 副作用(检查单#3): p3_reboot_evt 总计={sum(int(r.get('p3_reboot_evt', 0)) for r in rows)}",
    f"- KILL FAIL 行(若>0=FC 拒绝面,逐轮看 result 码): {len(killfail)} 轮",
    f"- CSV: {csvp}",
]
per_scene = []
for scn in SCENES:
    srows = [r for r in rows if r.get("scene") == scn]
    s_ok = sum(1 for r in srows if r.get("verdict") == "PASS")
    per_scene.append(f"  {scn}: {s_ok}/5 {'PASS' if s_ok == 5 else 'NOT-PASS'}")
lines += per_scene
lines.append(f"- 批终判: {'PASS' if ok == len(rows) and len(rows) == 20 else 'NOT-PASS'}")
txt = "\n".join(lines) + "\n"
open(os.path.join(OUT, "reverify_final_verdict_v1139.md"), "w").write(txt)
print(txt)
sys.exit(0 if ok == len(rows) else 1)
