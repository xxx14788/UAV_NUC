# -*- coding: utf-8 -*-
"""D6 md 生成器：读 derived/d6_*.csv，产出 d6_time_profiles.md"""
import pandas as pd, numpy as np, os, math

DER='D:/drone_VINS/t4_work_20261002/derived'
VI='D:/drone_VINS/t4_work_20261002/raw/vision_inputs'
long_=pd.read_csv(os.path.join(DER,'d6_window_metrics_long.csv'))
worst=pd.read_csv(os.path.join(DER,'d6_worst_windows.csv'))
flags=pd.read_csv(os.path.join(DER,'d6_collapse_flags.csv'))
anch=pd.read_csv(os.path.join(DER,'d6_bag_anchors.csv'))
MAIN=['X1img_015950','WC2OBS1_030927','WC2OBS1_032005','U3PG_210307','U3PO_211438','U3PR2_213717']
EXT=['X1img2_020706','U3PH_210708','U3PR1_212450','X1final_173345']
SC=dict(zip(worst.bag,worst.scenario))

def f(x,nd=3):
    if x is None or (isinstance(x,float) and math.isnan(x)): return '—'
    return f'{x:.{nd}f}'

L=[]  # md lines
A=L.append
A('# D6 时间局部化剖面（30s 分箱时序总表 / 共塌陷对齐 / 最差窗注册）')
A('')
A('- 计算员=D6（时序剖面员），2026-10-02；零 NUC IO，全部读本机 `D:/drone_VINS/t4_work_20261002/raw/`。')
A('- 主池=6 袋（matrix_5faces.md L9-16），扩展池=4 袋（matrix L20-25，行内一律带「扩展池」标注）。')
A('- 时间基=bag 相对秒：manifest `t_rec`（帧）/ odom_pc_csv `t`（odometry/点云 header.stamp），两源同基（extract_summary.json first_odom_t=13.072 ↔ U3PG manifest t_range 起 13.08）。')
A('- 窗=30s 定宽左闭右开 `[w0,w1)`；列=时刻窗（宽袋拆 A/B/C 三张分块表，列仍=时刻窗）。')
A('- 最差窗在列头以 ▲ 标注（composite 口径见 §3）。')
A('')
A('## 0. 指标→字段映射与判据锚（溯源）')
A('')
A('| 剖面指标 | 源文件 | 字段/口径 |')
A('|---|---|---|')
A('| M1 供给率 | `vision_inputs/metrics_*.json` per_frame | `corners_gFT/150`（max_cnt=150 锚，t4_j2_threshold_prep.md L11；与 per_frame.supply_frac 逐位一致，U3 系 6 袋 max\\|dev\\|=0.0 实测；X1img/X1img2 per_frame 无 supply_frac 列，同式可算） |')
A('| M2 占用格 | 同上 per_frame | `grid4x4_occupancy_frac`（X1img/X1img2 旧版无此列→该两袋 M2 缺） |')
A('| M3 平坦梯度 | 同上 per_frame | `grad_med`；M3zero=窗内 `grad_med==0` 帧占比 |')
A('| M4 方向能量 | 同上 per_frame | `grad_dir_maxbin_frac`（M4=模糊代理「Laplacian+方向能量」的方向能量半边，prep L27；metrics json 无 Laplacian 字段，降级登记见 §5） |')
A('| FB 残差 | `vision_inputs/fbres_*.json`（X1img=`fb_X1img_sim.json`） | `temporal[i].p50/p90`（时序侧主）+ `stereo[i].p50`（立体侧辅）；条目无时间戳→索引映射（降级登记 §5） |')
A('| 云率/云空窗 | `vision_inputs/odom_pc_csv/jr3_replay_*_pc.csv` | `n_points`；云率=窗内 Σ点数/覆盖秒（覆盖=窗∩[pc.t 范围]，`cov_s` 行给分母）；非空率=窗内 n_points>0 消息占比 |')
A('| \\|v\\| | `odom_pc_csv/jr3_replay_*_odom.csv` | px,py,pz 前向差分/Δt（twist 未提取，降级 §5）；同 stamp 重样本每 stamp 留末位；\\|v\\|>15 m/s 判非物理跳变样本剔除并计数（n_vjump 行） |')
A('| z | 同上 | `pz` 中位 + p10/p90（世界系） |')
A('| γ | `metrics_*.json` metrics | `gamma_pair.by_seg_median`（官方逐 seg 中位+n），seg→窗按 manifest 各 seg t_rec 区间最大重叠映射（γ 无逐帧数组，窗粒度=seg，降级 §5） |')
A('| 塌陷判据（绝对门） | t4_j2_threshold_prep.md L36-38 | M1<0.2 / M2<0.5(8/16) / M3zero>0.3；残差尖峰锚=X1img temporal_pool p90=30.663px（fb_X1img_sim.json，判读账本 L74「时序 pool P90=30.7px」） |')
A('| 塌陷判据（袋内相对门） | 本剖面对齐表 | 窗中位 ≤ 该袋帧级 P10（M1/M2/M3）或 ≥ 该袋 FB 条目级 P90（残差） |')
A('')

