#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t3_anchor_sentinel v1.0 — 判读器输出锚点校验哨兵（T3 单元 3，任务书 v11.1，2026-10-10）

防"列语义勘误类事故"复发（T2 C-6：三臂判读表第 4 数值列实为 maxjump 而非 j0_end，曾被按
j0_end 消费）。机制：判读器输出 CSV 消费前，对冻结正源锚点（表类型:锚行:列:期望值）机械校验；
任何锚点失配/列缺失/锚行缺失 → RC=1 并逐条报错；全中 → RC=0。
列语义防线设计：锚行内 j0_end 与 maxjump 相差 1~3 个数量级（0.0143 vs 55.041；4.5462 vs
0.740），列序错乱/语义漂移必然爆锚；跨表锚（j0d.j0_total 与 combo.j0 同锚 HVNET1）互证。

锚点正源 = t3_results 20261009 冻结表：
  j0d_stats_20261009b.csv / combo_matrix_20261009_rounds.csv / three_arm_verdict_view_20261009.csv

用法：
  python3 t3_anchor_sentinel.py --table <csv> [--table <csv> ...]   # 校验给定表（按表头签名自动识别）
  python3 t3_anchor_sentinel.py --selftest                          # 内置正例+负例四件
  python3 t3_anchor_sentinel.py --list                              # 打印锚点表
