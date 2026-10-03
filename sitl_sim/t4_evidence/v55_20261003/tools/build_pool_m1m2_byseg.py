#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4-池件① 六袋 M1/M2 × 场景段(manifest seg)细分 —— 机械统计产出，无判读行。

输入(NUC):
  derived/pool_m1m2_j3img_<bag>.json   j3_image_metrics.py 输出(六袋, 本次新跑, C14 修复版)
  derived/smooth_lie_perframe.csv      仅取 U3PR2 in_window 标志做口径自检(5.5/D9 对表)
  ~/sitl_sim/vision_inputs/<bag>_j3/manifest.json   核素材覆盖

口径(与 5.5 包/D9 同):
  - seg = manifest frames[].seg = j3_extract_frames.py --segments 3 时基三等分(左闭右开)
  - 只取主帧 tag==''；左右相机(/iris_stereo_vins/vins_cam_left|_right)池化
  - M1 supply_frac / M2 grid4x4_occupancy_frac；非有限值帧剔除
  - P25/P50/P90 = numpy.percentile 线性插值；P50 CI = 覆盖>=95% 顺序统计量最窄区间(同 D9)

自检:
  A) U3PR2 窗内(in_window==1 主帧) M1/M2 P25/P50/P90 vs d9_freeze_profile.md 全窗表值(相对偏差<=1e-5)
  B) 每袋每 seg 本表 P50/n vs 工具 by_seg_median(精确一致)
  C) 每袋 ALL 本表 n/P50/P90 vs 工具 aggregate(精确一致)

输出:
  derived/pool_m1m2_byseg.csv
  derived/pool_m1m2_byseg.md
