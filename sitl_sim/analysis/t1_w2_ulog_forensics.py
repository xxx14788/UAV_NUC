#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# T1-P0C.2: W2 五场景 ulog 层2取证（PX4 位置环/EV 链/模式切换/参数面）
# 输出 JSON：每 ulg 一份。只读，0锁。
import sys, json, math
from pyulog import ULog

def pct(a, p):
    if not a: return None
    a = sorted(a); k = (len(a)-1)*p/100.0
    f, c = int(math.floor(k)), int(math.ceil(k))
    return a[f] if f == c else a[f]+(a[c]-a[f])*(k-f)

def dt_ms(ts):  # timestamp array (us) -> positive deltas ms
    return [(ts[i]-ts[i-1])/1000.0 for i in range(1,len(ts)) if ts[i] > ts[i-1]]

def transitions(ts, vals):
    out = []; last = None
    for t, v in zip(ts, vals):
        if last is None or v != last[1]:
            out.append([round((t-ts[0])/1e6,2), int(v) if isinstance(v,(int,float)) else v]); last = (t,v)
    return out

def get(u, name):
    for d in u.data_list:
        if d.name == name: return d
    return None

def sidx(u, name, fields):
    d = get(u, name)
    if d is None: return None
    out = {"n": len(d.data['timestamp'])}
    for f in fields:
        if f in d.data:
            arr = d.data[f]
            out[f] = {"min": float(arr.min()), "max": float(arr.max()),
                      "first": float(arr[0]), "last": float(arr[-1])} if len(arr) else None
    return out

ulg_path, out_path, tag = sys.argv[1], sys.argv[2], sys.argv[3]
u = ULog(ulg_path, None)
R = {"ulg": ulg_path, "tag": tag,
     "t0": u.start_timestamp, "dur_s": round((u.last_timestamp-u.start_timestamp)/1e6,1),
     "params": {}, "events": {}}

ip = dict(u.initial_parameters)
KEYS = ['EV_CTRL','SYS_HAS_MAG','MPC_XY_VEL_MAX','MPC_XY_P','MPC_XY_VEL_P_ACC','MPC_Z_VEL_MAX_UP',
        'MPC_THR_HOVER','MPC_TILTMAX_AIR','EKF2_EV_POS_M','EKF2_EV_DELAY','EKF2_GPS_CTRL',
        'EKF2_PREDICT_US','EKF2_DELAY_MAX','EKF2_EV_QMIN','EKF2_MAG_TYPE','EKF2_HGT_REF',
        'COM_RCL_EXCEPT','NAV_DLL_EXCT','MPC_XY_CRUISE','MC_ROLLRATE_MAX','MC_PITCHRATE_MAX']
for k in KEYS:
    if k in ip: R["params"][k] = ip[k]
R["params_n_total"] = len(ip)
ev_keys = [k for k in ip if 'EV' in k and ('CTRL' in k or 'EKF2' in k)]
R["params"]["_ev_related"] = {k: ip[k] for k in sorted(ev_keys)[:20]}

# --- EV 供给流(PX4 眼中) + EV 融合状态
d = get(u, 'vehicle_visual_odometry')
if d is not None and len(d.data['timestamp']):
    ts = d.data['timestamp']; g = dt_ms(ts)
    R["events"]["vo_supply"] = {"n": len(ts), "rate_hz": round(len(ts)/((ts[-1]-ts[0])/1e6),1),
        "dt_p50": pct(g,50), "dt_p95": pct(g,95),
        "cov_nonzero": (int(sum(1 for x in d.data['pose_covariance'][0][:6] if x > 0)) if 'pose_covariance' in d.data else None)}
d = get(u, 'estimator_odometry')
if d is not None and len(d.data['timestamp']):
    f = {}
    for k in ('posFusion','velFusion','hgtFusion','yawFusion'):
        if k in d.data: f[k] = int(d.data[k].max())
    R["events"]["ev_fusion_max_flags"] = f or {"fields": list(d.data.keys())[:12]}
# --- 模式/解锁
for name, fields in [('vehicle_status', ['arming_state','nav_state','failsafe']),
                     ('vehicle_control_mode', ['flag_control_offboard_enabled','flag_control_position_enabled','flag_control_velocity_enabled','flag_control_altitude_enabled','flag_control_attitude_enabled','flag_control_rates_enabled']),
                     ('vehicle_land_detected', ['landed'])]:
    d = get(u, name)
    if d is not None and len(d.data['timestamp']):
        out = {}
        for f in fields:
            if f in d.data: out[f] = transitions(d.data['timestamp'], d.data[f])
        R["events"][name] = out
# --- local_position 输出率 + GT 失控量级
d = get(u, 'vehicle_local_position')
if d is not None and len(d.data['timestamp']):
    g = dt_ms(d.data['timestamp'])
    R["events"]["lp_rate"] = {"n": len(g)+1, "dt_p50": pct(g,50), "dt_p95": pct(g,95)}
for nm, tagk in [('vehicle_local_position_groundtruth','gt_lp'), ('vehicle_attitude_setpoint','att_sp'), ('trajectory_setpoint','traj_sp'), ('vehicle_local_position_setpoint','lp_sp'), ('manual_control_setpoint','manual')]:
    d = get(u, nm)
    if d is not None and len(d.data['timestamp']):
        ts = d.data['timestamp']
        e = {"n": len(ts)}
        if len(ts) > 10:
            g = dt_ms(ts); e["rate_hz"] = round(len(ts)/((ts[-1]-ts[0])/1e6),1); e["dt_p50"] = pct(g,50)
        if tagk == 'gt_lp':
            import numpy as np
            x,y,z = d.data['x'], d.data['y'], d.data['z']
            e.update({"x_range":[round(float(x.min()),2),round(float(x.max()),2)],
                      "y_range":[round(float(y.min()),2),round(float(y.max()),2)],
                      "z_max": round(float(z.max()),2), "xy_max_abs": round(float(max(abs(x).max(),abs(y).max())),2)})
        R["events"][tagk] = e
# --- 创新测试比（哪些检测超线）
d = get(u, 'estimator_innovation_test_ratios')
if d is not None and len(d.data['timestamp']):
    over = {}
    for k in d.data:
        if k == 'timestamp': continue
        try: mx = float(d.data[k].max())
        except Exception: continue
        if mx > 1.0: over[k] = round(mx,2)
    R["events"]["innov_ratio_over1"] = over or "none"
# --- 文本事件
d = get(u, 'log_message')
if d is not None:
    R["events"]["log_messages"] = list(set(str(x) for x in d.data['text'][:200]))[:20]
txt = json.dumps(R, indent=1, ensure_ascii=False, default=str)
open(out_path,'w').write(txt)
print(tag, 'OK  dur=%ss' % R['dur_s'], 'vo:', R['events'].get('vo_supply',{}).get('rate_hz'),
      'ev_flags:', R['events'].get('ev_fusion_max_flags'), 'innov_over1:', str(R['events'].get('innov_ratio_over1'))[:120])
