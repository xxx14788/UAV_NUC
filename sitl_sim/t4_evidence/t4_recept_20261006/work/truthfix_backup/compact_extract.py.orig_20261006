#!/usr/bin/env python3
# compact bag mechanical face: three sources (vins odom / mavros local_position / gazebo truth iris)
import sys, json, math
import rosbag

bag_path, out_json, draft, run, j0d, received = sys.argv[1:7]
bag = rosbag.Bag(bag_path, 'r')
t0b = bag.get_start_time(); t1b = bag.get_end_time()

sel = []
try:
    ti = bag.get_type_and_topic_info()
    for tn, info in ti.topics.items():
        if info.msg_count > 0 and (tn == '/vins_estimator/odometry'
                                   or tn.startswith('/mavros/local_position')
                                   or tn == '/gazebo/model_states'):
            sel.append(tn)
except Exception:
    pass

SRC = {'odom': [], 'mavros': [], 'truth': []}
for topic, msg, t in bag.read_messages(topics=sel):
    try:
        if topic == '/vins_estimator/odometry':
            p = msg.pose.pose.position; SRC['odom'].append((t.to_sec(), p.x, p.y, p.z))
        elif topic.startswith('/mavros/local_position'):
            p = msg.pose.pose.position; SRC['mavros'].append((t.to_sec(), p.x, p.y, p.z))
        elif topic == '/gazebo/model_states':
            if hasattr(msg, 'name') and 'iris' in list(msg.name):
                i = list(msg.name).index('iris'); p = msg.pose[i].position
                SRC['truth'].append((t.to_sec(), p.x, p.y, p.z))
    except Exception:
        pass
bag.close()

def stats(arr):
    if not arr:
        return None
    n = len(arr); z = [a[3] for a in arr]
    jumps = 0; jmax = 0.0
    for a, b in zip(arr, arr[1:]):
        d = math.sqrt((a[1]-b[1])**2 + (a[2]-b[2])**2 + (a[3]-b[3])**2)
        if d > 0.5: jumps += 1
        if d > jmax: jmax = d
    return {'n': n, 'dur_s': round(arr[-1][0]-arr[0][0], 3),
            'z_min': round(min(z), 4), 'z_max': round(max(z), 4),
            'jump_cnt_gt05m': jumps, 'jump_max_m': round(jmax, 4)}

res = {'run': run, 'bag': bag_path, 'bag_dur_s': round(t1b-t0b, 3), 'received': int(received),
       'sources': {k: stats(v) for k, v in SRC.items()}}
if SRC['odom'] and SRC['truth']:
    o = SRC['odom'][-1]; tr = SRC['truth'][-1]
    res['end_diff_odom_vs_truth_m'] = round(math.sqrt((o[1]-tr[1])**2 + (o[2]-tr[2])**2 + (o[3]-tr[3])**2), 4)
else:
    res['end_diff_odom_vs_truth_m'] = None
res['j0d_ref'] = j0d if j0d else 'T3 工具产出后增列'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

d = res['sources']
ed = res['end_diff_odom_vs_truth_m']
if ed is None:
    flavor = '末端位置差不可得(源缺失)——素材缺失·如实登记'
elif ed > 1.10:
    flavor = '超健康带上界(>1.10m)=爆型 A 域素材'
elif ed >= 0.79:
    flavor = '落健康带 0.79-1.10m=精度地板 C 域素材'
else:
    flavor = '健康带下(<0.79m)=两味素材之外(素材中性)'
lines = []
lines.append('')
lines.append('## [COMPACT] %s — 草稿·待主会话定稿' % run)
rcv = ' | received=1(W1 收货集 MACH-compact, v5.19 补判读行)' if received == '1' else ''
lines.append('- 分类: ③紧凑零图像%s | 第五坑登记: EX-FAIL 零图像(W1 挂账, v5.19 本批补 odom/truth 机械面)' % rcv)
def fmt(s, k):
    return s[k] if s else '-'
lines.append('- 数据段(perbag/%s.json): bag时长%.1fs | odom n=%s dur=%ss pz=[%s,%s] | mavros n=%s pz=[%s,%s] | truth n=%s pz=[%s,%s]' % (
    run, res['bag_dur_s'],
    fmt(d['odom'], 'n'), fmt(d['odom'], 'dur_s'), fmt(d['odom'], 'z_min'), fmt(d['odom'], 'z_max'),
    fmt(d['mavros'], 'n'), fmt(d['mavros'], 'z_min'), fmt(d['mavros'], 'z_max'),
    fmt(d['truth'], 'n'), fmt(d['truth'], 'z_min'), fmt(d['truth'], 'z_max')))
lines.append('- 末端位置差 odom-vs-truth = %s m' % (('%.4f' % ed) if ed is not None else 'N/A'))
lines.append('- jump 普查(|dP|>0.5m, 相邻样本): odom cnt=%s max=%sm | truth cnt=%s max=%sm' % (
    fmt(d['odom'], 'jump_cnt_gt05m'), fmt(d['odom'], 'jump_max_m'),
    fmt(d['truth'], 'jump_cnt_gt05m'), fmt(d['truth'], 'jump_max_m')))
lines.append('- j0d 引用: %s%s' % (j0d if j0d else 'T3 工具产出后增列', ' (在册即引·不代判)' if j0d else ''))
lines.append('- FAIL 两味素材: 末端漂移 %s 对照健康带 0.79-1.10 m (T3 anchor v1.4 修正口径: t3_anchor_survey_v1.csv + round_result v1.4=c708151f) -> %s (草稿素材·主会话定标)' % (
    (('%.4f m' % ed) if ed is not None else 'N/A'), flavor))
lines.append('- 受控注记: cohort 外袋不出三态——本行不构成三态判定; 数值面=极值/普查+n, 无单帧结论')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('COMPACT_DONE %s end_diff=%s' % (run, ed))
