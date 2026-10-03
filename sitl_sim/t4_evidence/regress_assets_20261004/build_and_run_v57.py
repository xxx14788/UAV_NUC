#!/usr/bin/env python3
# ASCII only. Build 10 synthetic cases and run 3 tools x cases on NUC.
# Tools are NOT modified. Results go to results.jsonl + logs/.
import json
import os
import shutil
import subprocess
import time

import cv2
import numpy as np

ROOT = '/tmp/t4_v57_selftest'
CASES = ROOT + '/cases'
LOGS = ROOT + '/logs'
ANALYSIS = '/home/uav/catkin_ws/sitl_sim/analysis'

shutil.rmtree(ROOT, ignore_errors=True)
os.makedirs(CASES)
os.makedirs(LOGS)

W, H = 640, 480
rng = np.random.RandomState(7)
NOISE8 = rng.randint(0, 256, (H, W)).astype(np.uint8)
NOISE16 = rng.randint(0, 65536, (H, W)).astype(np.uint16)


def arr_for(kind, shape=(H, W), depth=8):
    if kind == 'white':
        return np.full(shape, 255, np.uint8)
    if kind == 'black':
        return np.zeros(shape, np.uint8)
    if kind == 'noise':
        if depth == 16:
            return NOISE16
        return NOISE8 if shape == (H, W) else rng.randint(0, 256, shape).astype(np.uint8)
    raise ValueError(kind)


def wpng(path, a):
    assert cv2.imwrite(path, a), path


