#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t1_gate_watch.py — T1 v11.20 单元1 双门引擎(纯脚本面;vins_node/libvins_lib 零接触)

三模式(同一求值核,在线/离线逐位同代码——ROC 重放=门可信度的构造性保证):
  --pregate  <round_dir>          1a 起飞前门: init 健康度三指标 → verdict PASS/REINIT/ABORT
                                  → pregate_<tag>.json
  --inflight <round_dir>          1b 飞行中前兆门 watchdog: tail simvins.log,双指标双门结构
                                  → gate_timeline_<tag>.jsonl(1Hz 滚动比值,支持后验阈值扫描)
                                  → 触发写 gatehit_<tag>.json + gatehit.flag,exit 3
  --replay   <logfile> [--grid F] 单元2 ROC: 静态 log 全量重放;--grid 参数网格逐组输出
                                  would-trip 时刻表(零误拦/全触发/提前量分布)
参数正源=t1_gate_params.json(PLACEHOLDER→T2 科学包填参冻结;null=OBSERVE 不触发只记时间线)

判值结构(任务书 1b 预注册):
  指标=cost 主([T2slv] phase=1 final_cost)+|Bas| 副([T2diag]);
  双门=①绝对门(滚动中位 vs 绝对包络)②轮内自适应门(起飞稳定窗自身分布为基线,
  偏离倍数持续窗);起飞检测=T2diag |V|>to_det_v 持续 to_det_s(自含,不依赖外部相位信号)。
  侧证吸收: 绿格 cost 瞬态峰比 10-104(定因机械腿 side-finding)→单峰不触发,
  必须持续窗+滚动中位;判别力在"平台持续性"非峰值。
时间基: [T2slv]/[T2diag] 同基(vins node 起,sim 秒);两行 flush 延迟实测登记面=timeline
  的 flush_est 列(wall 到达差-sim 推进差,含 RTF 系统偏差的保守上界)。