A('## 1. 主池逐袋 30s 分箱全指标时序总表')
A('')
A('> 每袋 3 张分块表：A=供给/纹理图像侧（含 γ），B=FB 残差/特征云，C=运动/几何。列=时刻窗；n 行在表内。')
A('')

def wide(bag):
    d=long_[long_.bag==bag].sort_values('w0').reset_index(drop=True)
    w1v=worst[(worst.bag==bag)&(worst['rank']=='worst1')]
    bad = int(w1v.iloc[0]['w0']) if len(w1v) else None
    heads=[f"{int(r.w0)}-{int(r.w1)}s"+(' ▲' if bad is not None and r.w0==bad else '') for _,r in d.iterrows()]
    return d,heads

for bag in MAIN:
    d,heads=wide(bag)
    A(f'### {bag} — {SC[bag]}')
    A('')
    nwin=len(d); t0=d.w0.min(); t1=d.w1.max()
    A(f'窗数={nwin}（{t0:.0f}s 起）；有帧窗覆盖 {int(d[d.n_f>0].w0.min()) if (d.n_f>0).any() else int(t0)}-{int(d[d.n_f>0].w1.max()) if (d.n_f>0).any() else int(t1)}s；')
    A('')
    A('**表A 供给/纹理（图像侧，左目帧）**')
    A('')
    A('| 行 | ' + ' | '.join(heads) + ' |')
    A('|---'*(len(heads)+1)+'|')
    rowsA=[('n_f(帧)','n_f',0),('M1_med','M1_med',3),('M2_med','M2_med',4),('M3_med','M3_med',2),
           ('M3zero%','M3zero',3),('M4_med','M4_med',3)]
    for lab,c,nd in rowsA:
        A(f'| {lab} | ' + ' | '.join(f(v,nd) for v in d[c]) + ' |')
    gam=[f"{f(r.gam,2)}(n={int(r.gam_n)},s{int(r.gam_seg)})" for _,r in d.iterrows()]
    A('| γ(seg映射) | ' + ' | '.join(gam) + ' |')
    A('')
    mname='metrics_X1img_sim.json' if bag=='X1img_015950' else ('metrics_%s_w3.json'%bag if bag.startswith('WC2') else 'metrics_%s.json'%bag)
    A('源：`vision_inputs/%s` per_frame 逐帧值按 manifest t_rec 入窗取中位；γ=metrics.gamma_pair.by_seg_median。'%mname)
    A('')
    A('**表B FB 残差/特征云**')
    A('')
    A('| 行 | ' + ' | '.join(heads) + ' |')
    A('|---'*(len(heads)+1)+'|')
    rowsB=[('FB_n(条目)','FB_n',0),('FBt_p50(px)','FB_p50',3),('FBt_p90max(px)','FB_p90mx',2),('FBs_p50(px)','FBs_p50',2),
           ('pc_n(消息)','pc_n',0),('pc非空%','pc_nonempty',3),('云率 pts/s(覆盖归一)','pts_s',1),('cov_s','cov_s',1)]
    for lab,c,nd in rowsB:
        A(f'| {lab} | ' + ' | '.join(f(v,nd) for v in d[c]) + ' |')
    A('')
    fbname='fb_X1img_sim.json' if bag=='X1img_015950' else 'fbres_%s.json'%bag
    A('源：`vision_inputs/%s` temporal/stereo 条目按 stride-2 索引映射入窗（§5 降级①）；`odom_pc_csv/jr3_replay_%s_pc.csv`。'%(fbname,bag))
    A('')
    A('**表C 运动/几何（回放 odometry）**')
    A('')
    A('| 行 | ' + ' | '.join(heads) + ' |')
    A('|---'*(len(heads)+1)+'|')
    rowsC=[('n_o','n_o',0),('n_vjump','n_vjump',0),(r'\|v\|_med','v_med',3),(r'\|v\|_p90','v_p90',3),
           ('z_med','z_med',3),('z_p10','z_p10',3),('z_p90','z_p90',3)]
    for lab,c,nd in rowsC:
        A(f'| {lab} | ' + ' | '.join(f(v,nd) for v in d[c]) + ' |')
    A('')
    A('源：`odom_pc_csv/jr3_replay_%s_odom.csv` px,py,pz；|v| 门与重 stamp 处理见 §0/§5。'%bag)
    A('')
    vjfrac = float(anch[anch.bag==bag].iloc[0]['bagVJ'] ) if 'bagVJ' in anch.columns else None
    A('')