"""
import csv
import datetime
import json
import math
import os

import numpy as np

BASE = '/home/uav/catkin_ws/sitl_sim/t4_evidence/v55_20261003/derived'
J3 = '/home/uav/sitl_sim/vision_inputs'
BAGS = ['U3PG_210307', 'U3PH_210708', 'U3PO_211438',
        'U3PR1_212450', 'U3PR2_213717', 'X1final_173345']
METRICS = [('M1_supply_frac', 'supply_frac'),
           ('M2_grid4x4_occupancy_frac', 'grid4x4_occupancy_frac')]
# derived/d9_freeze_profile.md 复现自检表(全窗 P25/P50/P90, 显示值 6 位)
D9_TARGET = {
    'M1_supply_frac': (66, 0.453333, 0.473333, 0.533333),
    'M2_grid4x4_occupancy_frac': (66, 0.6875, 0.6875, 0.75),
}
TOOL_MD5 = '3721399e7a78e42f6e1cd81a2680286e'  # NUC analysis/j3_image_metrics.py (C14 修复版)


def med_ci95(vals):
    """P50 CI = 覆盖>=95% 的顺序统计量最窄区间(0-based [r,s])；n<5 覆盖不可达, 返回 None."""
    n = len(vals)
    if n < 5:
        return None
    pmf = [math.comb(n, k) * 0.5 ** n for k in range(n + 1)]
    cdf = np.cumsum(pmf)
    best = None
    for r in range(n):
        base = cdf[r - 1] if r > 0 else 0.0
        for s in range(r, n):
            if cdf[s] - base >= 0.95:
                if best is None or (s - r) < (best[1] - best[0]):
                    best = (r, s)
                break
    if best is None:
        return None
    sv = np.sort(np.asarray(vals, dtype=float))
    return float(sv[best[0]]), float(sv[best[1]])


def q(vals):
    a = np.asarray(vals, dtype=float)
    p25, p50, p90 = np.percentile(a, [25, 50, 90])  # 线性插值(默认)
    return float(p25), float(p50), float(p90)


def fin(m, key):
    v = m.get(key)
    return isinstance(v, (int, float)) and math.isfinite(v)


def main():
    rows = []          # csv 行: bag,seg,metric,n,p25,p50,p90,ci_lo,ci_hi
    baginfo = []       # (bag, n_man, n_man_main, n_primary)
    ck_b, ck_c = [], []

    for bag in BAGS:
        with open(os.path.join(BASE, 'pool_m1m2_j3img_%s.json' % bag)) as f:
            j = json.load(f)
        with open(os.path.join(J3, bag + '_j3', 'manifest.json')) as f:
            man = json.load(f)
        n_man = len(man['frames'])
        n_man_main = sum(1 for fr in man['frames'] if fr.get('tag', '') == '')
        baginfo.append((bag, n_man, n_man_main, j['n_primary']))
        per = [m for m in j['per_frame'] if m['tag'] == '']

        for label, key in METRICS:
            pts = [(m['seg'], m[key]) for m in per if fin(m, key)]
            segs = sorted(set(s for s, _ in pts))
            for seg in segs + ['ALL']:
                v = [x for s, x in pts if seg == 'ALL' or s == seg]
                p25, p50, p90 = q(v)
                ci = med_ci95(v)
                rows.append([bag, seg, label, len(v), p25, p50, p90,
                             ci[0] if ci else '', ci[1] if ci else ''])
                if seg != 'ALL':
                    t = j['metrics'][key]['by_seg_median'][str(int(seg))]
                    ck_b.append((bag, seg, label,
                                 t['n'] == len(v) and t['p50'] == p50))
            agg = j['metrics'][key]
            ar = [r for r in rows if r[0] == bag and r[1] == 'ALL' and r[2] == label][0]
            ck_c.append((bag, label,
                         agg['n'] == ar[3] and agg['p50'] == ar[5] and agg['p90'] == ar[6]))

    # 自检 A: U3PR2 窗内主帧 vs D9 全窗表值
    flag = {}
    with open(os.path.join(BASE, 'smooth_lie_perframe.csv'), newline='') as f:
        for r in csv.DictReader(f):
            if r['tag'] == '':
                flag[r['file']] = r['in_window']
    with open(os.path.join(BASE, 'pool_m1m2_j3img_U3PR2_213717.json')) as f:
        u3 = json.load(f)
    ck_a = {}
    for label, key in METRICS:
        v = [m[key] for m in u3['per_frame']
             if m['tag'] == '' and flag.get(m['file']) == '1' and fin(m, key)]
        p25, p50, p90 = q(v)
        tn, t25, t50, t90 = D9_TARGET[label]
        rel = max(abs(p25 - t25) / abs(t25), abs(p50 - t50) / abs(t50),
                  abs(p90 - t90) / abs(t90))
        ck_a[label] = (len(v), p25, p50, p90, rel, tn, len(v) == tn and rel <= 1e-5)

    # ---- CSV ----
    with open(os.path.join(BASE, 'pool_m1m2_byseg.csv'), 'w', newline='',
              encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bag', 'seg', 'metric', 'n', 'p25', 'p50', 'p90',
                    'p50_ci95_lo', 'p50_ci95_hi'])
        for r in rows:
            nums = ['%.10g' % x for x in r[4:7]]
            ci = ['%.10g' % r[7], '%.10g' % r[8]] if r[7] != '' else ['', '']
            w.writerow([r[0], r[1], r[2], r[3]] + nums + ci)

    # ---- MD ----
    L = []
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    L.append('# T4-池件① 六袋 M1/M2 × 场景段(manifest seg)细分表（J2 分场景附录用素材）')
    L.append('')
    L.append('- 生成：%s，NUC uav4，脚本经 /tmp 两段式上传后运行；本件为脚本机械输出，无判读行。' % now)
    L.append('- 被测工具：`sitl_sim/analysis/j3_image_metrics.py`（md5=%s，C14 修复版；'
             '修复前旧版 md5=abcc5fc811007b6ad16b8000d96f3022）。' % TOOL_MD5)
    L.append('- 帧级输入：`derived/pool_m1m2_j3img_<bag>.json`（六袋本次新跑，'
             '命令 `j3_image_metrics.py --frames-dir ~/sitl_sim/vision_inputs/<bag>_j3 '
             '--out derived/pool_m1m2_j3img_<bag>.json`，六袋退出码全 0）。')
    L.append('- seg 口径：manifest `frames[].seg` = `j3_extract_frames.py --segments 3` '
             '对袋时基三等分（t_min+span*i/3，左闭右开），seg=0/1/2 为时间早/中/晚三段，'
             '非语义场景标签。')
    L.append('- 统计口径（与 5.5 包/D9 同）：只取主帧 tag==\'\'，左右相机池化；'
             'P25/P50/P90=线性插值分位；P50 CI=覆盖>=95% 的顺序统计量最窄区间'
             '（同 d9_freeze_profile.md 约定，n<5 留空）。')
    L.append('')
    L.append('## 素材覆盖与缺素材注记')
    L.append('')
    L.append('| bag | manifest 帧记录 | 主帧(tag==\'\') | 工具 n_primary | 缺文件/不可读 |')
    L.append('|---|---|---|---|---|')
    for bag, n_man, n_man_main, n_prim in baginfo:
        miss = n_man_main - n_prim
        L.append('| %s | %d | %d | %d | %d |' % (bag, n_man, n_man_main, n_prim, miss))
    L.append('')
    L.append('注记：六袋 manifest 主帧 PNG 全部可读（缺文件/不可读=0），无缺素材袋；'
             'U3PG_210307 主帧 73、U3PO_211438 主帧 74，较标称 12 选中帧×2 相机=24/seg '
             '多 1–2 帧（seg0 为 25/26），按 manifest 原样计入，不作剔除。')
    L.append('')
    L.append('## 复现自检')
    L.append('')
    L.append('A) U3PR2_213717 窗内（smooth_lie_perframe.csv in_window==1 主帧）重算 vs '
             '`derived/d9_freeze_profile.md` 全窗表值（相对偏差<=1e-5 判一致）：')
    L.append('')
    L.append('| 指标 | n(本/表) | P25 本 | P50 本 | P90 本 | 最大相对偏差 | 一致 |')
    L.append('|---|---|---|---|---|---|---|')
    for label in ('M1_supply_frac', 'M2_grid4x4_occupancy_frac'):
        n, p25, p50, p90, rel, tn, ok = ck_a[label]
        L.append('| %s | %d/%d | %.10g | %.10g | %.10g | %.3g | %s |'
                 % (label, n, tn, p25, p50, p90, rel, 'yes' if ok else 'NO'))
    nb = sum(1 for x in ck_b if x[3])
    nc = sum(1 for x in ck_c if x[2])
    L.append('')
    L.append('B) 每袋每 seg 本表 P50/n vs 工具 `by_seg_median`： %d/%d 一致。' % (nb, len(ck_b)))
    L.append('C) 每袋 ALL 行 n/P50/P90 vs 工具 `aggregate`： %d/%d 一致。' % (nc, len(ck_c)))
    L.append('')
    L.append('## 细分表（每袋：seg 0/1/2 与 ALL；M1=supply_frac，M2=grid4x4_occupancy_frac）')
    L.append('')
    for bag in BAGS:
        L.append('### %s' % bag)
        L.append('')
        L.append('| seg | M1 n | M1 P25 | M1 P50 | M1 P50 CI95 | M1 P90 | M2 n | M2 P25 | M2 P50 | M2 P50 CI95 | M2 P90 |')
        L.append('|---|---|---|---|---|---|---|---|---|---|---|')
        for seg in [0, 1, 2, 'ALL']:
            cells = ['%s' % seg]
            for label, _ in METRICS:
                r = [x for x in rows if x[0] == bag and x[1] == seg and x[2] == label][0]
                ci = '%.10g, %.10g' % (r[7], r[8]) if r[7] != '' else '–'
                cells += ['%d' % r[3], '%.10g' % r[4], '%.10g' % r[5], ci, '%.10g' % r[6]]
            L.append('| ' + ' | '.join(cells) + ' |')
        L.append('')
    L.append('## 尾注')
    L.append('')
    L.append('- 本件全部为机械统计量（分位+n+CI），不含 PASS/FAIL 或三态判读；'
             '供 J2 判读文分场景附录引用，判读语待主会话定稿。')
    L.append('- 每格 n 约 24（12 选中帧×2 相机），为小样本分位，CI 较宽；跨 seg/跨袋对比'
             '请连同 n 与 CI 一起读。')
    L.append('- 数据链：vision_inputs/<bag>_j3 PNG → j3_image_metrics.py（帧级 JSON 已入库'
             ' derived/）→ 本脚本聚合（tools/build_pool_m1m2_byseg.py）。')
    with open(os.path.join(BASE, 'pool_m1m2_byseg.md'), 'w', encoding='utf-8',
              newline='\n') as f:
        f.write('\n'.join(L) + '\n')

    # ---- stdout 摘要 ----
    print('SELFCHK_A ' + ' '.join(
        '%s=%s' % (k, 'PASS' if ck_a[k][6] else 'FAIL(rel=%.3g)' % ck_a[k][4])
        for k in ('M1_supply_frac', 'M2_grid4x4_occupancy_frac')))
    print('SELFCHK_B %d/%d' % (nb, len(ck_b)))
    print('SELFCHK_C %d/%d' % (nc, len(ck_c)))
    print('ROWS %d' % len(rows))
    for r in rows:
        if r[2] == 'M1_supply_frac':
            print('ROW %s seg=%s n=%d P50=%.10g' % (r[0], r[1], r[3], r[5]))


if __name__ == '__main__':
    main()
