#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2_bc_alive_join.py -- bc CSV alive 列伪影修复(任务书 v10.10 单元4 钦定口径:
alive 列由批尾统一判读器输出[bc_recovery_judge.txt]生成,非脚本内联读)
根因: 恢复脚本 replay_eval_row 的 AL 内联读 t3_results/$TAG/vins_alive.txt 路径
      与回放落盘路径错位→CSV alive 恒 0(伪影);轮目录 vins_alive.txt=1×11 实证。
Usage: t2_bc_alive_join.py <bc_recovery_results.csv> <bc_recovery_judge.txt>
行为: 就地重写 CSV alive 列(judge 无该轮行的行保持原值=dryrun-fail 类如实);
      原件备份 .bak_pre_alive_fix。
"""
import sys, csv, shutil, re

csv_path, judge_path = sys.argv[1], sys.argv[2]
judge_alive = {}
with open(judge_path, errors="replace") as f:
    for line in f:
        m = re.match(r"^([^,]+),([01]),", line)
        if m:
            judge_alive[m.group(1)] = m.group(2)

shutil.copy2(csv_path, csv_path + ".bak_pre_alive_fix")
rows = list(csv.DictReader(open(csv_path)))
fixed = kept = 0
for r in rows:
    tag = r["tag"]
    hit = None
    for k, v in judge_alive.items():
        if k.endswith("_%s_edited" % tag) or ("_%s_" % tag) in k:
            hit = v
            break
    if hit is not None:
        if r["alive"] != hit:
            r["alive"] = hit
            fixed += 1
        else:
            kept += 1
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("alive-join done: fixed=%d unchanged=%d total=%d (backup=%s)" %
      (fixed, kept, len(rows), csv_path + ".bak_pre_alive_fix"))