A('## 2. 共塌陷检测（供给塌陷 × 残差尖峰 / 纹理塌陷 / 占用格退化 同时窗对齐）')
A('')
A('### 2.1 判据命中总览（主池 76 窗）')
A('')
fam_abs=['abs_供给M1<0.2','abs_占用M2<0.5','abs_纹理零梯>0.3','abs_残差p90>30.7px']
fam_rel=['rel_供给≤袋P10','rel_占用≤袋P10','rel_纹理≤袋P10','rel_残差≥袋P90']
fm=flags[flags.pool=='主池']
A('| 判据族 | 门 | 主池命中窗数 | 命中袋×窗 |')
A('|---|---|---|---|')
for c in fam_abs:
    sub=fm[fm[c]==1]
    bags='; '.join(f'{b}×{len(s)}' for b,s in sub.groupby('bag')) if len(sub) else '—'
    A(f'| {c[4:]}（绝对门） | {c[4:]} | {len(sub)} | {bags} |')
for c in fam_rel:
    sub=fm[fm[c]==1]
    bags='; '.join(f'{b}×{len(s)}' for b,s in sub.groupby('bag')) if len(sub) else '—'
    A(f'| {c[4:]}（袋内相对门） | {c[4:]} | {len(sub)} | {bags} |')
A('')
A('### 2.2 绝对门同时窗命中（≥2 族同窗）')
A('')
ab=fm[fm.n_abs>=2]
if len(ab)==0:
    A('主池无绝对门 ≥2 族同窗命中。绝对门逐族命中仅：纹理零梯（X1img_015950 全部 11 窗，grad_med≡0）与残差 p90>30.663px（40 窗，见 d6_collapse_flags.csv）；供给 M1<0.2 与占用 M2<0.5 零命中。')
else:
    A('| 袋 | 窗 | 命中族 |')
    A('|---|---|---|')
    for _,r in ab.iterrows():
        hits=[c[4:] for c in fam_abs if r[c]==1]
        A(f"| {r.bag} | {int(r.w0)}-{int(r.w1)}s | {', '.join(hits)} |")
A('')
A('### 2.3 袋内相对门对齐表（≥2 族同窗，全池）')
A('')
rl=flags[flags.n_rel>=2].copy()
A(f'命中窗总数={len(rl)}（主池 {len(rl[rl.pool=="主池"])}，扩展池 {len(rl[rl.pool=="扩展池"])}）。数值=窗内中位（残差=条目 p90 最大值）；括号=判据锚值（该袋帧级 P10 / FB 条目级 P90）。')
A('')
A('| 袋(池) | 窗 | 供给 M1_med(锚=袋帧P10) | 占用 M2_med(锚=袋帧P10) | 纹理 M3_med(锚=袋帧P10) | 残差 FBp90max(锚=袋FB条目P90) | n_rel |')
A('|---|---|---|---|---|---|---|')
# need bag-level anchors P10 values: recompute from raw quickly
import json
bagP={}; fbP={}
for bag in MAIN+EXT:
    mdir=os.path.join(VI, 'X1img_j3' if bag=='X1img_015950' else ('X1img2_j3' if bag=='X1img2_020706' else bag+'_j3'))
    man=json.load(open(os.path.join(mdir,'manifest.json')))
    rows=pd.DataFrame(man['frames']).drop_duplicates(subset=['file','topic'])
    Lr=rows[rows.topic.str.contains('left')].sort_values('t_rec')
    mf='metrics_X1img_sim.json' if bag=='X1img_015950' else ('metrics_X1img2_sim.json' if bag=='X1img2_020706' else ('metrics_%s_w3.json'%bag if bag.startswith('WC2') else 'metrics_%s.json'%bag))
    mj=json.load(open(os.path.join(VI,mf)))
    pf=pd.DataFrame(mj['per_frame']).drop_duplicates(subset=['file','topic'])
    j=Lr.merge(pf,on=['file','topic'],how='left')
    bagP[bag]=(float((j.corners_gFT/150).quantile(0.1)),
               float(j.grid4x4_occupancy_frac.quantile(0.1)) if 'grid4x4_occupancy_frac' in j.columns and j.grid4x4_occupancy_frac.notna().any() else float('nan'),
               float(j.grad_med.quantile(0.1)))
    fbfn='fb_X1img_sim.json' if bag=='X1img_015950' else ('fbres_X1img2_020706.json' if bag=='X1img2_020706' else 'fbres_%s.json'%bag)
    fbj=json.load(open(os.path.join(VI,fbfn)))
    fbP[bag]=float(pd.Series([e['p90'] for e in fbj['temporal']]).quantile(0.9))
