#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C-15 残留钩子：WC2OBS1 echo 同型 bit 级复核（T4 自域件，2026-10-03）。

钩子原文（T2 台账:1803，t4_t2_handoff_tracking.md §3 登记）：
  "WC2OBS1 同型（T4 983/2035 步 dt≤0）按同机制归档（echo），bit 级复核由 T4 自域需要时执行
   （features.bag=T4 域产物）"
源袋已删（W-0 清理）；本复核可行面=T4 自域 replay 产物 jr3_replay_WC2OBS1_0{30927,32005}_odom.csv。
echo 签名（对照 U3PR2 csv STRUCTURE AUDIT 在册值：dup_stamp_groups=6066/12142 行，max 2 行/stamp）：
  同 stamp 重复行组数 + 每 stamp 最大行数 + dt≤0 步（核对点名步 983/2035）。
只产统计事实，判语归主会话/台账登记。
"""
import csv, json, sys
from collections import Counter

def audit(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    tstr = [r['t'] for r in rows]           # 字符串精确分组（bit 级）
    tf = [float(x) for x in tstr]
    c = Counter(tstr)
    dup = {k: v for k, v in c.items() if v > 1}
    dt_le0 = [i for i in range(1, len(tf)) if tf[i] - tf[i - 1] <= 0]  # i=数据行 1-based 前驱差分
    dup_pz_pairs = []
    for k in list(dup)[:5]:
        pz = [r['pz'] for r in rows if r['t'] == k]
        dup_pz_pairs.append({'t': k, 'pz_values': pz})
    return {
        'file': path.split('/')[-1],
        'data_rows': len(rows),
        't_range': [min(tf), max(tf)] if tf else None,
        'dup_stamp_groups': len(dup),
        'dup_rows_total': sum(dup.values()),
        'max_rows_per_stamp': max(dup.values()) if dup else 1,
        'dup_t_first5': sorted(dup)[:5],
        'dup_pz_pairs_sample': dup_pz_pairs,
        'dt_le0_count': len(dt_le0),
        'dt_le0_steps_1based_first20': dt_le0[:20],
        'dt_le0_steps_1based_all_if_le20': dt_le0 if len(dt_le0) <= 20 else '(>20, 见前20)',
        'noted_steps_983_2035_hit': [s for s in (983, 2035) if s in dt_le0],
    }

out = [audit(p) for p in sys.argv[1:]]
print(json.dumps(out, ensure_ascii=False, indent=1))
