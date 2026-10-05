#!/usr/bin/env python3
# T4 pool piece 2: bitwise leaf-level comparison of two metrics JSON files.
# ASCII only. Usage: python3 compare_leaves.py <a.json> <b.json>
import json
import sys
import difflib


def walk(obj, path, out):
    if isinstance(obj, dict):
        for k in sorted(obj.keys()):
            walk(obj[k], path + [str(k)], out)
    elif isinstance(obj, list):
        out.append((tuple(path + ['__len__']), len(obj)))
        for i, v in enumerate(obj):
            walk(v, path + [str(i)], out)
    else:
        out.append((tuple(path), obj))


def typename(v):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'bool'
    if isinstance(v, int):
        return 'int'
    if isinstance(v, float):
        return 'float'
    if isinstance(v, str):
        return 'str'
    return type(v).__name__


def main():
    pa, pb = sys.argv[1], sys.argv[2]
    with open(pa, 'r', encoding='utf-8') as f:
        a = json.load(f)
    with open(pb, 'r', encoding='utf-8') as f:
        b = json.load(f)
    la, lb = [], []
    walk(a, [], la)
    walk(b, [], lb)
    da = dict(la)
    db = dict(lb)
    keys_a = set(da.keys())
    keys_b = set(db.keys())
    only_a = sorted(keys_a - keys_b)
    only_b = sorted(keys_b - keys_a)
    common = sorted(keys_a & keys_b)
    diffs = []
    for k in common:
        va, vb = da[k], db[k]
        if typename(va) != typename(vb):
            diffs.append('%s: TYPE %s vs %s' % ('.'.join(k), typename(va), typename(vb)))
        elif va != vb:
            diffs.append('%s: %r vs %r' % ('.'.join(k), va, vb))
    print('LOADED a=%s b=%s' % (pa, pb))
    print('TOP_KEYS_EQ=%s' % (sorted(a.keys()) == sorted(b.keys())))
    print('LEAF_COUNT_A=%d LEAF_COUNT_B=%d COMMON=%d' % (len(la), len(lb), len(common)))
    print('ONLY_IN_A=%d ONLY_IN_B=%d' % (len(only_a), len(only_b)))
    for k in only_a:
        print('ONLY_A %s = %r' % ('.'.join(k), da[k]))
    for k in only_b:
        print('ONLY_B %s = %r' % ('.'.join(k), db[k]))
    print('LEAF_DIFF=%d' % len(diffs))
    for d in diffs:
        print('DIFF %s' % d)
    with open(pa, 'r', encoding='utf-8', errors='replace') as fa, \
         open(pb, 'r', encoding='utf-8', errors='replace') as fb:
        ta = fa.readlines()
        tb = fb.readlines()
    dl = list(difflib.unified_diff(ta, tb, fromfile='a', tofile='b', n=0))
    print('DIFFLIB_HUNKS=%d' % len(dl))
    for line in dl[:10]:
        print('UDIFF %s' % line.rstrip('\n'))
    if not diffs and not only_a and not only_b and len(la) == len(lb):
        print('VERDICT=BITIDENTICAL')
    else:
        print('VERDICT=DIFF')


if __name__ == '__main__':
    main()
