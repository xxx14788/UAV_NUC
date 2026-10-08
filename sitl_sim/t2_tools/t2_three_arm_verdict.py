#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2_three_arm_verdict.py -- T2 v10.7 unit3: three-arm final verdict table.
Consumes: three_arm judge snapshot (arm A, v11.31 + night_chain), bc_recovery_results.csv
(arm B/C), writes verdict table with pre-registered criteria:
  eliminate  = j0_end < 1.0   (strong)
  waterfall  = j0_end >= 75.0 AND jumps >= 500   (baseline-like = no effect)
  else       = form-change candidate (needs time/amp check from eval.json) (weak)
Arm-level: both reps agree -> verdict; mixed -> "sensitive" annotation.
Two-caliber note (C-3 on record): j0_end column = end-start caliber (same as arm-A verdict);
frame_jumps column = jump count caliber; jump_prepost caliber differs for transit-slow-drift
dominant bags -- the "eliminate" branch consumption requires caliber declaration (this note).
"""
import csv, json, os, re, sys

HOME = os.path.expanduser("~")
IF = os.path.join(HOME, "sitl_sim/t2_results/INPUTFACE")
RUNS = os.path.join(IF, "1c_runs")
JUDGE_MID = "/tmp/judge_mid.txt"   # night_chain mid snapshot (arm A authoritative numbers)

def load_arm_a():
    """Parse judge_mid snapshot: tag,alive,ate,j0_end,t_jump,n_jumps"""
    rows = {}
    if not os.path.exists(JUDGE_MID):
        J = os.path.join(RUNS, "armA_judge.txt")
        if os.path.exists(J): JUDGE = J
        else: return rows
    src = JUDGE_MID if os.path.exists(JUDGE_MID) else os.path.join(RUNS, "armA_judge.txt")
    for line in open(src):
        parts = line.strip().split(",")
        if len(parts) < 6: continue
        tag = parts[0]
        try:
            rows[tag] = dict(alive=int(parts[1]), ate=float(parts[2]), j0_end=float(parts[3]),
                             t_jump=float(parts[4]), n_jumps=int(parts[5]))
        except ValueError:
            continue
    return rows

def classify(j0, nj):
    try: j0f = float(j0); njf = float(nj)
    except (TypeError, ValueError): return "NO-DATA"
    if j0f < 1.0: return "ELIMINATE"
    if j0f >= 75.0 and njf >= 500: return "WATERFALL(no-effect)"
    if 1.0 <= j0f < 75.0: return "FORM-CHANGE-cand"
    return "WATERFALL(no-effect)"   # j0>=75 but jumps<500: silent-drift form

def main():
    out = {}
    print("== ARM A (timestamp pairing; verdict v11.31: C1 real, dc in (2,5)ms) ==")
    arows = load_arm_a()
    for tag in sorted(arows):
        r = arows[tag]
        c = classify(r["j0_end"], r["n_jumps"])
        print("%-46s j0=%8.3f jumps=%5d t=%7.1f -> %s" % (tag, r["j0_end"], r["n_jumps"], r["t_jump"], c))
    print()
    print("== ARM B (frame rhythm) + ARM C (frame content) -- this campaign ==")
    bc = os.path.join(RUNS, "bc_recovery_results.csv")
    if not os.path.exists(bc):
        print("MISSING bc_recovery_results.csv"); return
    groups = {}
    for row in csv.DictReader(open(bc)):
        key = (row["arm"], row["param"], row["rep"])
        groups.setdefault((row["arm"], row["param"]), []).append(row)
        print("%-22s %-16s rep%s j0=%-8s jumps=%-6s ate=%-8s alive=%s -> %s" % (
            row["tag"], row["param"], row["rep"], row["j0_end"], row["jumps_n"],
            row["ate60"], row["alive"],
            classify(row["j0_end"], row["jumps_n"])))
    print()
    print("== ARM-LEVEL VERDICT ==")
    for (arm, param), rows in sorted(groups.items()):
        verdicts = [classify(r["j0_end"], r["jumps_n"]) for r in rows]
        if all(v == "ELIMINATE" for v in verdicts):
            lv = "ELIMINATE(strong) -- candidate CONFIRMED"
        elif all(v.startswith("WATERFALL") for v in verdicts):
            lv = "NO-EFFECT"
        elif any(v == "NO-DATA" for v in verdicts):
            lv = "INCOMPLETE(nodata)"
        else:
            lv = "SENSITIVE/MIXED(form-change weak candidate; per-rep: %s)" % "+".join(verdicts)
        print("  arm %s %-16s -> %s" % (arm, param, lv))

if __name__ == "__main__":
    main()