lg=long_.set_index(['bag','w0'])
for _,r in rl.iterrows():
    key=(r.bag,r.w0); row=lg.loc[key]
    m1,m2,m3=bagP[r.bag]; fp90=fbP[r.bag]
    def cell(v,thr,nd):
        if v is None or (isinstance(v,float) and math.isnan(v)): return '—'
        s=f'{v:.{nd}f}';  return f'**{s}**' if (not math.isnan(thr) and ((v<=thr) if '≤' in '' else True)) else s
    def b(txt,on): return f'**{txt}**' if on else txt
    c1=b(f"{row.M1_med:.3f} (锚{m1:.3f})", int(r['rel_供给≤袋P10'])==1)
    if isinstance(row.M2_med,float) and math.isnan(row.M2_med): c2='缺列'
    else:
        m2s='锚—' if math.isnan(m2) else f'锚{m2:.4f}'
        c2=b(f"{row.M2_med:.4f} ({m2s})", int(r['rel_占用≤袋P10'])==1)
    c3=b(f"{row.M3_med:.2f} (锚{m3:.2f})", int(r['rel_纹理≤袋P10'])==1)
    c4='—' if (isinstance(row.FB_p90mx,float) and math.isnan(row.FB_p90mx)) else b(f"{row.FB_p90mx:.2f} (锚{fp90:.2f})", int(r['rel_残差≥袋P90'])==1)
    A(f"| {r.bag}（{r.pool}） | {int(r.w0)}-{int(r.w1)}s | {c1} | {c2} | {c3} | {c4} | {int(r.n_rel)} |")
A('')
A('上表仅列命中窗（≥2 族），加粗=该族判据实际命中；判据为 ≤/≥ 含等界（并列最小值计命中，如 U3PG 0-30s 占用 0.5625=锚 0.5625）。全 122 行旗标见 `d6_collapse_flags.csv`。')
A('饱和袋相对门退化注记：U3PH（供给/占用帧级 P10=1.000，判读账本 L221-222 饱和三例之一）相对门逐窗退化命中；X1final/X1PR1 占用 P10=0.75/0.625 高位同理敏感性偏松。X1img/X1img2 纹理锚=0.0（grad_med≡0 袋），全窗并列命中。')
A('')

A('## 3. 逐袋「最差 30s 窗」注册表（composite 分位秩和）')
A('')
A('口径：袋内有帧窗（n_f>0）内，对 7 指标各算窗间分位秩（pandas rank pct，并列取均值）：M1↓、M2↓、M3↓（低=差）、M4↑、FBt_p90max↑、云率↓、|v|med↑（高=差）；composite=可得指标秩和，comp_norm=秩和/指标数；该袋 comp_norm 最大窗=worst1，次大=worst2。指标在窗内缺值即退出该窗该指标；袋内非 NaN 窗数<2 的指标整列退出（X1img/X1img2 的 M2、无 odom 袋的云率/|v| 如此）。γ 恒 1.0 无区分度不入秩，仅上下文列。')
A('')
A('### 3.1 主池（6 袋）')
A('')
wm=worst[(worst.pool=='主池')]
cols=['bag','rank','w0','w1','comp_norm','comp_sum','n_ind','M1_med','M2_med','M3_med','M4_med','FB_p90mx','pts_s','v_med','n_f']
A('| '+' | '.join(['袋','名次','窗','窗末','comp_norm','秩和','n_ind','M1','M2','M3','M4','FBp90max','云率pts/s',r'\|v\|med','n_f'])+' |')
A('|---'*15+'|')
for _,r in wm.iterrows():
    cells=[]
    for c in cols:
        v=r[c]
        if c in ('bag','rank'): cells.append(str(v))
        elif c in ('w0','w1','n_ind','n_f'): cells.append(str(int(v)))
        elif c=='comp_norm': cells.append(f'{v:.4f}')
        elif c=='comp_sum': cells.append(f'{v:.4f}')
        else: cells.append('—' if (isinstance(v,float) and math.isnan(v)) else f'{v:.3f}')
    A('| '+' | '.join(cells)+' |')
