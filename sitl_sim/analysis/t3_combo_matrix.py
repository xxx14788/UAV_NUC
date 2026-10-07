#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3 v9.9 单元 1: 组合矩阵工具(判读域) — 臂×栈×boot×结果全库矩阵 + 三歧结论列。

扫描 ~/sitl_sim/vins_smoke_runs 全部 run_* 轮(判读域全库口径; t3_results WA 系
X 线前战役轮不在本矩阵范围, 其谱系见 prereg §6)。逐轮提取:
  - 出生机器: RESULT.txt 证据路径 /home/ghj=3090, /home/uav=NUC(同步正本)
  - 时间: 目录名 HHMMSS + 目录 mtime 日期(flight.bag mtime 优先)
  - boot 段: 仅 3090 轮, mtime → last reboot 谱系(B 表硬编码, 来源 2026-10-06 实读)
  - 臂(arm): simvins.log banner 实读([T2SGCFG]/[T2GATECFG]/[T2RFIXCFG])优先;
    无 banner 轮按战役名映射(来源=DECISION_LOG/STATUS/prereg 在册记录), provenance 标注
  - 栈(stack): 日志内登记 md5 优先; 否则年代分水岭映射(285278cc→fixface→build-2→streamguard)
  - 结果: 四指标(到位/避障/poscmd/disarm)+RESULT+j0(jump)+T2fail+L3 join(arr_new/res_new)
  - j0d 三列: wa_gate_online.json xline.j0_decomp(jump_m/transit_m/dominant)+njf(jumps_in/out)
聚合: arm×stack×boot → 轮数/四绿数/风暴数(T2fail>0)/净轮数(j0<0.5∧T2fail=0∧四绿)
三歧结论列(每 arm×stack 组合, 跨 boot 维度):
  Z=零成功轮歧: 该组合全 boot 四绿计数为 0?
  M=机器态歧: 同组合不同 boot 结果剖分不一致(存在 0 绿 boot 与 ≥1 绿 boot 并存)?
  C=cauchy 依赖歧: 该组合在场轮的 cauchy 状态与绿的关联(在场才绿=依赖/不在场也绿=独立)

用法: python3 t3_combo_matrix.py [--root ~/sitl_sim/vins_smoke_runs]
        [--l3 <l3_recompute_v14.csv>] [--out <prefix>]