RC：0=全中/自测全过；1=锚点失配或自测负例未如期爆；2=表无法识别/正源不可读
"""
import argparse
import csv
import io
import os
import sys

ABS_TOL = 1e-3  # 同表同值重出的紧容差；超过即视为语义变化

# (类型, 期望值, 描述)；f=浮点(容差比对) i=整数 s=字符串(精确)
SIGNATURES = {
    'j0d':      {'round', 'machine', 'boot', 'arm', 'cat', 'j0_total', 'jump_m',
                 'transit_m', 'jump_frac', 'n_jump', 'dominant', 'n_prop'},
    'combo':    {'round', 'date', 'machine', 'result', 'j0', 'j0d_jump',
                 'j0d_transit', 'j0d_dom', 'judge_site'},
    'threearm': {'tag', 'src', 'arm', 'op', 'delta', 'rep', 'material', 'alive',
                 'j0_end', 'maxjump', 'jump_t', 'njumps'},
}

ANCHORS = {
    'j0d': {
        'key_col': 'round',
        'rows': {
            'run_X4_1e_HVNET1_040009': {
                'j0_total':  ('f', 4.1185, 'HVNET1 悬停 j0 锚(在线域正源)'),
                'jump_m':    ('f', 0.4089, '同行 jump 分量'),
                'transit_m': ('f', 3.7189, '同行 transit 分量(j0=jump+transit 加性互证)'),
                'n_jump':    ('i', 4,      '同行跳变事件数'),
                'dominant':  ('s', 'transit', '同行主导分型'),
            },
        },
    },
    'combo': {
        'key_col': 'round',
        'rows': {
            'run_X4_1e_HVNET1_040009': {
                'j0':         ('f', 4.119,  'HVNET1 j0(与 j0d.j0_total=4.1185 跨表互证,四舍五入位)'),
                'result':     ('s', 'FAIL', '同轮判读结果'),
                'judge_site': ('s', '3090', '判读场地'),
            },
        },
    },
    'threearm': {
        'key_col': 'tag',
        'rows': {
            '3ARM_A_MA_d+10_r1_ta_3ARM_A_MA_d+10_r1_edited': {
                'j0_end':  ('f', 0.0143, 'MA 跳变族标本终态(T2 C-6 事故表:曾被误当 maxjump 消费)'),
                'maxjump': ('f', 55.041, 'MA 标本最大跳(与 j0_end 差 3 个数量级=列语义探针)'),
                'jump_t':  ('f', 104.5,  '最大跳时刻'),
                'njumps':  ('i', 11,     '跳变事件数(δ≥5ms 逐位收敛态)'),
            },
            '3ARM_base_MB_r1': {
                'j0_end':  ('f', 4.5462, 'MB 慢漂族基线标本终态(≈4.5m 带,任务书锚点)'),
                'maxjump': ('f', 0.740,  '同行 maxjump(慢漂族=小跳大终态,与 MA 标本互补探针)'),
                'njumps':  ('i', 0,      '慢漂族零跳事件'),
            },
        },
    },
}


def detect_table_type(header):
    hdr = set(header)
    matched = [t for t, sig in SIGNATURES.items() if sig <= hdr]
    if len(matched) == 1:
        return matched[0]
    return None


def check_cell(kind, expect, got):
    """返回 None=通过；否则失配原因字符串。"""
    if kind == 's':
        return None if got == expect else 'str mismatch'
    if kind == 'i':
        try:
            return None if int(float(got)) == int(expect) else 'int mismatch'
        except (TypeError, ValueError):
            return 'not an int'
    if kind == 'f':
        try:
            v = float(got)
        except (TypeError, ValueError):
            return 'not a float'
        if abs(v - expect) <= ABS_TOL:
            return None
        return 'float drift'
    return 'unknown kind'


def verify_table(rows_iter, header):
    """rows_iter=csv 行迭代器(已含 header 上下文)。返回 (failures, n_rows, table_type)。"""
    ttype = detect_table_type(header)
    if ttype is None:
        return [('TABLE', 'unknown', '-', 'header signature unrecognized', ','.join(header[:6] + ['...']))], 0, None
    spec = ANCHORS[ttype]
    key_col = spec['key_col']
    if key_col not in header:
        return [('TABLE', ttype, key_col, 'key column missing', '')], 0, ttype
    failures = []
    n_rows = 0
    keyed = {}
    idx = {col: i for i, col in enumerate(header)}
    ki = idx[key_col]
    for r in rows_iter:
        n_rows += 1
        if ki >= len(r):
            continue
        k = r[ki]
        if k in spec['rows']:
            keyed[k] = {col: r[idx[col]] for col in spec['rows'][k] if col in idx and idx[col] < len(r)}
    for row_key, cells in spec['rows'].items():
        if row_key not in keyed:
            failures.append(('ROW', ttype, row_key, 'anchor row missing', ''))
            continue
        row = keyed[row_key]
        for col, (kind, expect, _desc) in cells.items():
            if col not in header:
                failures.append(('COL', ttype, row_key, 'column missing: %s' % col, ''))
                continue
            got = row.get(col)
            if got is None or got == '':
                failures.append(('CELL', ttype, row_key, 'col=%s empty' % col, ''))
                continue
            reason = check_cell(kind, expect, got)
            if reason is not None:
                failures.append(('CELL', ttype, row_key,
                                 'col=%s %s' % (col, reason),
                                 'expect=%r got=%r' % (expect, got)))
    return failures, n_rows, ttype


def run_table(path):
    print('[SENTINEL] table=%s' % path)
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                print('  FAIL empty file')
                return 1
            failures, n_rows, ttype = verify_table(reader, header)
    except OSError as e:
        print('  FAIL unreadable: %s' % e)
        return 2
    label = ttype if ttype else 'UNKNOWN'
    print('  type=%s rows=%d anchors=%d' % (label, n_rows,
          sum(len(c) for c in ANCHORS.get(ttype, {}).get('rows', {}).values())))
    for lvl, t, key, why, detail in failures:
        print('  MISS [%s] %s row=%s :: %s %s' % (lvl, t, key, why, detail))
    ok = not failures
    print('  -> %s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


def _csv_rows(text):
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    return header, list(reader)


def selftest(repo_results_dir):
    """正例=三正源表；负例=列交换/值漂移/行缺失。全部按期爆/按期过才 RC0。"""
    results = []

    def rec(name, expect_rc, got_rc):
        ok = (expect_rc == got_rc)
        results.append(ok)
        print('  [%s] %s expect_rc=%d got_rc=%d' % ('PASS' if ok else 'FAIL', name, expect_rc, got_rc))

    # S1 正例：三张冻结正源表
    srcs = {
        'j0d': 'j0d_stats_20261009b.csv',
        'combo': 'combo_matrix_20261009_rounds.csv',
        'threearm': 'three_arm_verdict_view_20261009.csv',
    }
    for t, fn in srcs.items():
        p = os.path.join(repo_results_dir, fn)
        if not os.path.exists(p):
            print('  FAIL selftest cannot read authoritative source: %s' % p)
            return 2
        rc = run_table(p)
        rec('S1 positive %s' % t, 0, rc)

    # S2 负例：三臂表 j0_end<->maxjump 列交换（T2 C-6 事故模式复现）
    with open(os.path.join(repo_results_dir, srcs['threearm']), encoding='utf-8-sig') as f:
        r = list(csv.reader(f))
    hdr, rows = r[0], r[1:]
    i0, im = hdr.index('j0_end'), hdr.index('maxjump')
    swapped = [hdr] + [row[:i0] + [row[im]] + row[i0 + 1:im] + [row[i0]] + row[im + 1:] for row in rows]
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\n').writerows(swapped)
    fl, n, t = verify_table(csv.reader(io.StringIO(buf.getvalue())), hdr)
    rec('S2 column-swap (C-6 replay) must FAIL', True, bool(fl))

    # S3 负例：j0d HVNET1 j0_total 值漂移
    with open(os.path.join(repo_results_dir, srcs['j0d']), encoding='utf-8-sig') as f:
        r = list(csv.reader(f))
    hdr, rows = r[0], r[1:]
    ij = hdr.index('j0_total')
    drifted = [hdr]
    for row in rows:
        if row[0] == 'run_X4_1e_HVNET1_040009':
            row = row[:ij] + ['4.9000'] + row[ij + 1:]
        drifted.append(row)
    fl, n, t = verify_table(csv.reader(io.StringIO(
        '\n'.join(','.join(x) for x in drifted))), hdr)
    rec('S3 value drift must FAIL', True, bool(fl))

    # S4 负例：锚行缺失
    reduced = [hdr] + [row for row in rows if row[0] != 'run_X4_1e_HVNET1_040009']
    fl, n, t = verify_table(csv.reader(io.StringIO(
        '\n'.join(','.join(x) for x in reduced))), hdr)
    rec('S4 anchor-row missing must FAIL', True, bool(fl))

    # S5 表类型未识别
    fl, n, t = verify_table(csv.reader(io.StringIO('a,b,c\n1,2,3')), ['a', 'b', 'c'])
    rec('S5 unknown header must FAIL', True, bool(fl))

    all_ok = all(results)
    print('  SELFTEST -> %s (%d/%d)' % ('PASS' if all_ok else 'FAIL', sum(results), len(results)))
    return 0 if all_ok else 1


def list_anchors():
    for t, spec in ANCHORS.items():
        print('[%s] key=%s' % (t, spec['key_col']))
        for row_key, cells in spec['rows'].items():
            for col, (kind, expect, desc) in cells.items():
                print('  %-55s %-10s %-4s %10r  # %s' % (row_key, col, kind, expect, desc))


def main():
    ap = argparse.ArgumentParser(description='T3 anchor sentinel v1.0')
    ap.add_argument('--table', action='append', default=[], help='CSV to verify (repeatable)')
    ap.add_argument('--selftest', action='store_true', help='run built-in selftest')
    ap.add_argument('--repo-results', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 't3_results'),
        help='repo t3_results dir for selftest authoritative sources')
    ap.add_argument('--list', action='store_true', help='print anchor table')
    args = ap.parse_args()

    if args.list:
        list_anchors()
        return 0
    if args.selftest:
        print('[SENTINEL] selftest mode, repo_results=%s' % args.repo_results)
        return selftest(args.repo_results)
    if not args.table:
        print('[SENTINEL] nothing to do (give --table or --selftest or --list)', file=sys.stderr)
        return 2
    rc_final = 0
    for p in args.table:
        rc = run_table(p)
        rc_final = max(rc_final, rc)
    return rc_final


if __name__ == '__main__':
    sys.exit(main())
