#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E4 切点稳健全因子细网格（x08–x12 含 x09/x11）+ 分量比近界余量画像（2026-10-03，0 锁池件）。

数据源（全部在册产物，不重跑重活）：
  e4_framelevel_conditions.csv（21db0db 注册基线：cut/pool_p50/p90/hi_share/x08/x12/ftype_*）
  e4_framelevel_fbres_*.json（v55 副本，per-frame stereo 条目）
帧级高位簇统计量：entry['p50'] > cut×k（先对照注册 hi_share/x08/x12 验证统计量口径，MISMATCH 则如实报）。
分型映射=t4_e4_bimodal_prereg.md §3（低位健康 p90<10 / 两簇分离 hi≤0.2 且 p50/p90<0.1 /
混合 0.2–0.5 / 高位主体 ≥0.5；映射空隙如实标注）。
近界画像：三条件各自距门余量（ΔBIC 门 10 / BC 门 0.555 / 分量比门 1.5）+ 分量比阈值网格翻位点。
只产统计表，判语归主会话。
"""
import csv, json, os

V55 = '/home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived'
BAGS = ['X1final_173345', 'U3PR1_212450', 'U3PR2_213717', 'U3PG_210307', 'U3PO_211438', 'U3PH_210708']
MULTS = [0.8, 0.9, 1.0, 1.1, 1.2]

cond = {}
with open(os.path.join(V55, 'e4_framelevel_conditions.csv'), encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        cond[row['bag']] = row

def ftype(hi, p50, p90):
    if p90 < 10:
        return '低位健康型'
    if hi <= 0.2 and (p90 > 0 and p50 / p90 < 0.1):
        return '两簇分离型'
    if hi >= 0.5:
        return '高位主体型'
    if 0.2 < hi < 0.5:
        return '混合型'
    return 'MAPPING-GAP'

rows, issues = [], []
for b in BAGS:
    c = cond[b]
    cut, p50, p90 = float(c['cut']), float(c['pool_p50']), float(c['pool_p90'])
    d = json.load(open(os.path.join(V55, 'e4_framelevel_fbres_%s.json' % b)))
    p50s = [e['p50'] for e in d['stereo']]
    n = len(p50s)
    hs = {k: sum(1 for v in p50s if v > cut * k) / n for k in MULTS}
    ok = (abs(hs[1.0] - float(c['hi_share'])) < 1e-9
          and abs(hs[0.8] - float(c['hi_share_x08'])) < 1e-9
          and abs(hs[1.2] - float(c['hi_share_x12'])) < 1e-9)
    if not ok:
        issues.append('%s 统计量口径对照 MISMATCH(注册 %.4f/%.4f/%.4f vs 重算 %.4f/%.4f/%.4f)' % (
            b, float(c['hi_share']), float(c['hi_share_x08']), float(c['hi_share_x12']),
            hs[1.0], hs[0.8], hs[1.2]))
    types = {k: ftype(hs[k], p50, p90) for k in MULTS}
    for k in (0.8, 1.2):
        reg = c['ftype_x08'] if k == 0.8 else c['ftype_x12']
        if types[k] != reg:
            issues.append('%s ftype_x%02d 重算=%s 注册=%s（边界口径差，如实登记）' % (b, int(k * 10), types[k], reg))
    rows.append({
        'bag': b, 'n_frames': n, 'cut': round(cut, 4), 'pool_p50': round(p50, 4), 'pool_p90': round(p90, 4),
        **{'hi_share_x%02d' % int(k * 10): round(hs[k], 6) for k in MULTS},
        **{'ftype_x%02d' % int(k * 10): types[k] for k in MULTS},
        'cut_robust_fine': 'YES' if len(set(types.values())) == 1 else 'NO',
        'validate_statistic': 'OK' if ok else 'MISMATCH',
        'registered_ftype': c['ftype'],
    })

# 近界余量画像（六袋全列，U3PR2 为近界主角）
margins = []
THETAS = [1.35, 1.40, 1.45, 1.50, 1.55, 1.60, 1.65]
for b in BAGS:
    c = cond[b]
    dbic, bc, ratio = float(c['dbic']), float(c['bc']), float(c['ratio'])
    # cond1 口径=1GMM_BIC−2GMM_BIC>10（csv dbic 为 2GMM−1GMM，故过门条件 dbic<−10）
    cond1, cond2 = dbic < -10, bc > 0.555
    m = {
        'bag': b, 'dbic': round(dbic, 4), 'cond1_margin': round(-dbic - 10, 4),
        'bc': round(bc, 4), 'cond2_margin': round(bc - 0.555, 4),
        'ratio': round(ratio, 4), 'cond3_margin': round(ratio - 1.5, 4),
        'ratio_flip_band': [t for t in THETAS if (ratio >= t) != (ratio >= 1.5)] and
                           'theta_in_%.2f-%.2f' % (min(ratio, 1.5), max(ratio, 1.5)) if abs(ratio - 1.5) > 1e-12 else 'at-threshold',
        'cond3_true_theta_grid': [t for t in THETAS if ratio >= t],
        'three_all_any_theta': None,
    }
    # 合取在各 θ 网格点是否可能为真（cond1/cond2 固定值不随 θ 变）
    m['three_all_any_theta'] = 'NO(cond1/cond2 固定不全过)' if not (cond1 and cond2) else \
        ('YES' if cond1 and cond2 and ratio >= min(THETAS) else 'depends')
    margins.append(m)

with open(os.path.join(V55, 'pool_e4_cutpoint_scan.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
with open(os.path.join(V55, 'pool_e4_margin.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(margins[0].keys()))
    w.writeheader()
    w.writerows(margins)

print('== CUTPOINT FINE GRID ==')
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
print('== MARGIN PROFILE ==')
for m in margins:
    print(json.dumps(m, ensure_ascii=False))
print('== ISSUES ==')
print('\n'.join(issues) if issues else 'NONE')
