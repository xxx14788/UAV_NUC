#!/usr/bin/env python3
import sys, os, json, time, glob

ev = sys.argv[1]
final = '--final' in sys.argv
fatal = None
for a in sys.argv[2:]:
    if a.startswith('--fatal='):
        fatal = a.split('=', 1)[1]

bags = {}
for p in sorted(glob.glob(os.path.join(ev, 'perbag', '*.json'))):
    b = os.path.basename(p)
    if b.endswith('.d9.json'):
        continue
    try:
        d = json.load(open(p, encoding='utf-8'))
        bags[d.get('run', b[:-5])] = d
    except Exception:
        pass

counts = {'total_runs': 0, 'nobag': 0, 'compact': 0, 'compact_received': 0,
          'img_unlinked_fullchain': 0, 'img_linked_verify': 0, 'img_received_verify': 0,
          't1_round_defer': 0, 'hov_verify': 0, 'err_info': 0,
          'done_ok': 0, 'deferred_final': 0, 'partial': 0}
for r, d in bags.items():
    counts['total_runs'] += 1
    c = d.get('class', '')
    if c == 'NOBAG': counts['nobag'] += 1
    elif c == 'ERR_INFO': counts['err_info'] += 1
    elif c == 'T1_ROUND': counts['t1_round_defer'] += 1
    elif c == 'COMPACT': counts['compact'] += 1
    elif c == 'R_COMPACT': counts['compact_received'] += 1
    elif c == 'IMG_FULLCHAIN': counts['img_unlinked_fullchain'] += 1
    elif c == 'IMG_LINKED_VERIFY': counts['img_linked_verify'] += 1
    elif c == 'R_IMG_VERIFY': counts['img_received_verify'] += 1
    elif c == 'HOV_VERIFY': counts['hov_verify'] += 1
    rc = d.get('rc', '')
    if rc == 'OK': counts['done_ok'] += 1
    elif rc == 'DEFERRED_FINAL': counts['deferred_final'] += 1
    elif rc == 'PARTIAL': counts['partial'] += 1

deferred = sorted([r for r, d in bags.items() if d.get('rc') == 'DEFERRED_FINAL'])
summary = {
    'script': 't4_recept_batch_v519.sh',
    'updated_at': time.strftime('%F %T'),
    'counts': counts,
    'deferred_final': deferred,
    'batch_complete': bool(final) and counts['deferred_final'] == 0 and fatal is None,
}
if fatal:
    summary['fatal'] = fatal
json.dump(summary, open(os.path.join(ev, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SUMMARY counts=%s complete=%s' % (json.dumps(counts), summary['batch_complete']))
