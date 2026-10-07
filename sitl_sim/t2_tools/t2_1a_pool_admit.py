#!/usr/bin/env python3
"""t2_1a_pool_admit.py -- 1a pool admission per frozen A1 amendment (T2 v10.4).
criteria (frozen): |pre-post|<0.5m AND [T2fail] count==0 AND odom |P|max<15m.
|P|max from [T2diag] P=[x y z] lines (10Hz diag, per-frame).
usage: t2_1a_pool_admit.py <run_dir>...
"""
import csv, os, re, sys

RE_J0 = re.compile(r"pre-post\|=([\d.]+)")
RE_P = re.compile(r"P=\[([^\]]+)\]")

def check(rd):
    try:
        res = open(os.path.join(rd, "RESULT.txt"), errors="replace").read()
    except FileNotFoundError:
        return {"run": os.path.basename(rd), "j0": None, "t2fail": -1,
                "pmax": -1.0, "admit": False}
    m = RE_J0.search(res)
    j0 = float(m.group(1)) if m else None
    nfail = 0
    pmax = 0.0
    try:
        for line in open(os.path.join(rd, "simvins.log"), errors="replace"):
            if "[T2fail]" in line:
                nfail += 1
            elif "[T2diag]" in line:
                m2 = RE_P.search(line)
                if m2:
                    try:
                        xyz = [float(v) for v in m2.group(1).replace(",", " ").split()]
                        pmax = max(pmax, max(abs(v) for v in xyz[:3]))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    admit = (j0 is not None and j0 < 0.5 and nfail == 0 and pmax < 15.0)
    return {"run": os.path.basename(rd), "j0": j0, "t2fail": nfail,
            "pmax": round(pmax, 2), "admit": admit}

if __name__ == "__main__":
    rows = [check(rd) for rd in sys.argv[1:]]
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
    n_adm = sum(1 for r in rows if r["admit"])
    sys.stderr.write("# admitted %d/%d\n" % (n_adm, len(rows)))