def write_case(name, files, manifest, truncate_frac=None):
    d = CASES + '/' + name
    os.makedirs(d)
    for fn, a in files:
        p = d + '/' + fn
        wpng(p, a)
        if truncate_frac is not None:
            b = open(p, 'rb').read()
            open(p, 'wb').write(b[:int(len(b) * truncate_frac)])
    with open(d + '/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=1)
    return d


def tmpl_manifest(frames):
    return {
        'bag': '/tmp/t4_v57_selftest/synthetic_source.bag',
        'topics': ['cam_left', 'cam_right'],
        't_range': [0.0, 1.8],
        'duration_s': 1.8,
        'msg_counts': {'cam_left': 9, 'cam_right': 8},
        'camera_info': {},
        'sensor_property': [],
        'frames': frames,
    }


def tmpl_frames(space_suffix=False, drop_tag=False, dup_first=False):
    fr = []
    t = 0.0

    def rec(fn, topic, tag=''):
        r = {'file': fn + (' ' if space_suffix else ''), 'topic': topic,
             't_rec': round(t, 3), 'seg': 0, 'tag': tag, 'size': [W, H]}
        if drop_tag:
            r.pop('tag')
        return r

    names = [('L_s%03d.png' % i, 'cam_left') for i in range(8)]
    names += [('R_s%03d.png' % i, 'cam_right') for i in range(8)]
    for fn, tp in names:
        fr.append(rec(fn, tp))
        t += 0.1
    fr.append(rec('L_s000_next.png', 'cam_left', 'next'))
    t += 0.1
    if dup_first:
        fr.insert(1, dict(fr[0]))
    return fr


def tmpl_files(kind):
    out = [('L_s%03d.png' % i, arr_for(kind)) for i in range(8)]
    out += [('R_s%03d.png' % i, arr_for(kind)) for i in range(8)]
    out.append(('L_s000_next.png', arr_for(kind)))
    return out


dirs = {}

# case1a: empty dir (no manifest)
d = CASES + '/case1a_emptydir'
os.makedirs(d)
dirs['case1a_emptydir'] = d

# case1b: manifest only, frames=[]
dirs['case1b_manifestonly'] = write_case(
    'case1b_manifestonly', [], tmpl_manifest([]))

# case2: single frame
d0 = CASES + '/case2_singleframe'
os.makedirs(d0)
wpng(d0 + '/L_s000.png', arr_for('noise'))
dirs['case2_singleframe'] = d0
with open(d0 + '/manifest.json', 'w') as f:
    json.dump(tmpl_manifest([
        {'file': 'L_s000.png', 'topic': 'cam_left', 't_rec': 0.0,
         'seg': 0, 'tag': '', 'size': [W, H]}]), f, indent=1)

# case3/4/5: template dirs
dirs['case3_allwhite'] = write_case(
    'case3_allwhite', tmpl_files('white'), tmpl_manifest(tmpl_frames()))
dirs['case4_allblack'] = write_case(
    'case4_allblack', tmpl_files('black'), tmpl_manifest(tmpl_frames()))
dirs['case5_constnoise'] = write_case(
    'case5_constnoise', tmpl_files('noise'), tmpl_manifest(tmpl_frames()))

# case6: truncated corrupted PNGs (same template, all truncated)
dirs['case6_truncpng'] = write_case(
    'case6_truncpng', tmpl_files('noise'), tmpl_manifest(tmpl_frames()),
    truncate_frac=0.6)

# case7: duplicate manifest record (same file + same t_rec)
dirs['case7_dupts'] = write_case(
    'case7_dupts', tmpl_files('noise'),
    tmpl_manifest(tmpl_frames(dup_first=True)))

# case8: manifest frames missing required 'tag' field
dirs['case8_missingfield'] = write_case(
    'case8_missingfield', tmpl_files('noise'),
    tmpl_manifest(tmpl_frames(drop_tag=True)))

# case9: trailing-space filenames in manifest (files on disk are clean)
dirs['case9_trailspace'] = write_case(
    'case9_trailspace', tmpl_files('noise'),
    tmpl_manifest(tmpl_frames(space_suffix=True)))

# case12: odd bit-depth / odd sizes
d = CASES + '/case12_odddepth'
os.makedirs(d)
wpng(d + '/L_s000.png', arr_for('noise'))
wpng(d + '/L_s001.png', arr_for('noise', depth=16))          # 16-bit png
wpng(d + '/R_s000.png', arr_for('noise'))
wpng(d + '/R_s001.png', arr_for('noise', shape=(48, 72)))    # 72x48, not 16-multiple
wpng(d + '/L_s000_next.png', arr_for('noise', shape=(240, 320)))  # size mismatch vs base
frames12 = [
    {'file': 'L_s000.png', 'topic': 'cam_left', 't_rec': 0.0, 'seg': 0, 'tag': '', 'size': [640, 480]},
    {'file': 'L_s001.png', 'topic': 'cam_left', 't_rec': 0.1, 'seg': 0, 'tag': '', 'size': [640, 480], 'bit_depth': 16},
    {'file': 'R_s000.png', 'topic': 'cam_right', 't_rec': 0.0, 'seg': 0, 'tag': '', 'size': [640, 480]},
    {'file': 'R_s001.png', 'topic': 'cam_right', 't_rec': 0.1, 'seg': 0, 'tag': '', 'size': [72, 48]},
    {'file': 'L_s000_next.png', 'topic': 'cam_left', 't_rec': 0.2, 'seg': 0, 'tag': 'next', 'size': [320, 240]},
]
with open(d + '/manifest.json', 'w') as f:
    json.dump(tmpl_manifest(frames12), f, indent=1)
dirs['case12_odddepth'] = d

TOOLS = {
    'metrics': ANALYSIS + '/j3_image_metrics.py --frames-dir {dir} --out {out}',
    'fb': ANALYSIS + '/j3_fb_residual.py --frames-dir {dir} --out {out}',
    'density_offset': ANALYSIS + '/j3_feature_density.py --mode offset --bag {dir}',
}

ERR_TOKENS = ['ZeroDivisionError', 'cv2.error', 'Traceback', 'divide by zero',
              'RuntimeWarning', 'AssertionError', 'KeyError', 'ValueError',
              'IndexError', 'FileNotFoundError', 'IsADirectoryError',
              'ROSException', 'ROSBagException', 'MemoryError']


def scan_tokens(txt):
    return sorted(t for t in ERR_TOKENS if t in txt)


def strict_json(txt):
    hits = []

    def pc(x):
        hits.append(x)
        return 0.0
    try:
        obj = json.loads(txt, parse_constant=pc)
        return True, hits, obj
    except Exception:
        return False, hits, None


def head(txt, n=240):
    t = txt.strip()
    return t[:n]


def tail(txt, n=420):
    t = txt.strip()
    return t[-n:] if len(t) > n else t


results = []
for case in sorted(dirs):
    d = dirs[case]
    for tool in sorted(TOOLS):
        out = d + '/out_' + tool + '.json'
        cmd = TOOLS[tool].replace('{dir}', d).replace('{out}', out)
        full = ('source /opt/ros/noetic/setup.bash >/dev/null 2>&1; timeout 90 '
                + cmd + ' 2>' + LOGS + '/%s_%s.stderr 1>' + LOGS + '/%s_%s.stdout')
        t0 = time.time()
        p = subprocess.run(['bash', '-lc', full % (case, tool, case, tool)],
                           capture_output=True, timeout=150)
        el = round(time.time() - t0, 2)
        so = open(LOGS + '/%s_%s.stdout' % (case, tool)).read()
        se = open(LOGS + '/%s_%s.stderr' % (case, tool)).read()
        rec = {'case': case, 'tool': tool, 'rc': p.returncode, 'elapsed_s': el,
               'out_path': out, 'out_exists': os.path.exists(out),
               'stdout_head': head(so), 'stdout_tail': tail(so),
               'stderr_head': head(se), 'stderr_tail': tail(se),
               'stderr_tokens': scan_tokens(se),
               'stdout_json_ok': strict_json(so)[0],
               'stdout_nonfinite_hits': len(strict_json(so)[1])}
        if rec['out_exists']:
            txt = open(out).read()
            ok, hits, obj = strict_json(txt)
            rec['out_bytes'] = len(txt)
            rec['out_json_ok'] = ok
            rec['out_nonfinite_hits'] = len(hits)
            rec['out_top_keys'] = sorted(obj.keys()) if isinstance(obj, dict) else None
            if isinstance(obj, dict) and 'metrics' in obj:
                rec['metrics_n'] = {k: v.get('n') for k, v in obj['metrics'].items()
                                    if isinstance(v, dict)}
                rec['n_primary'] = obj.get('n_primary')
            if isinstance(obj, dict) and 'temporal_pool' not in obj:
                rec['missing_pool_keys'] = [k for k in ('temporal_pool', 'stereo_pool', 'h6_tail_compare')
                                            if k not in obj]
        else:
            rec['out_bytes'] = 0
            rec['out_json_ok'] = None
            rec['out_nonfinite_hits'] = None
        results.append(rec)

with open(ROOT + '/results.jsonl', 'w') as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('cells=%d' % len(results))
for r in results:
    print(r['case'], r['tool'], 'rc=%s' % r['rc'], 'el=%s' % r['elapsed_s'],
          'out=%s' % r['out_json_ok'], 'nan=%s' % r['out_nonfinite_hits'],
          'tok=%s' % ','.join(r['stderr_tokens'])[:80])
