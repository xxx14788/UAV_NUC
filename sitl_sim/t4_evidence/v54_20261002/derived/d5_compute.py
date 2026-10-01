# -*- coding: utf-8 -*-
"""D5 单元3 数据面计算脚本（本机零 NUC IO）。

数据源（全部本地落盘，路径相对 D:/drone_VINS/t4_work_20261002/）：
  raw/vision_inputs/fbres_<bag>.json      字段 stereo（分箱 list[{n,p50,p90,p95,p99,median,p90_ci}]）+ stereo_pool
  raw/vision_inputs/<bag>_j3/manifest.json 字段 frames[].t_rec / frames[].topic（时间轴唯一来源）

粒度声明：立体残差逐帧原始值在本地素材不存在（fb json 仅 33-37 箱分位摘要+池化；
j3 目录仅 manifest.json 落盘、无 PNG）→ 全部统计在“分箱级 p50/p90 序列 + 池化分位”上计算，
显式降级注记见 d5_bimodal.md。

箱→时间映射假设（不可本地核验，生成脚本 j3_fb_residual.py 未随素材落盘）：
  stereo 箱 = 主帧（left topic 去重 t_rec 升序）序列的等分切分；
  箱 k 覆盖帧索引 [floor(k*N/K), floor((k+1)*N/K))，时间跨度=[首帧 t_rec, 末帧 t_rec]。
"""
import json
import numpy as np

RAW = 'raw/vision_inputs'

BAGS = [
    # (bag, fbres 前缀, 池标注)
    ('U3PG_210307',   'fbres_U3PG_210307',   '主池'),
    ('U3PO_211438',   'fbres_U3PO_211438',   '主池'),
    ('U3PR2_213717',  'fbres_U3PR2_213717',  '主池'),
    ('U3PR1_212450',  'fbres_U3PR1_212450',  '扩展池'),
    ('U3PH_210708',   'fbres_U3PH_210708',   '扩展池'),
    ('X1final_173345','fbres_X1final_173345','扩展池'),
]

WIN = (55.0, 64.0)          # d) 载体窗（任务给定）
N_BOOT = 10000              # b) bootstrap 次数
SEED = 20261002


# ---------- 纯 numpy GMM-EM ----------
def kmeanspp_init(x, k, rng):
    """标量数据 k-means++ 初值（返回 k 个初值中心）。"""
    x = np.asarray(x, float)
    centers = [float(rng.choice(x))]
    for _ in range(k - 1):
        d2 = np.min([(x - c) ** 2 for c in centers], axis=0)
        s = d2.sum()
        if s <= 0:
            centers.append(float(rng.choice(x)))
            continue
        centers.append(float(rng.choice(x, p=d2 / s)))
    return np.sort(np.array(centers))


def gmm_em(x, k, rng, max_iter=500, tol=1e-8, p_floor=1e-6):
    """1D GMM EM。返回 (loglik, pi, mu, sigma, degenerate_flag)。

    σ 地板=0.01·std(x)（尺度正则，防单点分量 σ→0 似然爆炸；方法选择已在 md 登记，
    类比 sklearn reg_covar 但随数据尺度缩放）。degenerate_flag=True 表示任一 σ 触地板。
    """
    x = np.asarray(x, float)
    n = x.size
    s_floor = max(1e-12, 0.01 * x.std())
    mu = kmeanspp_init(x, k, rng)
    sigma = np.full(k, max(x.std(), s_floor))
    pi = np.full(k, 1.0 / k)
    ll_old = -np.inf
    for _ in range(max_iter):
        # E 步
        comp = np.stack([pi[j] / np.sqrt(2 * np.pi * sigma[j] ** 2) *
                         np.exp(-0.5 * ((x - mu[j]) / sigma[j]) ** 2)
                         for j in range(k)], axis=1) + 1e-300
        resp = comp / comp.sum(axis=1, keepdims=True)
        ll = np.log(comp.sum(axis=1)).sum()
        # M 步
        nk = np.maximum(resp.sum(axis=0), p_floor)
        pi = nk / n
        mu = (resp * x[:, None]).sum(axis=0) / nk
        var = np.maximum((resp * (x[:, None] - mu) ** 2).sum(axis=0) / nk, s_floor ** 2)
        sigma = np.sqrt(var)
        if abs(ll - ll_old) < tol:
            break
        ll_old = ll
    degenerate = bool(np.any(sigma <= s_floor * (1 + 1e-9)))
    return ll, pi, mu, sigma, degenerate


