#!/usr/bin/env python3
import sys, json

run, received, cls, draft, metrics_json, fbres_json, d9_json, topics_l, topics_r, cfg_note = sys.argv[1:11]

def load(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None

met = load(metrics_json); fb = load(fbres_json); d9 = load(d9_json)
lines = []
lines.append('')
lines.append('## [IMAGE%s] %s — 草稿·待主会话定稿' % ('-RECEIVED-VERIFY' if received == '1' else '', run))
lines.append('- 分类: %s | 双目话题 L=%s R=%s' % (cls, topics_l or '-', topics_r or '-'))
if received == '1':
    lines.append('- W1 收货集在册(I 章): 本行仅核对台账族在位, 不重链不代判')
if met:
    M = met.get('metrics', {})
    def row(key, label):
        v = M.get(key)
        if not isinstance(v, dict):
            return '- %s(%s): 缺(如实登记)' % (label, key)
        return '- %s(%s): p10=%s p50=%s p90=%s n=%s p90_ci=%s med_ci=%s' % (
            label, key, v.get('p10'), v.get('p50'), v.get('p90'), v.get('n'), v.get('p90_ci'), v.get('med_ci'))
    lines.append(row('supply_frac', 'M1 supply_frac'))
    lines.append(row('grid4x4_occupancy_frac', 'M2 grid4x4_occupancy_frac'))
    lines.append(row('d12_sigma_p25', 'sigma_hat P25 (d12_sigma_p25)'))
    lines.append(row('med_gray', 'med_gray'))
    lines.append('- 数值口径: 工具输出分位+CI+n 原样引用(sigma 只认 P25); n_primary=%s' % met.get('n_primary'))
else:
    lines.append('- metrics JSON 缺失/不可读 -> 指标面缺失(如实登记)')
if fb:
    for pool in ('temporal', 'stereo'):
        arr = fb.get(pool, [])
        if isinstance(arr, list):
            for e in arr:
                if isinstance(e, dict) and 'label' in e:
                    lines.append('- FB %s: label=%s n=%s p50=%s p90=%s p95=%s p90_ci=%s' % (
                        pool, e.get('label'), e.get('n'), e.get('p50'), e.get('p90'), e.get('p95'), e.get('p90_ci')))
else:
    lines.append('- fbres JSON 缺失/不可读 -> FB 残差面缺失(如实登记)')
if d9:
    lines.append('- D9 扩样腿: %s (详见 perbag/%s.d9.json)' % (d9.get('d9'), run))
else:
    lines.append('- D9 扩样腿: 未产出(如实登记)')
lines.append('- config 注记: %s' % cfg_note)
lines.append('- 域外注记: cohort 外袋不出三态——本行不构成三态判定 (H/I 章先例)')
lines.append('- 受控注记: 任一门拦截+完整恢复=受控失败; 门/腿 rc 记录见 chain.log 与 perbag json')
with open(draft, 'a', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print('ROW_DONE %s' % run)
