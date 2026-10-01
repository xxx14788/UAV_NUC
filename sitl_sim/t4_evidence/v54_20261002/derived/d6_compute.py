# -*- coding: utf-8 -*-
"""
D6 时序剖面计算（2026-10-02，只读本机 raw/，零 NUC IO）
输入: D:/drone_VINS/t4_work_20261002/raw/ 下的 manifest/metrics/fbres/odom_pc_csv
输出: derived/d6_time_profiles.md, derived/d6_worst_windows.csv, derived/d6_window_metrics_long.csv
口径注记全部落在 md 头部与方法行；每个数字可溯源到 源文件+字段名。
"""
import json, os, math
import numpy as np
import pandas as pd

RAW = 'D:/drone_VINS/t4_work_20261002/raw'
VI  = os.path.join(RAW, 'vision_inputs')
DER = 'D:/drone_VINS/t4_work_20261002/derived'
MAXCNT = 150.0          # t4_j2_threshold_prep.md L11
WIN = 30.0              # 任务指定 30s 分箱

MAIN = ['X1img_015950','WC2OBS1_030927','WC2OBS1_032005','U3PG_210307','U3PO_211438','U3PR2_213717']
EXT  = ['X1img2_020706','U3PH_210708','U3PR1_212450','X1final_173345']
ALLB = MAIN + EXT

MF   = {'X1img_015950':'metrics_X1img_sim.json','X1img2_020706':'metrics_X1img2_sim.json',
        'WC2OBS1_030927':'metrics_WC2OBS1_030927_w3.json','WC2OBS1_032005':'metrics_WC2OBS1_032005_w3.json'}
FBF  = {'X1img_015950':'fb_X1img_sim.json','X1img2_020706':'fbres_X1img2_020706.json'}
MDIR = {'X1img_015950':'X1img_j3','X1img2_020706':'X1img2_j3'}
SCEN = {  # 溯源: matrix_5faces.md L11-25 / t4_verdicts_v2.md L127-200, L245
 'X1img_015950'   :'X1 注入前袋(4:33轮; 原始袋已删=挂账禁重试)',
 'WC2OBS1_030927' :'W-C2 轮1(重放 t=71.87s 爆炸; 特征云止~72s/袋376s)',
 'WC2OBS1_032005' :'W-C2 轮1R(T2fail t=128.5 |Bas|=2.772 爆; 在线134.8s爆离线复现)',
 'U3PG_210307'    :'U3-prime ground 轮(袋45.1s)',
 'U3PO_211438'    :'U3-prime obstacles 轮(袋360s, 在线PASS)',
 'U3PR2_213717'   :'U3-prime route2 轮(袋613s, 在线PASS但漂离121.9m级)',
 'X1img2_020706'  :'[扩展池] X1 注入前袋2(跨域dt segv 物理性禁重放)',
 'U3PH_210708'    :'[扩展池] U3-prime 悬停近距袋(源袋已删=N-A)',
 'U3PR1_212450'   :'[扩展池] U3-prime route1(替代compact袋在位, 话题面未验证)',
 'X1final_173345' :'[扩展池] X1 final(源袋已删=特征重放永久不可行)',
}
# 塌陷判据锚（t4_j2_threshold_prep.md L36-38 草案嫌疑门; fb_X1img_sim.json temporal_pool.p90=30.663 判读账本 L74）
ABS_GATE = {'M1':0.2, 'M2':0.5, 'M3zero':0.3, 'FBp90':30.66296310424803}