A('')
A('### 3.2 扩展池（4 袋，一律「扩展池」标注；粒度降级见 §5）')
A('')
we=worst[(worst.pool=='扩展池')]
A('| '+' | '.join(['袋（扩展池）','名次','窗','comp_norm','秩和','n_ind','M1','M3','M4','FBp90max','n_f'])+' |')
A('|---'*11+'|')
for _,r in we.iterrows():
    cells=[r.bag,r['rank'],f"{int(r.w0)}-{int(r.w1)}s",f'{r.comp_norm:.4f}',f'{r.comp_sum:.4f}',str(int(r.n_ind)),
           '—' if (isinstance(r.M1_med,float) and math.isnan(r.M1_med)) else f'{r.M1_med:.3f}',
           '—' if (isinstance(r.M3_med,float) and math.isnan(r.M3_med)) else f'{r.M3_med:.2f}',
           '—' if (isinstance(r.M4_med,float) and math.isnan(r.M4_med)) else f'{r.M4_med:.3f}',
           '—' if (isinstance(r.FB_p90mx,float) and math.isnan(r.FB_p90mx)) else f'{r.FB_p90mx:.2f}',
           str(int(r.n_f))]
    A('| '+' | '.join(cells)+' |')
A('')
A('全字段（含 z/γ/pc/n_vjump 等上下文）见 `d6_worst_windows.csv`（20 行=10 袋×worst1/2）。')
A('')

A('## 4. 袋级锚表（官方池化值，与 §1 窗表互校）')
A('')
A('| 袋(池) | n_primary | corners_p50 | grid_p50 | gradmed_p50 | maxbin_p50 | γ_p50(n) | FBt p50/p90 | FBs p50/p90 | density pts_total | per_msg p50 |')
A('|---|---|---|---|---|---|---|---|---|---|---|')
for _,r in anch.iterrows():
    A(f"| {r.bag}（{r.pool}） | {int(r.n_primary)} | {r.corners_p50:.1f} | {'—' if pd.isna(r.grid_p50) else f'{r.grid_p50:.3f}'} | {r.gradmed_p50:.2f} | {r.maxbin_p50:.3f} | {r.gamma_p50:.2f}({int(r.gamma_n)}) | {r.fbT_p50:.3f}/{r.fbT_p90:.2f} | {r.fbS_p50:.2f}/{r.fbS_p90:.2f} | {'—' if pd.isna(r.dens_pts_total) else str(int(r.dens_pts_total))} | {'—' if pd.isna(r.dens_pmsg_p50) else str(int(r.dens_pmsg_p50))} |")
A('')
A('源：`metrics_*.json` metrics.*（n/p10/p50/p90）+ `fbres_*` temporal_pool/stereo_pool + `metrics_*_density.json`（points_total/per_msg_points.p50；密度分区判读边界=判读账本 L199/225，本表仅存档）。')
A('')