def best_gmm(x, k, n_restart=5, seed=0):
    """k-means++ 初值 × n_restart 次全 EM，取最优对数似然。"""
    rng = np.random.default_rng(seed + 7919 * k)
    best = None
    for _ in range(n_restart):
        out = gmm_em(x, k, rng)
        if best is None or out[0] > best[0]:
            best = out
    return best


def bic(ll, n, n_param):
    return -2.0 * ll + n_param * np.log(n)


def gmm_bic_compare(x, seed=0):
    x = np.asarray(x, float)
    n = x.size
    ll1, pi1, mu1, s1, dg1 = best_gmm(x, 1, seed=seed)
    ll2, pi2, mu2, s2, dg2 = best_gmm(x, 2, seed=seed)
    b1, b2 = bic(ll1, n, 2), bic(ll2, n, 5)   # k=1: 2 参数; k=2: 5 参数
    # 高位分量 = mu 较大者；后验
    order = np.argsort(mu2)
    pi_s, mu_s, s_s = pi2[order], mu2[order], s2[order]
    comp = np.stack([pi_s[j] / np.sqrt(2 * np.pi * s_s[j] ** 2) *
                     np.exp(-0.5 * ((x - mu_s[j]) / s_s[j]) ** 2) for j in (0, 1)], axis=1) + 1e-300
    post_hi = comp[:, 1] / comp.sum(axis=1)
    return dict(n=n, ll1=ll1, bic1=b1, ll2=ll2, bic2=b2, dbic=b2 - b1,
                pi1=pi1, mu1=mu1, s1=s1, deg1=dg1, deg2=dg2,
                pi2=(pi_s[0], pi_s[1]), mu2=(mu_s[0], mu_s[1]), s2=(s_s[0], s_s[1]),
                post_hi=post_hi, x=x)


def posterior_half_cross(g):
    """高位分量后验=0.5 的交点（px 轴）。

    细网格（两均值区间 1e5 点）上求 post_hi-0.5 的符号变化，取两均值之间
    由 <0.5 升越 >0.5 的交点（即进入高位簇的阈值）；若无升越点则取区间内
    最接近均值中点的交点，再无则返回 NaN。方差不等时后验=0.5 集合为二次
    曲线，至多两根，网格法免闭式解代数符号错误。
    """
    pl, ph = g['pi2']
    ml, mh = g['mu2']
    sl, sh = g['s2']
    grid = np.linspace(ml, mh, 100001)
    fl = pl / sl * np.exp(-0.5 * ((grid - ml) / sl) ** 2)
    fh = ph / sh * np.exp(-0.5 * ((grid - mh) / sh) ** 2)
    pv = fh / (fl + fh + 1e-300)
    d = pv - 0.5
    sign_change = np.where(np.diff(np.sign(d)) != 0)[0]
    if len(sign_change) == 0:
        return float('nan')
    # 线性插值求交点
    crosses = []
    for i in sign_change:
        t = grid[i] - d[i] * (grid[i + 1] - grid[i]) / (d[i + 1] - d[i])
        crosses.append((t, d[i] < 0))  # (交点, 是否升越)
    asc = [t for t, is_asc in crosses if is_asc]
    if asc:
        return float(asc[0])
    return float(min(crosses, key=lambda c: abs(c[0] - 0.5 * (ml + mh)))[0])


