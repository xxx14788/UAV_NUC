#!/usr/bin/env python3
"""VRFY1 -nan 交互链解剖: simvins.log 全量解析 -> 事件表+时间线CSV+摘要.

产出目录: /home/ghj/sitl_sim/t2_results/nan_dissect_vrfy1/
"""
import json
import re
import sys
from pathlib import Path

LOG = Path(sys.argv[1] if len(sys.argv) > 1 else
           "/home/ghj/sitl_sim/vins_smoke_runs/run_VRFY1_023908/simvins.log")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else
           "/home/ghj/sitl_sim/t2_results/nan_dissect_vrfy1")
OUT.mkdir(parents=True, exist_ok=True)

# ---- patterns ----
re_t2 = re.compile(r'\[(T2slv|T2gate|T2diag|T2depth|T2xcross)\] t=([0-9.eE+-]+) (.*)$')
re_ros_t = re.compile(r'\[\d+\.\d+, ([0-9.eE+-]+)\]: ?')
re_ros_msg = re.compile(r'\[\d+\.\d+, [0-9.eE+-]+\]: (.*)$')
re_kv = re.compile(r'(\w+)=("[^"]*"|\S+)')

last_t = 0.0          # most recent sim time seen on any timestamped line
last_t_src = ""

events = []   # dicts: seq, t, line, type, detail
slv = []
gate = []
diag = []
depth_sec = {}   # t_int -> dict(n, ok, flags{})
xcross_sec = {}  # t_int -> dict(n, rel_sum, rel_max, svd_min)

stats = dict(
    total_lines=0, slv_n=0, slv_nan=0, slv_phase0=0, slv_phase0_nan=0,
    slv_phase1=0, slv_phase1_nan=0, gate_n=0,
    init_finish=0, cost_reboot=0, gate_reject=0, insane=0,
    t2opt_nan=0, t2opt_n=0, ceres_err=0, gyro_calib=0,
    post_reject=0, uls=0, settle_skip=0,
)

cur_ceres_block = None   # last seen "Residual Block size: NxM" before an error dump

def flush_ceres_error(ln):
    events.append(dict(t=last_t, line=ln, type="ceres_eval_err",
                       detail=cur_ceres_block or "?"))

