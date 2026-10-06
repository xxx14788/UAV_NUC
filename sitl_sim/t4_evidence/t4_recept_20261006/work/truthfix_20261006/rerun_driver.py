#!/usr/bin/env python3
# T4-truthfix rerun driver: 3 workers, per-bag timeout 300, nice 10, /tmp workspace only
import json, subprocess, concurrent.futures, time
WS = '/tmp/t4_truthfix'
rows = []
for l in open(WS + '/baglist.tsv'):
    l = l.strip()
    if not l: continue
    parts = l.split('|'); bag, run = parts[0], parts[1]
    rows.append((bag, run))
def one(row):
    bag, run = row
    out = '%s/out/%s.json' % (WS, run)
    log = '%s/out/%s.log' % (WS, run)
    t0 = time.time()
    rc = None
    try:
        r = subprocess.run(['nice', '-n', '10', 'timeout', '300', 'python3',
                            WS + '/rerun_extract.py', bag, out],
                           stdout=open(log, 'w'), stderr=subprocess.STDOUT, timeout=320)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    except Exception as e:
        rc = -1
        open(log, 'w').write(repr(e))
    return run, rc, round(time.time() - t0, 1)
res = []
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    for run, rc, dt in ex.map(one, rows):
        print('%s rc=%s %ss' % (run, rc, dt), flush=True)
        res.append({'run': run, 'rc': rc, 'dt_s': dt})
json.dump(res, open(WS + '/driver_result.json', 'w'), indent=1)
print('ALL_DONE %d' % len(res))