输出: <prefix>_rounds.csv(逐轮) + <prefix>_matrix.txt(矩阵+三歧结论, 人读)
"""
import argparse, csv, datetime, glob, json, os, re, sys

ROOT_DEF = os.path.expanduser("~/sitl_sim/vins_smoke_runs")
L3_DEF = os.path.expanduser("~/catkin_ws/sitl_sim/t1_evidence/v11_7_2026-10-05/l3_recompute_v14.csv")

# 3090 boot 谱系(2026-10-06 实读 last reboot; 区间左闭右开, end=None=在运行)
BOOTS_3090 = [
    ("B0928a", "2026-09-28 23:54", "2026-09-29 00:05"),
    ("B0928b", "2026-09-29 00:13", "2026-09-29 00:44"),
    ("B0929",  "2026-09-29 16:26", "2026-09-29 22:56"),
    ("B0930",  "2026-09-30 18:13", "2026-09-30 23:21"),
    ("B1001",  "2026-10-01 18:08", "2026-10-01 22:53"),
    ("B1003a", "2026-10-03 19:51", "2026-10-03 20:10"),
    ("B1003b", "2026-10-03 20:11", "2026-10-04 01:51"),
    ("B1004",  "2026-10-04 17:21", "2026-10-05 21:59"),   # 10-05 白昼(boot-0 晨)
    ("B1005",  "2026-10-05 21:59", "2026-10-06 02:25"),   # 10-05 夜 reboot-1(风暴夜)
    ("B1006",  "2026-10-06 02:26", None),                 # reboot-2(VRFY/VRG 判别夜)
]

# 栈年代分水岭(mtime; 3090 执行域。NUC 轮用 NUC 谱系名)
STACK_ERAS = [
    ("pre-285278cc(NUC lineage)",      None,               "2026-10-01 20:35"),
    ("285278cc",                       "2026-10-01 20:35", "2026-10-02 12:00"),
    ("fixface-2(1d7d2302/47d4308e)",   "2026-10-02 12:00", "2026-10-03 20:11"),
    ("fixface-3=e7044319/08a46d0a",    "2026-10-03 20:11", "2026-10-04 17:21"),
    ("build-2(8c3453c0/2ad9676e)",     "2026-10-04 17:21", "2026-10-05 12:00"),
    ("streamguard(b7de133d node 族)",  "2026-10-05 12:00", "2026-10-07 14:45"),
    # IQG 栈=T1-B M2 写码窗产物(f622bae2 lib/886b1e90 node); 分界=STATUS 10-07 14:45
    # "M2 写码窗完成"里程碑(此前 14:06-14:45 窗内 D1 首跑为 ENV-FAIL 归档轮)
    ("IQG(f622bae2/886b1e90)",         "2026-10-07 14:45", None),
]

# 战役名映射(无 banner 轮的臂; 来源=STATUS/DECISION_LOG/prereg 在册)
CAMPAIGN_ARM = [
    (re.compile(r"^run_X1(final)?_"), "X-line(gates-config canonical)", "era-map:prereg§0/X线"),
    (re.compile(r"^run_X2g\d+_"),     "X-line(gates-config canonical)", "era-map:prereg§0/X线五位形"),
    (re.compile(r"^run_X3l2[ab]_"),   "X-line(gates-config canonical)", "era-map:prereg§0/X线五位形"),
    (re.compile(r"^run_X1p_"),        "X-line(gates-config canonical)", "era-map:prereg§0/X1prime"),
    (re.compile(r"^run_T2BL\d+_"),    "T2并轮(gates+cauchy,W2BB)",      "era-map:T2 v9.1 STATUS 22:4x"),
    (re.compile(r"^run_T2MACH\d+_"),  "T2MACH(机器对照,T2域)",          "era-map:T2 v9.3 B3"),
    (re.compile(r"^run_T2RA\d+"),     "T2RA(streamguard 验证轮)",       "era-map:T2 v9.5 RA1-24"),
    (re.compile(r"^run_T2ZETA"),      "T2zeta(旋钮试验,T2域)",          "era-map:T2 v8.9 ζ"),
    (re.compile(r"^run_T2U4OBS"),     "T2域(U4 对照)",                  "era-map:T2 v8.9"),
    (re.compile(r"^run_DIAGCAUCHY_"), "诊断(cauchy 隔离,banner 臂+cauchy)", "era-map:T1 v11.7u5 00:4x"),
    (re.compile(r"^run_DIAGGUARD_"),  "诊断(guard 单臂)",               "era-map:T1 v11.7u5 00:4x"),
    (re.compile(r"^run_ARMCHK_"),     "检查轮(臂核查)",                 "era-map:T1 v11.9"),
    (re.compile(r"^run_VRFY1_"),      "VRFY(gates 臂验证轮)",           "era-map:T1 v11.9 单元1"),
    (re.compile(r"^run_VRG1_"),       "VRG(guard 臂判别轮,boot-2)",     "era-map:T1 v11.9 单元1"),
    (re.compile(r"^run_SUPHV2"),      "供给窗(guard 臂 P2/P3)",         "era-map:T1 v11.7u5 供给窗"),
    (re.compile(r"^run_M3R"),         "M3R(T1-B M3 v1.1 批,IQG v1.1 臂)", "era-map:T1 v11.25r2 M3 批"),
    (re.compile(r"^run_DRILL"),       "演练轮(注入演练,T1 域)",          "era-map:T1 v11.25r2 演练五案"),
    (re.compile(r"^run_H15_"),        "H15(用户指令验证轮,DESIGNER)",    "era-map:STATUS 10-07 18:05"),
]

def dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")

def boot_of(ts):
    for name, a, b in BOOTS_3090:
        if ts >= dt(a) and (b is None or ts < dt(b)):
            return name
    return None  # 落在关机窗=同步产物/NUC 出生

def stack_of(ts, machine):
    if machine.startswith("NUC") or machine.startswith("?"):
        # NUC 轮/机器不明轮 mtime=同步时间(10-04 09:2x 批), 非飞行时间, 不做年代细分
        return "NUC-lineage(mtime=同步时间,不细分)" if machine.startswith("NUC") else "?(机器不明,栈不可判)"
    for name, a, b in STACK_ERAS:
        if (a is None or ts >= dt(a)) and (b is None or ts < dt(b)):
            return name
    return "?"

ANSI = re.compile(r"\x1b\[[0-9;]*m")

def arm_short(arm):
    """紧凑双轴显示: SG(guard=?)·GATE(cost_gate=?) — 两 banner 独立轴."""
    g = re.search(r"SG:guard=(\d+)\s+sane_p=([\d.]+)\s+sane_v=([\d.]+)", arm)
    c = re.search(r"GATE:cost_gate=(\d+)", arm)
    parts = []
    if g:
        parts.append("SG(g=%s,p%s,v%s)" % (g.group(1), g.group(2), g.group(3)))
    elif "SG:" in arm:
        parts.append("SG(其他)")
    if c:
        parts.append("GATE(cg=%s)" % c.group(1))
    elif "GATE" in arm:
        parts.append("GATE(其他)")
    i = re.search(r"IQG:gate=(\d+)", arm)
    if i:
        parts.append("IQG(g=%s)" % i.group(1))
    elif "IQG:" in arm:
        parts.append("IQG(其他)")
    if "RFIX" in arm:
        parts.append("RFIX")
    if not parts:
        return arm.split("(")[0][:44]
    return arm.split("(")[0].strip()[:24] + " " + "·".join(parts)

def arm_of(d, name, simvins):
    """banner 实读优先; 否则战役名映射; 再否则 legacy."""
    simvins = ANSI.sub("", simvins or "")
    arm, prov, cauchy = None, None, None
    if simvins:
        m = re.search(r"\[T2SGCFG\]\s*(.+)", simvins)
        if m:
            arm = "SG:" + m.group(1).strip()
            prov = "banner:T2SGCFG"
        if re.search(r"\[T2GATECFG\]", simvins):
            g = re.search(r"\[T2GATECFG\]\s*(.+)", simvins)
            arm = (arm + " | " if arm else "") + "GATE:" + (g.group(1).strip() if g else "?")
            prov = (prov + "+" if prov else "") + "banner:T2GATECFG"
        if re.search(r"\[T2RFIXCFG\]", simvins):
            arm = (arm + " | " if arm else "") + "RFIX(staged)"
            prov = (prov + "+" if prov else "") + "banner:T2RFIXCFG"
        if re.search(r"\[T2IQGCFG\]", simvins):
            g = re.search(r"\[T2IQGCFG\]\s*(.+)", simvins)
            arm = (arm + " | " if arm else "") + "IQG:" + (g.group(1).strip() if g else "?")
            prov = (prov + "+" if prov else "") + "banner:T2IQGCFG"
    if arm is None:
        for rx, label, src in CAMPAIGN_ARM:
            if rx.match(name):
                return label, src, cauchy
        return "legacy(无banner)", "era-map:默认", cauchy
    # cauchy 在场判定: 名字映射战役的 cauchy 状态 + DIAGCAUCHY
    if "CAUCHY" in name.upper():
        cauchy = "in(DIAGCAUCHY)"
    elif re.match(r"^run_T2BL\d+_", name):
        cauchy = "in(T2并轮)"
    elif re.match(r"^run_T2RA\d+", name) and arm and arm.startswith("SG:"):
        cauchy = "in(RA cfg_streamguard=gates+cauchy+guard)"
    return arm, prov, cauchy

def parse_result(path):
    """RESULT.txt 四指标+j0+RESULT. 返回 dict."""
    r = dict(arrive=None, arrive_pass=None, avoid_pass=None, poscmd_pass=None,
             disarm=None, j0=None, result=None, dual_flag=None, anchor_line=None)
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return r
    m = re.search(r"leg1 到位\(真值\) min=([\d.-]+) m \(<[\d.]+.*?\)->([01])", txt)
    if m:
        r["arrive"], r["arrive_pass"] = float(m.group(1)), int(m.group(2))
    m = re.search(r"避障 min_dist=[\d.-]+ m \(>[\d.]+\)->([01])", txt)
    if m:
        r["avoid_pass"] = int(m.group(1))
    m = re.search(r"poscmd ([\d.]+) Hz \(>=\d+\)->([01])", txt)
    if m:
        r["poscmd_pass"] = int(m.group(2))
    m = re.search(r"auto_disarm->([01?])", txt)
    if m:
        r["disarm"] = m.group(1)
    m = re.search(r"帧稳定性 \|pre-post\|=([\d.]+) m", txt)
    if m:
        r["j0"] = float(m.group(1))
    m = re.search(r"RESULT=(PASS|FAIL|ENV-FAIL)", txt)
    if m:
        r["result"] = m.group(1)
    m = re.search(r"DUAL-ANCHOR v1\.4:.*?flag=(\S+)", txt)
    if m:
        r["dual_flag"] = m.group(1)
    m = re.search(r"anchor\(.*?\): (.+)", txt)
    if m:
        r["anchor_line"] = m.group(1).strip()[:60]
    return r

def parse_simvins(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def parse_wa_json(path):
    r = dict(j0d_jump=None, j0d_transit=None, j0d_dom=None, njf=None, wa_verdict=None, cf=None)
    try:
        d = json.load(open(path))
    except Exception:
        # 注意(v10.6 扩切口决策): j0d 列只认 wa_gate_online.json 历史源语义——不做
        # j0_decomp.json 回退填充(回退会改写旧行空列, 违反扩切口加性/零重判纪律);
        # 新轮的 j0d 数据权威通道=t3_results/j0d_stats 表(直读 j0_decomp.json)
        return r
    x = d.get("xline", {})
    dec = x.get("j0_decomp", {})
    if dec.get("available"):
        r["j0d_jump"], r["j0d_transit"] = dec.get("jump_m"), dec.get("transit_m")
        r["j0d_dom"] = dec.get("dominant")
    c = d.get("controlled", {})
    if "jumps_in" in c:
        r["njf"] = c.get("jumps_in", 0) + c.get("jumps_out", 0)
    r["wa_verdict"] = d.get("verdict")
    # cf 面: verdict 或 failed 列表
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT_DEF)
    ap.add_argument("--l3", default=L3_DEF)
    ap.add_argument("--out", default=os.path.expanduser("~/catkin_ws/sitl_sim/t3_results/combo_matrix_20261006"))
    a = ap.parse_args()

    l3 = {}
    if os.path.exists(a.l3):
        with open(a.l3) as f:
            for row in csv.DictReader(f):
                l3[row["round"]] = row

    rows = []
    for d in sorted(glob.glob(os.path.join(a.root, "run_*"))):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        # T1 v11.17(10-06): 注入/验证测试轮排除面——STARVE*(starve DoD 注入)/
        # PLAINCHK*(world 特征工程验证)/REGCHK(build 回归)非科学样本,禁入矩阵
        if re.match(r"run_(STARVE|PLAINCHK|REGCHK)", name):
            continue
        # 时间: bag mtime 优先, 否则目录 mtime
        bag = os.path.join(d, "flight.bag")
        ts_src = bag if os.path.exists(bag) else d
        try:
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(ts_src))
        except OSError:
            continue
        sim = parse_simvins(os.path.join(d, "simvins.log"))
        res = parse_result(os.path.join(d, "RESULT.txt"))
        # 出生机器
        ev = res.get("result") and ""
        try:
            rtxt = open(os.path.join(d, "RESULT.txt"), encoding="utf-8", errors="replace").read()
            m = re.search(r"证据[:：]\s*/home/(\w+)/", rtxt)
            if m:
                machine = {"ghj": "3090", "uav": "NUC"}.get(m.group(1), "?")
            else:
                # 无证据行轮(x4_batch/T1 F3 系产物): mtime 落 3090 boot 窗=推定 3090;
                # NUC 同步轮 mtime=10-04 09:2x 恰在关机窗 → 不会误推定
                machine = "3090(推定:boot窗)" if boot_of(ts) else "?(无证据行,关机窗)"
        except OSError:
            machine = "?"
        boot = boot_of(ts) if machine.startswith("3090") else "n/a"
        stack = stack_of(ts, machine if machine[0] in "3N?" else machine)
        arm, prov, cauchy = arm_of(d, name, sim)
        # T2fail 计数
        t2fail = sim.count("failure detection")
        wa = parse_wa_json(os.path.join(d, "wa_gate_online.json"))
        # 四绿: 到位/避障/poscmd/disarm 全 1
        four = None
        if all(res.get(k) is not None for k in ("arrive_pass", "avoid_pass", "poscmd_pass")) and res.get("disarm") in "01":
            four = int(res["arrive_pass"] == 1 and res["avoid_pass"] == 1
                       and res["poscmd_pass"] == 1 and res["disarm"] == "1")
        # 净轮: 四绿 ∧ j0<0.5 ∧ T2fail=0 (j0 取 j0d_jump 若有否则 pre-post)
        j0v = wa["j0d_jump"] if wa["j0d_jump"] is not None else res["j0"]
        net = int(four == 1 and t2fail == 0 and j0v is not None and j0v < 0.5) if four is not None else None
        rr = l3.get(name, {})
        # provenance 三源列(T3 v10.6 单元 2 框架; judge_site 恒 3090=判读单源化纪律)
        if name.startswith("n3_"):
            birth_machine, sync_channel = "nuc3", "nuc3-shipped"
        elif name.startswith("u4_"):
            birth_machine, sync_channel = "uav4", "uav4-synced"
        elif machine.startswith("3090"):
            birth_machine, sync_channel = "3090", "native"
        elif machine.startswith("NUC"):
            birth_machine, sync_channel = "uav4", "uav4-synced"
        else:
            birth_machine, sync_channel = "?", "?"
        rows.append(dict(
            round=name, date=ts.strftime("%Y-%m-%d %H:%M"), machine=machine, boot=boot,
            arm=arm, arm_prov=prov, cauchy=cauchy or "-", stack=stack,
            result=res["result"], arrive=res["arrive"], arrive_l3=rr.get("arr_new", ""),
            res_l3=rr.get("res_new", ""), dual=rr.get("flag", res.get("dual_flag") or ""),
            j0=res["j0"], j0d_jump=wa["j0d_jump"], j0d_transit=wa["j0d_transit"],
            j0d_dom=wa["j0d_dom"], njf=wa["njf"], t2fail=t2fail,
            four_green=four, net_round=net, wa_verdict=wa["wa_verdict"],
            birth_machine=birth_machine, sync_channel=sync_channel, judge_site="3090",
        ))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out + "_rounds.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- 聚合矩阵: arm×stack(3090 轮再剖 boot) ----
    combos = {}
    for r in rows:
        mgrp = "3090" if r["machine"].startswith("3090") else ("NUC" if r["machine"].startswith("NUC") else "?")
        key = (mgrp, r["arm"], r["stack"])
        combos.setdefault(key, {"rounds": [], "boots": {}})
        combos[key]["rounds"].append(r)
        combos[key]["boots"].setdefault(r["boot"], []).append(r)

    out = []
    out.append("=" * 100)
    out.append("T3 组合矩阵(判读域) — 臂×栈×boot×结果  生成: %s" % datetime.datetime.now().strftime("%F %T"))
    out.append("全库口径: %s (%d 轮) | L3 join: %s | 范围注: t3_results WA 系 X 线前战役轮不在册" % (a.root, len(rows), a.l3))
    out.append("boot 谱系: B1004=10-05白昼(晨boot-0) B1005=10-05夜(reboot-1,风暴夜) B1006=10-06凌晨(reboot-2,VRFY/VRG)")
    out.append("四绿=到位/避障/poscmd/disarm 全1 | 净轮=四绿∧j0(jump)<0.5∧T2fail=0 | 风暴轮=T2fail>0")
    out.append("=" * 100)
    hdr = "%-5s %-40s %-24s %-6s %-4s %-4s %-4s %-4s %-6s %s" % (
        "机", "臂", "栈", "boot", "轮数", "四绿", "净轮", "风暴", "绿率", "j0(jump)范围")
    for mk in ("3090", "NUC", "?"):
        sub = {k: v for k, v in combos.items() if k[0] == mk}
        if not sub:
            continue
        out.append("")
        out.append("### 出生机器=%s (%d 组合)" % (mk, len(sub)))
        for key in sorted(sub, key=lambda k: (k[1], k[2])):
            machine, arm, stack = key
            v = sub[key]
            allr = v["rounds"]
            # 按 boot 剖分行
            for b in sorted(x for x in v["boots"] if x):
                brs = v["boots"][b]
                four = sum(1 for r in brs if r["four_green"] == 1)
                net = sum(1 for r in brs if r["net_round"] == 1)
                storm = sum(1 for r in brs if (r["t2fail"] or 0) > 0)
                j0s = [r["j0d_jump"] if r["j0d_jump"] is not None else r["j0"] for r in brs]
                j0s = [x for x in j0s if x is not None]
                rng = ("%.3f-%.3f" % (min(j0s), max(j0s))) if j0s else "-"
                gr = "%.0f%%" % (100.0 * four / len(brs)) if four else "0%"
                out.append("%-5s %-46s %-24s %-6s %4d %4d %4d %4d %5s  %s" % (
                    machine, arm_short(arm), stack[:24], b, len(brs), four, net, storm, gr, rng))
            # 组合级(跨 boot)三歧
            four_all = sum(1 for r in allr if r["four_green"] == 1)
            net_all = sum(1 for r in allr if r["net_round"] == 1)
            per_boot_green = {b: sum(1 for r in v["boots"][b] if r["four_green"] == 1)
                              for b in v["boots"] if b}
            z = "Z=零成功(组合0四绿)" if four_all == 0 else "Z-否(四绿%d)" % four_all
            boots_pos = [b for b, g in per_boot_green.items() if g > 0]
            boots_neg = [b for b, g in per_boot_green.items() if g == 0]
            m_ = "M=机器态歧(绿/非绿boot并存)" if (boots_pos and boots_neg) else ("M-否" if four_all else "M-不可判(全0)")
            if not boots_pos:
                m_ = "M-不可判(全0)"
            cay = {r["cauchy"] for r in allr if r["cauchy"] and r["cauchy"] != "-"}
            greens_c = {r["cauchy"] for r in allr if r["four_green"] == 1 and r["cauchy"] and r["cauchy"] != "-"}
            if four_all == 0:
                c_ = "C-不可判(0绿)"
            elif greens_c and all(str(x).startswith("in") for x in greens_c):
                c_ = "C=cauchy在场才绿(依赖嫌疑)" if not any(str(x).startswith("out") for x in cay) else "C-混合"
            else:
                c_ = "C-否(绿与cauchy无绑定)"
            out.append("     >> 三歧: %s | %s | %s | 净轮合计=%d" % (z, m_, c_, net_all))

    txt = "\n".join(out)
    open(a.out + "_matrix.txt", "w").write(txt)
    print(txt)
    print("\n[输出] %s_rounds.csv / %s_matrix.txt" % (a.out, a.out))

if __name__ == "__main__":
    main()