with LOG.open("r", errors="replace") as f:
    for ln, raw in enumerate(f, 1):
        stats["total_lines"] += 1
        line = raw.rstrip("\n")
        # strip ANSI
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)

        # tagged T2 lines (authoritative sim time)
        m = re_t2.match(clean)
        if m:
            tag, t, rest = m.group(1), float(m.group(2)), m.group(3)
            last_t, last_t_src = t, tag
            kvs = dict(re_kv.findall(rest))
            if tag == "T2slv":
                stats["slv_n"] += 1
                ic, fc = kvs.get("init_cost"), kvs.get("final_cost")
                isnan = ("nan" in (ic or "")) or ("nan" in (fc or ""))
                ph = int(kvs.get("phase", -1))
                stats["slv_phase0" if ph == 0 else "slv_phase1"] += 1
                if isnan:
                    stats["slv_nan"] += 1
                    stats["slv_phase0_nan" if ph == 0 else "slv_phase1_nan"] += 1
                slv.append(dict(line=ln, t=t, phase=ph, init_cost=ic,
                                final_cost=fc, iters=kvs.get("iters"),
                                term=kvs.get("term"), slv_ms=kvs.get("slv_ms")))
            elif tag == "T2gate":
                stats["gate_n"] += 1
                gate.append(dict(line=ln, t=t, tri=kvs.get("tri"), rej=kvs.get("rej"),
                                 xrej=kvs.get("xrej"),
                                 init_replace=kvs.get("init_replace"),
                                 gate=kvs.get("gate"), ir_st=kvs.get("ir_st"),
                                 ir_m2=kvs.get("ir_m2"), ir_shift=kvs.get("ir_shift")))
            elif tag == "T2diag":
                diag.append(dict(line=ln, t=t,
                                 Px=kvs.get("P"), rest=rest[:160],
                                 track=kvs.get("track")))
            elif tag == "T2depth":
                s = depth_sec.setdefault(int(t), dict(n=0, ok=0, flags={}))
                s["n"] += 1
                if kvs.get("flag") == "ok":
                    s["ok"] += 1
                else:
                    s["flags"][kvs.get("flag", "?")] = \
                        s["flags"].get(kvs.get("flag", "?"), 0) + 1
            elif tag == "T2xcross":
                s = xcross_sec.setdefault(int(t), dict(n=0))
                s["n"] += 1
            continue

        # ROS lines: may carry sim time
        mt = re_ros_t.search(clean)
        msg = ""
        if mt:
            try:
                last_t = float(mt.group(1))
                last_t_src = "ros"
            except ValueError:
                pass
            mm = re_ros_msg.search(clean)
            msg = mm.group(1) if mm else ""
        else:
            msg = clean.strip()

        # event classification
        if "T2OPT post-solve" in clean:
            stats["t2opt_n"] += 1
            kvs2 = dict(re_kv.findall(clean))
            ic = kvs2.get("init_cost", "")
            isn = "nan" in ic
            if isn:
                stats["t2opt_nan"] += 1
            events.append(dict(t=last_t, line=ln, type="t2opt_initial_solve",
                               nan=isn, detail=clean[clean.find("T2OPT"):][:140]))
        elif "Initialization finish" in clean:
            stats["init_finish"] += 1
            events.append(dict(t=last_t, line=ln, type="init_finish", detail=""))
        elif "cost gate: streak" in clean:
            stats["cost_reboot"] += 1
            events.append(dict(t=last_t, line=ln, type="cost_gate_reboot",
                               detail=clean[clean.find("cost gate"):][:80]))
        elif "gate reject" in clean:
            stats["gate_reject"] += 1
            events.append(dict(t=last_t, line=ln, type="gate_reject",
                               detail=clean[clean.find("gate reject"):][:80]))
        elif "insane states" in clean:
            stats["insane"] += 1
            events.append(dict(t=last_t, line=ln, type="insane_states", detail=clean[:100]))
        elif "stereo init post-optimization states insane" in clean:
            stats["post_reject"] += 1
            events.append(dict(t=last_t, line=ln, type="post_opt_reject", detail=""))
        elif "gyroscope bias initial calibration" in clean:
            stats["gyro_calib"] += 1
            # not an event per se; counted only
        elif "Residual Block size:" in clean:
            cur_ceres_block = clean.strip()
        elif "Error in evaluating the ResidualBlock" in clean:
            stats["ceres_err"] += 1
            flush_ceres_error(ln)
        elif "T2SNAP" in clean:
            events.append(dict(t=last_t, line=ln, type="t2snap",
                               detail=clean[clean.find("T2SNAP"):][:200]))
        elif "failure detection" in clean:
            events.append(dict(t=last_t, line=ln, type="failure_detection", detail=""))
        elif clean.startswith("[T2fail]"):
            kvs2 = dict(re_kv.findall(clean))
            events.append(dict(t=last_t, line=ln, type="t2fail_snapshot",
                               detail=f"P={kvs2.get('P')} V={kvs2.get('V')} Bas={kvs2.get('|Bas|')} Bgs={kvs2.get('|Bgs|')} track={kvs2.get('track')}"))

# ---- write CSVs ----
import csv

def wcsv(name, rows, fields):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

wcsv("slv.csv", slv, ["line", "t", "phase", "init_cost", "final_cost",
                      "iters", "term", "slv_ms"])
wcsv("gate.csv", gate, ["line", "t", "tri", "rej", "xrej", "init_replace",
                        "gate", "ir_st", "ir_m2", "ir_shift"])
wcsv("diag.csv", diag, ["line", "t", "Px", "track", "rest"])
drows = [dict(t_sec=k, n=v["n"], ok=v["ok"],
              flags=";".join(f"{a}x{b}" for a, b in v["flags"].items()))
         for k, v in sorted(depth_sec.items())]
wcsv("depth_sec.csv", drows, ["t_sec", "n", "ok", "flags"])
evrows = [dict(seq=i + 1, **e) for i, e in enumerate(events)]
wcsv("events.csv", evrows,
     ["seq", "t", "line", "type", "nan", "detail"])
# events rows may lack 'nan'
with (OUT / "events.json").open("w") as f:
    json.dump(events, f, indent=1)
with (OUT / "summary.json").open("w") as f:
    json.dump(stats, f, indent=1)
print(json.dumps(stats, indent=1))
print(f"events={len(events)} -> {OUT}")