# ---------- bimodality coefficient ----------
def skew_kurt(x):
    x = np.asarray(x, float)
    m = x.mean()
    m2 = ((x - m) ** 2).mean()
    m3 = ((x - m) ** 3).mean()
    m4 = ((x - m) ** 4).mean()
    g1 = m3 / m2 ** 1.5
    g2ex = m4 / m2 ** 2 - 3.0
    return g1, g2ex


def bimod_coef(x):
    g1, g2ex = skew_kurt(x)
    return (g1 ** 2 + 1.0) / (g2ex + 3.0)


def bc_bootstrap_ci(x, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        vals[i] = bimod_coef(rng.choice(x, size=x.size, replace=True))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------- 时间映射与窗运算 ----------
def load_bag(bag, fbres):
    d = json.load(open(f'{RAW}/{fbres}.json', encoding='utf-8'))
    man = json.load(open(f'{RAW}/{bag}_j3/manifest.json', encoding='utf-8'))
    t_left = sorted(set(f['t_rec'] for f in man['frames'] if 'left' in f['topic']))
    bins = d['stereo']
    K = len(bins)
    N = len(t_left)
    # 半开连续分割：箱 k = [t[idx_lo], t[idx_hi])，idx_hi=下一箱首帧索引；末箱右端=末主帧时刻。
    # （首版用 [首帧,末帧] 会在帧成对聚簇时留下不属于任何箱的间隙，扭曲 d) 的区间测度。）
    spans = []
    for k in range(K):
        lo_i = int(np.floor(k * N / K))
        hi_i = int(np.floor((k + 1) * N / K))
        t_end = float(t_left[hi_i]) if hi_i < N else float(t_left[N - 1])
        spans.append((float(t_left[lo_i]), max(t_end, float(t_left[lo_i]))))
    return d, t_left, spans


def overlap_len(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def union_len(intervals):
    if not intervals:
        return 0.0
    iv = sorted(intervals)
    tot, cs, ce = 0.0, iv[0][0], iv[0][1]
    for s, e in iv[1:]:
        if s > ce:
            tot += ce - cs
            cs, ce = s, e
        else:
            ce = max(ce, e)
    tot += ce - cs
    return tot


def main():
    rng_seed = 0
    report = {}
    for bag, fbres, pool_tag in BAGS:
        d, t_left, spans = load_bag(bag, fbres)
        bins = d['stereo']
        K = len(bins)
        p50 = np.array([b['p50'] for b in bins])
        p90 = np.array([b['p90'] for b in bins])
        nb = np.array([b['n'] for b in bins], float)
        pool = d['stereo_pool']
        mass_check = int(nb.sum()) == int(pool['n'])

        # a) GMM（p50 主 / p90 次）
        g50 = gmm_bic_compare(p50, seed=rng_seed)
        g90 = gmm_bic_compare(p90, seed=rng_seed + 1)
        cut = posterior_half_cross(g50)

        # b) BC + bootstrap（p50 主 / p90 次）
        bc = bimod_coef(p50)
        bc90 = bimod_coef(p90)
        g1, g2ex = skew_kurt(p50)
        lo, hi = bc_bootstrap_ci(p50)
        lo90, hi90 = bc_bootstrap_ci(p90, seed=SEED + 1)

        # d) 高位簇 = post_hi>0.5 且 p50>切点（不等方差下左侧远尾存在次级 post>0.5 区域，
        #    如 U3PG 交点 38.15px<μ低，须用切点侧别排除；约定登记于 md 方法附注）
        hi_mask = (g50['post_hi'] > 0.5) & (p50 > cut)
        hi_iv = [spans[i] for i in range(K) if hi_mask[i]]
        w0, w1 = WIN
        inter = union_len([(max(s, w0), min(e, w1)) for s, e in hi_iv if e > w0 and s < w1])
        union = union_len([(s, e) for s, e in hi_iv] + [(w0, w1)])
        cov = inter / (w1 - w0)
        jac = inter / union if union > 0 else 0.0

        # e) 60s 窗聚合
        rows_e = []
        t0, t1 = spans[0][0], max(e for _, e in spans)
        w_starts = np.arange(np.floor(t0 / 60) * 60, t1, 60.0)
        for ws in w_starts:
            we = ws + 60.0
            idx = [i for i in range(K) if spans[i][1] >= ws and spans[i][0] < we]
            if not idx:
                continue
            sub_p50, sub_p90, sub_n = p50[idx], p90[idx], nb[idx]
            wmed = float(np.median(np.repeat(sub_p50, sub_n.astype(int)))) if sub_n.sum() else float(np.median(sub_p50))
            rows_e.append(dict(win=(float(ws), float(we)), k=len(idx), n=int(sub_n.sum()),
                               p50_lo=float(sub_p50.min()), p50_hi=float(sub_p50.max()),
                               p90_lo=float(sub_p90.min()), p90_hi=float(sub_p90.max()),
                               p50_wmed=wmed))

        report[bag] = dict(pool_tag=pool_tag, fbres=fbres, K=K, N_left=len(t_left),
                           t_span=(t_left[0], t_left[-1]), spans=spans,
                           p50=p50, p90=p90, nb=nb, pool=pool, mass_check=mass_check,
                           g50=g50, g90=g90, cut=cut, bc=bc, bc_ci=(lo, hi), g1=g1, g2ex=g2ex,
                           bc90=bc90, bc90_ci=(lo90, hi90),
                           hi_mask=hi_mask, cov=cov, jac=jac, n_hi=int(hi_mask.sum()),
                           rows_e=rows_e)
    return report


def write_outputs(rep):
    import csv
    w0, w1 = WIN
    # ---------- d5_overlap.csv ----------
    with open('derived/d5_overlap.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['bag', 'pool_tag', 'src_json', 'K_bins', 'n_bins_high',
                    'win_lo_s', 'win_hi_s', 'win_len_s',
                    'n_bins_in_win', 'n_bins_high_in_win', 'high_time_in_win_s',
                    'coverage_frac', 'high_time_total_s', 'union_time_s', 'jaccard',
                    'time_mapping_note'])
        for bag, r in rep.items():
            hi_iv = [r['spans'][i] for i in range(r['K']) if r['hi_mask'][i]]
            in_win = [(s, e) for s, e in hi_iv if e > w0 and s < w1]
            n_in_win = sum(1 for s, e in r['spans'] if e > w0 and s < w1)
            inter = union_len([(max(s, w0), min(e, w1)) for s, e in in_win])
            union = union_len([(s, e) for s, e in hi_iv] + [(w0, w1)])
            w.writerow([bag, r['pool_tag'], 'raw/vision_inputs/' + r['fbres'] + '.json:stereo',
                        r['K'], r['n_hi'],
                        f'{w0:g}', f'{w1:g}', f'{w1 - w0:g}',
                        n_in_win, len(in_win), f'{inter:.4f}',
                        f'{r["cov"]:.6f}', f'{union_len(hi_iv):.4f}', f'{union:.4f}',
                        f'{r["jac"]:.6f}',
                        'inferred: equal-split of manifest left-frame t_rec sequence; '
                        'bin edges not recorded in fbres json'])

    # ---------- _d5_tables.md（md 表格片段，供 d5_bimodal.md 引用） ----------
    L = []
    A = L.append
    A('### 池化参考（fbres_*.json:stereo_pool，未参与拟合，仅对照）')
    A('')
    A('| bag | 池标注 | n | p50 px | p90 px | p95 px | p99 px | Σ箱n=池n |')
    A('|---|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        p = r['pool']
        A(f"| {bag} | {r['pool_tag']} | {p['n']} | {p['p50']:.4g} | {p['p90']:.4g} | {p['p95']:.4g} | {p['p99']:.4g} | {'一致' if r['mass_check'] else '不一致!'} |")
    A('')
    A('### a) 2-GMM vs 1-GMM（目标=各袋 stereo 箱级 p50 序列，n=箱数；EM 详见方法附注）')
    A('')
    A('ΔBIC = BIC(k=2) − BIC(k=1)；负值偏向 2 分量，正值偏向 1 分量。BIC=−2LL+p·ln(n)，p₁=2、p₂=5。')
    A('')
    A('| bag | n(箱) | LL₁ | BIC₁ | LL₂ | BIC₂ | ΔBIC | μ₁(px) | μ低(px) | μ高(px) | π高 | σ低 | σ高 | σ触地板 |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        g = r['g50']
        A(f"| {bag} | {g['n']} | {g['ll1']:.4f} | {g['bic1']:.4f} | {g['ll2']:.4f} | {g['bic2']:.4f} | **{g['dbic']:.4f}** | {g['mu1'][0]:.4g} | {g['mu2'][0]:.4g} | {g['mu2'][1]:.4g} | {g['pi2'][1]:.4g} | {g['s2'][0]:.4g} | {g['s2'][1]:.4g} | {'是' if g['deg2'] else '否'} |")
    A('')
    A('次要面：同法作用于箱级 p90 序列（立体残差尾部时序）：')
    A('')
    A('| bag | n(箱) | ΔBIC(p90) | μ低(px) | μ高(px) | π高 | σ低 | σ高 | σ触地板 |')
    A('|---|---|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        h = r['g90']
        A(f"| {bag} | {h['n']} | {h['dbic']:.4f} | {h['mu2'][0]:.4g} | {h['mu2'][1]:.4g} | {h['pi2'][1]:.4g} | {h['s2'][0]:.4g} | {h['s2'][1]:.4g} | {'是' if h['deg2'] else '否'} |")
    A('')
    A('### b) bimodality coefficient + bootstrap 95% CI（目标=箱级序列；BC=(g₁²+1)/(g₂+3)，g₁=偏度、g₂=非超额峰度，有偏矩估计；bootstrap=序贯重采样箱值 10000 次，percentile 法，seed=20261002/p90 用 20261003）')
    A('')
    A('| bag | n(箱) | BC(p50序列) | 95% CI | BC(p90序列) | 95% CI | 参考线 5/6≈0.5556 |')
    A('|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        A(f"| {bag} | {r['g50']['n']} | {r['bc']:.4f} | [{r['bc_ci'][0]:.4f}, {r['bc_ci'][1]:.4f}] | {r['bc90']:.4f} | [{r['bc90_ci'][0]:.4f}, {r['bc90_ci'][1]:.4f}] | — |")
    A('')
    A('### c) 切点（p50 序列 2-GMM 高位分量后验=0.5 升越交点，px 轴）±20% 扫描')
    A('')
    A('扫描行 = 阈值取切点的 0.8×/1.0×/1.2×；"≥阈值箱数/箱占"对 36(或 35/37)个箱计，"≥阈值残差量/量占"对该批箱的 n 之和 Σn 计（n 源=fbres json stereo[].n）。')
    A('')
    A('| bag | 切点(px) | 阈值(px) | ≥阈值箱数 | 箱占 | ≥阈值Σn | 量占 |')
    A('|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        c = r['cut']
        for f in (0.8, 1.0, 1.2):
            thr = c * f
            above = r['p50'] >= thr
            nk = int(above.sum())
            mk = int(r['nb'][above].sum())
            A(f"| {bag} | {c:.4f} | {thr:.4f} | {nk}/{r['K']} | {nk / r['K']:.4g} | {mk}/{int(r['nb'].sum())} | {mk / r['nb'].sum():.4g} |")
    A('')
    A('### d) 高位簇（后验>0.5）箱时刻 vs 55–64s 载体窗（时间=推断映射，见降级登记）')
    A('')
    A('逐袋明细在 d5_overlap.csv；摘要（覆盖率=窗内高位簇时间/9s；Jaccard=|高位簇∩窗|/|高位簇∪窗|，区间测度）：')
    A('')
    A('| bag | 池标注 | 高位簇箱数 | 窗内箱数 | 窗内高位簇箱数 | 高位簇时间_窗内(s) | 覆盖率 | Jaccard |')
    A('|---|---|---|---|---|---|---|---|')
    for bag, r in rep.items():
        hi_iv = [r['spans'][i] for i in range(r['K']) if r['hi_mask'][i]]
        in_win = [(s, e) for s, e in hi_iv if e > WIN[0] and s < WIN[1]]
        n_in_win = sum(1 for s, e in r['spans'] if e > WIN[0] and s < WIN[1])
        inter = union_len([(max(s, WIN[0]), min(e, WIN[1])) for s, e in in_win])
        A(f"| {bag} | {r['pool_tag']} | {r['n_hi']}/{r['K']} | {n_in_win} | {len(in_win)} | {inter:.3f} | {r['cov']:.4f} | {r['jac']:.4f} |")
    A('')
    A('### e) 残差 60s 窗时序（窗边界对齐 60s；窗内统计为箱级摘要的汇总，非原始残差分位）')
    A('')
    for bag, r in rep.items():
        A(f"**{bag}**（{r['pool_tag']}，帧时轴 {r['t_span'][0]:g}–{r['t_span'][1]:g}s，K={r['K']} 箱；p50* = 窗内各箱 p50 按 n 加权中值——摘要的摘要，非池化分位）：")
        A('')
        A('| 窗[s] | 箱数 | Σn | p50 min–max(px) | p50* | p90 min–max(px) |')
        A('|---|---|---|---|---|---|')
        for e_ in r['rows_e']:
            A(f"| [{e_['win'][0]:g},{e_['win'][1]:g}) | {e_['k']} | {e_['n']} | {e_['p50_lo']:.4g}–{e_['p50_hi']:.4g} | {e_['p50_wmed']:.4g} | {e_['p90_lo']:.4g}–{e_['p90_hi']:.4g} |")
        A('')
    with open('derived/_d5_tables.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    return


if __name__ == '__main__':
    rep = main()
    write_outputs(rep)
    print('wrote derived/d5_overlap.csv + derived/_d5_tables.md')
    for bag, r in rep.items():
        g = r['g50']
        print(f"== {bag} [{r['pool_tag']}] K={r['K']} N_left={r['N_left']} t=[{r['t_span'][0]},{r['t_span'][1]}] mass_ok={r['mass_check']}")
        print(f"   a p50: LL1={g['ll1']:.4f} BIC1={g['bic1']:.4f} | LL2={g['ll2']:.4f} BIC2={g['bic2']:.4f} dBIC={g['dbic']:.4f} deg1={g['deg1']} deg2={g['deg2']}")
        print(f"     mu1c=({g['mu1'][0]:.4f}) ; 2comp mu=({g['mu2'][0]:.4f},{g['mu2'][1]:.4f}) pi=({g['pi2'][0]:.4f},{g['pi2'][1]:.4f}) sd=({g['s2'][0]:.4f},{g['s2'][1]:.4f}) cut={r['cut']:.4f}")
        h = r['g90']
        print(f"   a p90: dBIC={h['dbic']:.4f} deg2={h['deg2']} mu2=({h['mu2'][0]:.4f},{h['mu2'][1]:.4f}) sd=({h['s2'][0]:.4f},{h['s2'][1]:.4f}) cut90={posterior_half_cross(h):.4f}")
        print(f"   b BC50={r['bc']:.4f} CI=({r['bc_ci'][0]:.4f},{r['bc_ci'][1]:.4f}) g1={r['g1']:.4f} g2ex={r['g2ex']:.4f}")
        print(f"     BC90={r['bc90']:.4f} CI=({r['bc90_ci'][0]:.4f},{r['bc90_ci'][1]:.4f})")
        print(f"   d n_hi={r['n_hi']}/{r['K']} cov={r['cov']:.4f} jac={r['jac']:.4f}")
        print(f"   e rows={len(r['rows_e'])}")
