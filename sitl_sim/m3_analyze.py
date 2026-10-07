#!/usr/bin/env python3
"""M3 格级双列对比分析(T1 v11.25 阶段 3;判据=REGEN v1.1 §3 格级双列输出)
读 m3_batch_report.csv → 每格: 史绿率→M3 绿率+Δ;组间: 毒格组 Δ均值 vs 绿格组 Δ均值。
史带基线(REGEN v1.1 冻结数字): E8P 跳变率 100%;S12P 0%;S8O 0%;绿格组 70.5%/轮。
输出=stdout 表格+m3_celltable.md。"""
import csv, os, sys

BASE = {
    # cell: (史绿率%, 史带注)
    "E8P": (0.0, "毒格:史 4/4+1/1 跳=100% 失败(绿率 0)"),
    "S12P": (0.0, "毒格:X4 true_fail 单轮史(绿率 0)"),
    "S8O": (0.0, "毒格:X4 true_fail 单轮史(绿率 0)"),
    "E12O": (100.0, "绿格:X4 phys_green 史(1/1)"),
    "NE8O": (100.0, "绿格:X4 phys_green 史(1/1)"),
    "N8P": (100.0, "绿格:X4 phys_green 史(1/1)"),
}
POISON = {"E8P", "S12P", "S8O"}

def main():
    rows = list(csv.DictReader(open(os.path.expanduser(
        "~/sitl_sim/t3_results/m3_batch_report.csv"))))
    per = {}
    for r in rows:
        c = r["cell"]
        per.setdefault(c, []).append(r)
    lines = ["# M3 格级双列对比（REGEN v1.1 §3；T1 v11.25 阶段 3）", "",
             "| 格 | 组 | 史绿率→M3 绿率 | Δ | 明细(M3 轮) |", "|---|---|---|---|---|"]
    g_deltas = {"P": [], "G": []}
    for c in sorted(per):
        rs = per[c]
        n = len(rs)
        green = sum(1 for r in rs if r["verdict"] == "PASS")
        m3 = 100.0 * green / n
        hist = BASE[c][0]
        d = round(m3 - hist, 1)
        grp = "毒格" if c in POISON else "绿格"
        g_deltas["P" if c in POISON else "G"].append(d)
        detail = "; ".join("%s r%s=%s j=%s a=%s rej=%s" %
                           (r["tag"], r["round"], r["verdict"], r["jump"],
                            r["arrive"], r["iqg_rejects"]) for r in rs)
        lines.append("| %s | %s | %.0f%% → %.0f%% (%d/%d) | %+_.1f | %s |"
                     .replace("%+_.1f", "%+.1f") % (c, grp, hist, m3, green, n, d, detail))
    pd = sum(g_deltas["P"]) / len(g_deltas["P"]) if g_deltas["P"] else 0
    gd = sum(g_deltas["G"]) / len(g_deltas["G"]) if g_deltas["G"] else 0
    lines += ["", "组间对比: 毒格组 Δ均值=%+.1f pp vs 绿格组 Δ均值=%+.1f pp(分离=%+.1f pp)"
              % (pd, gd, pd - gd),
              "活性证: 拒收计数>0 的轮数=%d" % sum(1 for r in rows if r["iqg_rejects"] not in ("", "0"))]
    out = "\n".join(lines)
    print(out)
    p = os.path.expanduser("~/sitl_sim/t3_results/m3_celltable.md")
    open(p, "w").write(out + "\n")
    print("-> %s" % p)

if __name__ == "__main__":
    main()
