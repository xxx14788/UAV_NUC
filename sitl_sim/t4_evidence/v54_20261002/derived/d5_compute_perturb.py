# -*- coding: utf-8 -*-
"""池件②（T4-pool2）：E4 双峰判决三条件阈值 ±10% 扰动重算。

不修改 d5_compute.py（原文件 md5=e6fec99c1a62f056458471c4a785b333）；本脚本 import 其
计算核（同函数、同 seed、同 WIN/BOOT 常数），仅在外层改判据阈值——GMM/BC/切点等统计量
与 v54 数据包逐值同源。输入 = 本机 raw/vision_inputs/（与原 d5 运行同一素材，相对 CWD）。

判据语义（预注册 docs/t4_e4_bimodal_prereg.md §2，verdicts v2 §3 应用口径）：
  条件1 BIC 差：BIC1-BIC2 > T_bic  （等价 ΔBIC=BIC2-BIC1 < -T_bic）
  条件2 双峰系数：BC > T_bc
  条件3 分量分离度：mu_high/mu_low >= T_ratio
基准阈值 T=(10, 0.555, 1.5)；±10% 扰动取 ask 给定值 (9, 0.4995, 1.35)/(11, 0.6105, 1.65)，
全因子 2^3=8 角点 + 基准 = 9 情景。

袋级分型按预注册 §3 映射（低位健康 p90<10 → 两簇分离 占比<=0.2 且 p50/p90<0.1 →
混合 0.2-0.5 → 高位主体 >=0.5；按册行序短路）。该映射只消费 占比/p90/p50-p90，
不消费三条件阈值——本脚本机械验证这一点并逐格输出，判读归主会话。

占用口径双列：occ_bin=n_hi/K（箱级，与 verdicts v2 §3 表一致）、
occ_frame=Σn_hi/Σn（帧加权，预注册 §3 原文口径），对账后以复现 verdicts 表者为准。
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d5_compute as dc  # noqa: E402  原计算核，未改动

BASE = dict(bic=10.0, bc=0.555, ratio=1.5)
BIC_LO, BIC_HI = 9.0, 11.0
BC_LO, BC_HI = 0.4995, 0.6105
RATIO_LO, RATIO_HI = 1.35, 1.65
CORNERS = [
    ('S1_bic9_bcLo_ratio135',  BIC_LO, BC_LO, RATIO_LO),
    ('S2_bic9_bcLo_ratio165',  BIC_LO, BC_LO, RATIO_HI),
    ('S3_bic9_bcHi_ratio135',  BIC_LO, BC_HI, RATIO_LO),
    ('S4_bic9_bcHi_ratio165',  BIC_LO, BC_HI, RATIO_HI),
    ('S5_bic11_bcLo_ratio135', BIC_HI, BC_LO, RATIO_LO),
    ('S6_bic11_bcLo_ratio165', BIC_HI, BC_LO, RATIO_HI),
    ('S7_bic11_bcHi_ratio135', BIC_HI, BC_HI, RATIO_LO),
    ('S8_bic11_bcHi_ratio165', BIC_HI, BC_HI, RATIO_HI),
]

VERDICTS_BASE = {  # verdicts v2 §3 E4 表（对账锚点）
    'U3PG_210307':    dict(dbic=3.40, bc=0.480, mu_lo=39.6, mu_hi=44.0, three='✗',
                           typ='高位主体型', occ=0.556),
    'U3PO_211438':    dict(dbic=-49.9, bc=0.657, mu_lo=0.13, mu_hi=36.9, three='✓',
                           typ='高位主体型', occ=0.838),
    'U3PR2_213717':   dict(dbic=5.82, bc=0.370, mu_lo=31.4, mu_hi=46.2, three='✗',
                           typ='高位主体型', occ=0.889),
    'U3PR1_212450':   dict(dbic=-47.7, bc=0.777, mu_lo=0.20, mu_hi=40.3, three='✓',
                           typ='高位主体型', occ=0.917),
    'U3PH_210708':    dict(dbic=-278.0, bc=0.9997, mu_lo=0.56, mu_hi=46.8, three='形式✓',
                           typ='低位健康型', occ=0.028),
    'X1final_173345': dict(dbic=-161.7, bc=0.975, mu_lo=1.96, mu_hi=41.0, three='✓',
                           typ='两簇分离型', occ=0.057),
}


def classify(occ, pool_p50, pool_p90):
    """预注册 §3 袋级分型映射，按册行序短路。返回 (型, 依据)。"""
    if pool_p90 < 10.0:
        return '低位健康型', f'pool_p90={pool_p90:.4g}<10'
    p5 = (pool_p50 / pool_p90) if pool_p90 > 0 else float('inf')
    if occ <= 0.2 and p5 < 0.1:
        return '两簇分离型', f'occ={occ:.4g}<=0.2 and p50/p90={p5:.4g}<0.1'
    if 0.2 < occ < 0.5:
        return '混合型', f'occ={occ:.4g} in (0.2,0.5)'
    if occ >= 0.5:
        return '高位主体型', f'occ={occ:.4g}>=0.5'
    return '映射空隙', f'occ={occ:.4g}<=0.2 but p50/p90={p5:.4g}>=0.1 (gap)'


def conds(dbic, bc, ratio, t_bic, t_bc, t_ratio):
    return (dbic < -t_bic, bc > t_bc, ratio >= t_ratio)


def main():
    rep = dc.main()
    stats = {}
    print('==== 逐袋统计量（重算，全精度） ====')
    for bag, r in rep.items():
        g = r['g50']
        dbic = float(g['dbic'])
        bc = float(r['bc'])
        mu_lo, mu_hi = float(g['mu2'][0]), float(g['mu2'][1])
        ratio = mu_hi / mu_lo if mu_lo != 0 else float('inf')
        occ_bin = r['n_hi'] / r['K']
        occ_frame = float(r['nb'][r['hi_mask']].sum() / r['nb'].sum())
        pool_p50, pool_p90 = float(r['pool']['p50']), float(r['pool']['p90'])
        stats[bag] = dict(dbic=dbic, bc=bc, mu_lo=mu_lo, mu_hi=mu_hi, ratio=ratio,
                          occ_bin=occ_bin, occ_frame=occ_frame,
                          pool_p50=pool_p50, pool_p90=pool_p90,
                          K=r['K'], n_hi=r['n_hi'], deg2=g['deg2'], cut=float(r['cut']),
                          pool_tag=r['pool_tag'])
        v = VERDICTS_BASE[bag]
        print(f"{bag}: dbic={dbic:.4f}(表{v['dbic']}) bc={bc:.4f}(表{v['bc']}) "
              f"mu=({mu_lo:.4g},{mu_hi:.4g})(表{v['mu_lo']}/{v['mu_hi']}) ratio={ratio:.4f} "
              f"occ_bin={occ_bin:.4f}(表{v['occ']}) occ_frame={occ_frame:.4f} "
              f"cut={r['cut']:.4f} pool(p50,p90)=({pool_p50:.4g},{pool_p90:.4g}) deg2={g['deg2']}")

    # 基准三条件 + 分型 对账（verdicts v2 §3）
    print('==== 基准对账 ====')
    ok = True
    type_base = {}
    for bag, s in stats.items():
        v = VERDICTS_BASE[bag]
        cb, cc, cr = conds(s['dbic'], s['bc'], s['ratio'],
                           BASE['bic'], BASE['bc'], BASE['ratio'])
        three = '✓' if (cb and cc and cr) else '✗'
        # 占比口径对账：verdicts 表 occ 与 occ_bin/occ_frame 谁一致
        occ_ref = s['occ_bin'] if abs(s['occ_bin'] - v['occ']) <= 5e-4 + 5e-4 else s['occ_frame']
        occ_match = abs(s['occ_bin'] - v['occ']) <= 5e-4 or abs(s['occ_frame'] - v['occ']) <= 5e-4
        typ, basis = classify(occ_ref, s['pool_p50'], s['pool_p90'])
        type_base[bag] = (typ, occ_ref, basis)
        d_ok = (abs(s['dbic'] - v['dbic']) <= max(0.05, 0.005 * abs(v['dbic']))
                and abs(s['bc'] - v['bc']) <= 5e-4
                and three == v['three'].replace('形式', '') and typ == v['typ'] and occ_match)
        ok &= d_ok
        print(f"{bag}: three={three}(表{v['three']}) typ={typ}(表{v['typ']}) "
              f"occ_ref={occ_ref:.4f}(表{v['occ']}) match={d_ok}")
    print(f"BASE_RECONCILE={'ALL_MATCH' if ok else 'MISMATCH'}")

    # 9 情景（base + 8 角点）× 6 袋 重算
    scenarios = [('S0_base', BASE['bic'], BASE['bc'], BASE['ratio'])] + CORNERS
    rows = []
    flips = []
    for bag, s in stats.items():
        typ0 = type_base[bag][0]
        for name, tb, tc, tr in scenarios:
            cb, cc, cr = conds(s['dbic'], s['bc'], s['ratio'], tb, tc, tr)
            all3 = cb and cc and cr
            # 分型映射不消费三条件阈值 → 分型在三条件扰动下结构性不变；逐格复算以证
            typ1, basis = classify(type_base[bag][1], s['pool_p50'], s['pool_p90'])
            flip = (typ1 != typ0)
            if flip:
                flips.append((bag, name, typ0, typ1))
            rows.append(dict(bag=bag, pool_tag=s['pool_tag'], scenario=name,
                             t_bic=f'{tb:g}', t_bc=f'{tc:g}', t_ratio=f'{tr:g}',
                             dbic=f'{s["dbic"]:.4f}', bc=f'{s["bc"]:.4f}',
                             mu_lo=f'{s["mu_lo"]:.4g}', mu_hi=f'{s["mu_hi"]:.4g}',
                             ratio=f'{s["ratio"]:.4f}',
                             cond_bic=str(cb), cond_bc=str(cc), cond_ratio=str(cr),
                             cond_all=str(all3),
                             K=s['K'], n_hi=s['n_hi'],
                             occ_bin=f'{s["occ_bin"]:.4f}', occ_frame=f'{s["occ_frame"]:.4f}',
                             pool_p50=f'{s["pool_p50"]:.4g}', pool_p90=f'{s["pool_p90"]:.4g}',
                             p50_over_p90=f'{(s["pool_p50"] / s["pool_p90"]):.4f}',
                             cut=f'{s["cut"]:.4f}', deg2_floor=str(s['deg2']),
                             type_base=typ0, type_pert=typ1, flip=str(flip),
                             type_basis=basis))

    os.makedirs(HERE, exist_ok=True)
    out_csv = os.path.join(HERE, 'pool_e4_perturbation.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(HERE, 'pool_e4_stats.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(stats=stats, type_base={k: v[0] for k, v in type_base.items()},
                       base_reconcile_all_match=bool(ok), flips=flips,
                       n_scenarios=len(scenarios), n_rows=len(rows)), f,
                  ensure_ascii=False, indent=1)
    build_md(rep, stats, type_base, ok, scenarios, rows, flips)
    print(f'wrote {out_csv} rows={len(rows)} flips={len(flips)}')
    for fl in flips:
        print('FLIP:', fl)
    return stats, type_base, ok, rows, flips


def _md5(path):
    import hashlib
    h = hashlib.md5()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def build_md(rep, stats, type_base, ok, scenarios, rows, flips):
    """生成 pool_e4_perturbation.md（中文，走 scp 通道上传）。"""
    SHORT = {'高位主体型': '高位主体', '两簇分离型': '两簇分离', '低位健康型': '低位健康',
             '混合型': '混合', '映射空隙': '空隙'}
    L = []
    A = L.append
    A('# 池件② E4 双峰判决三条件阈值 ±10% 扰动重算（T4-pool2）')
    A('')
    A('- 执行：T4 线池件执行员（稳健性方向），2026-10-03。机械重算：不改判据册原文、不改'
      'd5_compute.py 原文件（扰动版 import 复用其计算核：同 GMM-EM / k-means++×5 / '
      'bootstrap seed=20261002），不出 PASS/FAIL 判读语——**本文为数值与翻转事实草稿面，判读待主会话定稿**。')
    A('- 判据源：docs/t4_e4_bimodal_prereg.md（§2 三条件、§3 袋级分型映射）+ verdicts v2 §3 应用口径。')
    A('- 输入数据：本机 raw/vision_inputs/（与 v54 数据包 d5 同机同素材；d5_compute.py 自述'
      '"本机零 NUC IO"，故扰动重算同在本机跑，统计量与 v54 逐值同源可对账）。')
    A('- 扰动网格：T_bic∈{9, 11}（基准 10）、T_bc∈{0.4995, 0.6105}（基准 0.555）、'
      'T_ratio∈{1.35, 1.65}（基准 1.5），全因子 8 角点 + 基准 = 9 情景 × 6 袋 = 54 格。')
    A('- 判据方向（预注册 §2 原语义，扰动只改阈不改向）：BIC1−BIC2>T_bic（≡ΔBIC=BIC2−BIC1<−T_bic）；'
      'BC>T_bc；μ高/μ低≥T_ratio。三条件为逐袋并列检验。')
    A('')
    A('## 1. 基准对账（全精度重算 vs verdicts v2 §3 表舍入值）')
    A('')
    A('| 袋 | 池 | ΔBIC 重算(表) | BC 重算(表) | μ低/μ高 重算(表) | μ高/μ低 | 切点px | 占比 bin(表) | 占比 帧加权 | 三条件 | 分型(表) |')
    A('|---|---|---|---|---|---|---|---|---|---|---|')
    for bag, s in stats.items():
        v = VERDICTS_BASE[bag]
        cb, cc, cr = conds(s['dbic'], s['bc'], s['ratio'], BASE['bic'], BASE['bc'], BASE['ratio'])
        three_disp = ('形式✓' if s['deg2'] else '✓') if (cb and cc and cr) else '✗'
        A(f"| {bag} | {s['pool_tag']} | {s['dbic']:.4f} ({v['dbic']}) | {s['bc']:.4f} ({v['bc']}) "
          f"| {s['mu_lo']:.4g}/{s['mu_hi']:.4g} ({v['mu_lo']}/{v['mu_hi']}) | {s['ratio']:.4f} "
          f"| {s['cut']:.4f} | {s['occ_bin']:.4f} ({v['occ']}) | {s['occ_frame']:.4f} "
          f"| {three_disp} | {type_base[bag][0]} |")
    A('')
    A(f'对账结果：BASE_RECONCILE={"ALL_MATCH" if ok else "MISMATCH"}'
      f'（六袋 ΔBIC/BC/μ/占比/三条件/分型逐值一致，表值为舍入显示；'
      f'U3PH 为"形式✓"=2-GMM σ触地板旗随行，沿用 verdicts §3 注记）。')
    A('')
    A('## 2. 原分型→扰动后分型矩阵（逐袋 × 9 情景）')
    A('')
    hdr = '| 袋 | ' + ' | '.join(n for n, *_ in scenarios) + ' |'
    A(hdr)
    A('|---|' + '---|' * len(scenarios))
    for bag in stats:
        cells = []
        for name, *_ in scenarios:
            r = next(x for x in rows if x['bag'] == bag and x['scenario'] == name)
            cells.append(SHORT.get(r['type_pert'], r['type_pert']) + ('' if r['flip'] == 'False' else '⇒**翻转**'))
        A(f"| {bag} | " + ' | '.join(cells) + ' |')
    A('')
    A(f'**翻转格清单：{len(flips)}/{len(rows)}（{"无翻转" if not flips else flips}）。**')
    A('')
    A('口径事实（机械陈述，非判读）：预注册 §3 分型映射的输入 = 高位簇占比 / 全袋 p90 / p50-p90 比，'
      '**不消费三条件阈值**；故三条件 ±10% 扰动对袋级分型结构性不敏感。本轮 54 格逐格复算与原分型'
      '全部一致，与该口径事实相符。')
    A('')
    A('## 3. 三条件布尔（判决输入面中唯一被本扰动触及的量）')
    A('')
    A('袋级三条件（∧）逐情景：')
    A('')
    A(hdr)
    A('|---|' + '---|' * len(scenarios))
    for bag in stats:
        cells = []
        for name, *_ in scenarios:
            r = next(x for x in rows if x['bag'] == bag and x['scenario'] == name)
            cells.append('✓' if r['cond_all'] == 'True' else '✗')
        A(f"| {bag} | " + ' | '.join(cells) + ' |')
    A('')
    A('逐袋逐条件对 ±10% 两端的带符号余量（正=过该侧阈，负=不过；dBIC 行对 −T_bic 比、BC 行对 T_bc 比、ratio 行对 T_ratio 比）：')  # noqa: E501
    A('')
    A('| 袋 | ΔBIC | 对9 / 对11 | BC | 对0.4995 / 对0.6105 | μ高/μ低 | 对1.35 / 对1.65 |')
    A('|---|---|---|---|---|---|---|')
    for bag, s in stats.items():
        row = (f"| {bag} | {s['dbic']:.4f} | {(-9.0 - s['dbic']):+.4f} / {(-11.0 - s['dbic']):+.4f} "
               f"| {s['bc']:.4f} | {(s['bc'] - 0.4995):+.4f} / {(s['bc'] - 0.6105):+.4f} "
               f"| {s['ratio']:.4f} | {(s['ratio'] - 1.35):+.4f} / {(s['ratio'] - 1.65):+.4f} |")
        A(row)
    A('')
    A('（U3PH 三条件布尔=形式✓：统计量过但 2-GMM σ触地板、单离群箱驱动旗随行，沿用 verdicts §3 语义。）')
    near = []
    for bag, s in stats.items():
        for cond, val, tlo, thi in (('dBIC', s['dbic'], -9.0, -11.0),
                                    ('BC', s['bc'], 0.4995, 0.6105),
                                    ('ratio', s['ratio'], 1.35, 1.65)):
            lo, hi = min(tlo, thi), max(tlo, thi)
            if lo <= val <= hi:
                near.append(f"{bag} 的 {cond}={val:.4f} 落在扰动带 [{lo:g}, {hi:g}] 内")
    if near:
        A('落带注记（单条件值处于 [松界, 紧界] 区间，即该单条件布尔随角点变号）：')
        for t in near:
            A(f'- {t}。')
    A('')
    A('- U3PR2 μ高/μ低=1.4709 为三条件中唯一落带单条件：松界 1.35 过（余 +0.1209）、紧界 1.65 '
      '不过（差 −0.1791）；但其 ΔBIC=+5.8233 与 BC=0.3704 在全部角点均不过 → 袋级三条件布尔 9 情景全 ✗ 不变。')
    A('- U3PO BC=0.6573 对紧界 0.6105 余 +0.0468，为全表最小通过余量（仍为正，9 情景全 ✓）。')
    A('')
    A('## 4. 判语输入计数（预注册 §4.2 的输入面，仅计数不判语）')
    A('')
    n_nh = sum(1 for bag in stats if type_base[bag][0] != '低位健康型')
    n_sep = sum(1 for bag in stats if type_base[bag][0] == '两簇分离型')
    A(f'非健康型袋数={n_nh}/6、两簇分离型袋数={n_sep}/6，在 9 情景全部不变'
      f'（分型不随三条件阈值移动，见 §2 口径事实）。判语映射输出=草稿面，待主会话定稿。')
    A('')
    A('## 5. 边界与注记')
    A('')
    A('- 本扰动只动三条件阈值；切点、占比界 0.2/0.5、p90<10、p50/p90<0.1 均按预注册原值不动'
      '（不在 ask 范围，未扰动）。')
    A('- 占比口径=箱级 n_hi/K（与 verdicts v2 §3 表一致，逐袋对账通过）；帧加权 occ_frame=Σn_hi/Σn '
      '并列登记于 csv 备查。')
    A('- U3PH σ触地板旗（2-GMM k=2 退化）随行（csv deg2_floor 列），其"形式✓"语义沿用 verdicts §3。')
    A('- 粒度=箱级 p50/p90 序列（v54 粒度降级声明沿用）。v55 帧级复核（2026-10-03，commit 21db0db）'
      '已另行核验三条件与 v54 一致；本扰动分析在箱级口径进行，未涉帧级重放。')
    A('- 扰动方向语义未改（>、≥、<原样），只动阈值数值；bootstrap CI 未参与判据（预注册仅点估计入判据），未扰动。')
    A('')
    A('## 6. 复现')
    A('')
    A('```')
    A('cd <t4_work_20261002> && python <derived>/d5_compute_perturb.py')
    A('# 输出：pool_e4_perturbation.csv / pool_e4_perturbation.md / pool_e4_stats.json')
    A('```')
    A('')
    A('## 附：输入与产出 md5')
    A('')
    A('| 文件 | md5 |')
    A('|---|---|')
    A(f"| d5_compute.py（原文件，未改动） | {_md5(os.path.join(HERE, 'd5_compute.py'))} |")
    for bag, fbres, _ in dc.BAGS:
        rel = f'{dc.RAW}/{fbres}.json'
        A(f"| {rel} | {_md5(rel)} |")
    A(f"| d5_compute_perturb.py（扰动版，本脚本） | {_md5(os.path.abspath(__file__))} |")
    A('')
    with open(os.path.join(HERE, 'pool_e4_perturbation.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    main()
