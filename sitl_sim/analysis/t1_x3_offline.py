#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# T1-X3 离线参数现值件 + P0-C 尾件3(offboard_control_mode/vehicle_command 序列)
# 输入: w2 五场景 ulg(路径取自 w2_ulogs/*.json 的 ulg 字段)
# 输出: X3_offline_w2.json + stdout 摘要(参数矩阵/EV too fast 计数/模式序列)
# 只读,0锁,不触栈。v9.0 等待池③④/尾件3 用。
import io, json, sys, glob, os
from pyulog import ULog

EV_KEYS = ['EKF2_EV_CTRL', 'EKF2_GPS_CTRL', 'EKF2_TAU_POS', 'EKF2_TAU_VEL',
           'EKF2_EVP_NOISE', 'EKF2_EVV_NOISE', 'EKF2_PREDICT_US', 'EKF2_DELAY_MAX',
           'EKF2_EV_DELAY', 'EKF2_EV_QMIN', 'EKF2_HGT_REF', 'EKF2_MAG_TYPE']
EV_DIR = os.path.expanduser('~/catkin_ws/sitl_sim/t1_evidence/v8_2026-10-01/w2_ulogs')
OUTJ = os.path.expanduser('~/catkin_ws/sitl_sim/t1_evidence/v9_2026-10-01/X3_offline_w2.json')

def transitions(u, topic, fields=None):
    d = next((x for x in u.data_list if x.name == topic), None)
    if d is None: return None
    keys = [k for k in d.data if k != 'timestamp'] if fields is None else fields
    ts = d.data['timestamp']
    out, last = [], None
    for i, t in enumerate(ts):
        snap = tuple(int(d.data[k][i]) for k in keys if k in d.data)
        if snap != last:
            out.append([round((t - ts[0]) / 1e6, 2), dict(zip([k for k in keys if k in d.data], snap))])
            last = snap
    return out

def main():
    os.makedirs(os.path.dirname(OUTJ), exist_ok=True)
    res = {}
    for jf in sorted(glob.glob(os.path.join(EV_DIR, '*.json'))):
        meta = json.load(io.open(jf, encoding='utf-8'))
        tag = os.path.basename(jf).replace('.json', '')
        ulg = meta.get('ulg')
        if not ulg or not os.path.exists(ulg):
            res[tag] = {'skip': 'ulg missing: %s' % ulg}; continue
        u = ULog(ulg, None)
        p = u.initial_parameters
        res[tag] = {'ulg': ulg, 'dur_s': round((u.last_timestamp - u.start_timestamp) / 1e6, 1),
                    'params': {k: p.get(k) for k in EV_KEYS if k in p},
                    'missing_keys': [k for k in EV_KEYS if k not in p],
                    'ev_too_fast_msgs': [getattr(m, 'message', str(m))[:120] for m in
                                         getattr(u, 'logged_messages', [])
                                         if 'too fast' in str(getattr(m, 'message', '')).lower()
                                         and 'ev' in str(getattr(m, 'message', '')).lower()],
                    'offboard_control_mode': transitions(u, 'offboard_control_mode'),
                    'vehicle_command': transitions(u, 'vehicle_command', ['command']),
                    'vehicle_status_nav': transitions(u, 'vehicle_status', ['nav_state'])}
        print('%-12s dur=%5.1fs params=%s too_fast=%d offboard_trans=%d vcmd=%d' % (
            tag, res[tag]['dur_s'], json.dumps(res[tag]['params']), len(res[tag]['ev_too_fast_msgs']),
            len(res[tag]['offboard_control_mode'] or []), len(res[tag]['vehicle_command'] or [])))
    io.open(OUTJ, 'w', encoding='utf-8').write(json.dumps(res, indent=1, ensure_ascii=False))
    print('WROTE', OUTJ)

if __name__ == '__main__':
    main()