"""
import os, re, sys, json, time, argparse, statistics as st

RE_SLV = re.compile(r"\[T2slv\] t=([\d.]+) phase=(\d+) init_cost=([\d.eE+-]+) "
                    r"final_cost=([\d.eE+-]+) iters=(\d+) term=(\d+) slv_ms=([\d.]+)")
RE_DIA = re.compile(r"\[T2diag\] t=([\d.]+) P=\[([-0-9.eE ]+)\] V=\[([-0-9.eE ]+)\] "
                    r"\|Bas\|=([\d.eE+-]+).*track=(\d+)")
RE_KNOBS = re.compile(r"T2 knobs: (.*)")

DEF_PARAMS = {
    "version": "PLACEHOLDER-T2-PENDING-v0",
    "frozen": False,
    "pregate": {"init_cost_max": None, "bas_med_max": None, "track_min": None},
    "inflight": {
        "abs": {"cost_max": None, "bas_max": None, "sustain_s": 5.0},
        "adapt": {"to_det_v": 0.5, "to_det_z": 0.25, "to_det_s": 3.0,
                  "base_mode": "after_takeoff",
                  "base_off_a": 8.0, "base_off_b": 28.0, "dev_after_off": 32.0,
                  "cost_ratio": None, "bas_ratio": None,
                  "sustain_s": 5.0, "roll_med_s": 5.0},
    },
}

def load_params(path):
    if not path or not os.path.exists(path):
        return json.loads(json.dumps(DEF_PARAMS))
    p = json.load(open(path))
    # 浅合并缺省(允许 T2 包只给部分键)
    for k, v in DEF_PARAMS.items():
        p.setdefault(k, json.loads(json.dumps(v)))
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, dict):
                    p[k].setdefault(k2, json.loads(json.dumps(v2)))
                else:
                    p[k].setdefault(k2, v2)
    return p

class Samples:
    def __init__(self):
        self.t, self.cost, self.bas, self.speed, self.track, self.pos_z = [], [], [], [], [], []
    def roll_med(self, metric, t_now, win):
        s = getattr(self, metric)
        lo, hi = 0, len(s) - 1
        while lo < len(self.t) and self.t[lo] < t_now - win: lo += 1
        while hi > lo and self.t[hi] > t_now: hi -= 1
        vals = [x for x in s[lo:hi + 1] if x == x]
        return st.median(vals) if vals else None

def parse_lines(text, S, knobs):
    for ln in text.splitlines():
        m = RE_DIA.search(ln)
        if m:
            t = float(m.group(1))
            try:
                v = [float(x) for x in m.group(3).split()]
                spd = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5 if len(v) == 3 else 0.0
            except ValueError:
                spd = 0.0
            try:
                p = [float(x) for x in m.group(2).split()]
                pz = p[2] if len(p) == 3 else float("nan")
            except ValueError:
                pz = float("nan")
            S.t.append(t); S.bas.append(float(m.group(4)))
            S.speed.append(spd); S.track.append(float(m.group(5))); S.cost.append(float("nan"))
            S.pos_z.append(pz)
            continue
        m = RE_SLV.search(ln)
        if m:
            t, ph = float(m.group(1)), int(m.group(2))
            if ph != 1:
                if ph == 0 and not knobs.get("init"):
                    knobs["init"] = (t, float(m.group(4)))
                continue
            S.t.append(t); S.cost.append(float(m.group(4)))
            S.bas.append(float("nan")); S.speed.append(float("nan")); S.track.append(float("nan"))
            S.pos_z.append(float("nan"))
            continue
        m = RE_KNOBS.search(ln)
        if m and not knobs.get("line"):
            knobs["line"] = m.group(1)[:120]

def detect_takeoff(S, a):
    """t_to=起飞时刻。主探=odom z>to_det_z 持续 to_det_s(物理离地;慢速巡航剖面 V 阈不可用,
    12m/60s≈0.2m/s 实测);兜底=|V|>to_det_v(若 z 面至 t2slv+60 未触发)。nan=缺样跳过不重置。"""
    def run_find(getter, thr):
        run0 = None
        for i, t in enumerate(S.t):
            v = getter(i)
            if v != v:
                continue
            if v > thr:
                if run0 is None: run0 = t
                elif t - run0 >= a["to_det_s"]:
                    return run0
            else:
                run0 = None
        return None
    z = run_find(lambda i: S.pos_z[i], a.get("to_det_z", 0.25))
    if z is not None:
        return z
    if S.t and S.t[-1] > 60:
        return run_find(lambda i: S.speed[i], a.get("to_det_v", 0.5))
    return None

class GateState:
    """在线门状态机:feed(t_now) 后查 .tripped"""
    def __init__(self, P):
        self.P = P
        self.S = Samples()
        self.knobs = {}
        self.t_to = None
        self.base_cost = self.base_bas = None
        self.onset = {}      # cond名 → 首真时刻
        self.tripped = None  # (metric, gate, t, value, base)
        self.last_tick = 0.0
    def conditions(self, t_now, dev_from):
        a = self.P["inflight"]["adapt"]; ab = self.P["inflight"]["abs"]; roll = a["roll_med_s"]
        rc = self.S.roll_med("cost", t_now, roll)
        rb = self.S.roll_med("bas", t_now, roll)
        out = {}
        if ab["cost_max"] is not None and rc is not None:
            out["cost_abs"] = (rc, ab["cost_max"], rc > ab["cost_max"])
        if ab["bas_max"] is not None and rb is not None:
            out["bas_abs"] = (rb, ab["bas_max"], rb > ab["bas_max"])
        if self.base_cost is not None and a["cost_ratio"] is not None and rc is not None and t_now >= dev_from:
            out["cost_adapt"] = (rc, self.base_cost * a["cost_ratio"], rc > self.base_cost * a["cost_ratio"])
        if self.base_bas is not None and a["bas_ratio"] is not None and rb is not None and t_now >= dev_from:
            out["bas_adapt"] = (rb, self.base_bas * a["bas_ratio"], rb > self.base_bas * a["bas_ratio"])
        return rc, rb, out
    def tick(self, t_now):
        a = self.P["inflight"]["adapt"]
        if self.t_to is None:
            self.t_to = detect_takeoff(self.S, a)
            return None
        if a.get("base_mode", "after_takeoff") == "round_abs":
            wa, wb = a["base_off_a"], a["base_off_b"]
            dev_from = a["dev_after_off"]
        else:
            wa, wb = self.t_to + a["base_off_a"], self.t_to + a["base_off_b"]
            dev_from = self.t_to + a["dev_after_off"]
        if (self.base_cost is None or self.base_bas is None) and t_now >= wb:
            cs = [c for tt, c in zip(self.S.t, self.S.cost) if wa <= tt <= wb and c == c]
            bs = [b for tt, b in zip(self.S.t, self.S.bas) if wa <= tt <= wb and b == b]
            if cs: self.base_cost = st.median(cs)
            if bs: self.base_bas = st.median(bs)
        rc, rb, conds = self.conditions(t_now, dev_from)
        for name, (val, thr, hit) in conds.items():
            sust = self.P["inflight"]["abs"]["sustain_s"] if name.endswith("_abs") else a["sustain_s"]
            if hit:
                t0 = self.onset.get(name)
                if t0 is None:
                    self.onset[name] = t_now
                elif t_now - t0 >= sust and not self.tripped:
                    metric = "cost" if name.startswith("cost") else "bas"
                    gate = "absolute" if name.endswith("_abs") else "adaptive"
                    base = self.base_cost if metric == "cost" else self.base_bas
                    self.tripped = (metric, gate, t_now, val, base)
                    return self.tripped
            else:
                self.onset.pop(name, None)
        return None

def obs_ratio(self_rc, base):
    return round(self_rc / base, 3) if (self_rc is not None and base) else None

# ---------------- pregate ----------------
def do_pregate(rd, params):
    tag = os.path.basename(rd).replace("run_", "").rsplit("_", 1)[0]
    log = os.path.join(rd, "simvins.log")
    if not os.path.exists(log):
        out = {"tag": tag, "verdict": "ABORT", "reason": "simvins.log 缺席", "params_version": params["version"]}
        json.dump(out, open(os.path.join(rd, "pregate_%s.json" % tag), "w"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False)); return
    S = Samples(); knobs = {}
    parse_lines(open(log, errors="replace").read(), S, knobs)
    init = knobs.get("init")
    post = [b for t, b in zip(S.t, S.bas) if init and init[0] <= t <= init[0] + 5 and b == b]
    trk = [x for x in S.track if x == x]
    m = {"init_final_cost": init[1] if init else None,
         "bas_med_post_init": round(st.median(post), 5) if post else None,
         "track_med": st.median(trk) if trk else None,
         "knobs_line": knobs.get("line"), "n_t2slv_p1": sum(1 for c in S.cost if c == c),
         "n_t2diag": sum(1 for b in S.bas if b == b)}
    pg = params["pregate"]; fails = []
    if pg["init_cost_max"] is not None and m["init_final_cost"] is not None and m["init_final_cost"] > pg["init_cost_max"]:
        fails.append("init_cost %s > %s" % (m["init_final_cost"], pg["init_cost_max"]))
    if pg["bas_med_max"] is not None and m["bas_med_post_init"] is not None and m["bas_med_post_init"] > pg["bas_med_max"]:
        fails.append("bas_med %s > %s" % (m["bas_med_post_init"], pg["bas_med_max"]))
    if pg["track_min"] is not None and m["track_med"] is not None and m["track_med"] < pg["track_min"]:
        fails.append("track %s < %s" % (m["track_med"], pg["track_min"]))
    if fails:
        verdict = "REINIT"
    elif params["frozen"]:
        verdict = "PASS"
    else:
        verdict = "PASS(OBSERVE)"  # 参数未冻结=观察面,如实标注
    # 注:最终拒绝判决名='block'(T3 trichotomy 契约字段;REINIT=中途重启域,block=轮作废域)
    out = {"tag": tag, "params_version": params["version"], "frozen": params["frozen"],
           "metrics": m, "fails": fails, "verdict": verdict,
           "action": "none" if verdict.startswith("PASS") else ("vins_restart(≤2)" if verdict == "REINIT" else "block-round(env-abort)")}
    json.dump(out, open(os.path.join(rd, "pregate_%s.json" % tag), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))

# ---------------- inflight / replay 共核 ----------------
def run_eval(rd_or_log, params, mode, tick_out=None, stop_flag=None):
    """mode: 'inflight'(tail 活文件,写 gatehit) / 'replay'(静态文件,只报)。返回 GateState。"""
    G = GateState(params)
    is_file = mode == "replay"
    tag = "replay"
    m = re.search(r"run_(.+)_\d{6}$", rd_or_log.rstrip("/")) or re.search(r"(.+)_cost\.tsv$", rd_or_log)
    if m: tag = m.group(1)
    tl_path = tick_out
    fp = open(rd_or_log, errors="replace") if is_file else open(rd_or_log, "simvins.log", errors="replace")
    pos0 = fp.tell()
    wall0 = None; t_sim0 = None; eval_t = None
    last_size = 0
    while True:
        chunk = fp.read()
        if chunk:
            pos_new = fp.tell()
            if pos_new > last_size:
                pass
            if wall0 is None:
                wall0 = time.time()
            parse_lines(chunk, G.S, G.knobs)
            if G.S.t and t_sim0 is None:
                t_sim0 = G.S.t[0]
            # 步进求值:0.5s 一 tick(replay 单大 chunk 亦逐点过持续窗——机理与在线一致)
            if eval_t is None and G.S.t:
                eval_t = max(0.0, G.S.t[0] - 0.5)
            while G.S.t and eval_t + 0.5 <= G.S.t[-1]:
                eval_t += 0.5
                t_now = eval_t
                trip = G.tick(t_now)
                flush_est = round((time.time() - wall0) - (t_now - (t_sim0 or t_now)), 1) if wall0 else None
                if tl_path and t_now - G.last_tick >= 0.9:
                    G.last_tick = t_now
                    rc = G.S.roll_med("cost", t_now, G.P["inflight"]["adapt"]["roll_med_s"])
                    rb = G.S.roll_med("bas", t_now, G.P["inflight"]["adapt"]["roll_med_s"])
                    rec = {"t": t_now, "cost_roll": round(rc, 2) if rc == rc else None,
                           "bas_roll": round(rb, 4) if rb == rb else None,
                           "cost_base": G.base_cost, "bas_base": (round(G.base_bas, 4) if G.base_bas else None),
                           "cost_r": obs_ratio(rc, G.base_cost), "bas_r": obs_ratio(rb, G.base_bas),
                           "t_to": G.t_to, "flush_est_s": flush_est}
                    if tl_path == "stdout":
                        print(json.dumps(rec, ensure_ascii=False), flush=True)
                    else:
                        with open(tl_path, "a") as tf:
                            tf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if trip and params["frozen"]:
                    last_slv = max((t for t, c in zip(G.S.t, G.S.cost) if c == c), default=None)
                    last_dia = max((t for t, b in zip(G.S.t, G.S.bas) if b == b), default=None)
                    # 字段名对齐 T3 trichotomy 契约(t_trig/value/action/landed; landed 由
                    # vins_smoke gate_abort 收束后回写 1)
                    hit = {"tag": tag, "t_trig": round(trip[2], 2), "metric": trip[0], "gate": trip[1],
                           "value": round(trip[3], 3), "trigger_value": round(trip[3], 3),
                           "baseline": round(trip[4], 3) if trip[4] else None,
                           "action": "goal-stop->controlled-abort(land)->teardown",
                           "landed": 0,
                           "trip_t": round(trip[2], 2),
                           "params_version": params["version"],
                           "vins_stream": {"last_t2slv_t": last_slv, "last_t2diag_t": last_dia,
                                           "gap_s": (round(t_now - max(x for x in (last_slv, last_dia) if x), 1)
                                                     if (last_slv or last_dia) else None)},
                           "action_chain": "goal_stop->land(H-1 kill planner first)->teardown",
                           "degrade_ladder": "①odom可信段LAND ②stream死/未disarm→悬停+kill电机(实机=需人工接管协议)"}
                    base_dir = os.path.dirname(os.path.abspath(rd_or_log)) if not is_file else os.path.dirname(rd_or_log)
                    json.dump(hit, open(os.path.join(base_dir, "gatehit_%s.json" % tag), "w"),
                              ensure_ascii=False, indent=1)
                    open(os.path.join(base_dir, "gatehit.flag"), "w").write("%s\n" % trip[0])
                    print("GATEHIT " + json.dumps(hit, ensure_ascii=False), flush=True)
                    return G
        else:
            if is_file:
                break
            if stop_flag and os.path.exists(stop_flag):
                break
            time.sleep(0.4)
    return G

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pregate"); ap.add_argument("--inflight"); ap.add_argument("--replay")
    ap.add_argument("--params", default=os.path.expanduser("~/sitl_sim/t1_gate_params.json"))
    ap.add_argument("--timeline", default=None)
    ap.add_argument("--grid", default=None)
    a = ap.parse_args()
    params = load_params(a.params)
    if a.pregate:
        do_pregate(a.pregate, params); return
    if a.inflight:
        tl = a.timeline or os.path.join(a.inflight, "gate_timeline_%s.jsonl" %
             os.path.basename(a.inflight).replace("run_", "").rsplit("_", 1)[0])
        run_eval(a.inflight, params, "inflight", tick_out=tl,
                 stop_flag=os.path.join(a.inflight, "gate_stop.flag")); return
    if a.replay:
        G = run_eval(a.replay, params, "replay", tick_out=a.timeline)
        print(json.dumps({"replay": a.replay, "tripped": bool(G.tripped),
                          "trip": G.tripped, "t_to": G.t_to,
                          "base_cost": G.base_cost, "base_bas": G.base_bas}, ensure_ascii=False))
        return
    print("need --pregate/--inflight/--replay"); sys.exit(2)

if __name__ == "__main__":
    main()