A('## 5. 方法降级与数据缺口登记（本剖面全部非理想口径）')
A('')
A('① **FB 条目无时间戳**：fbres_*.json temporal/stereo 条目仅 `temporal_fb_tN` 序号，无时刻字段→按「entry i ↔ 左目帧 2i」stride-2 索引映射（U3PG 36 条=ceil(71/2) 精确吻合；主池其余袋条目数与 ceil(L/2) 差 1-2（如 U3PO stereo 37>35、WC2#1 temporal 33<35），尾部条目映射偏差上界≈2 个 L 帧间隔（长袋≈10s 量级），已按原样入窗不校正。')
A('② **|v| 为差分副本**：odom_pc_csv 只含 t,px,py,pz,四元数（extract_odom_pc.py L2 表头），twist.linear 未提取→|v|=位置前向差分；同 stamp 成对样本（U3PG 413/853、U3PR2 6066/12142、WC2#2 983/2036，U3PO 无重复）每 stamp 留末位；回放 odometry 存在流间跳变样本（|v|>15 m/s 非物理门剔除占比：X1img 0%、U3PG 0%、WC2#1 8.7%、WC2#2 36.2%、U3PO 90.2%、U3PR2 44.9%）——n_vjump 行给出逐窗剔除数，U3PO 窗 60-90s 等 n_vjump≈n_o 窗的 |v| 读数按不可靠对待；z 中位在发散袋（WC2#2 z 至 -206m、U3PO 至 -16.9m、U3PR2 至 +42.4m）受双流污染，z_p10/z_p90 行如实给出散布。')
A('③ **γ 无逐帧数组**（数据字典 §per_frame 13 数值键不含 gamma_pair）→窗值=官方 by_seg_median 按最大重叠 seg 映射，长袋一个 seg 跨多窗重复同值；γ 无 |v|<0.3 近静止门复算（prep L43 口径保留官方值，未做副本重算）。')
A('④ **M4 无 Laplacian 字段**：metrics json 12 子键无模糊域读数，M4 以 grad_dir_maxbin_frac（方向能量）单半边代理（prep L27 方向能量口径；E7「方向能量 sim 0.200=纹理本底」）。')
A('⑤ **主池 3 份 fb json 为工作流内新增件**：fbres_WC2OBS1_030927/032005、fbres_X1img2_020706 不在 raw_manifest.md5（L33-39 仅 7 份 fb），matrix_5faces.md L12/13/22 判其为 NUC 侧「缺（可补）」→本工作流期间由兄弟线回填落盘，本剖面按在位文件使用（值域抽查：WC2#2 temporal_fb_t5.p90=471.540 与文件逐位一致）。')
A('⑥ **WC2 两袋窗覆盖截断**：帧面到 402/401s，但回放 odom/pc 止于 71.9/134.7s（爆炸窗，判读账本 L132-142）→90s 后各窗 n_o=pc_n=0（B/C 表如实空）；X1img 回放覆盖 27.2-235.0s（帧面至 301.1s），235s 后窗无 odom/pc。')
A('⑦ **无 CI**：窗中位数样本 n 以行给出；prep §3.3 bootstrap 单元=轮，窗级重采样单元未预注册→不出 CI（非 Silent，登记）。')
A('⑧ **绝对门零命中注记**：供给 M1<0.2 与占用 M2<0.5 在主池 76 窗零命中，与 J1.3 注入代供给 P10=0.55（判读账本 L208-210）同向；纹理零梯度门仅 X1img（注入前袋，grad_med 69/69 帧=0.0，实测本 raw）全窗命中。')
A('⑨ **扩展池粒度**：X1img2 pc.csv 全零行（回放 18.2s segv，判读账本 L107-110）→其窗云率=0 属「无点产出」而非场景读数；X1img2 fb 条目 18/23 对 ceil(75/2)=38 缺口大，其 FB 窗映射偏差上界大于主池，仅存档。U3PH/U3PR1/X1final 无 odom/pc 面（源袋已删类）→无 |v|/z/云率列。')
A('')

A('## 6. 产出文件')
A('')
A('| 文件 | 内容 |')
A('|---|---|')
A('| `derived/d6_time_profiles.md` | 本文 |')
A('| `derived/d6_worst_windows.csv` | 逐袋最差窗注册表，20 行×30 列（10 袋×worst1/worst2，含扩展池标注） |')
A('| `derived/d6_window_metrics_long.csv` | 全部 122 窗×28 指标长表（主池 76+扩展池 46） |')
A('| `derived/d6_collapse_flags.csv` | 122 窗×4 族×2 判据旗标 |')
A('| `derived/d6_bag_anchors.csv` | 10 袋官方池化锚值 |')
A('| `derived/d6_compute.py`、`derived/d6_make_md.py` | 计算与本文生成脚本（python 3.12.7+numpy 2.4.4+pandas 3.0.2，本机实测在位=数据字典 §3） |')
A('')

with open(os.path.join(DER,'d6_time_profiles.md'),'w',encoding='utf-8') as fho:
    fho.write('\n'.join(L))
print('md written, lines=',len(L))