def jload(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

def load_bag(bag):
    d = {}
    mdir = os.path.join(VI, MDIR.get(bag, bag+'_j3'))
    man = jload(os.path.join(mdir,'manifest.json'))
    rows = pd.DataFrame(man['frames'])
    dup = int(rows.duplicated(subset=['file','topic']).sum())
    rows = rows.drop_duplicates(subset=['file','topic'], keep='first').reset_index(drop=True)
    L = rows[rows.topic.str.contains('left')].sort_values('t_rec').reset_index(drop=True)
    # per_frame join
    mfn = os.path.join(VI, MF.get(bag, f'metrics_{bag}.json'))
    mj = jload(mfn)
    pf = pd.DataFrame(mj['per_frame'])
    pf = pf.drop_duplicates(subset=['file','topic'], keep='first')
    j = L.merge(pf, on=['file','topic'], how='left')
    unm = int(j['corners_gFT'].isna().sum())
    j['M1'] = j['corners_gFT']/MAXCNT
    dev = np.nan
    if 'supply_frac' in j.columns:
        s = j['supply_frac'].notna()
        if s.any(): dev = float((j.loc[s,'M1']-j.loc[s,'supply_frac']).abs().max())
    j['M2'] = j['grid4x4_occupancy_frac'] if 'grid4x4_occupancy_frac' in j.columns else np.nan
    j['M3'] = j['grad_med']
    j['M4'] = j['grad_dir_maxbin_frac']
    d.update(man_rows=len(man['frames']), dup=dup, L=j, unm=unm, m1dev=dev, mj=mj,
             metrics_file=os.path.basename(mfn), n_primary=mj.get('n_primary'))
    # gamma official
    gp = mj['metrics']['gamma_pair']
    d['gamma_pool'] = {'n':gp['n'],'p50':gp['p50'],'p90':gp['p90']}
    d['gamma_seg'] = {int(k):{'n':v['n'],'p50':v['p50']} for k,v in gp['by_seg_median'].items()}
    seg_rng = rows.groupby('seg').agg(t0=('t_rec','min'), t1=('t_rec','max'))
    d['seg_rng'] = {int(k):(float(v['t0']),float(v['t1'])) for k,v in seg_rng.iterrows()}
    # fb (temporal 为主, stereo 次要)
    fb = jload(os.path.join(VI, FBF.get(bag, f'fbres_{bag}.json')))
    d['fb_file'] = os.path.basename(FBF.get(bag, f'fbres_{bag}.json'))
    d['fb_temporal_pool'] = fb['temporal_pool']; d['fb_stereo_pool'] = fb['stereo_pool']
    # stride-2 索引映射: entry i -> L帧 2i (超界钳到最后帧)
    def mapfb(entries):
        out=[]; clamp=0
        for i,e in enumerate(entries):
            k=min(2*i, len(L)-1)
            if 2*i > len(L)-1: clamp+=1
            out.append({'t':float(L.iloc[k]['t_rec']), 'p50':e['p50'], 'p90':e['p90'], 'n':e['n']})
        return pd.DataFrame(out), clamp
    d['fbT'], d['fbT_clamp'] = mapfb(fb['temporal'])
    d['fbS'], d['fbS_clamp'] = mapfb(fb['stereo'])
    # odom / pc (仅主池 6 袋 + X1img2 有)
    odf = os.path.join(VI,'odom_pc_csv',f'jr3_replay_{bag}_odom.csv')
    pcf = os.path.join(VI,'odom_pc_csv',f'jr3_replay_{bag}_pc.csv')
    if os.path.exists(odf):
        od = pd.read_csv(odf); pc = pd.read_csv(pcf)
        n_odom_raw = len(od)
        od = od.sort_values('t').drop_duplicates(subset='t', keep='last').reset_index(drop=True)  # dt=0 重 stamp 对→每 stamp 留最后, ~10Hz
        dt = od['t'].diff().shift(-1)
        dp = np.sqrt((od['px'].diff().shift(-1))**2+(od['py'].diff().shift(-1))**2+(od['pz'].diff().shift(-1))**2)
        v = (dp/dt).iloc[:-1]                          # 前向差分速度, 记在区间左端点
        VJUMP = 15.0                                   # 预声明非物理门: |v|>15 m/s 判回放 odom 跳变样本, 剔除
        jm = np.append((v > VJUMP).values, False)      # 对齐到 od 行数(末位补 False)
        od['v'] = np.nan; od.loc[od.index[:-1],'v'] = v.values
        od.loc[jm, 'v'] = np.nan
        od['vjump'] = jm
        d['vjump_frac'] = float((v > VJUMP).sum()/max(len(v),1))
        d['odom']=od; d['pc']=pc
    else:
        d['odom']=None; d['pc']=None
    return d

def windows(bag, d):
    t0s=[]; t1s=[]
    if len(d['L']): t0s.append(d['L']['t_rec'].min()); t1s.append(d['L']['t_rec'].max())
    if d['odom'] is not None and len(d['odom']):
        t0s.append(d['odom']['t'].min()); t1s.append(d['odom']['t'].max())
    w0 = math.floor(min(t0s)/WIN)*WIN; w1 = math.ceil(max(t1s)/WIN)*WIN
    return [(s, s+WIN) for s in np.arange(w0, w1, WIN)]

def agg_window(d, ws, we):
    L = d['L']; m = (L['t_rec']>=ws)&(L['t_rec']<we); lw = L[m]
    r = {'n_f':len(lw)}
    for c in ['M1','M2','M3','M4']:
        r[c+'_med'] = float(lw[c].median()) if lw[c].notna().any() else np.nan
    r['M3zero'] = float((lw['M3']==0).mean()) if len(lw) else np.nan
    fbT = d['fbT']; mT = (fbT['t']>=ws)&(fbT['t']<we); fT = fbT[mT]
    r['FB_p50'] = float(fT['p50'].median()) if len(fT) else np.nan
    r['FB_p90mx'] = float(fT['p90'].max()) if len(fT) else np.nan
    r['FB_n'] = len(fT)
    fbS = d['fbS']; mS = (fbS['t']>=ws)&(fbS['t']<we); fS = fbS[mS]
    r['FBs_p50'] = float(fS['p50'].median()) if len(fS) else np.nan
    # gamma seg 映射: 取重叠最大的 seg
    best=None; bo=-1
    for s,(t0,t1) in d['seg_rng'].items():
        ov = min(t1,we)-max(t0,ws)
        if ov>bo: bo=ov; best=s
    if best is not None and best in d['gamma_seg']:
        r['gam'] = d['gamma_seg'][best]['p50']; r['gam_n'] = d['gamma_seg'][best]['n']; r['gam_seg'] = best
    else:
        r['gam']=np.nan; r['gam_n']=0; r['gam_seg']=-1
    od=d['odom']; pc=d['pc']
    if od is not None and len(od):
        mo=(od['t']>=ws)&(od['t']<we); ow=od[mo]
        r['n_o']=len(ow)
        r['n_vjump']=int(ow['vjump'].sum())
        r['v_med']=float(ow['v'].median()) if ow['v'].notna().any() else np.nan
        r['v_p90']=float(ow['v'].quantile(0.9)) if ow['v'].notna().any() else np.nan
        r['z_med']=float(ow['pz'].median()) if len(ow) else np.nan
        r['z_p10']=float(ow['pz'].quantile(0.1)) if len(ow) else np.nan
        r['z_p90']=float(ow['pz'].quantile(0.9)) if len(ow) else np.nan
        cov = max(0.0, min(float(od['t'].max()),we)-max(float(od['t'].min()),ws))
        mp=(pc['t']>=ws)&(pc['t']<we); pw=pc[mp]
        r['pc_n']=len(pw)
        r['pc_nonempty']=float((pw['n_points']>0).mean()) if len(pw) else np.nan
        r['pts_s']=float(pw['n_points'].sum()/cov) if cov>0 else np.nan
        r['cov_s']=round(float(cov),2)
    else:
        r.update(n_o=0,v_med=np.nan,v_p90=np.nan,z_med=np.nan,z_p10=np.nan,z_p90=np.nan,n_vjump=0,pc_n=0,pc_nonempty=np.nan,pts_s=np.nan,cov_s=0.0)
    return r

def fnum(x, nd=3):
    if x is None or (isinstance(x,float) and (math.isnan(x))): return '—'
    return f'{x:.{nd}f}'

# ---------------- 逐袋计算 ----------------
BAGS={}; LONG=[]
for bag in ALLB:
    d=load_bag(bag); BAGS[bag]=d
    wl=windows(bag,d)
    recs=[]
    for ws,we in wl:
        r=agg_window(d,ws,we); r['w0']=ws; r['w1']=we; recs.append(r)
        LONG.append({'bag':bag,'pool':'主池' if bag in MAIN else '扩展池','w0':ws,'w1':we, **r})
    d['win']=pd.DataFrame(recs)

long_df=pd.DataFrame(LONG)
long_df.to_csv(os.path.join(DER,'d6_window_metrics_long.csv'), index=False, encoding='utf-8-sig')

# ---------------- 共塌陷检测 ----------------
def flag_sets(bag,d):
    w=d['win']; res=[]
    Lv=d['L']
    bagP={ 'M1': float(Lv['M1'].quantile(0.10)), 'M2': float(Lv['M2'].quantile(0.10)) if Lv['M2'].notna().any() else np.nan,
           'M3': float(Lv['M3'].quantile(0.10)) }
    fbT_all=d['fbT']; fbP90=float(fbT_all['p90'].quantile(0.90)) if len(fbT_all) else np.nan
    for _,r in w.iterrows():
        flags_abs={}; flags_rel={}
        flags_abs['供给M1<0.2'] = (not math.isnan(r['M1_med'])) and r['M1_med']<ABS_GATE['M1']
        flags_abs['占用M2<0.5'] = (not math.isnan(r['M2_med'])) and r['M2_med']<ABS_GATE['M2']
        flags_abs['纹理零梯>0.3'] = (not math.isnan(r['M3zero'])) and r['M3zero']>ABS_GATE['M3zero']
        flags_abs['残差p90>30.7px'] = (not math.isnan(r['FB_p90mx'])) and r['FB_p90mx']>ABS_GATE['FBp90']
        flags_rel['供给≤袋P10'] = (not math.isnan(r['M1_med'])) and r['M1_med']<=bagP['M1']
        flags_rel['占用≤袋P10'] = (not math.isnan(r['M2_med'])) and (not math.isnan(bagP['M2'])) and r['M2_med']<=bagP['M2']
        flags_rel['纹理≤袋P10'] = (not math.isnan(r['M3_med'])) and r['M3_med']<=bagP['M3']
        flags_rel['残差≥袋P90'] = (not math.isnan(r['FB_p90mx'])) and (not math.isnan(fbP90)) and r['FB_p90mx']>=fbP90
        res.append({'w0':r['w0'],'w1':r['w1'],'abs':flags_abs,'rel':flags_rel,
                    'n_abs':sum(flags_abs.values()),'n_rel':sum(flags_rel.values()),
                    'bagP':bagP,'fbP90':fbP90})
    return res

# ---------------- composite 最差窗 ----------------
DIRS={'M1_med':'low','M2_med':'low','M3_med':'low','M4_med':'high','FB_p90mx':'high','pts_s':'low','v_med':'high'}
worst_rows=[]
for bag in ALLB:
    d=BAGS[bag]; w=d['win'].copy()
    w=w[w['n_f']>0].reset_index(drop=True)
    ranks={}
    for c,dirn in DIRS.items():
        col=w[c]
        if col.notna().sum()>=2:
            rk=col.rank(pct=True, na_option='keep')
            if dirn=='low': rk=1.0-rk  # 低=差: 秩反转, 保持 [0,1]
            ranks[c]=rk
    comp=pd.Series(0.0,index=w.index); nin=pd.Series(0,index=w.index)
    for c,rk in ranks.items():
        ok=rk.notna(); comp[ok]+=rk[ok]; nin[ok]+=1
    w['comp']=comp; w['n_ind']=nin
    w['comp_norm']=np.where(w['n_ind']>0, w['comp']/w['n_ind'].replace(0,np.nan), np.nan)
    if (w['n_ind']>0).any():
        wi=w['comp_norm'].idxmax()
        # 次差
        w2=w.drop(index=wi)
        wi2=w2['comp_norm'].idxmax() if len(w2) and (w2['n_ind']>0).any() else None
    else:
        wi=None; wi2=None
    def rowout(idx,tag):
        if idx is None: return None
        r=w.loc[idx]
        o={'pool':'主池' if bag in MAIN else '扩展池','bag':bag,'scenario':SCEN[bag],'rank':tag,
           'w0':int(r['w0']),'w1':int(r['w1']),'comp_sum':round(float(r['comp']),4),
           'n_ind':int(r['n_ind']),'comp_norm':round(float(r['comp_norm']),4),'n_f':int(r['n_f'])}
        for c in DIRS: o[c]= None if (isinstance(r[c],float) and math.isnan(r[c])) else round(float(r[c]),4)
        for c in ['M3zero','FB_n','pc_n','pc_nonempty','z_med','z_p10','z_p90','gam','gam_n','FB_p50','v_p90','n_o','n_vjump']:
            v=r[c]; o[c]= None if (isinstance(v,float) and math.isnan(v)) else (int(v) if c in ('FB_n','pc_n','gam_n','n_o','n_vjump') else round(float(v),4))
        return o
    worst_rows.append(rowout(wi,'worst1'))
    worst_rows.append(rowout(wi2,'worst2'))
worst=pd.DataFrame([r for r in worst_rows if r])
worst.to_csv(os.path.join(DER,'d6_worst_windows.csv'), index=False, encoding='utf-8-sig')

# ---------------- bag 级锚表 ----------------
anchor=[]
for bag in ALLB:
    d=BAGS[bag]; mj=d['mj']
    def q(k): 
        m=mj['metrics'].get(k); 
        return (m['n'],m['p10'],m['p50'],m['p90']) if m else (0,np.nan,np.nan,np.nan)
    nM1,p10_1,p50_1,p90_1=q('corners_gFT')
    dn=json.load(open(os.path.join(VI,f'metrics_{bag}_density.json'))) if os.path.exists(os.path.join(VI,f'metrics_{bag}_density.json')) else None
    anchor.append({'bag':bag,'pool':'主池' if bag in MAIN else '扩展池',
      'n_primary':d['n_primary'],'L_rows':len(d['L']),'join_unmatched':d['unm'],'dup_dropped':d['dup'],
      'M1_dev_vs_supplyfrac':d['m1dev'],
      'corners_p50':p50_1,'grid_p50':q('grid4x4_occupancy_frac')[2],'gradmed_p50':q('grad_med')[2],
      'maxbin_p50':q('grad_dir_maxbin_frac')[2],
      'gamma_n':d['gamma_pool']['n'],'gamma_p50':d['gamma_pool']['p50'],
      'fbT_p50':d['fb_temporal_pool']['p50'],'fbT_p90':d['fb_temporal_pool']['p90'],
      'fbS_p50':d['fb_stereo_pool']['p50'],'fbS_p90':d['fb_stereo_pool']['p90'],
      'dens_pts_total':dn['points_total'] if dn else None,
      'dens_pmsg_p50':dn['per_msg_points']['p50'] if dn else None})
anchor=pd.DataFrame(anchor)
anchor.to_csv(os.path.join(DER,'d6_bag_anchors.csv'), index=False, encoding='utf-8-sig')

# ---------------- 塌陷表导出 ----------------
colrows=[]
for bag in ALLB:
    d=BAGS[bag]; fl=flag_sets(bag,d)
    for f in fl:
        colrows.append({'bag':bag,'pool':'主池' if bag in MAIN else '扩展池','w0':int(f['w0']),'w1':int(f['w1']),
            **{f'abs_{k}':int(v) for k,v in f['abs'].items()}, **{f'rel_{k}':int(v) for k,v in f['rel'].items()},
            'n_abs':f['n_abs'],'n_rel':f['n_rel']})
pd.DataFrame(colrows).to_csv(os.path.join(DER,'d6_collapse_flags.csv'), index=False, encoding='utf-8-sig')

# 保存中间对象给 md 生成
import pickle
with open(os.path.join(DER,'d6_state.pkl'),'wb') as f:
    pickle.dump({'BAGS':{b:{'win':BAGS[b]['win'],'fbT_clamp':BAGS[b]['fbT_clamp'],'fbS_clamp':BAGS[b]['fbS_clamp'],
                            'gamma_seg':BAGS[b]['gamma_seg'],'seg_rng':BAGS[b]['seg_rng'],
                            'n_primary':BAGS[b]['n_primary'],'L_rows':len(BAGS[b]['L']),'unm':BAGS[b]['unm'],
                            'dup':BAGS[b]['dup'],'m1dev':BAGS[b]['m1dev'],
                            'fb_file':BAGS[b]['fb_file'],'metrics_file':BAGS[b]['metrics_file'],
                            'fb_temporal_pool':BAGS[b]['fb_temporal_pool'],'fb_stereo_pool':BAGS[b]['fb_stereo_pool'],
                            'gamma_pool':BAGS[b]['gamma_pool'],
                            'odom_t':(None if BAGS[b]['odom'] is None else (float(BAGS[b]['odom']['t'].min()),float(BAGS[b]['odom']['t'].max()),len(BAGS[b]['odom']))),
                            'pc_t':(None if BAGS[b]['pc'] is None else (float(BAGS[b]['pc']['t'].min()),float(BAGS[b]['pc']['t'].max()),len(BAGS[b]['pc'])))} for b in ALLB},
                 'SCEN':SCEN}, f)
print('OK windows/long/worst/collapse/anchors written')
print(worst.to_string())
