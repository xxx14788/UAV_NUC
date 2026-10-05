#!/usr/bin/env python3
import sys, json, time
path, patch = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path, encoding='utf-8'))
except Exception:
    d = {}
p = json.loads(patch)
def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
merge(d, p)
d['updated_at'] = time.strftime('%F %T')
json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
