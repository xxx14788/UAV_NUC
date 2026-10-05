#!/usr/bin/env python3
# D9: freeze window = continuous spans with odom z > 5.0 m (prereg book sec.2, mechanical, no min length)
import sys, json
import rosbag

bag_path, manifest_json, metrics_json, out_json, draft, run = sys.argv[1:7]

bag = rosbag.Bag(bag_path, 'r')
zseries = []
for topic, msg, t in bag.read_messages(topics=['/vins_estimator/odometry']):
    zseries.append((t.to_sec(), msg.pose.pose.position.z))
bag.close()

windows = []
cur = None
for t, z in zseries:
    if z > 5.0:
        if cur is None:
            cur = [t, t, 1]
        else:
            cur[1] = t; cur[2] += 1
    else:
        if cur is not None:
            windows.append(cur); cur = None
if cur is not None:
    windows.append(cur)
wins = [{'t0': round(w[0], 3), 't1': round(w[1], 3), 'n_samples': w[2], 'len_s': round(w[1]-w[0], 3)} for w in windows]
out = {'run': run, 'freeze_windows': wins, 'n_windows': len(wins)}

if not wins:
    out['d9'] = 'no_freeze_window -> skip (如实注记)'
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(draft, 'a', encoding='utf-8') as f:
        f.write('- D9 扩样腿: 无冻结窗(odom_z>5.0m 零窗) -> 跳过(如实注记, 判据册 §2 口径)\n')
    print('D9_NOWINDOW %s' % run)
    sys.exit(0)

man = json.load(open(manifest_json, encoding='utf-8'))
trec = {}
for fr in man.get('frames', []):
    fn = fr.get('file') or fr.get('fname') or fr.get('name') or fr.get('path')
    tt = fr.get('t_rec', fr.get('t'))
    if fn and tt is not None:
        trec[fn] = float(tt)

met = json.load(open(metrics_json, encoding='utf-8'))
pf = met.get('per_frame', [])
if not isinstance(pf, list) or not pf:
    out['d9'] = 'per_frame_missing -> frozen subset not computable (如实注记)'
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(draft, 'a', encoding='utf-8') as f:
        f.write('- D9 扩样腿: 冻结窗检出但 metrics 无 per_frame -> 冻结子集重算不可行(如实注记)\n')
    print('D9_NOPF %s' % run)
    sys.exit(0)

def inwin(t):
    return any(w[0] <= t <= w[1] for w in windows)

MET6 = ['supply_frac', 'grid4x4_occupancy_frac', 'd12_sigma_p25', 'd12_sigma_flat', 'med_gray', 'corners_gFT']
frozen = {m: [] for m in MET6}
outside = {m: [] for m in MET6}
n_in = 0; n_out = 0; n_unmapped = 0
for row in pf:
    fn = row.get('file') or row.get('path')
    t = trec.get(fn) if fn else None
    if t is None:
        n_unmapped += 1; continue
    if inwin(t):
        n_in += 1; tgt = frozen
    else:
        n_out += 1; tgt = outside
    for m in MET6:
        v = row.get(m)
        if isinstance(v, (int, float)):
            tgt[m].append(float(v))

import numpy as np
def q(v):
    if not v:
        return None
    a = np.array(v)
    return {'n': len(v), 'p10': round(float(np.percentile(a, 10)), 4),
            'p50': round(float(np.percentile(a, 50)), 4), 'p90': round(float(np.percentile(a, 90)), 4)}

out['d9'] = 'freeze_subset_recomputed'
out['frames_in_window'] = n_in
out['frames_outside'] = n_out
out['frames_unmapped'] = n_unmapped
out['frozen_subset'] = {m: q(frozen[m]) for m in MET6}
out['outside_subset'] = {m: q(outside[m]) for m in MET6}
json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

lines = ['', '### [D9 扩样行] %s — 草稿·待主会话定稿' % run]
lines.append('- 冻结窗(odom_z>5.0m 连续窗, 判据册 §2 机械判定): %d 窗, 窗长(s)=%s, 帧归属 in=%d out=%d unmapped=%d' % (
    len(wins), ','.join(str(w['len_s']) for w in wins[:8]), n_in, n_out, n_unmapped))
lines.append('- 六指标冻结子集(分位+n, 无CI=草稿素材): ' + '; '.join(
    '%s: n=%s p50=%s' % (m, (out['frozen_subset'][m] or {}).get('n'), (out['frozen_subset'][m] or {}).get('p50'))
    for m in MET6))
lines.append('- n 扩样口径: 基线 n_primary=%s -> 冻结子集 n=%d(窗内帧); 窗外子集另报(outside_subset)' % (
    met.get('n_primary'), n_in))
lines.append('- 受控注记: 扩样行=数据段草稿, 不构成三态判定')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('D9_WINDOW %s wins=%d in=%d' % (run, len(wins), n_in))
