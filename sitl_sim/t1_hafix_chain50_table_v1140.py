#!/usr/bin/env python3
# t1_hafix_chain50_table_v1140.py — HAFIX 修复链全程判读总表生成器（工程合并册单元 2）
# 输入=三个批的 verdict_v1140.csv（修复前复验 20 + 增量 10 + 终验 20 = 50 轮完整链）
# 输出=50 轮总表 md：逐轮行（六环旗+判+路径）+ 批级六环达成率列 + 修复前后对照。
# 用法: t1_hafix_chain50_table_v1140.py <out_md>
import csv, os, sys

OUTMD = os.path.expanduser(sys.argv[1])
BATCHES = [
    ("修复前复验批(20)", "~/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_reverify/verdict_v1140.csv", "pre-fix"),
    ("增量批(梯①盲降二次修复,10)", "~/sitl_sim/t1_evidence/v11_39_2026-10-09/hafix_increment10/verdict_v1140.csv", "post-fix"),
    ("终验批(20)", "~/sitl_sim/t1_evidence/v11_40_2026-10-10/hafix_finalverify/verdict_v1140.csv", "post-fix"),
]
RINGS = ["r1", "r2", "r3", "r4", "r5", "r6"]

def ring_set(rings_str):
    return set(x for x in (rings_str or "").split("/") if x)

rows_all = []
lines = ["# HAFIX 修复链全程判读总表（50 轮完整链——工程合并册单元 2）", "",
         "> 生成器 t1_hafix_chain50_table_v1140.py；判读器 t1_rejudge_hafix_v1140.py（B-7 参数化，"
         "S4 边界解读 SILENT-OK 预注册）；六环=①watch ②AUTO_LAND ③KILL ④armed drop ⑤z 落地 ⑥disarm landed 门。", ""]
summary = []
for label, path, era in BATCHES:
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        lines.append("## %s\n\n**CSV 缺失**（%s）\n" % (label, path))
        continue
    rows = list(csv.DictReader(open(path)))
    lines.append("## %s\n" % label)
    lines.append("| 轮 | 场景 | r1 | r2 | r3 | r4 | r5 | r6 | hafix行 | landed | 路径 | 判 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    cnt = {k: 0 for k in RINGS}; verdicts = {}
    for r in rows:
        rs = ring_set(r.get("rings", ""))
        for k in RINGS:
            if k in rs: cnt[k] += 1
        v = r.get("verdict", "?")
        verdicts[v] = verdicts.get(v, 0) + 1
        lines.append("| %s | %s | %s |" % (
            r.get("round"), r.get("scene"),
            " | ".join("✓" if k in rs else "·" for k in RINGS))
            + " | %s | %s | %s | %s |" % (r.get("hafix_lines"), r.get("landed"),
                                           r.get("path", "-"), v))
        rows_all.append((era, label, r, rs))
    n = len(rows)
    lines.append("")
    lines.append("- 六环达成率: " + " ".join("%s=%d/%d(%.0f%%)" % (
        k, cnt[k], n, 100.0*cnt[k]/n if n else 0) for k in RINGS))
    lines.append("- 判读分布: " + " ".join("%s=%d" % kv for kv in sorted(verdicts.items())))
    ok = verdicts.get("PASS", 0); sil = verdicts.get("SILENT-OK", 0)
    paths = {}
    for r in rows: paths[r.get("path", "-")] = paths.get(r.get("path", "-"), 0) + 1
    lines.append("- 路径分布: " + " ".join("%s=%d" % kv for kv in sorted(paths.items())))
    lines.append("")
    summary.append((label, n, cnt, verdicts, paths))

# 修复前后对照
lines.append("## 修复前后对照（终判口径）")
lines.append("")
lines.append("| 批 | 轮数 | PASS | SILENT-OK | FAIL | KILL 路径 | LAND 路径 |")
lines.append("|---|---|---|---|---|---|---|")
for label, n, cnt, verdicts, paths in summary:
    lines.append("| %s | %d | %d | %d | %d | %d | %d |" % (
        label, n, verdicts.get("PASS", 0), verdicts.get("SILENT-OK", 0),
        verdicts.get("FAIL", 0), paths.get("KILL", 0), paths.get("LAND", 0)))
lines.append("")
pre = [s for s in summary if "复验" in s[0]]
post = [s for s in summary if "复验" not in s[0]]
if pre and post:
    pn = sum(s[1] for s in pre); pp = sum(s[1] for s in post)
    pre_ok = sum(s[3].get("PASS", 0) for s in pre)
    post_ok = sum(s[3].get("PASS", 0) + s[3].get("SILENT-OK", 0) for s in post)
    post_pure = sum(s[3].get("PASS", 0) for s in post)
    lines.append("**修复前**（%d 轮）: PASS %d（%.0f%%）；**修复后**（增量+终验 %d 轮）: "
                 "PASS %d（%.0f%%）+SILENT-OK %d——物理链（LAND/KILL 落地路径）修复前 %d 轮 → 修复后 %d 轮。"
                 % (pn, pre_ok, 100.0*pre_ok/pn, pp, post_pure, 100.0*post_pure/pp,
                    post_ok - post_pure,
                    sum(s[4].get("LAND", 0) + s[4].get("KILL", 0) for s in pre),
                    sum(s[4].get("LAND", 0) + s[4].get("KILL", 0) for s in post)))
    lines.append("")
    # 六环对照行
    for k in RINGS:
        pre_r = sum(s[2][k] for s in pre); post_r = sum(s[2][k] for s in post)
        lines.append("- %s: 修复前 %d/%d（%.0f%%）→ 修复后 %d/%d（%.0f%%）" % (
            k, pre_r, pn, 100.0*pre_r/pn, post_r, pp, 100.0*post_r/pp))

open(OUTMD, "w").write("\n".join(lines) + "\n")
print("\n".join(lines[-14:]))
print("[OUT]", OUTMD)
